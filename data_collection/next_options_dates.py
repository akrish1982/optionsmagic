import requests
import re
import json
import datetime

def extract_options_dates(ticker):
    """
    Extracts all available options expiration dates from Yahoo Finance's options page.
    
    Args:
        ticker (str): The stock ticker symbol (e.g., "AAPL").
        
    Returns:
        list: A list of dictionaries with date information (date string and timestamp).
    """
    url = f"https://finance.yahoo.com/quote/{ticker}/options"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            return []
        
        # First try the escaped JSON pattern (\\\"expirationDates\\\":)
        pattern = r'\\\"expirationDates\\\":\[([0-9,]+)\]'
        match = re.search(pattern, response.text)
        
        # Extract and parse the timestamps array
        timestamps_str = "[" + match.group(1) + "]"
        print(f"Extracted timestamps string: {timestamps_str}")
        try:
            timestamps = json.loads(timestamps_str)
        except json.JSONDecodeError as e:
            print(f"Failed to parse timestamps JSON: {e}")
            print(f"Timestamps string: {timestamps_str}")
            return []
        
        # Convert timestamps to readable dates
        date_info = []
        for ts in timestamps:
            
            date_obj = datetime.datetime.fromtimestamp(ts)
            day_after = date_obj + datetime.timedelta(days=1)
            date_str = day_after.strftime("%b %d, %Y")  # Format like "Apr 11, 2025"
            date_info.append({
                "date_string": date_str,
                "timestamp": ts,
                "iso_date": day_after.strftime("%Y-%m-%d")
            })
        
        return date_info
    
    except Exception as e:
        print(f"Error extracting expiration dates: {e}")
        return []

def generate_options_urls(ticker, dates_info, num_dates):
    """
    Generates options page URLs for each expiration date.
    
    Args:
        ticker (str): The stock ticker symbol.
        dates_info (list): List of dictionaries with date information.
        
    Returns:
        list: List of URLs for each expiration date.
    """
    urls = []
    dates = [date_info['iso_date'] for date_info in dates_info]
    for date_info in dates_info:
        urls.append(f"https://finance.yahoo.com/quote/{ticker}/options?date={date_info['timestamp']}")
    
    return urls[:num_dates], dates[:num_dates]

# Example usage
if __name__ == "__main__":
    ticker = "AAPL"
    dates_info = extract_options_dates(ticker)
    
    if dates_info:
        print(f"Found {len(dates_info)} expiration dates for {ticker}:")
        for i, date_info in enumerate(dates_info):
            print(f"{i+1}. {date_info['date_string']} (Timestamp: {date_info['timestamp']})")
        
        # Generate URLs for the first 8 dates or all dates if fewer than 8
        num_dates = min(8, len(dates_info))
        urls, dates = generate_options_urls(ticker, dates_info[:num_dates], num_dates)
        print(f"\nURLs for the next {num_dates} expiration dates:")
        for i, url in enumerate(urls):
            print(f"{i+1}. {dates_info[i]['date_string']}: {url}")
    else:
        print(f"No expiration dates found for {ticker}")