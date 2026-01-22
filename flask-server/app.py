from flask import Flask, request, jsonify
from flask_cors import CORS
import happybase
import json
import time
import uuid
import datetime

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
HBASE_HOST = '10.47.246.170'  # YOUR SERVER IP
HBASE_PORT = 9090
TABLE_STUDENTS = 'students'
TABLE_LOGS = 'system_logs'

def get_db(table_name, retry=True):
    try:
        connection = happybase.Connection(
            HBASE_HOST, port=HBASE_PORT, timeout=5000, 
            transport='buffered', protocol='binary', autoconnect=True
        )
        tables = connection.tables()
        
        # Enable Versioning for History
        if TABLE_STUDENTS.encode() not in tables:
            connection.create_table(TABLE_STUDENTS, {
                'info': dict(), 
                'academic': {'max_versions': 5}
            })
        if TABLE_LOGS.encode() not in tables:
            connection.create_table(TABLE_LOGS, {'details': dict()})
            
        return connection, connection.table(table_name)
    except Exception as e:
        print(f"⚠️ DB Connect Error: {e}")
        if retry:
            time.sleep(1)
            return get_db(table_name, retry=False)
        return None, None

def log_action(action, details):
    conn, table = get_db(TABLE_LOGS)
    if not table: return
    try:
        timestamp = str(int(time.time() * 1000))
        row_key = f"{timestamp}_{uuid.uuid4().hex[:8]}"
        table.put(row_key.encode(), {
            b'details:action': action.encode(),
            b'details:info': details.encode(),
            b'details:time': timestamp.encode()
        })
    finally:
        if conn: conn.close()

# --- MATH LOGIC (UPDATED) ---
def get_grade_letter(score):
    """Converts numeric score to Letter Grade."""
    try:
        s = float(score)
        if s >= 70: return 'A', 5
        if s >= 60: return 'B', 4
        if s >= 50: return 'C', 3
        if s >= 45: return 'D', 2
        return 'F', 0
    except:
        return 'F', 0

def calculate_gpa_data(courses):
    """Calculates GPA and populates Letter Grades."""
    total_points = 0
    total_units = 0
    processed_courses = []

    for course in courses:
        # Get score and unit
        score = course.get('score', 0)
        unit = int(course.get('unit', 3))
        
        # Calculate Grade & Point
        letter, point = get_grade_letter(score)
        
        # Inject Letter Grade into the course object!
        course['grade'] = letter 
        
        total_points += (point * unit)
        total_units += unit
        processed_courses.append(course)

    if total_units == 0:
        return "0.00", processed_courses
    
    gpa = total_points / total_units
    return "{:.2f}".format(gpa), processed_courses

def calculate_cumulative(history):
    total_points = 0
    total_units = 0
    for semester in history:
        for course in semester.get('courses', []):
            try:
                score = course.get('score', 0)
                unit = int(course.get('unit', 3))
                _, point = get_grade_letter(score)
                
                total_points += (point * unit)
                total_units += unit
            except: continue

    if total_units == 0: return "0.00"
    return "{:.2f}".format(total_points / total_units)

# --- ROUTES ---

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if data.get('passcode') == 'admin123':
        log_action("ADMIN_LOGIN", "Admin accessed the dashboard")
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Invalid Passcode'}), 401

@app.route('/api/students', methods=['GET'])
def get_all_students():
    conn, table = get_db(TABLE_STUDENTS)
    if not table: return jsonify([]), 500
    students = []
    try:
        for key, data in table.scan(limit=100):
            students.append({
                'matricNumber': key.decode('utf-8'),
                'name': data.get(b'info:name', b'').decode('utf-8'),
                'department': data.get(b'info:dept', b'').decode('utf-8'),
                'cgpa': data.get(b'info:cgpa', b'0.00').decode('utf-8')
            })
    finally:
        if conn: conn.close()
    return jsonify(students)

@app.route('/api/results/<matric>', methods=['GET'])
def get_student(matric):
    if matric == 'SEED001': return jsonify({'matricNumber': 'SEED001', 'name': 'System Check', 'cgpa': '5.00'})
    conn, table = get_db(TABLE_STUDENTS)
    try:
        row = table.row(matric.encode())
        if not row: return jsonify({'error': 'Student not found'}), 404
        academic_json = row.get(b'academic:history', b'[]').decode('utf-8')
        return jsonify({
            'matricNumber': matric,
            'name': row.get(b'info:name', b'').decode('utf-8'),
            'department': row.get(b'info:dept', b'').decode('utf-8'),
            'cgpa': row.get(b'info:cgpa', b'0.00').decode('utf-8'),
            'academicHistory': json.loads(academic_json)
        })
    finally:
        if conn: conn.close()

@app.route('/api/history/<matric>', methods=['GET'])
def get_student_history(matric):
    conn, table = get_db(TABLE_STUDENTS)
    try:
        cells = table.cells(matric.encode(), b'academic:history', versions=5)
        history_log = []
        for value, timestamp in cells:
            dt_object = datetime.datetime.fromtimestamp(timestamp / 1000)
            date_str = dt_object.strftime('%Y-%m-%d %H:%M:%S')
            data = json.loads(value.decode('utf-8'))
            last_action = "Result Update"
            if data:
                last_sem = data[-1]
                last_action = f"Uploaded {last_sem.get('level')} Lvl {last_sem.get('semester')} Sem"
            history_log.append({'timestamp': date_str, 'action': last_action, 'total_semesters': len(data)})
        return jsonify(history_log)
    except Exception as e:
        return jsonify([])
    finally:
        if conn: conn.close()

@app.route('/api/results', methods=['POST'])
def save_result():
    data = request.json
    matric = data.get('matricNumber')
    conn, table = get_db(TABLE_STUDENTS)
    try:
        row = table.row(matric.encode())
        existing_json = row.get(b'academic:history', b'[]').decode('utf-8')
        history = json.loads(existing_json) if existing_json else []

        # 1. Calculate GPA & Inject Letter Grades into Courses
        raw_courses = data.get('courses', [])
        semester_gpa, processed_courses = calculate_gpa_data(raw_courses)

        new_sem = {
            'semester': data.get('semester', 'First'),
            'level': data.get('level', '100'),
            'courses': processed_courses, # Now contains 'grade': 'A'
            'gpa': semester_gpa           # Explicitly save Semester GPA
        }
        
        # 2. Update History
        history = [h for h in history if not (h['level'] == new_sem['level'] and h['semester'] == new_sem['semester'])]
        history.append(new_sem)
        
        # 3. Calculate CGPA
        new_cgpa = calculate_cumulative(history)

        # 4. Save
        table.put(matric.encode(), {
            b'info:name': data.get('name', '').encode(),
            b'info:dept': data.get('department', '').encode(),
            b'info:gpa': semester_gpa.encode(), # Save current GPA
            b'info:cgpa': new_cgpa.encode(),    # Save Cumulative
            b'academic:history': json.dumps(history).encode()
        })
        
        log_action("RESULT_UPLOAD", f"Updated result for {matric}")
        return jsonify({'success': True, 'gpa': semester_gpa, 'cgpa': new_cgpa})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/results/<matric>', methods=['DELETE'])
def delete_student(matric):
    if not matric or matric == 'undefined': return jsonify({'error': 'Invalid ID'}), 400
    conn, table = get_db(TABLE_STUDENTS)
    try:
        table.delete(matric.encode())
        log_action("DELETE_STUDENT", f"Deleted record: {matric}")
        return jsonify({'success': True})
    finally:
        if conn: conn.close()

@app.route('/api/logs', methods=['GET'])
def get_logs_route():
    conn, table = get_db(TABLE_LOGS)
    logs = []
    try:
        for key, data in table.scan(limit=50, reverse=True):
            logs.append({
                'id': key.decode('utf-8'),
                'action': data.get(b'details:action', b'').decode('utf-8'),
                'details': data.get(b'details:info', b'').decode('utf-8'),
                'timestamp': int(data.get(b'details:time', b'0').decode('utf-8'))
            })
    finally:
        if conn: conn.close()
    return jsonify(logs)

@app.route('/api/logs', methods=['DELETE'])
def clear_logs():
    conn, table = get_db(TABLE_LOGS)
    try:
        admin_conn = happybase.Connection(HBASE_HOST, port=HBASE_PORT)
        admin_conn.open()
        admin_conn.disable_table(TABLE_LOGS)
        admin_conn.delete_table(TABLE_LOGS)
        admin_conn.create_table(TABLE_LOGS, {'details': dict()})
        admin_conn.close()
        return jsonify({'success': True})
    finally:
        if conn: conn.close()
        
@app.route('/api/health', methods=['GET'])
def health_check():
    conn, table = get_db(TABLE_STUDENTS, retry=False) 
    if conn:
        conn.close()
        return jsonify({'status': 'online'}), 200
    return jsonify({'status': 'offline'}), 503

if __name__ == '__main__':
    print("🚀 Flask Server is running on port 5000...")
    app.run(port=5000, debug=True)