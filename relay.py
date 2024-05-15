from flask import Flask, request, jsonify
import requests
import json
from flask_cors import CORS
import base64
import re
from io import BytesIO
from PIL import Image
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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


def forward_request(url):
    # Extract JSON data from incoming request
    incoming_data = request.get_json()
    headers = {'Content-Type': 'application/json'}

    # Forward the request to the specified URL
    response = requests.post(url, json=incoming_data, headers=headers)
    
    # Return the response received from the remote server
    return jsonify(response.json())

@app.route('/advanced-test', methods=['POST'])
def forward_test():
    ip_address = request.remote_addr
    logging.info(f"Request to /advanced-test from IP: {ip_address}")
    return forward_request("https://tryon-advanced-test.tianlong.co.uk/upload/images")

@app.route('/advanced', methods=['POST'])
def forward_production():
    ip_address = request.remote_addr
    logging.info(f"Request to /advanced from IP: {ip_address}")
    return forward_request("https://tryon-advanced.tianlong.co.uk/upload/images")

@app.route('/', methods=['POST'])
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
    response = requests.post('https://sd2.tianlong.co.uk/reactor/image', json=full_data)

    # Handle the response
    if response.status_code == 200:
        return jsonify(response.json())
    else:
        # Specify the path to your image file
        image_path = '/home/faishion/backend/maintain.png'
        
        # Open the image, read it, and encode it to base64
        with open(image_path, 'rb') as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Return the base64-encoded image in the response
        return jsonify({"image": encoded_image})

if __name__ == '__main__':
    app.run(debug=False)

