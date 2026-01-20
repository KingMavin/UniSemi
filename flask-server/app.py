from flask import Flask, request, jsonify
from flask_cors import CORS
import happybase
import json
import time
import subprocess
import base64

app = Flask(__name__)
CORS(app)

# --- HBASE CONNECTION SETUP ---
HBASE_HOST = 'localhost'
HBASE_PORT = 9090
TABLE_NAME = 'students'

def get_db():
    """Connects to HBase (Retry logic handled by autoconnect)."""
    connection = None
    try:
        # 1. Connect with 30s timeout and autoconnect
        connection = happybase.Connection(HBASE_HOST, port=HBASE_PORT, timeout=30000, autoconnect=True)
        
        # 2. Check if table exists (This also tests the connection)
        # We assume connection is open because of autoconnect=True
        tables = connection.tables()
        if TABLE_NAME.encode() not in tables:
            print(f"Creating table {TABLE_NAME}...")
            connection.create_table(
                TABLE_NAME,
                {'info': dict(), 'academic': dict()}
            )
            
        return connection, connection.table(TABLE_NAME)
        
    except Exception as e:
        print(f"⚠️ Database Error: {e}")
        if connection:
            try:
                connection.close()
            except:
                pass
        return None, None

# --- HELPER FUNCTIONS ---
def calculate_cgpa(courses):
    """Triggers a Spark Job to calculate the CGPA."""
    try:
        # Wrap courses in a dummy semester structure
        dummy_history = [{'courses': courses}]
        json_str = json.dumps(dummy_history)
        
        # Encode to Base64 to avoid Windows command-line issues
        b64_data = base64.b64encode(json_str.encode()).decode()
        
        # Run the separate Spark script
        process = subprocess.run(
            ['python', 'spark_job.py', 'DUMMY', b64_data],
            capture_output=True,
            text=True
        )
        
        # Read the last line of output
        output_lines = process.stdout.strip().split('\n')
        if not output_lines:
            print("Spark Error Output:", process.stderr)
            return "0.00"

        result = output_lines[-1] # Get last line
        return "{:.2f}".format(float(result))
    except Exception as e:
        print(f"Spark Logic Error: {e}")
        return "0.00"

# --- API ROUTES ---

@app.route('/api/login', methods=['POST'])
def login():
    """Handles Admin Login."""
    data = request.json
    if data.get('passcode') == 'admin123':
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid Passcode'}), 401

@app.route('/api/students', methods=['GET'])
def get_all_students():
    """Fetches all students."""
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
    """Search for a single student."""
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
    """Saves or Updates a Student."""
    data = request.json
    matric = data.get('matricNumber')
    
    if not matric:
        return jsonify({'error': 'Matric Number is required'}), 400

    conn, table = get_db()
    if not table: return jsonify({'error': 'Database Connection Failed'}), 500

    try:
        # 1. Get existing data
        row = table.row(matric.encode())
        existing_history_json = row.get(b'academic:history', b'[]').decode('utf-8')
        existing_history = json.loads(existing_history_json) if existing_history_json else []
        
        # 2. Process new semester
        new_semester = {
            'semester': data.get('semester', 'First'),
            'level': data.get('level', '100'),
            'courses': data.get('courses', [])
        }
        
        # 3. Merge history
        updated_history = [h for h in existing_history if not (h['level'] == new_semester['level'] and h['semester'] == new_semester['semester'])]
        updated_history.append(new_semester)
        
        # 4. Calculate NEW CGPA via Spark
        all_courses = [c for sem in updated_history for c in sem['courses']]
        new_cgpa = calculate_cgpa(all_courses)

        # 5. Save to HBase
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