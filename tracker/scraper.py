import requests
from bs4 import BeautifulSoup
import random
import re
import json
import urllib.parse

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
]

BLACKLIST_TITLES = [
    "Add to your order",
    "Amazon.in",
    "Amazon.com",
    "Shopping Cart",
    "Page Not Found",
    "Robot Check",
    "Welcome to Amazon",
]

def get_headers(url=None):
    # More realistic headers to avoid bot detection
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Referer': 'https://www.google.com/',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Connection': 'keep-alive',
    }
    
    # Flipkart specific: Use mobile UA to bypass 500 errors
    if url and 'flipkart.com' in url:
        headers['User-Agent'] = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        
    return headers

def clean_price(price_str):
    if not price_str:
        return None, '$'
    
    price_str = str(price_str).strip()
    
    # Extract currency symbol
    currency = '$'
    # Common symbols
    if '₹' in price_str: currency = '₹'
    elif '€' in price_str: currency = '€'
    elif '£' in price_str: currency = '£'
    elif '¥' in price_str: currency = '¥'
    
    # Remove common currency symbols and whitespace
    price_str = re.sub(r'[^\d.,]', '', price_str)
    
    # Handle cases like 1,299.00 or 1.299,00
    if ',' in price_str and '.' in price_str:
        if price_str.find(',') < price_str.find('.'):
            # 1,299.00 format
            price_str = price_str.replace(',', '')
        else:
            # 1.299,00 format
            price_str = price_str.replace('.', '').replace(',', '.')
    elif ',' in price_str:
        # 1,299 format (assuming comma is thousands separator if no decimal)
        price_str = price_str.replace(',', '')
        
    try:
        return float(price_str), currency
    except ValueError:
        return None, '$'

def get_product_details(url):
    session = requests.Session()
    try:
        # Use session for cookie handling
        response = session.get(url, headers=get_headers(url), timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Check for CAPTCHA
        if "Robot Check" in soup.title.string if soup.title else "" or "captcha" in response.url.lower():
            return {'title': None, 'price': None, 'currency': '$', 'image_url': None, 'error': "Amazon CAPTCHA detected. Try again later."}

        title = None
        price = None
        currency = '$'
        image_url = None

        # --- Amazon Specific Logic ---
        # Check both input URL and final URL (in case of redirects/short links)
        if 'amazon' in url or 'amzn' in url or 'amazon' in response.url:
            # Title Strategies
            title_selectors = [
                'productTitle', 
                'title', 
                'ebooksProductTitle'
            ]
            for selector in title_selectors:
                t = soup.find(id=selector)
                if t:
                    candidate_title = t.get_text().strip()
                    if candidate_title and candidate_title not in BLACKLIST_TITLES:
                        title = candidate_title
                        break
            
            # Image Extraction Strategy
            # 1. Check for data-a-dynamic-image in common IDs
            img_candidates = ['landingImage', 'imgBlkFront', 'main-image', 'ebooksImgBlkFront']
            for img_id in img_candidates:
                img_tag = soup.find('img', id=img_id)
                if img_tag:
                    # Try to parse the dynamic image JSON
                    dynamic_data = img_tag.get('data-a-dynamic-image')
                    if dynamic_data:
                        try:
                            # It's a JSON string like {"url":[w,h], ...}
                            # We want the largest one (or just the first one)
                            images_dict = json.loads(dynamic_data)
                            if images_dict:
                                # Get the first URL (keys are URLs)
                                image_url = list(images_dict.keys())[0]
                                break
                        except json.JSONDecodeError:
                            pass
                    
                    # Fallback to data-old-hires or src
                    if not image_url:
                        image_url = img_tag.get('data-old-hires') or img_tag.get('src')
                    
                    if image_url:
                        break
            
            # 2. Try dynamic image wrapper if ID lookup failed
            if not image_url:
                dynamic_img = soup.find('div', id='imgTagWrapperId')
                if dynamic_img:
                    img_tag = dynamic_img.find('img')
                    if img_tag:
                         # Try dynamic data here too
                        dynamic_data = img_tag.get('data-a-dynamic-image')
                        if dynamic_data:
                            try:
                                images_dict = json.loads(dynamic_data)
                                if images_dict:
                                    image_url = list(images_dict.keys())[0]
                            except:
                                pass
                        
                        if not image_url:
                            image_url = img_tag.get('src')
            
            # 3. Try finding the main image by class if IDs fail
            if not image_url:
                main_img_class = soup.find('img', class_='a-dynamic-image')
                if main_img_class:
                    image_url = main_img_class.get('src')

        # --- Myntra Specific Logic ---
        elif 'myntra.com' in url:
            # Try to extract data from window.__myx
            scripts = soup.find_all('script')
            for s in scripts:
                if s.string and 'window.__myx' in s.string:
                    match = re.search(r'window\.__myx\s*=\s*({.*});?', s.string, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            if 'pdpData' in data:
                                pdp = data['pdpData']
                                title = pdp.get('name')
                                price_data = pdp.get('price')
                                if price_data:
                                    price = price_data.get('discounted') or price_data.get('mrp')
                                    currency = '₹' # Myntra is India-focused
                                
                                # Try to get image from media
                                media = pdp.get('media', {})
                                albums = media.get('albums', [])
                                if albums and len(albums) > 0:
                                    images = albums[0].get('images', [])
                                    if images and len(images) > 0:
                                        image_url = images[0].get('src')
                                        if image_url:
                                            image_url = image_url.replace('($height)', '720').replace('($width)', '540').replace('($qualityPercentage)', '90')
                                
                                if title and price:
                                    break
                        except:
                            pass
            
            # Fallback for Myntra if JSON fails (will fall through to generic)


        # --- Generic Logic (Fallback) ---
        
        # Title Fallback
        if not title or title in BLACKLIST_TITLES:
            meta_title = soup.find('meta', property='og:title')
            if meta_title:
                title = meta_title['content']
            
            if not title or title in BLACKLIST_TITLES:
                 if soup.title:
                    title = soup.title.string.strip()
            
            if not title or title in BLACKLIST_TITLES:
                h1 = soup.find('h1')
                if h1:
                    title = h1.get_text().strip()
        
        # Clean title if it still contains bad strings (sometimes "Amazon.in: ...")
        if title:
            for bad in BLACKLIST_TITLES:
                if title == bad:
                    title = None
                    break

        # Priority 1: Meta tags (most reliable)
        price_meta_properties = [
            'product:price:amount',
            'og:price:amount',
            'price',
        ]
        
        for prop in price_meta_properties:
            meta_price = soup.find('meta', property=prop) or soup.find('meta', attrs={'name': prop})
            if meta_price:
                cleaned, detected_currency = clean_price(meta_price.get('content'))
                if cleaned:
                    price = cleaned
                    currency = detected_currency
                    break
        
        # Priority 2: Common price classes/IDs if meta failed
        if not price:
            # Regex for currency symbols followed by digits
            # Supports $, ₹, €, £
            price_regex = re.compile(r'[₹$€£]\s*[\d,.]+')
            
            # Search in specific price classes first
            price_classes = [
                'a-price-whole', 'a-offscreen', # Amazon
                'price', 'current-price', 'amount', # Generic
                '_30jeq3', # Flipkart
            ]
            
            for cls in price_classes:
                element = soup.find(class_=cls)
                if element:
                    # For Amazon 'a-price-whole', it might be just "1,299" without symbol
                    text = element.get_text().strip()
                    # If it's just digits and separators, assume it's the price
                    if re.match(r'^[\d,.]+$', text):
                         cleaned, _ = clean_price(text) # Currency might be missing here, default to $ or previous detection
                         if cleaned:
                             price = cleaned
                             # If we found a price but no currency yet, try to find a symbol nearby
                             if 'amazon' in url: # Amazon usually implies local currency if not specified, or we can look for symbol
                                 symbol_span = element.find_previous(class_='a-price-symbol')
                                 if symbol_span:
                                     currency = symbol_span.get_text().strip()
                             elif 'flipkart' in url:
                                 currency = '₹' # Flipkart is mostly India
                             break
                    
                    match = price_regex.search(text)
                    if match:
                        cleaned, detected_currency = clean_price(match.group())
                        if cleaned:
                            price = cleaned
                            currency = detected_currency
                            break
                if price: break

            # Flipkart Mobile Fallback
            if not price and 'flipkart.com' in url:
                # Strategy 3: Regex for JSON fields (finalPrice, fsp)
                # Found in window.__INITIAL_STATE__ or similar blobs
                # e.g. "ppd":{"fsp":51999,"finalPrice":51999,...}
                json_price_regexes = [
                    re.compile(r'"finalPrice":\s*(\d+)'),
                    re.compile(r'"fsp":\s*(\d+)'),
                    re.compile(r'"displayPrice":\s*(\d+)'),
                ]
                
                json_match_found = False
                for regex in json_price_regexes:
                    match = regex.search(str(soup))
                    if match:
                        val = float(match.group(1))
                        json_match_found = True
                        if val > 0:
                            price = val
                            currency = '₹'
                            break
                        # If val is 0, we found the key but it's 0. 
                        # This likely means unavailable/sold out.
                        # We mark json_match_found=True so we don't fall back to aggressive regex.

                if not price and not json_match_found:
                    # Search for price text directly ONLY if JSON method failed to find keys
                    price_text_regex = re.compile(r'₹\d{1,3}(?:,\d{3})*(?:\.\d+)?')
                    price_node = soup.find(string=price_text_regex)
                    if price_node:
                        cleaned, detected_currency = clean_price(price_node)
                        if cleaned:
                            price = cleaned
                            currency = detected_currency

        # Standard meta tag extraction (fallback for Amazon, primary for others)
        if not image_url:
            meta_image = soup.find('meta', property='og:image')
            if meta_image:
                image_url = meta_image.get('content')
        
        if not image_url:
            # Fallback to first large image
            images = soup.find_all('img')
            for img in images:
                src = img.get('src', '')
                if src.startswith('http') and 'logo' not in src.lower() and 'icon' not in src.lower() and 'sprite' not in src.lower():
                    image_url = src
                    break

        return {
            'title': title,
            'price': price,
            'currency': '₹',
            'image_url': image_url,
            'error': None
        }

    except Exception as e:
        return None

def search_amazon(query):
    """Searches Amazon for a product."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.amazon.in/s?k={encoded_query}"
    headers = get_headers(url)
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            # Amazon search results
            items = soup.find_all('div', {'data-component-type': 's-search-result'})
            
            for item in items:
                try:
                    # Updated selector - Amazon changed their HTML structure
                    title_tag = item.find('h2')
                    if title_tag:
                        title_span = title_tag.find('span')
                        title = title_span.text.strip() if title_span else None
                    else:
                        title = None
                    
                    price_tag = item.find('span', class_='a-price-whole')
                    link_tag = item.find('a', class_='a-link-normal')
                    
                    if title_tag and price_tag and link_tag:
                        title = title_tag.text.strip()
                        price_str = price_tag.text.strip()
                        price, _ = clean_price(price_str)
                        
                        # Construct absolute URL
                        link = link_tag.get('href')
                        if link and not link.startswith('http'):
                            link = 'https://www.amazon.in' + link
                            
                        results.append({
                            'source': 'Amazon',
                            'title': title,
                            'price': price,
                            'currency': '₹',
                            'url': link
                        })
                        
                        if len(results) >= 3: break
                except Exception:
                    continue
            return results
    except Exception as e:
        print(f"Amazon search error: {e}")
    return []

def search_flipkart(query):
    """Searches Flipkart for a product (Mobile View) using JSON state."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.flipkart.com/search?q={encoded_query}"
    headers = get_headers(url)
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            # Strategy 1: Parse window.__INITIAL_STATE__ JSON
            scripts = soup.find_all('script')
            json_data = None
            
            for script in scripts:
                if script.string and 'window.__INITIAL_STATE__' in script.string:
                    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*});', script.string)
                    if match:
                        try:
                            json_data = json.loads(match.group(1))
                            break
                        except:
                            pass
            
            if json_data:
                try:
                    # Traverse slots to find products
                    slots = json_data.get('multiWidgetState', {}).get('widgetsData', {}).get('slots', [])
                    for slot in slots:
                        if len(results) >= 3: break
                        
                        try:
                            widget = slot.get('slotData', {}).get('widget', {})
                            products = widget.get('data', {}).get('products', [])
                            
                            if products:
                                for prod in products:
                                    if len(results) >= 3: break
                                    
                                    # Correct structure: prod.value (not prod.productInfo.value)
                                    product_info = prod.get('value', {})
                                    action = prod.get('action', {})
                                    
                                    # Title
                                    titles = product_info.get('titles', {})
                                    title = titles.get('title') or titles.get('newTitle')
                                    
                                    # URL
                                    relative_url = action.get('url')
                                    if not relative_url: continue
                                    
                                    full_url = f"https://www.flipkart.com{relative_url}"
                                    
                                    # Price - Use displayPrice for actual selling price
                                    pricing = product_info.get('pricing', {})
                                    price_val = pricing.get('displayPrice')
                                    
                                    if not price_val:
                                        # Fallback to finalPrice if displayPrice not available
                                        final_price = pricing.get('finalPrice', {})
                                        price_val = final_price.get('value')
                                    
                                    if not price_val:
                                        # Fallback to prices array
                                        prices = pricing.get('prices', [])
                                        for p in prices:
                                            if p.get('name') == 'Selling Price':
                                                price_val = p.get('value')
                                                break
                                    
                                    if title and price_val:
                                        results.append({
                                            'source': 'Flipkart',
                                            'title': title,
                                            'price': float(price_val),
                                            'currency': '₹',
                                            'url': full_url
                                        })
                        except Exception:
                            continue
                except Exception as e:
                    print(f"Flipkart JSON parsing error: {e}")

            # Strategy 2: Fallback to HTML scraping if JSON failed or returned no results
            if not results:
                # Simplify query for matching
                query_words = query.split()[:2] # First 2 words
                if not query_words: return []
                
                # Regex to match at least one word
                pattern = re.compile(r"|".join([re.escape(w) for w in query_words]), re.IGNORECASE)
                
                body = soup.find('body')
                if body:
                    matches = body.find_all(string=pattern)
                    seen_urls = set()
                    
                    for match in matches:
                        if len(results) >= 3: break
                        
                        parent = match.parent
                        if parent.name in ['script', 'style', 'title']: continue
                        
                        # Walk up to find a container that might be a product card
                        container = parent
                        found_price = None
                        found_link = None
                        
                        # Check up to 5 levels up
                        for _ in range(5):
                            container = container.parent
                            if not container: break
                            
                            # Look for price in this container
                            if not found_price:
                                price_text = container.find(string=re.compile(r"₹"))
                                if price_text:
                                    p_str = price_text.strip()
                                    # Ensure it looks like a price
                                    if re.match(r'₹\d', p_str):
                                        found_price = p_str
                            
                            # Look for link
                            if not found_link:
                                if container.name == 'a':
                                    found_link = container.get('href')
                                else:
                                    link_tag = container.find('a')
                                    if link_tag: found_link = link_tag.get('href')
                                    
                            if found_price and found_link:
                                break
                        
                        if found_price and found_link:
                            # Clean up
                            full_link = found_link
                            if not full_link.startswith('http'):
                                full_link = 'https://www.flipkart.com' + full_link
                                
                            if full_link in seen_urls: continue
                            
                            price_val, _ = clean_price(found_price)
                            
                            results.append({
                                'source': 'Flipkart',
                                'title': match.strip()[:50] + "...", # Truncate for display
                                'price': price_val,
                                'currency': '₹',
                                'url': full_link
                            })
                            seen_urls.add(full_link)
                    
            return results
    except Exception as e:
        print(f"Flipkart search error: {e}")
    return []

def search_products(query):
    """Aggregates search results from all marketplaces."""
    results = []
    
    # Search all marketplaces
    results.extend(search_amazon(query))
    results.extend(search_flipkart(query))
    
    # TODO: Add Myntra search when implemented
    # results.extend(search_myntra(query))
    
    # Filter to only exact matches (50% word overlap)
    def is_exact_match(item):
        title_lower = item['title'].lower()
        query_lower = query.lower()
        
        query_words = set(query_lower.split())
        title_words = set(title_lower.split())
        
        # Calculate match score: how many query words are in the title
        match_score = len(query_words & title_words) / len(query_words) if query_words else 0
        
        # Use 50% threshold for better cross-marketplace matching
        # (product titles vary between marketplaces)
        return match_score >= 0.5
    
    # Filter to only exact matches
    exact_matches = [r for r in results if is_exact_match(r)]
    
    # Sort exact matches by price
    exact_matches.sort(key=lambda x: x['price'] if x['price'] else float('inf'))
    
    return exact_matches

