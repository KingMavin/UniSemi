import happybase
import time
import json
import random

# --- CONFIGURATION ---
HBASE_HOST = '10.47.246.170'  # YOUR SERVER IP
HBASE_PORT = 9090
TABLE_NAME = 'students'
TOTAL_STUDENTS = 100000  # Number of records to insert

def get_connection():
    try:
        return happybase.Connection(
            HBASE_HOST, 
            port=HBASE_PORT, 
            transport='buffered', 
            protocol='binary',
            timeout=10000
        )
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

def run_stress_test():
    print(f"🚀 STARTING STRESS TEST: {TOTAL_STUDENTS} Records target...")
    print(f"   Target Server: {HBASE_HOST}")
    
    conn = get_connection()
    if not conn: return

    try:
        table = conn.table(TABLE_NAME)
        
        # --- START TIMER ---
        start_time = time.time()
        print(f"   ⏱️  Timer Started at: {time.strftime('%H:%M:%S', time.localtime(start_time))}")

        # Use batch for speed (sends data in packets rather than 1 by 1)
        batch = table.batch()
        
        for i in range(TOTAL_STUDENTS):
            matric = f"STRESS-TEST-{i:04d}" # e.g., STRESS-TEST-0050
            
            # Randomize some data to make it realistic
            gpa = round(random.uniform(1.0, 5.0), 2)
            
            data = {
                b'info:name': f"Generated Student {i}".encode(),
                b'info:dept': b"Stress Analysis Dept",
                b'info:gpa': str(gpa).encode(),
                b'info:cgpa': str(gpa).encode(),
                b'academic:history': json.dumps([]).encode()
            }
            
            batch.put(matric.encode(), data)
            
            # Print a dot every 100 records so you know it's working
            if i > 0 and i % 100 == 0:
                print(".", end="", flush=True)

        # Send all remaining data
        batch.send()
        print(" Done!")

        # --- STOP TIMER ---
        end_time = time.time()
        
        # --- CALCULATE STATS ---
        duration = end_time - start_time
        speed = TOTAL_STUDENTS / duration

        print(f"\n{'='*40}")
        print(f"✅ STRESS TEST COMPLETED SUCCESSFULLY")
        print(f"{'='*40}")
        print(f"📊 Total Records : {TOTAL_STUDENTS}")
        print(f"⏱️  Time Taken    : {round(duration, 4)} seconds")
        print(f"🚀 Speed         : {int(speed)} records/second")
        print(f"{'='*40}")

    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_stress_test()