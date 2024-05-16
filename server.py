from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from urllib.parse import urlparse, urlunparse
from flask_cors import CORS
# Assuming you have an OpenAI library that supports GPT-4 Vision (this is a placeholder)
from openai import OpenAI
import json
import logging

app = Flask(__name__)
CORS(app)

# MongoDB connection setup
client = MongoClient('mongodb://localhost/')  # Update with your MongoDB URI if different
db = client.brand  # Replace with your database name
links_collection = db.links
size_guides_collection = db.size_guide
# Create a new collection for storing request results
recommendations_collection = db.recommendations

# OpenAI client (this is a placeholder, ensure your OpenAI library supports this syntax)
client = OpenAI()

logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')


def clean_url(url):
    parsed_url = urlparse(url)
    # Return the URL without query parameters
    return urlunparse(parsed_url._replace(query=""))


def extract_domain(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain


@app.route('/analyze-profile', methods=['POST'])
def analyze_profile():
    data = request.get_json()
    base64_image = data.get('base64_image')
    if not base64_image:
        return jsonify({"error": "Base64 image data is required"}), 400

    prompt = f"can you based on this profile image, generate the following characteristics: age, bodyShape, ethnic, sex, skinColor, hairStyle, hairColor. And generate compact json to represent it, the answer should just be pure text, without ticks prefix, it should only contain the characteristics I listed above, where age should be pure number, bodyShape will be one of Slim, Fit, Curvy"
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": base64_image,
                        },
                    },
                ],
            }
        ],
        max_tokens=300,
    )
    print(response.choices[0])
    choice = response.choices[0]
    content_text = choice.message.content

    print(json.loads(content_text))
    return jsonify(json.loads(content_text))


@app.route('/get-size-recommendation', methods=['POST'])
def get_size_recommendation():
    data = request.get_json()

    log_data = data.copy()
    # Remove sensitive keys
    log_data.pop('base64_image', None)
    logging.info(f"New size recommendation request: Request Data={log_data}")

    body_measurements = data.get('body_measurements')
    base64_image = data.get('base64_image')
    tabUrl = data.get('tabUrl')  # New parameter
    showing_chart = data.get('showing_chart', False)

    # Clean the URL to remove query parameters
    cleaned_url = clean_url(tabUrl)

    print(cleaned_url)
    # Check if there is an existing entry for this URL
    # if tabUrl:
    #    existing_entry = recommendations_collection.find_one({"tabUrl": cleaned_url})
    #    if existing_entry:
    #        return jsonify(existing_entry["recommendation"]), 200  # Return the stored result

    print(f"Body measurements: {body_measurements}")

    if showing_chart:
        prompt = f"Can you parse the size table on this image, and generate compact json to represent that table, your answer should only contain the json itself, each entry should at most contain Bust, Waist, Hips, Size(if they don't appear on the image size table, then don't include it in the json), the answer should just be pure text, without ticks prefix, if size is a range, add double quote around it to make sure it is a valid json"
        max_tokens = 1000  # Adjusted for potential complexity of HTML table
    else:
        prompt = f"Can you parse the size table on this image, and my body measurements are {body_measurements}, can you give my size recommadation, if there is no perfect match, e.g. different body part match to different size, give me explaination, be concise when possible"
        max_tokens = 300

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": base64_image,
                        },
                    },
                ],
            }
        ],
        max_tokens=max_tokens,
    )
    print(response.choices[0])
    choice = response.choices[0]
    content_text = choice.message.content

    print(content_text)
    # highlight content_text
    highlighted_guides = highlight(content_text, body_measurements)

    if tabUrl:
        recommendations_collection.insert_one({"tabUrl": cleaned_url, "recommendation": json.loads(highlighted_guides)})
        return jsonify(json.loads(highlighted_guides))

    return jsonify(highlighted_guides)


def parse_dimension_range(range_str):
    def convert_fractional_size(size_str):
        if "½" in size_str:
            return float(size_str.replace("½", "")) + 0.5
        return float(size_str)

    parts = [convert_fractional_size(part) for part in range_str.split(" - ")]
    if len(parts) == 1:
        return {"min": parts[0], "max": parts[0]}
    return {"min": min(parts), "max": max(parts)}


# Helper function to convert string with fractions to float
def to_float(value):
    if isinstance(value, (int, float)):
        return float(value)
    value = value.strip()
    if '½' in value:
        value = value.replace('½', '.5')
    return float(value)


# Helper function to check if a dimension is within a range
def is_within_range(value, range_str):
    range_str = str(range_str).strip()
    if '-' in range_str:
        low, high = map(to_float, range_str.split('-'))
        return low <= value <= high
    else:
        return to_float(range_str) == value


# Helper function to find the closest range
def find_closest_range(value, ranges):
    closest_range = None
    closest_diff = float('inf')

    for range_str in ranges:
        range_str = str(range_str).strip()
        if '-' in range_str:
            low, high = map(to_float, range_str.split('-'))
            diff = min(abs(low - value), abs(high - value))
        else:
            diff = abs(to_float(range_str) - value)

        if diff < closest_diff:
            closest_diff = diff
            closest_range = range_str

    return closest_range


# Helper function to find the minimum and maximum values in the sizes
def find_min_max(ranges):
    min_val = float('inf')
    max_val = float('-inf')

    for range_str in ranges:
        range_str = str(range_str).strip()
        if '-' in range_str:
            low, high = map(to_float, range_str.split('-'))
            min_val = min(min_val, low)
            max_val = max(max_val, high)
        else:
            val = to_float(range_str)
            min_val = min(min_val, val)
            max_val = max(max_val, val)

    return min_val, max_val


def highlight(guides, body_dimensions):
    highlighted_guides = []

    for guide in guides:
        highlighted_guide = {}
        for dimension, value in guide.items():
            highlighted_guide[dimension] = {"value": value, "highlight": False}

        highlighted_guides.append(highlighted_guide)

    for dimension, body_value in body_dimensions.items():
        # body_value could only be valid number
        body_value = to_float(body_value)
        ranges = [str(guide[dimension]) for guide in guides if dimension in guide]
        # Find the minimum and maximum values in the sizes
        print(ranges)
        min_val, max_val = find_min_max(ranges)
        # Check if the body value is out of bounds
        is_out_of_bounds = False
        if body_value < min_val or body_value > max_val:
            is_out_of_bounds = True

        additional_object = {"Size": {"value": "Size Unavailable", "highlight": False}}
        additional_object_needed = False

        if is_out_of_bounds:
            additional_object[dimension] = {"value": str(body_value), "highlight": True}
            additional_object_needed = True
        else:
            closest_range = find_closest_range(body_value, ranges)
            for guide in highlighted_guides:
                if dimension in guide:
                    if is_within_range(body_value, guide[dimension]["value"]):
                        guide[dimension]["highlight"] = True
                    elif not guide[dimension]["highlight"] and str(guide[dimension]["value"]) == closest_range:
                        guide[dimension]["highlight"] = True

        if additional_object_needed:
            highlighted_guides.append(additional_object)

    return highlighted_guides


@app.route('/get-size-guide', methods=['POST'])
def get_size_guide():
    data = request.get_json()
    product_url = data.get('product_url')
    img_src_url = data.get('img_src_url')
    page_title = data.get('page_title')
    # Initialize bodyDimensions
    body_dimensions = None
    # Extract dimensions
    body_dimensions_in = data.get('bodyDimensionsIn')
    body_dimensions_cm = data.get('bodyDimensionsCm')
    # Check if both bodyDimensionsIn and bodyDimensionsCm are empty
    if not body_dimensions_in and not body_dimensions_cm:
        return jsonify({"error": "No body dimensions provided"}), 400

    # Check if bodyDimensionsIn is empty and bodyDimensionsCm is provided
    elif not body_dimensions_in and body_dimensions_cm:
        # Convert cm to inches (1 inch = 2.54 cm)
        body_dimensions = {key: round(value / 2.54, 2) for key, value in body_dimensions_cm.items()}

    # If bodyDimensionsIn is provided, use it
    else:
        body_dimensions = body_dimensions_in

    logging.info(f"New size guide request: Request Data={data}")
    # if not product_url:
    #    return jsonify({"error": "Product URL is required"}), 400

    # Clean the product_url to remove query parameters
    cleaned_product_url = clean_url(product_url)
    print(cleaned_product_url)

    # Check if there's an existing entry for this cleaned URL in recommendations_collection
    existing_entry = recommendations_collection.find_one({"tabUrl": cleaned_product_url})
    if existing_entry:
        recommendation = highlight(existing_entry["recommendation"], body_dimensions)
        # return jsonify(existing_entry["recommendation"]), 200  # Return the stored result directly
        return jsonify(recommendation), 200
    domain = extract_domain(product_url)
    print(f"Domain: {domain}")

    # Search for the brand with and without 'www'
    link_record = links_collection.find_one({'$or': [{'domain_name': domain}, {'domain_name': 'www.' + domain}]})

    if not link_record:
        return jsonify({"error": "Brand not found"}), 404

    brand_id = link_record['_id']

    # Print all category_ids for the brand
    categories = size_guides_collection.find({'brand_id': ObjectId(brand_id)})
    category_ids = [category['category_id'] for category in categories]
    print(f"Category IDs for brand {link_record['brand_name']}: {category_ids}")

    filtered_categories = [category for category in category_ids if "numeric" not in category]

    print(f"Page title: {page_title}")
    print(f"Image URL: {img_src_url}")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Based on the title {page_title} and the picture, find which category {filtered_categories} it most likely fall into, answer with one word and it must be in the list of categories, avoid using plus size category unless the person in the picture is very fat"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": img_src_url,
                        },
                    },
                ],
            }
        ],
        max_tokens=300,
    )

    print(response.choices[0])

    choice = response.choices[0]
    content_text = choice.message.content

    print(content_text)
    category_id = content_text

    # Find the size guide based on brand_id and category_id
    size_guide = size_guides_collection.find_one({
        'brand_id': ObjectId(brand_id),
        'category_id': category_id
    })

    print(size_guide.get('sizes') if size_guide else None)

    if not size_guide.get('sizes'):
        return jsonify({"error": "Size guide not found"}), 404

    guides = size_guide.get('sizes')
    # guides = [
    #       { "Hips": '33 - 34', "Size": '0', "Waist": '24', "Brest": '22'},
    #       { "Hips": '35', "Size": '2', "Waist": '25' },
    #       { "Hips": '36', "Size": '4', "Waist": '27' },
    #       { "Hips": '37', "Size": '6', "Waist": '28' },
    #       { "Hips": '38', "Size": '8', "Waist": '29' },
    #       { "Hips": '39', "Size": '10', "Waist": '30' },
    #       { "Hips": '41', "Size": '12', "Waist": '31' },
    #       { "Hips": '42 - 44', "Size": '14', "Waist": '32' }
    #     ]

    # highlighted_guides = []
    #
    # for guide in guides:
    #     highlighted_guide = {}
    #     for dimension, value in guide.items():
    #         highlighted_guide[dimension] = {"value": value, "highlight": False}
    #
    #     highlighted_guides.append(highlighted_guide)
    #
    # for dimension, body_value in body_dimensions.items():
    #     # body_value could only be valid number
    #     body_value = to_float(body_value)
    #     ranges = [guide[dimension] for guide in guides if dimension in guide]
    #     # Find the minimum and maximum values in the sizes
    #     min_val, max_val = find_min_max(ranges)
    #     # Check if the body value is out of bounds
    #     is_out_of_bounds = False
    #     if body_value < min_val or body_value > max_val:
    #         is_out_of_bounds = True
    #
    #     additional_object = {"Size": {"value": "Size Unavailable", "highlight": False}}
    #     additional_object_needed = False
    #
    #     if is_out_of_bounds:
    #         additional_object[dimension] = {"value": str(body_value), "highlight": True}
    #         additional_object_needed = True
    #     else:
    #         closest_range = find_closest_range(body_value, ranges)
    #
    #         for guide in highlighted_guides:
    #             if dimension in guide:
    #                 if is_within_range(body_value, guide[dimension]["value"]):
    #                     guide[dimension]["highlight"] = True
    #                 elif not guide[dimension]["highlight"] and guide[dimension]["value"] == closest_range:
    #                     guide[dimension]["highlight"] = True
    #
    #     if additional_object_needed:
    #         highlighted_guides.append(additional_object)
    highlighted_guides = highlight(guides, body_dimensions)
    return jsonify(highlighted_guides)


if __name__ == '__main__':
    app.run(port=5200, debug=True)
