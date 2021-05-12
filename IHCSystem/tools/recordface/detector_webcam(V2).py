# detector_webcam.py
# Finding the person in front of the camera is anyone who stored in database
# Using USB webcam or IP Cam (single threading)
#
# Project: Face Recognition using OpenCV and Raspberry Pi
# Ref: https://www.pytorials.com/face-recognition-using-opencv-part-3/
# By: Mickey Chan @ 2019
#
# Send email attached with image
# Ref: https://www.youtube.com/watch?v=CBuu17j_WnA
# By: Techie Coder @ 2020
#
# Create a custom email GUI app using python (Tkinter and Smtplib)
# Ref: https://www.youtube.com/watch?v=qfOgihp-gEU
# By: johan godinho @ 2020
#
# Import required modules
import cv2
import os
import sqlite3
import RPi.GPIO as GPIO
import time
import datetime
from pydub import AudioSegment
from pydub.playback import play

from email.message import EmailMessage
from email.mime.image import MIMEImage
import smtplib
import os

import imghdr
from tkinter import *
from threading import *

# Create Object
root = Tk()
  
# Set geometry
root.geometry("400x220")

# set the position of the label
Label(root, text="Email", font=('Calibri', 11)).grid(row=1,sticky=W, padx=5)
Label(root, text="Password", font=('Calibri', 11)).grid(row=2,sticky=W, padx=5)
Label(root, text="To", font=('Calibri', 11)).grid(row=3,sticky=W, padx=5)
Label(root, text="Subject", font=('Calibri', 11)).grid(row=4,sticky=W, padx=5)
Label(root, text="Body", font=('Calibri', 11)).grid(row=5,sticky=W, padx=5)
notif = Label(root, text="", font=('Calibri', 11),fg="red")
notif.grid(row=7,sticky=S)

# set the attribute of input data
temp_username = StringVar()
temp_password = StringVar()
temp_receiver = StringVar()
temp_subject  = StringVar()
temp_body     = StringVar()

# set the position of the text field
usernameEntry = Entry(root, textvariable = temp_username)
usernameEntry.grid(row=1,column=30)
passwordEntry = Entry(root, show="*", textvariable = temp_password)
passwordEntry.grid(row=2,column=30)
receiverEntry  = Entry(root, textvariable = temp_receiver)
receiverEntry.grid(row=3,column=30)
subjectEntry  = Entry(root, textvariable = temp_subject)
subjectEntry.grid(row=4,column=30)
bodyEntry     = Entry(root, textvariable = temp_body)
bodyEntry.grid(row=5,column=30)

frame = Frame(root)

# craete a new folder to store the captured image of peole who are not recorded in database
dirName = "./UnauthorizedEntry"
if not os.path.exists(dirName):
    os.makedirs(dirName)
    print("UnauthorizedEntry Directory Created")

# send email if there is people are not recorded in database
def send_email():
    msg = EmailMessage()
    username = temp_username.get()
    password = temp_password.get()
    msg["Sender"]   = temp_username.get()
    msg["to"]       = temp_receiver.get()
    msg["subject"]  = temp_subject.get()
    body     = temp_body.get()
    msg.set_content(body)
    
    x = datetime.datetime.now()
    date_time = x.strftime("%m_%d_%Y_%H_%M_%S")
    img_name = dirName + "/" + date_time + ".png"     #set the image name and store it to the path
    
    with open(img_name,'rb') as m:
        file_data = m.read()
        file_type = imghdr.what(m.name)
        file_name = m.name
    msg.add_attachment(file_data, maintype = 'image', subtype = file_type, filename = file_name)  #attached the image to the email
                
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(username, password)
    server.send_message(msg)
    print("email sent")
    server.quit()

def open_cam():
    if temp_username.get()=="" or temp_password.get()=="" or temp_receiver.get()=="" or temp_subject.get()=="" or temp_body.get()=="":
        notif.config(text="All fields required", fg="red") #if one of the text field is emtpy, it will ask user to fill in all text field
        return
    else:
        # Connect SQLite3 database
        conn = sqlite3.connect('database.db')
        db = conn.cursor()

        # Assign the training data file
        fname = "recognizer/trainingData.yml"
        if not os.path.isfile(fname):
            print("Please train the data first")
            exit(0)

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

            
                    if conf <= 70:
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    # retrieve user name from database
                        db.execute("SELECT `name` FROM `users` WHERE `id` = (?);", (id_,))
                        result = db.fetchall()
                        name = result[0][0]
                        saveFace = False
                
                    # You may do anything below for detected user, e.g. unlock the door
                    #GPIO.output(relayPin, 1) # Unlock
                        lastUnlockedAt = time.time()
                        print("[Unlock] " + str(id_) + ":" + name + " (" + str(conf) + ")")
                        cv2.putText(frame, name, (x+2,y+h-5), font, 1, (150,255,0), 2)
                    else:
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                        sound = AudioSegment.from_mp3('/home/pi/Face detection/alarm.mp3')
                        play(sound)     #play the alarm sound if the detect peole who are not recorded in database
                
                        x = datetime.datetime.now()
                        date_time = x.strftime("%m_%d_%Y_%H_%M_%S")
                        img_name = dirName + "/" + date_time + ".png" #set the image name and store it to the path
                        cv2.imwrite(img_name, frame)
                        print("{} written!".format(img_name))
                        send_email()
                
        
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

    
#Button(root,text="Enter",font=("Helvetica 15"),command=open_cam).pack(pady=20)
Button(root, text = "Enter", command = open_cam).grid(row=6,   sticky=W,  pady=15, padx=5)
root.mainloop()