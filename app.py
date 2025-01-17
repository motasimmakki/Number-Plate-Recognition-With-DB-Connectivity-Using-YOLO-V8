from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, session, url_for
import os
import subprocess
import threading

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.secret_key = "your_secret_key"  # Required for session usage

def run_deep_learning_model(video_path):
    def run_model():
        curr_env = "python"
        try:
            # Run Script
            subprocess.run(
                [curr_env, "main.py", video_path],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error occurred while running the scripts: {e}")
            return []

    # Run the subprocess in a separate thread
    thread = threading.Thread(target=run_model, daemon=True)
    thread.start()
    print(f"Deep learning model is running in a separate thread for {video_path}.")

    # # Return recognized plates (dummy example)
    # return ["ABC123", "XYZ789", "LMN456", "UP113899"]

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
    base_url = url_for('serve_output_file', filename='')  # Get the base URL for the route
    return render_template('index.html', base_url=base_url)
    # return render_template("index.html")

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

@app.route("/test", methods=["POST"])
def test_model():
    video_path = request.form.get("video_path")
    if not video_path or not os.path.exists(video_path[1:]):  # Remove leading slash from file path
        return jsonify({"error": "Invalid video path"})

    # Run the deep learning model on the uploaded video
    recognized_plates = run_deep_learning_model(video_path[1:])  # Use the proper video path

    # Save results dynamically
    session["recognized_plates"] = recognized_plates  # Store plates in session for download
    return jsonify({"recognized_plates": recognized_plates})

@app.route("/download", methods=["GET"])
def download_results():
    result_file = os.path.join(UPLOAD_FOLDER, "recognized_plates.txt")

    # Retrieve the recognized plates from session or a persistent store
    recognized_plates = session.get("recognized_plates", [])
    if not recognized_plates:
        return jsonify({"error": "No recognized plates available for download"}), 400

    # Write recognized plates to a file
    with open(result_file, "w") as f:
        f.write("\n".join(recognized_plates))
    
    # Send the file for download
    return send_file(result_file, as_attachment=True)

@app.route('/save-recording', methods=['POST'])
def save_recording():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    return jsonify({"file_path": f"/uploads/{file.filename}"}), 200
    
if __name__ == "__main__":
    app.run(debug=True)

