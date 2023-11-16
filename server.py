from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from urllib.parse import urlparse
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# MongoDB connection setup
client = MongoClient('mongodb://localhost/')  # Update with your MongoDB URI if different
db = client.brand  # Replace with your database name
links_collection = db.links
size_guides_collection = db.size_guide

client = OpenAI()

def extract_domain(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

@app.route('/get-size-guide', methods=['POST'])
def get_size_guide():
    data = request.get_json()
    product_url = data.get('product_url')
    img_src_url = data.get('img_src_url')
    page_title = data.get('page_title')

    if not product_url:
        return jsonify({"error": "Product URL is required"}), 400

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
                        "text": f"Based on the title {page_title} and the picture, find which category {filtered_categories} it most likely fall into, answer with one word and it must be in the list of categories"
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
    app.run(debug=True)
