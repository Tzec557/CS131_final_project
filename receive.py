import zmq
import json

# Initialize ZMQ context
context = zmq.Context()
socket = context.socket(zmq.SUB)

# Connect to the detector
socket.connect("tcp://localhost:5555")

# Subscribe to the specific topic
socket.setsockopt_string(zmq.SUBSCRIBE, u"fall_events")

print "Waiting for fall events... (Python 2.7 mode)"

while True:
    try:
        # recv_multipart returns a list of bytes
        topic, message = socket.recv_multipart()
        
        # In Python 2, we just load the message string
        data = json.loads(message)
        
        # Use .format() for compatibility
        print "Received alert on topic [{}]:".format(topic)
        print "Status: {} at {}".format(data['event'], data['timestamp'])
        print "------------------------------"
        
    except KeyboardInterrupt:
        print "\nSubscriber stopped."
        break
    except Exception as e:
        print "Error: {}".format(str(e))
        break

