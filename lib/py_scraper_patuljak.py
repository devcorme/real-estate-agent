import requests
from bs4 import BeautifulSoup
from save_to_database import save_listing
import re

# Base URL for the real estate website
baseurl = 'https://patuljak.me/'

# Headers to mimic browser request
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_all_listing_urls():
    """Collect all real estate listing URLs from pages"""
    productlinks = []
    
    # Iterate through first 5 pages of listings
    for x in range(10):
        r = requests.get(f'https://patuljak.me/c/stanovi/namjena-prodaja/strana-{x}', headers=headers)
        soup = BeautifulSoup(r.content, 'lxml')
        productlist = soup.find_all('div', class_='product__v--l0')
        
        # Extract individual listing URLs
        for item in productlist:
            for link in item.find_all('a', href=True):
                productlinks.append(baseurl + link['href'].lstrip('/'))
    
    return productlinks

def extract_listing_details(url):
    """Extract details from a single real estate listing"""
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, 'lxml')
    
    result = {}
    
    # Extract title (property name/description)
    title = soup.find('div', class_='product_full__naslov_cijena')
    title_text = title.find('h1').text.strip() if title else "No title found"
    if 'garsonjera' in title_text.lower():
        result['type'] = 'garsonjera'
    else:
        result['type'] = 'stan'

    result['title'] = title_text
    # Extract price
    cijena = soup.find('div', class_='product_full__cijena_buttons')
    if cijena:
        price_span = cijena.find('span', itemprop='price')
        if price_span:
            if price_span.text.strip()[0].isdigit():
                result['price'] = float(price_span.text.strip().rstrip('€'))
            else:
                result['price'] = None
    
    # Extract property specifications (size, location, etc.)
    short_description = {}
    ispod_slike = soup.find('div', class_='product_full__ispod_slike--details')
    if ispod_slike:
        for ul in ispod_slike.find_all('ul'):
            for li in ul.find_all('li'):
                spans = li.find_all('span')
                if len(spans) >= 2:
                    key = spans[0].text.strip().rstrip(':')
                    if key != "":
                        if key=='Grad':
                            result['city'] = spans[1].text.strip()
                        elif 'kvadratura' in key.lower():
                            text = spans[1].text.strip()
                            numbers = re.findall(r'\d+', text)
                            result['size'] = float(numbers[0]) if numbers else None
                        elif key.lower()=='broj soba':
                            text = spans[1].text.strip()
                            room_map = {'jednosoban': 1, 'dvosoban': 2, 'trosoban': 3, 'četvorosoban': 4}
                            result['rooms'] = room_map.get(text.lower(), None)
                        elif key.lower()=='namješten':
                            result['furnished'] = True if spans[1].text.strip().lower() == 'da' else False
                        elif key.lower()=='sprat':
                            floor_text = spans[1].text.strip().lower()
                            if floor_text in ['visoko prizemlje', 'prizemlje']:
                                result['floor'] = 0
                            else:
                                try:
                                    result['floor'] = int(re.search(r'\d+', floor_text).group())
                                except (AttributeError, ValueError):
                                    result['floor'] = None
                        elif key.lower()=='naselje':
                            result['neighborhood'] = spans[1].text.strip()
                        else:
                            if key.lower()!="undefined":
                                value = spans[1].text.strip()
                                short_description[key] = value
    
    result['short_description'] = short_description
    
    # Extract detailed property description
    detailed_description = []
    phone_numbers = []
    more_data = soup.find('div', class_='baner__5--paralax_over')
    if more_data:
        details_divs = more_data.find_all('div', class_='product_full__ispod_slike--details')
        for div in details_divs:
            title = div.find('h2')
            if title and 'Detaljan opis:' in title.text:
                # Get all text after the h2 tag
                text = ''
                for element in title.next_siblings:
                    if element.string and element.string.strip():
                        text += ' ' + element.string.strip()
                
                text = text.strip()
                if text:
                    # Check for phone numbers
                    if '+382' in text:
                        numbers = re.findall(r'\+382\d{8}\d?', text.replace(' ', '').replace('/', '').replace('\\', '').replace('-', ''))
                        phone_numbers.extend(numbers)
                    elif '06' in text:
                        numbers = re.findall(r'06\d{7,8}', text.replace(' ', '').replace('/', '').replace('\\', '').replace('-', ''))
                        phone_numbers.extend(numbers)
                    detailed_description.append(text)
            elif title and 'Dodatno:' in title.text:
                # Get additional features
                items = div.find_all('li')
                for item in items:
                    if item.text.strip() != 'undefined':
                        detailed_description.append(item.text.strip())

    result['detailed_description'] = detailed_description
    result['phone_numbers'] = phone_numbers
    
    # Extract property images
    image_links = []
    slike = soup.find('div', class_='swiper-wrapper')
    if slike:
        for slide in slike.find_all('div', class_='swiper-slide'):
            for img in slide.find_all('img'):
                if 'data-src' in img.attrs:
                    image_links.append(baseurl + img['data-src'].lstrip('/'))
    
    result['images'] = image_links
    
    # Extract additional details from the bottom section
    bottom_section = soup.find('div', class_='product_full__bottom')
    if bottom_section:
        spans = bottom_section.find_all('span')
        for span in spans:
            bold_tag = span.find('b')
            if bold_tag:
                key = bold_tag.text.strip().rstrip(':').lower()
                value = span.text.replace(bold_tag.text, '').strip()
                if key == 'datum':
                    result['publish_date'] = value
                    # print(f"🕒 Publish date: {value}")
                elif key == 'broj pregleda':
                    try:
                        result['seen'] = int(value)
                        # print(f"👀 Seen: {value}")
                    except ValueError:
                        result['seen'] = None
    result['source'] = 'https://patuljak.me/'

    return result

def main():
    # Get all listing URLs
    urls = get_all_listing_urls()
    # Process each listing
    for url in urls:
        try:
            result = extract_listing_details(url)
            # print(result.get('detailed_description'))
            print(f"🏠 Processing : {url}")
            save_listing(result, url, auto_control=True)
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")

if __name__ == "__main__":
    main()
