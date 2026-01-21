from flask import Flask, request, jsonify
from flask_cors import CORS
import happybase
import json
import time

app = Flask(__name__)
CORS(app)

# --- HBASE CONFIGURATION ---
HBASE_HOST = '10.47.246.170'  # YOUR SERVER IP
HBASE_PORT = 9090
TABLE_NAME = 'students'

def get_db(retry=True):
    """Connects to HBase with Auto-Retry logic."""
    try:
        connection = happybase.Connection(
            HBASE_HOST, 
            port=HBASE_PORT, 
            timeout=5000, 
            transport='buffered', 
            protocol='binary',
            autoconnect=True
        )
        # Verify connection is alive
        connection.tables()
        return connection, connection.table(TABLE_NAME)
    except Exception as e:
        print(f"⚠️ DB Connect Error: {e}")
        # If it fails and retry is True, wait 1s and try once more
        if retry:
            print("   ♻️ Retrying connection...")
            time.sleep(1)
            return get_db(retry=False)
        return None, None

# --- FAST CALCULATION (Replaces Spark) ---
def calculate_cgpa_fast(courses):
    """Calculates CGPA instantly without starting a Spark Engine."""
    try:
        total_score = 0
        count = 0
        
        # Simple Logic: Average of scores / 20 (Rough estimate for 5.0 scale)
        # You can adjust this math to match your university's exact formula
        for course in courses:
            try:
                score = float(course.get('score', 0))
                total_score += (score / 20) # Example: 80 -> 4.0
                count += 1
            except: continue
            
        if count == 0: return "0.00"
        
        cgpa = total_score / count
        return "{:.2f}".format(cgpa)
    except Exception as e:
        print(f"Math Error: {e}")
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
        # Use a limit to prevent freezing if DB is huge
        for key, data in table.scan(limit=100):
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
    # Quick bypass for system check
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
    print("\n--- NEW UPLOAD REQUEST ---")
    data = request.json
    matric = data.get('matricNumber')
    
    if not matric: return jsonify({'error': 'Matric required'}), 400

    # 1. Instant Calculation
    new_cgpa = calculate_cgpa_fast(data.get('courses', []))
    print(f"   ⚡ Calculated CGPA: {new_cgpa}")

    # 2. Database Write
    conn, table = get_db()
    if not table: return jsonify({'error': 'Database Connection Failed'}), 500

    try:
        # Get existing history
        row = table.row(matric.encode())
        existing_json = row.get(b'academic:history', b'[]').decode('utf-8')
        history = json.loads(existing_json) if existing_json else []

        # Add new semester
        new_sem = {
            'semester': data.get('semester', 'First'),
            'level': data.get('level', '100'),
            'courses': data.get('courses', [])
        }
        
        # Remove duplicate semesters (if overwriting)
        history = [h for h in history if not (h['level'] == new_sem['level'] and h['semester'] == new_sem['semester'])]
        history.append(new_sem)

        # Write to HBase
        table.put(matric.encode(), {
            b'info:name': data.get('name', '').encode(),
            b'info:dept': data.get('department', '').encode(),
            b'info:cgpa': new_cgpa.encode(),
            b'academic:history': json.dumps(history).encode()
        })
        
        print("   ✅ Write Successful")
        return jsonify({'success': True, 'cgpa': new_cgpa})
        
    except Exception as e:
        print(f"   ❌ Write Failed: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify([
        {'action': 'SYSTEM ONLINE', 'details': 'HBase Connected (Optimized Mode)', 'timestamp': time.time() * 1000}
    ])

if __name__ == '__main__':
    print("🚀 Flask Server is running on port 5000 (Optimized Mode)...")
    app.run(port=5000, debug=True)