1. Setup datebase
   Please open setup.py and run it

2. Record your face
   Please open recordface_webcam.py and run it
   In the cmd interface, it will ask your name. Please input the name and press "Enter"
   Then the webcam will open and show the image on screen.
   Please face to the screen for capture, then press "f" to start capture

3. Train data
   Please open trainer.py and run it
   It will train all the human face in database for detection

4. Detect face
   Please open detector_webcam(V2).py and run it
   It will show the box for you to input the sender's email address, sender's email password, receipt's email address, subject and message body
   Click "Enter" button after input all information, it will show error message if you don't fill all the text field
   The webcam will open to detect people face

   If the preson who are not record in database
   The system will play alert sound and capture the person's face who are not record in database
   Then send email attached with captured screen to receipt's email address

Editor: Wong Chun Kit(Student ID: 20136820), Wong Tsz Fung(Student ID: 20152658)

Reference:
# Project: Face Recognition using OpenCV and Raspberry Pi
# Ref: https://www.pytorials.com/face-recognition-using-opencv-part-2/
# By: Mickey Chan @ 2019

# Send email attached with image
# Ref: https://www.youtube.com/watch?v=CBuu17j_WnA
# By: Techie Coder @ 2020

# Create a custom email GUI app using python (Tkinter and Smtplib)
# Ref: https://www.youtube.com/watch?v=qfOgihp-gEU
# By: johan godinho @ 2020