# detector_webcam.py
# Finding the person in front of the camera is anyone who stored in database
# Using USB webcam or IP Cam (single threading)
#
# Project: Face Recognition using OpenCV and Raspberry Pi
# Ref: https://www.pytorials.com/face-recognition-using-opencv-part-3/
# By: Mickey Chan @ 2019

# Import required modules
import cv2
import os
import sqlite3
import RPi.GPIO as GPIO
import time

# Connect SQLite3 database
conn = sqlite3.connect('database.db')
db = conn.cursor()

# Assign the training data file
fname = "recognizer/trainingData.yml"
if not os.path.isfile(fname):
    print("Please train the data first")
    exit(0)

# Setup GPIO for door lock
# relayPin = 26
# GPIO.setmode(GPIO.BCM)
# GPIO.setup(relayPin, GPIO.OUT)
# GPIO.output(relayPin, 0)

lastDetectedAt = 0
detectInterval = 5 # 1/n second, for reducing overhead
lastUnlockedAt = 0
unlockDuration = 5 # n second

# Font used for display
font = cv2.FONT_HERSHEY_SIMPLEX

# Connect to video source
#vSource = "rtsp://192.168.1.100:8554/live.sdp" # RTSP URL of IP Cam
vSource = 0 # first USB webcam
vStream = cv2.VideoCapture(vSource)

# Setup Classifier for detecting face
faceCascade = cv2.CascadeClassifier("/home/pi/opencv/data/haarcascades/haarcascade_frontalface_default.xml")
# Setup LBPH recognizer for face recognition
#recognizer = cv2.face.createLBPHFaceRecognizer() # or LBPHFaceRecognizer_create()
recognizer = cv2.face.LBPHFaceRecognizer_create()
# Load training data
#recognizer.load(fname) # change to read() for LBPHFaceRecognizer_create()
recognizer.read(fname)

while vStream.isOpened():
    # Lock the door again when timeout
    #if time.time() - lastUnlockedAt > unlockDuration:
        #GPIO.output(relayPin, 0)
    
    ok, frame = vStream.read() # Read frame
    if not ok: break
    
    timeElapsed = time.time() - lastDetectedAt
    if timeElapsed > 1./detectInterval:
        lastDetectedAt = time.time()
        
        # Detect face
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # Convert captured frame to grayscale
        faces = faceCascade.detectMultiScale(gray, scaleFactor = 1.3, minNeighbors = 5) # Detect face(s) inside the frame
        
        for (x, y, w, h) in faces:
            # Try to recognize the face using recognizer
            roiGray = gray[y:y+h, x:x+w]
            id_, conf = recognizer.predict(roiGray)
            print(id_, conf)
            
            # If recognized face has enough confident (<= 70),
            # retrieve the user name from database,
            # draw a rectangle around the face,
            # print the name of the user and
            # unlock the door for 5 secords
            if conf <= 70:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                # retrieve user name from database
                db.execute("SELECT `name` FROM `users` WHERE `id` = (?);", (id_,))
                result = db.fetchall()
                name = result[0][0]
                
                # You may do anything below for detected user, e.g. unlock the door
                #GPIO.output(relayPin, 1) # Unlock
                lastUnlockedAt = time.time()
                print("[Unlock] " + str(id_) + ":" + name + " (" + str(conf) + ")")
                cv2.putText(frame, name, (x+2,y+h-5), font, 1, (150,255,0), 2)
            else:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                #GPIO.output(relayPin, 0) # Lock the door if not enough confident
                #print("[Lock] " + name + " " + str(conf))
                #cv2.putText(frame, 'No Match', (x+2,y+h-5), font, 1, (0,0,255), 2)
        
    cv2.imshow("Face Recognizer", frame)
    
    # Press ESC or 'q' to quit the program
    key = cv2.waitKey(1) & 0xff
    if key == 27 or key == ord('q'):
        break

# Clean up
vStream.release()
conn.close()
cv2.destroyAllWindows()
# GPIO.cleanup()
print("END")
