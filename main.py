import cv2
from time import time
import numpy as np
from ultralytics.solutions.solutions import BaseSolution
from ultralytics.utils.plotting import Annotator, colors
from datetime import datetime
import mysql.connector
from paddleocr import PaddleOCR

import argparse
# Set up argument parser
parser = argparse.ArgumentParser(description="Process a video file.")
parser.add_argument('file', type=str, help="Path to the video file")
args = parser.parse_args()

import requests
# URL of the Flask app
BASE_URL = "http://127.0.0.1:5000"

class DetectPLate(BaseSolution):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.trkd_ids = []  # List for already tracked IDs
        self.trk_pt = {}  # Dictionary for previous timestamps
        self.trk_pp = {}  # Dictionary for previous positions
        self.logged_ids = set()  # Set to keep track of already logged IDs

        # Initialize the OCR system
        # Detect and correct the orientation of text in the image.
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en')

        # MySQL database connection
        self.db_connection = self.connect_to_db()

    def connect_to_db(self):
        """Establish connection to MySQL database and create database/table if not exists."""
        try:
            # Connect to MySQL server
            connection = mysql.connector.connect(
                host="localhost",
                user="root",  # MySQL username
                password="password"   # MySQL password
            )
            cursor = connection.cursor()

            # Create database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS number_plates")
            print("\nDatabase 'number_plates' - checked/created.")

            # Connect to the newly created or existing database
            connection.database = "number_plates"

            # Create table if it doesn't exist
            create_table_query = """
            CREATE TABLE IF NOT EXISTS detection_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                date DATE,
                time TIME,
                track_id INT,
                number_plate TEXT
            )
            """
            cursor.execute(create_table_query)
            print("\nTable 'detection_data' - checked/created.")

            return connection
        except mysql.connector.Error as err:
            print(f"Error connecting to database: {err}")
            raise

    def perform_ocr(self, image_array):
        """Performs OCR on the given image and returns the extracted text."""
        if image_array is None:
            raise ValueError("Image is None")
        if isinstance(image_array, np.ndarray):
            results = self.ocr.ocr(image_array, rec=True)
        else:
            raise TypeError("Input image is not a valid numpy array")
        return ' '.join([result[1][0] for result in results[0]] if results[0] else "")

    def save_to_database(self, date, time, track_id, number_plate):
        """Save data to the MySQL database."""
        try:
            cursor = self.db_connection.cursor()
            query = """
                INSERT INTO detection_data (date, time, track_id, number_plate)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (date, time, track_id, number_plate))
            self.db_connection.commit()
            print(f"Data saved to database: {date}, {time}, {track_id}, {number_plate}")
        except mysql.connector.Error as err:
            print(f"Error saving to database: {err}")
            raise

    def perform_detection(self, im0):
        """Detect vehicles and track them."""
        self.annotator = Annotator(im0, line_width=self.line_width)  # Initialize annotator
        self.extract_tracks(im0)  # Extract tracks

        # Get current date and time
        current_time = datetime.now()

        for box, track_id, cls in zip(self.boxes, self.track_ids, self.clss):
            self.store_tracking_history(track_id, box)  # Store track history

            if track_id not in self.trk_pt:
                self.trk_pt[track_id] = 0
            if track_id not in self.trk_pp:
                self.trk_pp[track_id] = self.track_line[-1]

            # Draw the bounding box and track ID on it
            label = f"ID: {track_id} | {self.names[int(cls)]}"  # Show track ID along with class
            self.annotator.box_label(box, label=label, color=colors(track_id, True))  # Draw bounding box

            # Update the previous tracking time and position
            self.trk_pt[track_id] = time()
            self.trk_pp[track_id] = self.track_line[-1]
            x1, y1, x2, y2 = map(int, box)  # Convert box coordinates to integers
            cropped_image = np.array(im0)[y1:y2, x1:x2]
            ocr_text = self.perform_ocr(cropped_image)

            # Ensure OCR text is not empty and save OCR text with the relevant details if not already logged
            # if track_id not in self.logged_ids and ocr_text.strip():
            if track_id not in self.logged_ids and ocr_text.strip():
                curr_date = current_time.strftime("%Y-%m-%d")
                curr_time = current_time.strftime("%H:%M:%S")
                recognized_number = ocr_text
                self.save_to_database(
                    curr_date,
                    curr_time,
                    track_id,
                    recognized_number
                )
                self.logged_ids.add(track_id)

                payload = {
                    "Date": curr_date,
                    "Time": curr_time,
                    "Tracked Number": recognized_number
                }
            
                # Send POST request
                response = requests.post(f"{BASE_URL}/test", json=payload)

                # Handle the response
                if response.status_code == 200:
                    # Server sends back a response
                    # print("Response sent successfully:", payload)
                    print(payload)
                else:
                    print("Failed to send the response. Status code:", response.status_code)

        self.display_output(im0)  # Display output with base class function
        return im0


# Open the video file
# cap = cv2.VideoCapture('./uploads/demo.mp4')

# Use the file name passed as a command-line argument
cap = cv2.VideoCapture(args.file)

# Check if the video file was opened successfully
if not cap.isOpened():
    print(f"Error: Cannot open video file {args.file}")
else:
    print(f"Processing video: {args.file}")

# Initialize the object counter
detection_obj = DetectPLate(
    model="detection_model.pt",  # YOLO model file
    line_width=2
)

count = 0

while True:
    # Read a frame from the video
    ret, frame = cap.read()
    if not ret:
        break

    count += 1
    if count % 3 != 0:  # Skip odd frames
        continue

    frame = cv2.resize(frame, (1020, 500))

    # Process the frame with the object counter
    result = detection_obj.perform_detection(frame)

    # Show the frame
    cv2.imshow("Processing. . .", result)
    if cv2.waitKey(2) & 0xFF == ord("q"):  # Press 'q' to quit
        break

# Release the video capture object and close the display window
cap.release()
cv2.destroyAllWindows()