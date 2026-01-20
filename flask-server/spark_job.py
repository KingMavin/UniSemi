import sys
import json
import base64  # <--- CRITICAL IMPORT
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ArrayType

def calculate_gpa_spark(matric_number, history_json):
    """
    Uses Apache Spark to calculate CGPA.
    In a real cluster, this would split the work across 100 computers.
    """
    # 1. Initialize Spark (Suppressing excessive logs)
    spark = SparkSession.builder \
        .appName("Student_CGPA_Processor") \
        .master("local[*]") \
        .config("spark.ui.showConsoleProgress", "false") \
        .getOrCreate()

    # Set log level to ERROR to keep output clean for our Python script to read
    spark.sparkContext.setLogLevel("ERROR")

    try:
        # 2. Convert JSON history into a Spark DataFrame
        # We flatten the structure: One row per course
        data = []
        try:
            history = json.loads(history_json)
        except json.JSONDecodeError:
            return 0.0
        
        for semester in history:
            for course in semester.get('courses', []):
                try:
                    data.append({
                        'score': int(course.get('score', 0)),
                        'unit': int(course.get('unit', 0))
                    })
                except:
                    continue

        if not data:
            return 0.0

        # Create DataFrame
        rdd = spark.sparkContext.parallelize(data)
        # Define schema explicitly to avoid inference overhead/errors on empty data
        schema = StructType([
            StructField("score", IntegerType(), True),
            StructField("unit", IntegerType(), True)
        ])
        df = spark.createDataFrame(rdd, schema)

        # 3. Define Grading Logic 
        def get_points(score):
            if score >= 70: return 5
            elif score >= 60: return 4
            elif score >= 50: return 3
            elif score >= 45: return 2
            else: return 0

        # Calculate Points locally for this small batch 
        total_units = 0
        total_points = 0
        
        rows = df.collect()
        for row in rows:
            u = row['unit']
            s = row['score']
            p = get_points(s)
            total_units += u
            total_points += (u * p)

        cgpa = total_points / total_units if total_units > 0 else 0.0
        return round(cgpa, 2)

    except Exception as e:
        # If Spark fails, we print to stderr so we can debug, but return 0.0 to app
        sys.stderr.write(f"Spark Job Error: {str(e)}\n")
        return 0.0
        
    finally:
        spark.stop()

if __name__ == "__main__":
    # Command Line Arguments: python spark_job.py [MATRIC] [BASE64_DATA]
    if len(sys.argv) > 2:
        matric = sys.argv[1]
        raw_data = sys.argv[2]
        
        try:
            # --- THE FIX: Decode Base64 back to JSON String ---
            history_json = base64.b64decode(raw_data).decode('utf-8')
            
            result = calculate_gpa_spark(matric, history_json)
            print(result) # Only print the number!
        except Exception as e:
            # Fallback
            print(0.0)