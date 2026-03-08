import zmq
import time
import json
import random

def main():
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:5555")

    devices = ["devA", "devB"]

    # independent timers for each device
    next_send = {
        "devA": time.time() + 1,
        "devB": time.time() + 2,
    }

    print("Independent dummy publishers running...")

    while True:
        now = time.time()

        for dev in devices:
            if now >= next_send[dev]:

                # Randomly choose FALL or STAND
                event = "FALL" if random.random() < 0.5 else "FALL"

                payload = {
                    "device_id": dev,
                    "event": event,
                    "timestamp": int(now)
                }

                socket.send_multipart([
                    b"fall_events",
                    json.dumps(payload).encode("utf-8")
                ])

                print(f"[{dev}] Sent:", payload)

                # schedule next event independently
                next_send[dev] = now + random.uniform(1.0, 3.0)

        time.sleep(0.01)

if __name__ == "__main__":
    main()