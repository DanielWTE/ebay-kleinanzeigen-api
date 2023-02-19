from flask import Flask, json, request
from api.getInseratDetails import *
from api.scrapeInserate import *
from api.getViews import *

api = Flask(__name__)

# Get details from a specific listing
@api.route('/getInseratDetails', methods=['GET'])
def details():
    url = request.headers['url']
    details = getInseratDetails(url)
    return json.dumps(details)

# Get all inserate listing
@api.route('/getInserateUrls', methods=['GET'])
def urls():
    urls = scrapeInserateUrls()
    return json.dumps(urls)


# Get views from a specific listing
@api.route('/getViews', methods=['GET'])
def viewsGet():
    url = request.headers['url']
    views = getViews(url)
    return json.dumps(views)

if __name__ == '__main__':
    #from waitress import serve
    # serve(api, host="0.0.0.0", port=80)
    api.run(host="0.0.0.0", port=80)
