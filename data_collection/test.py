import pandas as pd
from bs4 import BeautifulSoup
import requests

def get_ticker(ticker):
    # ---------- Pulling the data from chosen stock ticker ----------#

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0"
    }
    # url = "https://finviz.com/quote.ashx?t=" + ticker.upper()
    url = "https://finviz.com/screener.ashx?v=111&f=cap_mega,sh_opt_option&r=1"
    req = requests.get(url, headers=headers)
    # print(req.text)
    # get table from the req
    soup = BeautifulSoup(req.text, 'html.parser')
    # print(soup.find('table', class_='table-light'))
    # print(soup.select_one('table').prettify())
    print(soup.find(id='screener-content').prettify())
    # find <table class="table-light">
    # print(soup.select_one('table.table-light'))


    # table = pd.read_html(req.text, attrs={"class": "snapshot-table2"})
    # df = table[0]
    # return (df[1][3], df[1][2])


get_ticker("AAPL")