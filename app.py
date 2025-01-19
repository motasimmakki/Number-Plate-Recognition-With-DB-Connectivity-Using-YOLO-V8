# essential imports
from flask import Flask, render_template, request, Response, jsonify, send_file, send_from_directory, url_for
import os
import subprocess

import mysql.connector
import csv

# Initialize flask app
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
# update configuration settings
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def model_handler(video_path):
    """
    Executes the model as a subprocess.
    """
    def run_model():
        curr_env = "python"
        try:
            # Run the external script with the video path as an argument
            process = subprocess.Popen(
                [curr_env, "main.py", video_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,  # Enables text mode
                encoding='utf-8',  # Decodes output as UTF-8
            )
            # Stream output line-by-line
            for line in process.stdout:
                # yield f"Processing: {line.strip()}"
                yield f"{line.strip()}"
            process.wait()
        except subprocess.CalledProcessError as e:
            yield f"Error: {str(e)}"
    
    return run_model()

# Serve the 'logo' folder as static
@app.route('/logo/<path:filename>')
def serve_logos(filename):
    return send_from_directory('logo', filename)

# Serve the 'outputs' folder as static
@app.route('/outputs/<path:filename>')
def serve_output_file(filename):
    # print(f"Serving video: {filename}")
    return send_from_directory('outputs', filename, mimetype='video/mp4')

@app.route("/")
def index():
    # Get the base URL for the route
    base_url = url_for('serve_output_file', filename='') 
    return render_template('index.html', base_url=base_url)

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"})
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"})
    if file:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)
        return jsonify({"message": "File uploaded successfully", "file_path": f"/uploads/{file.filename}"})

@app.route("/uploads/<path:filename>")
def serve_uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route('/save-recording', methods=['POST'])
def save_recording():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    return jsonify({"file_path": f"/uploads/{file.filename}"}), 200

@app.route("/test", methods=["POST"])
def test_model():
    video_path = request.form.get("video_path")
    if not video_path or not os.path.exists(video_path[1:]):  # Remove leading slash from file path
        return jsonify({"error": "Invalid video path"})

    # Generator for streaming payload data only
    def generate():
        for message in model_handler(video_path[1:]):
            # if "curr_date" in message and "curr_time" in message and "recognized_number" in message:
            if "Date" in message and "Time" in message:
                yield f"data: {message}\n\n"  # Send only payload-like messages

    return Response(generate(), content_type="text/event-stream")

def download_from_db():
    """Establish connection to MySQL database and fetch the stored data."""
    try:
        # Connect to MySQL server
        connection = mysql.connector.connect(
            host="localhost",
            user="root",  # MySQL username
            password="password",   # MySQL password
            database="number_plates"  # Database name
        )
        cursor = connection.cursor()

        # Query to fetch all the data from the table
        select_query = "SELECT * FROM detection_data"

        cursor.execute(select_query)
        rows = cursor.fetchall()

        # Save to CSV file
        result_file = 'detection_data.csv'
        with open(result_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # Writing the headers
            writer.writerow([i[0] for i in cursor.description])
            # Writing the rows
            writer.writerows(rows)

        print("Data saved to 'detection_data.csv' successfully!")
        return result_file
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        raise

@app.route("/download", methods=["GET"])
def download_results():
    result_file = download_from_db()
    if not result_file:
        return jsonify({"error": "No recognized plates available for download"}), 400
    return send_file(result_file, as_attachment=True)
    
if __name__ == "__main__":
    app.run(debug=True)
