from flask import Flask, request, jsonify
from flask_cors import CORS
import happybase
import json
import time

app = Flask(__name__)
CORS(app)

# --- HBASE CONFIGURATION ---
HBASE_HOST = '10.47.246.170'  # Ensure this matches your Server IP
HBASE_PORT = 9090
TABLE_NAME = 'students'

def get_db(retry=True):
    """Connects to HBase with Auto-Retry."""
    try:
        connection = happybase.Connection(
            HBASE_HOST, 
            port=HBASE_PORT, 
            timeout=5000, 
            transport='buffered', 
            protocol='binary',
            autoconnect=True
        )
        connection.tables() # Keep-alive check
        return connection, connection.table(TABLE_NAME)
    except Exception as e:
        print(f"⚠️ DB Connect Error: {e}")
        if retry:
            time.sleep(1)
            return get_db(retry=False)
        return None, None

# --- MATH LOGIC ---
def calculate_gpa(courses):
    """Calculates GPA for a SINGLE semester."""
    total_points = 0
    count = 0
    for course in courses:
        try:
            score = float(course.get('score', 0))
            # Formula: Score / 20 (e.g., 60 -> 3.0, 80 -> 4.0)
            total_points += (score / 20) 
            count += 1
        except: continue
    
    if count == 0: return "0.00"
    return "{:.2f}".format(total_points / count)

def calculate_cumulative(history):
    """Calculates CGPA across ALL semesters."""
    total_points = 0
    total_courses = 0
    
    for semester in history:
        for course in semester.get('courses', []):
            try:
                score = float(course.get('score', 0))
                total_points += (score / 20)
                total_courses += 1
            except: continue

    if total_courses == 0: return "0.00"
    return "{:.2f}".format(total_points / total_courses)

# --- API ROUTES ---

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if data.get('passcode') == 'admin123':
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Invalid Passcode'}), 401

@app.route('/api/students', methods=['GET'])
def get_all_students():
    conn, table = get_db()
    if not table: return jsonify([]), 500
    students = []
    
    try:
        for key, data in table.scan(limit=100):
            # We assume the key is the Matric Number
            students.append({
                'matricNumber': key.decode('utf-8'),
                'name': data.get(b'info:name', b'').decode('utf-8'),
                'department': data.get(b'info:dept', b'').decode('utf-8'),
                'gpa': data.get(b'info:gpa', b'0.00').decode('utf-8'),   # Current Sem
                'cgpa': data.get(b'info:cgpa', b'0.00').decode('utf-8') # Cumulative
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
        if not row: return jsonify({'error': 'Student not found'}), 404

        academic_json = row.get(b'academic:history', b'[]').decode('utf-8')
        
        return jsonify({
            'matricNumber': matric,
            'name': row.get(b'info:name', b'').decode('utf-8'),
            'department': row.get(b'info:dept', b'').decode('utf-8'),
            'gpa': row.get(b'info:gpa', b'0.00').decode('utf-8'),
            'cgpa': row.get(b'info:cgpa', b'0.00').decode('utf-8'),
            'academicHistory': json.loads(academic_json)
        })
    finally:
        if conn: conn.close()

@app.route('/api/results', methods=['POST'])
def save_result():
    data = request.json
    matric = data.get('matricNumber')
    if not matric: return jsonify({'error': 'Matric required'}), 400

    conn, table = get_db()
    if not table: return jsonify({'error': 'Database Connection Failed'}), 500

    try:
        # 1. Fetch Existing History
        row = table.row(matric.encode())
        existing_json = row.get(b'academic:history', b'[]').decode('utf-8')
        history = json.loads(existing_json) if existing_json else []

        # 2. Process New Semester
        new_sem = {
            'semester': data.get('semester', 'First'),
            'level': data.get('level', '100'),
            'courses': data.get('courses', [])
        }
        
        # 3. Calculate GPA (Just this semester)
        current_gpa = calculate_gpa(new_sem['courses'])

        # 4. Merge History (Overwrite if level/semester matches)
        history = [h for h in history if not (h['level'] == new_sem['level'] and h['semester'] == new_sem['semester'])]
        history.append(new_sem)

        # 5. Calculate CGPA (All semesters combined)
        new_cgpa = calculate_cumulative(history)

        # 6. Save
        table.put(matric.encode(), {
            b'info:name': data.get('name', '').encode(),
            b'info:dept': data.get('department', '').encode(),
            b'info:gpa': current_gpa.encode(),   
            b'info:cgpa': new_cgpa.encode(),     
            b'academic:history': json.dumps(history).encode()
        })
        
        return jsonify({'success': True, 'gpa': current_gpa, 'cgpa': new_cgpa})
    except Exception as e:
        print(f"Save Error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/results/<matric>', methods=['DELETE'])
def delete_student(matric):
    if not matric or matric == 'undefined':
        return jsonify({'error': 'Invalid Matric'}), 400
    
    conn, table = get_db()
    try:
        table.delete(matric.encode())
        return jsonify({'success': True})
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    print("🚀 Flask Server is running on port 5000...")
    app.run(port=5000, debug=True)