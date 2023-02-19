import requests
import random

def check_proxy(proxy):
    try:
        response = requests.get('https://google.com', proxies={'http': proxy, 'https': proxy})
        if response.status_code == 200:
            return True
        else:
            return False
    except:
        return False

def getProxy():
    while True:
        # Here you can add your own proxies (HTTP)
        # Example: my_proxies = ['0.0.0.0:80', '0.0.0.1:80']
        my_proxies = ['']
        proxy = random.choice(my_proxies)
        if check_proxy(proxy):
            return proxy
            
working_proxy = getProxy()
print(working_proxy)
