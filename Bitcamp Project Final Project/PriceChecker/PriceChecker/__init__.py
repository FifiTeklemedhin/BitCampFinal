
import azure.functions as func

import datetime
import logging
# Download the helper library from https://www.twilio.com/docs/python/install
import os
from twilio.rest import Client
import requests
import requests #html requests
from bs4 import BeautifulSoup
import pyodbc

server = 'bitcamp.database.windows.net'
database = 'PriceScraper'
username = 'fi.leul3562'
password = 'Mrs.McKitty101'
cnxn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+ password)
cursor = cnxn.cursor()


def main(mytimer: func.TimerRequest) -> None:
    phonenumbers = get_Database_Information()[0]
    names = get_Database_Information()[1]
    links = get_Database_Information()[2]
    original_prices = get_Database_Information()[3]
    current_prices = get_Database_Information()[4]
    percentages = get_Database_Information()[5]
    durations = get_Database_Information()[6]

    increased_from_current = price_increased_from_current(current_prices, links, phonenumbers, names)
    increased_from_baseline = price_increased_from_baseline(original_prices, links, phonenumbers, percentages, current_prices, names)
    reached_durations = duration_reached(phonenumbers, durations, names, links, current_prices)

    send_messages(increased_from_current, increased_from_baseline, reached_durations)
    
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('DATA: %s', get_Database_Information())

def send_messages(increased_from_current, increased_from_baseline, reached_durations):
    
    for i in increased_from_current:
        phonenumber = i[0]
        name = i[1]
        old_price = i[2]
        current_price = i[3]
        link = i[4]
        send_message(phonenumber, "Product {} has increased in price from ${} to ${}\nLink to product: {}".format(name[0], old_price, current_price, link[0]))

    for i in increased_from_baseline:
        phonenumber = i[0]
        name = i[1]
        current_price = i[2]
        link = i[3]
        send_message(phonenumber, "Product {} meets your ideal discount percentage at ${}!\nLink to product: {}".format(name[0], current_price, link[0]))
    
    for i in reached_durations:
        phonenumber = i[0]
        name = i[1]
        current_price = i[2]
        link = i[3]
        send_message(phonenumber, "The set duration for {} is complete! The current price for this product is ${}\nLink to product: {}".format(name[0], current_price, link[0]))

#TODO: update all current prices after seen if increased from past current
#TODO: change duration to date in weeks from the day inputted

#if price increases from current
def price_increased_from_current(current_prices, links, phonenumbers, names):
    increased_notifs = []

    for i in range(len(current_prices)):
        updated_current_price = scrape_price(links[i], current_prices[i])
        if updated_current_price > current_prices[i]:
            increased_notifs.append([phonenumbers[i], names[i], current_prices[i], updated_current_price, links[i]])
    return increased_notifs
    #use to send to phone number 'price for <item> has increased from <old current> to <new current>

#if price is within baseline percentage
def price_increased_from_baseline(original_prices, links, phonenumbers, percentages, current_prices, names):
    baseline_notifs = []

    for i in range(len(original_prices)):
        original_price = original_prices[i]
        baseline_price = original_price - (original_price * percentages[i] * .01)
        updated_current_price = scrape_price(links[i], current_prices[i])
        current_price = current_prices[i]
        if current_price <= baseline_price:
            baseline_notifs.append([phonenumbers[i], names[i], updated_current_price, links[i]])
    return baseline_notifs

#if duration reached
def duration_reached(phonenumbers, durations, names, links, current_prices):
    duration_notifs = []
    
    today = datetime.date.today()

    for i in range(len(durations)):
        updated_current_price = scrape_price(links[i], current_prices[i])
        if(durations[i] == 0):
            duration_notifs.append([phonenumbers[i], names[i], updated_current_price, links[i]])
    
    return duration_notifs
def scrape_price(URL: str, current_price):
    headers = ({'User-Agent':
            'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
            'Accept-Language': 'en-US, en;q=0.5'})

    '''
    URL = str(URL)
    if 'dp/' in URL:
        url_short = URL[URL.index('dp/'):]
        if '?' in url_short:
            url_short = url_short[: URL.index('?')]
    '''
    

    page = requests.get(URL[0], headers=headers) #response.text gets page and html
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
        return current_price
    price = price_tag.get_text()
    #gets the lowest price if a range is listed
    if('-' in price):
        price = price[:price.index('-')]

    #turn into number
    price = price.replace('$', '')
    price = float(price)
    return price

def send_message(phonenumber, message): 
    # Your Account Sid and Auth Token from twilio.com/console
    # and set the environment variables. See http://twil.io/secure
    account_sid = 'ACe2b2df1f6ee8ba76efa28057641a1ba6'
    auth_token = '6070242aabd73eaad160f9e287dffe6a'
    client = Client(account_sid, auth_token)
    to_str = '+1{}'.format(phonenumber)
    message = client.messages \
                    .create(
                        body=message,
                        from_='+12057515364',
                        to= to_str[0:len(to_str)-1]
                    )

    print(message.sid)

def get_Database_Information():
    phonenumbers = []
    names = []
    links = []
    original_prices = []
    current_prices = []
    percentages = []
    durations = []

    cursor.execute('SELECT phonenumber,link,original_price FROM dbo.ScrapedData;')
    row = cursor.fetchone()
    row_str = ""
    while row:
        row_str += row.__repr__() + "\n"
        row = cursor.fetchone()

    # get all of each type of data
    cursor.execute('SELECT phonenumber FROM dbo.ScrapedData;')
    row = cursor.fetchone() 
    while row:
        row_str = row.__repr__()
        row_str = row_str.replace('(','')
        row_str = row_str.replace(')','')
        row_str = row_str.replace(',','')
        row_str = float(row_str)
        phonenumbers.append(row_str)
        row = cursor.fetchone()

    cursor.execute('SELECT item_name FROM dbo.ScrapedData;')
    row = cursor.fetchone()
    while row:
        row_str = row.__repr__()
        row_str = row_str.replace('(','')
        row_str = row_str.replace(')','')
        row_str = row_str.replace(',','')
        names.append(row)
        row = cursor.fetchone()

    cursor.execute('SELECT link FROM dbo.ScrapedData;')
    row = cursor.fetchone()
    while row:
        row_str = row.__repr__()
        row_str = row_str.replace('(','')
        row_str = row_str.replace(')','')
        row_str = row_str.replace(',','')
        links.append(row)
        row = cursor.fetchone()
    
    cursor.execute('SELECT original_price FROM dbo.ScrapedData;')
    row = cursor.fetchone()
    while row:
        row_str = row.__repr__()
        row_str = row_str.replace('(','')
        row_str = row_str.replace(')','')
        row_str = row_str.replace(',','')
        row_str = row_str.replace(' ', '')
        row_str = float(row_str)
        original_prices.append(row_str)
        row = cursor.fetchone()
    
    cursor.execute('SELECT current_price FROM dbo.ScrapedData;')
    row = cursor.fetchone()
    while row:
        row_str = row.__repr__()
        row_str = row_str.replace('(','')
        row_str = row_str.replace(')','')
        row_str = row_str.replace(',','')
        row_str = row_str.replace(' ', '')
        row_str = float(row_str)
        current_prices.append(row_str)
        row = cursor.fetchone()

    cursor.execute('SELECT baseline_percentage FROM dbo.ScrapedData;')
    row = cursor.fetchone()
    while row:
        row_str = row.__repr__()
        row_str = row_str.replace('(','')
        row_str = row_str.replace(')','')
        row_str = row_str.replace(',','')
        row_str = row_str.replace(' ', '')
        row_str = float(row_str)
        percentages.append(row_str)
        row = cursor.fetchone()

    cursor.execute('SELECT duration FROM dbo.ScrapedData;')
    row = cursor.fetchone()
    while row:
        row_str = row.__repr__()
        row_str = row_str.replace('(','')
        row_str = row_str.replace(')','')
        row_str = row_str.replace(',','')
        row_str = row_str.replace(' ', '')
        row_str = float(row_str)
        durations.append(row_str)
        row = cursor.fetchone()

    return phonenumbers, names, links, original_prices, current_prices, percentages, durations

    def get_current_prices(phonenumbers, prices, urls):

        for i in range len(urls):
            if(scrape_price(urls[i]) != prices[i]):
                cursor.execute('UPDATE dbo.ScrapedData SET current_price = {} WHERE phonenumber LIKE \'%{}%\' AND link LIKE \'%{}%\';'.format(scrape_price(url[i]), 8015587019, https://www.amazon.com/dp/B07XS9C9PV))
                cursor.commit()
