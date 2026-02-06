import os
import csv
import json
import time
import sys
from confluent_kafka import Consumer, KafkaError

# --- CONFIGURATION ---
BOOTSTRAP_SERVERS = os.environ.get('BOOTSTRAP_SERVERS', 'localhost:9092')
TOPIC_NAME = 'well-sensors'
# Use a static group ID so we don't spam Kafka with new groups
GROUP_ID = 'realtime-demo-group' 

def run_consumer():
    output_file = "final_dataset.csv"
    
    conf = {
        'bootstrap.servers': BOOTSTRAP_SERVERS,
        'group.id': GROUP_ID,
        
        # --- THE FIX ---
        # 'latest' means: Ignore old history. Only read new messages.
        # This prevents it from seeing old "DONE" signals.
        'auto.offset.reset': 'latest',
        
        'enable.auto.commit': True
    }
    
    consumer = Consumer(conf)
    consumer.subscribe([TOPIC_NAME])
    print(f" Consumer listening on {BOOTSTRAP_SERVERS}...")
    print(f" Saving data to: {output_file}")
    
    buffer = [] 
    count = 0
    
    # Open in 'a' (Append) mode so we don't delete file if we restart consumer
    with open(output_file, 'a', newline='') as f:
        writer = None 
        print(" Waiting for NEW stream data...")
        
        try:
            while True:
                msg = consumer.poll(1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    print(f" * Kafka Error: {msg.error()}")
                    continue

                try:
                    val = json.loads(msg.value().decode('utf-8'))
                    
                    if "status" in val and val["status"] == "DONE":
                        print(f"\n ./ Received DONE signal. Stream Finished.")
                        break 
                    
                    buffer.append(val)
                    count += 1
                    
                    if count % 20 == 0:
                        event_time = val.get('timestamp', 'Unknown')
                        print(f" ./ Received: {count} | Event Time: {event_time}", end='\r')

                    if len(buffer) >= 50:
                        if writer is None:
                            fieldnames = list(buffer[0].keys())
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            # Only write header if file is empty
                            if f.tell() == 0: writer.writeheader()
                        
                        writer.writerows(buffer)
                        f.flush()
                        buffer = []

                except Exception:
                    continue 

        except KeyboardInterrupt:
            print("\n * Stopping Consumer...")
            
        finally:
            if buffer and writer:
                writer.writerows(buffer)
            consumer.close()

if __name__ == '__main__':
    run_consumer()
