from time import sleep
import sys
from mfrc522 import SimpleMFRC522
import requests
from RPi import GPIO
import logging
import time


logging.getLogger().setLevel(logging.DEBUG)

server = 'http://192.168.0.110:8809'
url = '/api/v1/checkRfid'

roles = ['', 'manager', 'nurse', 'elder']

def main():
    reader = SimpleMFRC522()

    try:
        while True:
            print("waitting...")
            _id, text = reader.read()
            logging.debug("get uid " + hex(_id))
            resp = requests.post(server + url, json={'uid': _id, 'isGetIn': True})
            if resp.status_code == 200:
                data = resp.json()
                if data['status'] == 0:
                    print("%s %s %s" % (time.ctime(), data['data']['name'], roles[data['data']['type']]))
            else:
                logging.debug("request failed with " + str(resp.status_code))
                print("auth fail, please try again")
            sleep(3)
    except KeyboardInterrupt:
        GPIO.cleanup()
        raise

if __name__ == "__main__":
    main()
