import logging
import azure.functions as func

import requests #html requests
from bs4 import BeautifulSoup

import pyodbc

#TODO: update all current prices after seen if increased from past current
#TODO: change duration to date in weeks from the day inputted
#TODO: add parameter, scrape it in inputter

server = 'bitcamp.database.windows.net'
database = 'PriceScraper'
username = 'fi.leul3562'
password = 'Mrs.McKitty101'
cnxn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+ password)
cursor = cnxn.cursor()


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    phonenumber = req.params.get('phonenumber')
    url = req.params.get('url')
    baseline_percentage = req.params.get('baseline_percentage')
    duration = req.params.get('duration')
    name = req.params.get('name')
    
    all_vals = {"phone": phonenumber, "url": url, "percent": baseline_percentage, "dur": duration, "name": name}
    null_valls = ""

    if not phonenumber:
        null_valls += "phonenumber, "
    if not url:
        null_valls += "url, "
    if not baseline_percentage:
        null_valls += "baseline_percentage, "
    if not duration:
        null_valls += "duration, "
    if not name:
        null_valls += "name" 

    if url and scrape_price(url) == "incompatible":
        return func.HttpResponse(
             f'url unsupported',
             status_code=200
        )
    if url and phonenumber and baseline_percentage and duration and name:
        return func.HttpResponse(update_database(url, phonenumber, baseline_percentage, duration, scrape_price(url), scrape_price(url), name))
    
    else:
        return func.HttpResponse(
             null_valls,
             status_code=200
        )

def scrape_price(URL: str):
    headers = ({'User-Agent':
            'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
            'Accept-Language': 'en-US, en;q=0.5'})

    page = requests.get(URL, headers=headers) #response.text gets page and html
    soup = BeautifulSoup(page.text, 'html.parser')

    price_tag = soup.find(id='priceblock_ourprice')
    if price_tag is None:
        price_tag = soup.find(id='priceblock_dealprice')
    if price_tag is None:
        price_tag = soup.find('data-asin-price')
    if price_tag is None:
        price_tag = soup.find(id='price_inside_buybox')
    if price_tag is None:
        price_tag = soup.find(class_='p13n-sc-price')
    if price_tag is None:
        return "incompatible"
    price = price_tag.get_text()
    #gets the lowest price if a range is listed
    if('-' in price):
        price = price[:price.index('-')]

    #turn into number
    price = price.replace('$', '')
    price = float(price)
    return price

def update_database(url:str, phonenumber:int, baseline_percentage:float, duration:float, original_price:float, current_price:float, item_name: str):
    row_str = ""
    cursor.execute("INSERT INTO dbo.ScrapedData VALUES (?,?,?,?,?,?,?)", int(phonenumber),float(baseline_percentage), float(duration), float(scrape_price(url)), float(scrape_price(url)), url, item_name) 
    
    cnxn.commit()
    cursor.execute('''WITH removing AS (
    SELECT 
        phonenumber, 
        baseline_percentage, 
        duration, 
        original_price,
        current_price, 
        link,
        ROW_NUMBER() OVER (
            PARTITION BY 
                phonenumber,  
                link
            ORDER BY 
                phonenumber, 
                link
        ) row_num
        FROM 
            dbo.ScrapedData
        )
        DELETE FROM removing
        WHERE row_num > 1;''')

    cnxn.commit()
    cursor.execute("SELECT * FROM [PriceScraper].[dbo].[ScrapedData]")
    row = cursor.fetchone()
    while row:
        row_str += row.__repr__() + "\n"
        row = cursor.fetchone()
    return row_str

    