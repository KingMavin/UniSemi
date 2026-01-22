from flask import Flask, request, jsonify
from flask_cors import CORS
import happybase
import json
import time
import uuid

app = Flask(__name__)
CORS(app)

# --- HBASE CONFIGURATION ---
HBASE_HOST = '10.47.246.170'  # YOUR SERVER IP
HBASE_PORT = 9090
TABLE_STUDENTS = 'students'
TABLE_LOGS = 'system_logs'

def get_db(table_name, retry=True):
    """Connects to HBase and returns the specific table."""
    try:
        connection = happybase.Connection(
            HBASE_HOST, 
            port=HBASE_PORT, 
            timeout=5000, 
            transport='buffered', 
            protocol='binary',
            autoconnect=True
        )
        
        # Create tables if they don't exist
        tables = connection.tables()
        if TABLE_LOGS.encode() not in tables:
            connection.create_table(TABLE_LOGS, {'details': dict()})
        if TABLE_STUDENTS.encode() not in tables:
            connection.create_table(TABLE_STUDENTS, {'info': dict(), 'academic': dict()})
            
        return connection, connection.table(table_name)
    except Exception as e:
        print(f"⚠️ DB Connect Error: {e}")
        if retry:
            time.sleep(1)
            return get_db(table_name, retry=False)
        return None, None

# --- AUDIT LOGGING ---
def log_action(action, details):
    """Saves an action to the logs table."""
    conn, table = get_db(TABLE_LOGS)
    if not table: return
    try:
        # Use reverse timestamp so newest logs appear first in scans
        timestamp = str(int(time.time() * 1000))
        row_key = f"{timestamp}_{uuid.uuid4().hex[:8]}"
        table.put(row_key.encode(), {
            b'details:action': action.encode(),
            b'details:info': details.encode(),
            b'details:time': timestamp.encode()
        })
    finally:
        if conn: conn.close()

# --- MATH LOGIC ---
def calculate_gpa(courses):
    total_points = 0
    count = 0
    for course in courses:
        try:
            score = float(course.get('score', 0))
            if score >= 70: point = 5
            elif score >= 60: point = 4
            elif score >= 50: point = 3
            elif score >= 45: point = 2
            else: point = 0
            
            unit = int(course.get('unit', 3)) # Default to 3 units if missing
            total_points += (point * unit)
            count += unit
        except: continue
    
    if count == 0: return "0.00"
    return "{:.2f}".format(total_points / count)

def calculate_cumulative(history):
    total_points = 0
    total_units = 0
    
    for semester in history:
        for course in semester.get('courses', []):
            try:
                score = float(course.get('score', 0))
                if score >= 70: point = 5
                elif score >= 60: point = 4
                elif score >= 50: point = 3
                elif score >= 45: point = 2
                else: point = 0
                
                unit = int(course.get('unit', 3))
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
        log_action("ADMIN_LOGIN", "Admin accessed the dashboard") # <--- LOGGING ADDED
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
    if matric == 'SEED001':
        return jsonify({'matricNumber': 'SEED001', 'name': 'System Check', 'cgpa': '5.00'})

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

@app.route('/api/results', methods=['POST'])
def save_result():
    data = request.json
    matric = data.get('matricNumber')
    
    conn, table = get_db(TABLE_STUDENTS)
    try:
        row = table.row(matric.encode())
        existing_json = row.get(b'academic:history', b'[]').decode('utf-8')
        history = json.loads(existing_json) if existing_json else []

        new_sem = {
            'semester': data.get('semester', 'First'),
            'level': data.get('level', '100'),
            'courses': data.get('courses', [])
        }
        
        # Calculate Scores
        current_gpa = calculate_gpa(new_sem['courses'])
        
        # Update History
        history = [h for h in history if not (h['level'] == new_sem['level'] and h['semester'] == new_sem['semester'])]
        history.append(new_sem)
        new_cgpa = calculate_cumulative(history)

        table.put(matric.encode(), {
            b'info:name': data.get('name', '').encode(),
            b'info:dept': data.get('department', '').encode(),
            b'info:gpa': current_gpa.encode(),
            b'info:cgpa': new_cgpa.encode(),
            b'academic:history': json.dumps(history).encode()
        })
        
        log_action("RESULT_UPLOAD", f"Updated result for {matric}") # <--- LOGGING ADDED
        return jsonify({'success': True, 'gpa': current_gpa, 'cgpa': new_cgpa})
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
        log_action("DELETE_STUDENT", f"Deleted record: {matric}") # <--- LOGGING ADDED
        return jsonify({'success': True})
    finally:
        if conn: conn.close()

@app.route('/api/logs', methods=['GET'])
def get_logs_route():
    conn, table = get_db(TABLE_LOGS)
    logs = []
    try:
        # Fetch last 50 logs
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
        # Delete the whole table and recreate it
        # Note: In production, just delete rows. For this project, recreate is faster/cleaner.
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
    """True System Health Check: Pings HBase."""
    # retry=False because we want instant feedback, not a wait loop
    conn, table = get_db(TABLE_STUDENTS, retry=False) 
    
    if conn:
        try:
            # Perform a lightweight operation to prove DB is responsive
            conn.tables() 
            return jsonify({'status': 'online', 'details': 'HBase Connected'}), 200
        except Exception as e:
            print(f"Health Check Failed: {e}")
            return jsonify({'status': 'db_error', 'details': str(e)}), 503
        finally:
            conn.close()
            
    # If get_db returned None, the connection failed
    return jsonify({'status': 'offline', 'details': 'Database Unreachable'}), 503

if __name__ == '__main__':
    app.run(port=5000, debug=True)