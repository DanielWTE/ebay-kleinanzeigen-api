from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from lxml import etree
from bs4 import BeautifulSoup
import urllib
import random
import datetime
import sys
import json
import requests
import time

from functions.getProxy import *
from functions.getUserAgent import *

def scrapeInserateUrls():
    chrome_driver_path = '/usr/local/bin/chromedriver'
    driver = None
    try:
        start_time = time.time()

        proxy = getProxy()

        url = "https://www.ebay-kleinanzeigen.de/s-seite:1"

        prox_options = {
        'proxy': {
            'http': proxy
        }
        }

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--user-agent='+GET_UA())
        options.add_argument('--incognito')
        driver = webdriver.Chrome(service=Service(chrome_driver_path), options=options, seleniumwire_options=prox_options)

        driver.get(url)

        elements = driver.find_elements(By.CLASS_NAME, 'aditem')
        urlArray = []
        for element in elements:
            urlArray.append("https://www.ebay-kleinanzeigen.de"+element.get_attribute('data-href'))

        data = {'urls':urlArray}

        end_time = time.time()
        # print("Scraped "+str(len(urlArray))+" urls")
        print("scrapeInserate.py execution:")
        print(str(round(end_time - start_time, 2))+" seconds")
        print("Proxy: "+proxy)
        driver.quit()
        return (data)
    except Exception as e:
        print(e)
        driver.quit()
        return (None)
