import requests
from bs4 import BeautifulSoup
import re
from save_to_database import save_listing

baseurl = 'https://estitor.com'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_all_listing_urls():
    """Collect all real estate listing URLs from pages"""
    productlinks = set()

    for x in range(1, 10):
        page = '/strana-' + str(x) if x > 1 else ''
        link = f'https://estitor.com/me/nekretnine/namjena-prodaja/tip-stan{page}' + '?sort=createdAt%2Cdesc'
        print(link)
        r = requests.get(link, headers=headers)
        # print(r.content)

        soup = BeautifulSoup(r.content, 'lxml')
        productlist = soup.find_all('article', class_='items-stretch')

        for item in productlist:
            for link in item.find_all('a', href=True):
                if link['href'].startswith('/me/nekretnine/namjena-prodaja/tip-stan/grad'):
                    productlinks.add(baseurl + link['href'])
    return productlinks


def extract_listing_details(url):
    """Extract details from a single real estate listing"""
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, 'lxml')

    result = {}

    title = soup.find('h1', class_='inline text-xl text-dark-1 dark:text-white theme-transition')
    title_text = title.text.strip() if title else "No title found"

    if 'garsonjera' in title_text.lower():
        result['type'] = 'garsonjera'
    else:
        result['type'] = 'stan'

    result['title'] = title_text
    short_description = {}
    cijena = soup.find('div', class_='w-2/5 md:w-auto text-right')
    if cijena:
        price_span = cijena.find('span', class_='text-dark-green-1 font-bold text-2xl whitespace-nowrap')
        if price_span:
            if price_span.text.strip()[0].isdigit():
                result['price'] = float(price_span.text.strip().rstrip('€').strip().replace(',', ''))
            else:
                result['price'] = None

    address_div = soup.find('div', class_='flex items-center gap-2 text-light-blue-1')
    if address_div:
        links = address_div.find_all('a')
        for link in links:
            classes = link.get('class', [])
            if 'hover:text-light-blue-10' in classes and 'truncate' not in classes:
                result['neighborhood'] = link.text.strip().rstrip(',')
            elif 'truncate' in classes:
                result['city'] = link.text.strip().rstrip(',')

    grid_divs = soup.find_all('div', class_='grid grid-cols-2 md:grid-cols-3 gap-3 lg:grid-cols-4 text-grey-2 dark:text-white text-sm mt-5 theme-transition')
    features = []
    
    for grid_div in grid_divs:
        items = grid_div.find_all('div', class_='flex items-center gap-2')
        for item in items:
            span = item.find('span', class_=None)
            if span:
                text = span.text.strip()
                if ':' in text:
                    key_value = text.split(':')
                    key = key_value[0].strip()
                    value = key_value[1].strip().rstrip('.').strip()
                    # print(key, value)
                    if key.lower() == 'broj soba':
                        result['rooms'] = int(value) if value.isdigit() else value
                    elif key.lower() == 'sprat':
                        value = 0 if value == 'P' else value
                        if value != 0:
                            value = int(value) if value.isdigit() else value
                        result['floor'] = value
                    elif key != 'Referentni ID':  # Skip reference ID
                        short_description[key] = value
                else:
                    if text.lower() == 'opremljen':
                        result['furnished'] = True
                    elif text.lower() == 'neopremljen':
                        result['furnished'] = False
                    else:
                        features.append(text)
    
    if features:
        short_description['features'] = features
    result['short_description'] = short_description

    info_div = soup.find('div', class_='grid grid-cols-1 md:grid-cols-2 gap-3 text-grey-2 dark:text-white mt-4 theme-transition')
    if info_div:
        for li in info_div.find_all('li'):
            spans = li.find_all('span')
            if len(spans) == 2:
                if 'objavljen:' == spans[0].text.strip().lower():
                    result['publish_date'] = spans[1].text.strip()
                elif 'kvadratura:' == spans[0].text.strip().lower():
                    size_text = spans[1].text.strip()
                    size_value = re.search(r'(\d+)', size_text)
                    if size_value:
                        result['size'] = float(size_value.group(1))

    # Add this before the return statement
    detailed_description = []
    description_div = soup.find('div', class_='estate-description text-justify text-base font-light text-grey-2 dark:text-white mt-4 [&>*]:transition-all [&>*]:duration-500 [&>*]:ease-in-out')
    if description_div:
        # Get all text content, including nested elements
        for element in description_div.stripped_strings:
            if element.strip():  # Only add non-empty strings
                detailed_description.append(element.strip())
    
    result['detailed_description'] = detailed_description

    # Add this before the return statement, after detailed_description
    phone_numbers = []
    phone_div = soup.find('div', class_='flex lg:hidden items-center gap-3 xs:gap-4 w-full sticky bottom-0 bg-white dark:bg-dark-1 p-4 border-t border-light-blue-2 dark:border-grey-2 z-10 theme-transition overflow-scroll')
    if phone_div:
        phone_links = phone_div.find_all('a', href=lambda x: x and x.startswith('tel:'))
        for link in phone_links:
            phone = link['href'].replace('tel:', '')
            if phone:  # Only add if phone number exists
                phone_numbers.append(phone)
    
    result['phone_numbers'] = phone_numbers
    result['seen'] = 0 #this information is currently not available on the website

    # Find images from the slider
    slider_div = soup.find('div', id='slider')
    if slider_div:
        images = []
        
        # Get images from light-gallery buttons
        gallery_buttons = slider_div.find_all('button', class_='light-gallery-slide')
        for button in gallery_buttons:
            if 'data-src' in button.attrs:
                img_url = button['data-src']
                if img_url not in images:  # avoid duplicates
                    images.append(img_url)
        
        # Get images from splide__list
        splide_list = slider_div.find('ul', class_='splide__list')
        if splide_list:
            for img in splide_list.find_all('img'):
                if 'data-lg-src' in img.attrs:
                    img_url = img['data-lg-src']
                elif 'src' in img.attrs and 'lg.webp' in img['src']:
                    img_url = img['src']
                else:
                    continue
                    
                if img_url not in images:  # avoid duplicates
                    images.append(img_url)
        
        result['images'] = images
    result['source'] = 'https://estitor.com/me'
    return result

def main():
    urls = get_all_listing_urls()
    for url in urls:
        try:
            result = extract_listing_details(url)
            print(f"🏠 Processing : {url}")
            save_listing(result, url, auto_control=True)
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")

if __name__ == "__main__":
    main()
