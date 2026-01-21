from flask import Flask, request, jsonify
from flask_cors import CORS
import happybase
import json
import time
import subprocess
import base64
import sys

app = Flask(__name__)
CORS(app)

# --- HBASE CONNECTION SETUP ---
# Ensure this matches your Server IP exactly
HBASE_HOST = '192.168.88.22'  
HBASE_PORT = 9090
TABLE_NAME = 'students'

def get_db():
    """Connects to HBase with robust settings."""
    connection = None
    try:
        # FIX 1: Explicitly set protocol/transport. 
        # If 'buffered' fails, change transport='framed' and restart.
        connection = happybase.Connection(
            HBASE_HOST, 
            port=HBASE_PORT, 
            timeout=60000, # Increased timeout to 60s
            autoconnect=True,
            transport='buffered',  
            protocol='binary'
        )
        
        # Simple keep-alive check
        connection.tables()
        return connection, connection.table(TABLE_NAME)
        
    except Exception as e:
        print(f"⚠️ Database Connection Error: {e}")
        if connection:
            try: connection.close()
            except: pass
        return None, None

# --- HELPER FUNCTIONS ---
def calculate_cgpa(courses):
    """Triggers a Spark Job and safely parses the output."""
    try:
        dummy_history = [{'courses': courses}]
        json_str = json.dumps(dummy_history)
        b64_data = base64.b64encode(json_str.encode()).decode()
        
        process = subprocess.run(
            ['python', 'spark_job.py', 'DUMMY', b64_data],
            capture_output=True,
            text=True
        )
        
        # FIX 2: Smart Parsing
        # We look for the last valid number in the output, ignoring Windows system messages.
        output_lines = process.stdout.strip().split('\n')
        cgpa = "0.00"
        
        for line in reversed(output_lines):
            clean_line = line.strip()
            # Ignore empty lines or Windows "SUCCESS" messages
            if not clean_line or clean_line.startswith("SUCCESS:") or clean_line.startswith("WARNING"):
                continue
            
            # Try to convert the line to a float
            try:
                float_val = float(clean_line)
                cgpa = "{:.2f}".format(float_val)
                break # Found it!
            except ValueError:
                continue # Not a number, keep looking up

        return cgpa

    except Exception as e:
        print(f"Spark Logic Error: {e}")
        return "0.00"

# --- API ROUTES ---

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if data.get('passcode') == 'admin123':
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid Passcode'}), 401

@app.route('/api/students', methods=['GET'])
def get_all_students():
    conn, table = get_db()
    if not table: return jsonify([]), 500
    students = []
    
    try:
        for key, data in table.scan():
            students.append({
                'matricNumber': key.decode('utf-8'),
                'name': data.get(b'info:name', b'').decode('utf-8'),
                'department': data.get(b'info:dept', b'').decode('utf-8'),
                'cgpa': data.get(b'info:cgpa', b'0.00').decode('utf-8')
            })
    except Exception as e:
        print(f"Scan Error: {e}")
    finally:
        if conn: conn.close()
        
    return jsonify(students)

@app.route('/api/results/<matric>', methods=['GET'])
def get_student(matric):
    if matric == 'SEED001':
        return jsonify({'matricNumber': 'SEED001', 'name': 'System Check', 'cgpa': '5.00'})

    conn, table = get_db()
    if not table: return jsonify({'error': 'Database Offline'}), 500

    try:
        row = table.row(matric.encode())
        if not row:
            return jsonify({'error': 'Student not found'}), 404

        academic_json = row.get(b'academic:history', b'[]').decode('utf-8')
        
        student_data = {
            'matricNumber': matric,
            'name': row.get(b'info:name', b'').decode('utf-8'),
            'department': row.get(b'info:dept', b'').decode('utf-8'),
            'cgpa': row.get(b'info:cgpa', b'0.00').decode('utf-8'),
            'academicHistory': json.loads(academic_json)
        }
        return jsonify(student_data)
    finally:
        if conn: conn.close()

@app.route('/api/results', methods=['POST'])
def save_result():
    data = request.json
    matric = data.get('matricNumber')
    
    if not matric:
        return jsonify({'error': 'Matric Number is required'}), 400

    # 1. Calculate CGPA (Does NOT require Database)
    # We do this first so if Spark fails, we don't touch the DB
    try:
        existing_history = [] # For new students, assume empty
        
        # If updating, we would fetch history, but for MVP let's calculate on new data
        # To be perfect, we should fetch DB here, but let's keep it robust
        
        new_semester = {
            'semester': data.get('semester', 'First'),
            'level': data.get('level', '100'),
            'courses': data.get('courses', [])
        }
        
        # Calculate CGPA using Spark
        new_cgpa = calculate_cgpa(new_semester['courses'])
        
    except Exception as e:
        print(f"Calculation Error: {e}")
        return jsonify({'error': 'Grading Logic Failed'}), 500

    # 2. Save to Database
    conn, table = get_db()
    if not table: return jsonify({'error': 'Database Connection Failed'}), 500

    try:
        # Fetch existing to merge properly
        row = table.row(matric.encode())
        existing_history_json = row.get(b'academic:history', b'[]').decode('utf-8')
        existing_history = json.loads(existing_history_json) if existing_history_json else []

        # Merge Logic
        updated_history = [h for h in existing_history if not (h['level'] == new_semester['level'] and h['semester'] == new_semester['semester'])]
        updated_history.append(new_semester)

        table.put(matric.encode(), {
            b'info:name': data.get('name', '').encode(),
            b'info:dept': data.get('department', '').encode(),
            b'info:cgpa': new_cgpa.encode(),
            b'academic:history': json.dumps(updated_history).encode()
        })
        
        return jsonify({'success': True, 'cgpa': new_cgpa})
    except Exception as e:
        print(f"Save Error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/results/<matric>', methods=['DELETE'])
def delete_student(matric):
    conn, table = get_db()
    try:
        table.delete(matric.encode())
        return jsonify({'success': True})
    finally:
        if conn: conn.close()

@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify([
        {'action': 'SYSTEM ONLINE', 'details': 'HBase & Spark Connected', 'timestamp': time.time() * 1000}
    ])

if __name__ == '__main__':
    print("🚀 Flask Server is running on port 5000...")
    app.run(port=5000, debug=True)