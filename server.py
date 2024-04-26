from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from urllib.parse import urlparse, urlunparse
from flask_cors import CORS
# Assuming you have an OpenAI library that supports GPT-4 Vision (this is a placeholder)
from openai import OpenAI
import json

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

def clean_url(url):
    parsed_url = urlparse(url)
    # Return the URL without query parameters
    return urlunparse(parsed_url._replace(query=""))

def is_contain_grass(url):
    return "grass" in url

def extract_domain(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

@app.route('/get-size-recommendation', methods=['POST'])
def get_size_recommendation():
    data = request.get_json()
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
        model="gpt-4-vision-preview",
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
    if tabUrl:
        recommendations_collection.insert_one({"tabUrl": cleaned_url, "recommendation": json.loads(content_text)})
        return jsonify(json.loads(content_text))
    
    return jsonify(content_text)


@app.route('/get-size-guide', methods=['POST'])
def get_size_guide():
    data = request.get_json()
    product_url = data.get('product_url')
    img_src_url = data.get('img_src_url')
    page_title = data.get('page_title')

    # if not product_url:
    #    return jsonify({"error": "Product URL is required"}), 400

    # Clean the product_url to remove query parameters
    if is_contain_grass(product_url):
        return jsonify({"success": "size guide is not support grasses"}), 200

    cleaned_product_url = clean_url(product_url)
    print(cleaned_product_url)
    # Check if there's an existing entry for this cleaned URL in recommendations_collection
    existing_entry = recommendations_collection.find_one({"tabUrl": cleaned_product_url})
    if existing_entry:
        return jsonify(existing_entry["recommendation"]), 200  # Return the stored result directly

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
        model="gpt-4-vision-preview",
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

    return jsonify(size_guide.get('sizes'))

if __name__ == '__main__':
    app.run(port=5001, debug=True)

