import zmq 
import requests
import smtplib
from email.message import EmailMessage
import ssl
import json
import time
from dotenv import load_dotenv
import os

def send_text_alerts(text_message, phone_numbers):
    load_dotenv()
    smtp_user = os.getenv("SMTP_USER")
    smtp_auth = os.getenv("SMTP_AUTH")
    port = 587

    try: 
        server = smtplib.SMTP("smtp.gmail.com", port)

        server.starttls() 
        server.login(smtp_user, smtp_auth)
        
        for number in phone_numbers:
            msg = EmailMessage()
            msg.set_content(f"{text_message} (ts:{int(time.time())})")
            msg["From"] = smtp_user
            msg["To"] = number
            print("Sending to: ", number)
            server.send_message(msg, to_addrs=[number])
            print("Sent: ", number)
            time.sleep(3)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            server.quit()
        except:
            pass



def main():    

    phone_numbers = ["9512044131@vtext.com", "9512033126@vtext.com", "9512049294@vtext.com", "jmmontes217@gmail.com" ]

    while True:
         message_to_send = input("Enter Message: ")
         send_text_alerts(message_to_send, phone_numbers)




if __name__ == "__main__":
    main()