import zmq
import json

def start_subscriber():
    context = zmq.Context()
    socket = context.socket(zmq.SUB)

    # Replace 'localhost' with the actual IP addresses of the cameras if needed
    # If running two cameras on one PC, use two different ports (e.g., 5555 and 5556)
    socket.connect("tcp://localhost:5555")
    # socket.connect("tcp://localhost:5556") # Connect to the second camera here

    # Subscribe to the specific topic
    socket.setsockopt_string(zmq.SUBSCRIBE, "fall_events")

    print("Listening for fall events...")

    while True:
        try:
            topic, messagedata = socket.recv_multipart()
            data = json.loads(messagedata.decode())
            
            device = data.get("device_id")
            p_id = data.get("person_id")
            
            print("-" * 30)
            print(f"ALARM: Fall detected on {device}")
            print(f"Subject: Person {p_id}")
            print("-" * 30)
            
        except KeyboardInterrupt:
            break

    socket.close()
    context.term()

if __name__ == "__main__":
    start_subscriber()

