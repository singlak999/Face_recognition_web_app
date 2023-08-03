import os
import base64
import io
from flask import Flask, render_template, request, jsonify
import firebase_admin
from firebase_admin import credentials, db, storage
import face_recognition
import cv2
import pickle
import numpy as np
import datetime

app = Flask(__name__)

# Initialize Firebase Admin SDK
cred = credentials.Certificate("key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://face-recognition-6420f-default-rtdb.asia-southeast1.firebasedatabase.app/',
    'storageBucket': 'face-recognition-6420f.appspot.com'
})

# Firebase database reference
db_ref = db.reference('/Students')

# Firebase storage bucket reference
bucket = storage.bucket()

# Path to the local file for EncodeFile.p
local_file_path = 'EncodeFile.p'

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    success_message = None

    if request.method == 'POST':
        registration_number = request.form['registration_number']
        student_name = request.form['student_name']
        image_data = request.form['image_data']

        # Convert base64-encoded image data to bytes
        image_bytes = base64.b64decode(image_data.split(',')[1])

        # Perform face recognition on the captured image and get the face encodings
        face_image = face_recognition.load_image_file(io.BytesIO(image_bytes))
        face_encodings = face_recognition.face_encodings(face_image)

        if len(face_encodings) == 0:
            return "No faces found in the captured image. Please try again."

        # Assuming there's only one face in the image, take the first face encoding
        # If multiple faces are allowed per registration, you can store multiple encodings as a list
        student_face_encoding = face_encodings[0]

        # Download the existing EncodeFile.p from Firebase Storage if it exists
        try:
            blob = bucket.blob('EncodeFile.p')
            blob.download_to_filename(local_file_path)

            # Load the existing data from the local file
            with open(local_file_path, 'rb') as f:
                elkID = pickle.load(f)
        except Exception as e:
            # If the file does not exist or cannot be downloaded, create a new list
            elkID = [[], []]

        # Append the new face encoding and registration number to the respective lists
        elkID[0].append(student_face_encoding)
        elkID[1].append(registration_number)

        # Save the updated data back to the local file
        with open(local_file_path, 'wb') as f:
            pickle.dump(elkID, f)

        # Upload image to Firebase Storage
        if image_data:
            # Save the image with registration number as the name
            filename = f"{registration_number}.jpg"

            # Upload the image to Firebase Storage
            blob = bucket.blob(f"images/{filename}")
            blob.upload_from_file(io.BytesIO(image_bytes), content_type='image/jpeg')

        # Upload the updated file back to Firebase Storage
        blob = bucket.blob('EncodeFile.p')
        blob.upload_from_filename(local_file_path)

        # Remove the local file after uploading to Firebase Storage
        os.remove(local_file_path)

        # Update Firebase Realtime Database with the student's registration and name
        db_ref.child(registration_number).set({
            'Name': student_name
        })
        # Upload image to Firebase Storage
        if image_data:
            # Save the image with registration number as the name
            filename = f"{registration_number}.jpg"

            # Upload the image to Firebase Storage
            blob = bucket.blob(f"images/{filename}")
            blob.upload_from_file(io.BytesIO(image_bytes), content_type='image/jpeg')
        # Set the success message
        success_message = "Registration Successfully Completed"

    # Pass the success_message variable to the template
    return render_template('register.html', success_message=success_message)



@app.route('/mark_attendance', methods=['GET', 'POST'])
def mark_attendance():
    # Download the existing EncodeFile.p from Firebase Storage if it exists
    try:
        blob = bucket.blob('EncodeFile.p')
        blob.download_to_filename(local_file_path)

        # Load the existing data from the local file
        with open(local_file_path, 'rb') as f:
            elkID = pickle.load(f)
    except Exception as e:
        # If the file does not exist or cannot be downloaded, create a new list
        elkID = [[], []]
    # Get the image data from the POST request
    # Get the image data from the request
    if request.method == 'POST':
        image_data = request.form['image_data']

        # Decode the base64-encoded image data
        image_bytes = base64.b64decode(image_data.split(',')[1])

        # Perform face recognition on the captured image and get the face encodings
        face_image = face_recognition.load_image_file(io.BytesIO(image_bytes))
        face_encodings = face_recognition.face_encodings(face_image)

        if len(face_encodings) == 0:
            return "No faces found in the captured image. Please try again."

        # Assuming there's only one face in the image, take the first face encoding
        # If multiple faces are allowed for marking attendance, you can modify the logic accordingly
        student_face_encoding = face_encodings[0]

        # Match the face encoding with the known encodings
        elk, ID = elkID
        matches = face_recognition.compare_faces(elk, student_face_encoding)
        facedistance = face_recognition.face_distance(elk, student_face_encoding)

        print(facedistance)
        matchIndex = np.argmin(facedistance)
        if matches[matchIndex]:
            # Get the registration number associated with the recognized face
            registration_number = ID[matchIndex]

            # Update Firebase Realtime Database with the student's attendance for today
            db_ref.child(f'{registration_number}'.upper()).update({
                f'{datetime.date.today().strftime("%d-%m-%Y")}': "Present"
            })

            # return "Attendance marked successfully."
    
    return render_template('mark_attendance.html') 


if __name__ == '__main__':
    app.run(debug=True)
