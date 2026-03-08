import zmq 
import requests
import smtplib
from email.message import EmailMessage
import ssl
import json
import time
from dotenv import load_dotenv
import os
import json
from collections import deque
from datetime import datetime

class AlertEventBuffer:
    def __init__(self, devices, pairs, window_seconds=3.0):
        self.rolling_window = deque()

        self.device_state = {
            d["id"]: {
                "last_event": None,
                "last_event_time": None,
                "last_fall_time": None,
            }
            for d in devices
        }
        self.pairing_map = {}

        for pair in pairs:
            device_A = pair["primary"]
            device_B = pair["secondary"]

            self.pairing_map[device_A] = device_B
            self.pairing_map[device_B] = device_A
        self.window_seconds = window_seconds
    
    def insert_event(self, json_payload):
        device_id = json_payload["device_id"]
        event = json_payload["event"]

        now =  int(time.time())

        state = self.device_state[device_id]
        state["last_event"] = event
        state["last_event_time"] = now

        if event == "FALL":
            state["last_fall_time"] = now
            self.rolling_window.append((device_id, now))

        self._prune(now)
        print("BUFFER INSERT:", device_id, event, "WINDOW:", list(self.rolling_window))

    def _prune(self, now):
        while self.rolling_window:
            device_id, t = self.rolling_window[0]
            if now - t > self.window_seconds:
                self.rolling_window.popleft()
            else:
                break
    def fall_detected_in_buffer(self):

        recent_fall_devices = {dev for dev, t in self.rolling_window}

        print("CHECKING BUFFER:", recent_fall_devices, "PAIR MAP:", self.pairing_map)
        for dev in recent_fall_devices:
            partner = self.pairing_map.get(dev)
            if partner and partner in recent_fall_devices:
                return True 

        return False


def send_text_alerts(text_message, email_alerts_recipient):
    load_dotenv()
    smtp_user = os.getenv("SMTP_USER")
    smtp_auth = os.getenv("SMTP_AUTH")
    port = 587

    try: 
        server = smtplib.SMTP("smtp.gmail.com", port)

        server.starttls() 
        server.login(smtp_user, smtp_auth)
        
        for email in email_alerts_recipient:
            msg = EmailMessage()
            msg.set_content(f"{text_message}")
            msg["Subject"] = "ALERT PATIENT FALLEN"
            msg["From"] = smtp_user
            msg["To"] = email
            print("Sending to: ", email)
            server.send_message(msg, to_addrs=[email])
            print("Sent: ", email)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            server.quit()
        except:
            pass

def SendAlertRequest(AlertPayLoad):
    Backend_Alert_URL = os.getenv("BACKEND_URL_ALERTS")
    Auth_Token = os.getenv("NODE_SERVICE_TOKEN")
    headers = {
    "Authorization": f"Bearer {Auth_Token}"
    }

    response = requests.post(Backend_Alert_URL, json=AlertPayLoad, headers=headers)

    print("Status:", response.status_code)
    print("Response:", response.text)

def ListenForAlerts(devices, pairs, alert_emails, listening_window):

    context = zmq.Context()
    subscriber_socket = context.socket(zmq.SUB)
    subscriber_socket.setsockopt_string(zmq.SUBSCRIBE, "")
    
    port = "5555"

    publishers = [d["ip"] for d in devices]
    
    for ip in publishers:
        address = f"tcp://{ip}:{port}"
        subscriber_socket.connect(address)
        print(f"Connected to publisher at {address}")

    print("Subscriber is now connected to all publishers.")

    AlertBuffer = AlertEventBuffer(devices, pairs)

    while True:
        frames = subscriber_socket.recv_multipart() 
        topic = frames[0].decode("utf-8")
        json_bytes = frames[1]             
        data = json.loads(json_bytes.decode("utf-8"))

        dev_id = data.get("device_id")
        dev_timestamp = data.get("timestamp")
        dev_event = data.get("event")

        payload = {
        "device_id": dev_id,
        "event": dev_event,
        "timestamp": dev_timestamp,
        "location": next((d["name"] for d in devices if d["id"] == dev_id), "UNKNOWN")
        }

        AlertBuffer.insert_event(payload)

        #if AlertBuffer.fall_detected_in_buffer():
        if topic:
                
            send_text_alerts(f"FALL ALERT: AT {payload["location"]} {time.ctime(payload["timestamp"])} ", alert_emails)
            SendAlertRequest(payload)
                


def main():    


    with open("config.json", "r") as f:
            config = json.load(f)

    devices = config["devices"]
    pairs = config["pairs"]
    alert_emails = config["alertEmails"]
    window_of_listening = config["ListeningWindow"]

    ListenForAlerts(devices, pairs, alert_emails, window_of_listening)


if __name__ == "__main__":
    main()