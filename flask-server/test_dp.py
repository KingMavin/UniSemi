import sys
import socket
import subprocess
import happybase
import json
import time

# --- CONFIGURATION ---
SERVER_IP = '10.47.246.170'  # Ensure this matches your Server IP
SERVER_PORT = 9090
TABLE_NAME = 'students'     # The actual table your app uses

# Dummy Data (Exactly what your React app sends)
DUMMY_MATRIC = 'EMULATION_001'
DUMMY_DATA = {
    b'info:name': b'Test Student',
    b'info:dept': b'Computer Science',
    b'info:cgpa': b'4.50',
    b'academic:history': json.dumps([
        {'level': '100', 'semester': 'First', 'courses': [{'code': 'CSC101', 'score': 90}]}
    ]).encode()
}

def print_header(title):
    print(f"\n{'='*60}")
    print(f"   {title}")
    print(f"{'='*60}")

def test_ping():
    print_header("STEP 1: NETWORK CHECK (PING)")
    try:
        # -n 1 sends 1 ping, -w 1000 sets 1s timeout
        output = subprocess.run(['ping', '-n', '1', '-w', '1000', SERVER_IP], capture_output=True, text=True)
        if output.returncode == 0:
            print(f"✅ Ping Successful! Server {SERVER_IP} is reachable.")
            return True
        else:
            print(f"❌ Ping Failed. Your laptop cannot see {SERVER_IP}.")
            print("   -> Check if both are on the same Wi-Fi.")
            return False
    except Exception as e:
        print(f"❌ Execution Error: {e}")
        return False

def test_socket():
    print_header(f"STEP 2: PORT CHECK (TCP {SERVER_PORT})")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3) 
    try:
        result = sock.connect_ex((SERVER_IP, SERVER_PORT))
        if result == 0:
            print(f"✅ Port {SERVER_PORT} is OPEN. The Firewall allows connection.")
            sock.close()
            return True
        else:
            print(f"❌ Port {SERVER_PORT} is BLOCKED (Error Code: {result}).")
            print("   -> Windows Firewall on the Server is likely blocking this.")
            return False
    except Exception as e:
        print(f"❌ Error checking port: {e}")
        return False

def attempt_upload(protocol_name):
    print_header(f"STEP 3: UPLOAD SIMULATION ({protocol_name.upper()})")
    print(f"📡 Attempting connection using transport='{protocol_name}'...")
    
    connection = None
    try:
        # 1. Connect
        start_time = time.time()
        connection = happybase.Connection(
            SERVER_IP, 
            port=SERVER_PORT, 
            timeout=5000, # 5 second timeout
            transport=protocol_name,
            protocol='binary'
        )
        connection.open()
        
        # 2. Check Table
        print("   -> Connection open. Checking tables...")
        tables = connection.tables()
        if TABLE_NAME.encode() not in tables:
            print(f"   ⚠️ Table '{TABLE_NAME}' missing. Creating it...")
            connection.create_table(TABLE_NAME, {'info': dict(), 'academic': dict()})
        
        # 3. Write Data (The Simulation)
        print(f"   -> Uploading student result for {DUMMY_MATRIC}...")
        table = connection.table(TABLE_NAME)
        table.put(DUMMY_MATRIC.encode(), DUMMY_DATA)
        
        # 4. Read Data Back (Verification)
        print("   -> Verifying upload...")
        row = table.row(DUMMY_MATRIC.encode())
        
        # 5. Clean up (Delete dummy data)
        table.delete(DUMMY_MATRIC.encode())
        
        duration = round(time.time() - start_time, 2)
        
        if row:
            print(f"\n🎉 SUCCESS! Protocol '{protocol_name}' works perfectly.")
            print(f"   Time taken: {duration} seconds")
            return True
        else:
            print(f"\n❌ FAILURE: Data was written but could not be read back.")
            return False

    except Exception as e:
        print(f"\n❌ FAILED with error: {e}")
        return False
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    # 1. Basic Checks
    if not test_ping():
        sys.exit(1)
    if not test_socket():
        sys.exit(1)

    # 2. Test Both Protocols independently
    buffered_result = attempt_upload('buffered')
    framed_result = attempt_upload('framed')

    # 3. Final Recommendation
    print_header("FINAL DIAGNOSIS")
    if buffered_result:
        print("✅ RECOMMENDATION: Use transport='buffered' in your app.py")
    elif framed_result:
        print("✅ RECOMMENDATION: Use transport='framed' in your app.py")
    else:
        print("❌ CRITICAL: Both protocols failed.")
        print("   -> If Port Check passed, the HBase RegionServer inside Docker is crashed.")
        print("   -> Restart Docker on the Server.")