from flask import Flask, request, jsonify
import requests
import json
from flask_cors import CORS
import base64
import re
from io import BytesIO
from PIL import Image
from datetime import datetime

app = Flask(__name__)
CORS(app)

def is_base64(sb):
    try:
        if isinstance(sb, str):
            # If there's any unicode here, an exception will be thrown and the function will return false
            sb_bytes = bytes(sb, 'ascii')
        elif isinstance(sb, bytes):
            sb_bytes = sb
        else:
            raise ValueError("Argument must be string or bytes")
        return base64.b64encode(base64.b64decode(sb_bytes)) == sb_bytes
    except Exception:
        return False

def is_url(s):
    return re.match(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', s) is not None

def convert_image_to_base64(url):
    response = requests.get(url)
    image = Image.open(BytesIO(response.content))
    buffered = BytesIO()
    image_format = image.format or 'JPEG'  # Default format to JPEG if not detectable
    image.save(buffered, format=image_format)
    return base64.b64encode(buffered.getvalue()).decode()

@app.route('/relay', methods=['POST'])
def relay():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print("Received request. Current Time:", current_time)
    data = request.json
    source_image = data.get('source_image')
    target_image = data.get('target_image')
    #upscale = data.get('upscale')

    # Check and convert source image
    if is_url(source_image):
        source_image_base64 = convert_image_to_base64(source_image)
    else:
        source_image_base64 = source_image

    # Check and convert target image
    if is_url(target_image):
        target_image_base64 = convert_image_to_base64(target_image)
    else:
        target_image_base64 = target_image
    
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print("Constructing Request. Current Time:", current_time)

    # Add additional parameters
    full_data = {
        "source_image": source_image_base64,
        "target_image": target_image_base64,
        "upscaler": "4x_Struzan_300000",
        "scale": 2,
        "upscale_visibility": 1,
        "face_restorer": "CodeFormer",
        "restorer_visibility": 1,
        "restore_first": 1,
        "model": "inswapper_128.onnx",
        "gender_source": 0,
        "gender_target": 0,
        "save_to_file": 0,
        "result_file_path": ""
    } if data.get('upscale') else {
        "source_image": source_image_base64,
        "target_image": target_image_base64
    }
    now = datetime.now()
    # Format the time
    current_time = now.strftime("%H:%M:%S")

    # Print the time
    print("Ready to send to reactor. Current Time:", current_time)
    
    # Make the POST request to the target API
    response = requests.post('http://localhost:7860/reactor/image', json=full_data)

    # Handle the response
    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Failed to process image"}), response.status_code

if __name__ == '__main__':
    app.run(debug=False)

