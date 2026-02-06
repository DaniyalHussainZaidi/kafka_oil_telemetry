import os
import glob
import json
import pandas as pd
import time
import sys
import socket
from datetime import datetime, timedelta
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic

# --- CONFIGURATION ---
DATA_FOLDER = os.environ.get('DATA_FOLDER', './data/0') 
BOOTSTRAP_SERVERS = os.environ.get('BOOTSTRAP_SERVERS', 'localhost:9092') 
TOPIC_NAME = 'well-sensors'
SIMULATION_DELAY = 0.05 

def wait_for_kafka(server_string):
    host, port = server_string.split(':')
    port = int(port)
    print(f"⏳ Connecting to Kafka at {host}:{port}...", end='')
    sys.stdout.flush()
    while True:
        try:
            socket.create_connection((host, port), timeout=2).close()
            print(f" ✅ Connected!")
            return
        except:
            print(".", end='')
            sys.stdout.flush()
            time.sleep(1)

# --- THE FIX: RESET TOPIC ---
def reset_topic(server_string):
    """Deletes the old topic and creates a fresh one to remove old DONE messages."""
    print(f"🧹 Resetting topic '{TOPIC_NAME}'...", end='')
    sys.stdout.flush()
    
    admin_client = AdminClient({'bootstrap.servers': server_string})
    
    # 1. Try to delete
    try:
        fs = admin_client.delete_topics([TOPIC_NAME], operation_timeout=30)
        for t, f in fs.items():
            try:
                f.result() # Wait for deletion
            except Exception:
                pass # Topic might not exist, which is fine
    except:
        pass
        
    # Wait a moment for Kafka to clean up
    time.sleep(2) 
    
    # 2. Create Fresh
    new_topic = NewTopic(TOPIC_NAME, num_partitions=1, replication_factor=1)
    fs = admin_client.create_topics([new_topic])
    for t, f in fs.items():
        try:
            f.result()
        except Exception as e:
            print(f" (Warning: {e})", end='')
            
    print(" ✅ Fresh topic created.")

def get_producer_config():
    return {
        'bootstrap.servers': BOOTSTRAP_SERVERS,
        'linger.ms': 5,
        'acks': 1
    }

def process_file_batch(file_list):
    p = Producer(get_producer_config())
    
    for file_path in file_list:
        try:
            file_name = os.path.basename(file_path)
            time_part = file_name.split('_')[1].split('.')[0]
            start_time = datetime.strptime(time_part, "%Y%m%d%H%M%S")
            
            print(f"\n📂 Playing: {file_name}")
            
            df = pd.read_parquet(file_path, engine='pyarrow')
            df['source_id'] = file_name
            df = df.astype(object).where(pd.notnull(df), "nan")
            records = json.loads(df.to_json(orient='records', lines=False))
            
            for i, record in enumerate(records):
                current_time = start_time + timedelta(seconds=i)
                timestamp_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
                record['timestamp'] = timestamp_str
                
                while True:
                    try:
                        p.produce(TOPIC_NAME, json.dumps(record).encode('utf-8'))
                        p.poll(0)
                        break
                    except BufferError:
                        p.poll(0.1)
                
                print(f"📡 {timestamp_str} | ID: {record.get('source_id')}", end='\r')
                time.sleep(SIMULATION_DELAY)
            
            print(f"\n✅ Segment Done: {file_name}")
                
        except Exception as e:
            print(f"❌ Error in {file_name}: {e}")
            
    p.flush()

if __name__ == '__main__':
    wait_for_kafka(BOOTSTRAP_SERVERS)
    
    # CALL THE RESET FUNCTION
    reset_topic(BOOTSTRAP_SERVERS)

    all_files = sorted(glob.glob(os.path.join(DATA_FOLDER, "*.parquet")))
    if not all_files:
        print(f"❌ No files found in {DATA_FOLDER}")
        sys.exit(1)

    print(f"📦 Found {len(all_files)} files. Starting Stream...")
    process_file_batch(all_files)
        
    print("\n✅ Simulation Complete. Sending STOP signal...")
    p_final = Producer(get_producer_config())
    stop_msg = json.dumps({"status": "DONE"}).encode('utf-8')
    # Send it multiple times to ensure the consumer catches it
    for i in range(10):
        p_final.produce(TOPIC_NAME, stop_msg)
    p_final.flush()