import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import time
import random

# Set up the MongoDB connection
client = MongoClient('mongodb://localhost/')
db = client.brand

# Clear the existing data in the collections
db.links.delete_many({})
db.size_guide.delete_many({})

# Collections
links_collection = db.links
size_guide_collection = db.size_guide

# Function to parse a page and extract links, h3, and table data
def parse_page(url, brand_id=None):
    # Wait for a random time between 2 and 10 seconds
    time.sleep(random.randint(2, 10))
    
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # If it's the main page, find all brands and save them
    if not brand_id:
        section = soup.find('div', class_='section-pages-tag')
        if section:
            for a_tag in section.find_all('a'):
                href = a_tag.get('href')
                text = a_tag.get_text()
                # Save to MongoDB
                brand_record = {'href': href, 'brand_name': text}
                result = links_collection.insert_one(brand_record)
                brand_id = result.inserted_id
                # Recursively follow the link
                parse_page('https://sizechartdb.com' + href, brand_id=brand_id)
    else:
        # It's a subpage, find h3 and the following table
        for h3 in soup.find_all('h3'):
            category_id = h3.get('id')
            category_name = h3.get_text()

            # The table directly after the h3 contains the sizes
            table = h3.find_next_sibling('table')
            if table:
                headers = [th.get_text() for th in table.find('thead').find_all('th')]
                rows = []
                for row in table.find('tbody').find_all('tr'):
                    values = [td.get_text() for td in row.find_all('td')]
                    row_data = dict(zip(headers, values))
                    rows.append(row_data)
                
                size_guide_record = {
                    'brand_id': brand_id,
                    'category_id': category_id,
                    'category_name': category_name,
                    'sizes': rows
                }
                # Save to MongoDB
                size_guide_collection.insert_one(size_guide_record)

# Start crawling from the main page
parse_page('https://sizechartdb.com/')

# Close the database connection
client.close()
