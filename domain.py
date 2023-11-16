import requests
from pymongo import MongoClient
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote
import time
import random

def get_domain_from_duckduckgo(query):
    headers = {'User-Agent': 'Mozilla/5.0'}
    search_url = f"https://duckduckgo.com/html/?q={query}"

    try:
        response = requests.get(search_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            links = soup.findAll('a', class_='result__a')
            if links:
                href = links[0]['href']
                # Parse the query string in href
                query_string = urlparse(href).query
                params = parse_qs(query_string)
                if 'uddg' in params:
                    # Decode the URL
                    decoded_url = unquote(params['uddg'][0])
                    parsed_url = urlparse(decoded_url)
                    return parsed_url.netloc
    except Exception as e:
        print(f"Error occurred during DuckDuckGo search: {e}")
    return None

# MongoDB connection setup
client = MongoClient("mongodb://localhost/")
db = client.brand
collection = db.links

# Updating documents with domain name
for document in collection.find({}):
    brand_name = document['brand_name']
    time.sleep(random.randint(2, 6))
    domain_name = get_domain_from_duckduckgo(brand_name)
    print(f"Searching for {brand_name} for domain {domain_name}")
    if domain_name:
        collection.update_one({'_id': document['_id']}, {'$set': {'domain_name': domain_name}})
        print(f"Updated {brand_name} with domain {domain_name}")
    else:
        print(f"Domain not found for {brand_name}")

client.close()
