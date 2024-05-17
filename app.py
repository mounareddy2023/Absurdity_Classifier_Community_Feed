import logging
import requests

from crm.crm_service import CrmService
from feed.feed_service import FeedService
from rto.rto_service import RtoService
from services.tag_modification import TagModificationService
from services.edd import EddService
from flask import Flask, request, jsonify
from flask_redis import FlaskRedis
from rediscluster import RedisCluster
import request_id
import logging
#logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)

from main import *
from nltk.corpus import words
from pymongo import MongoClient

# Client = pymongo.MongoClient("mongodb://localhost:27017/")

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

with open('config.json') as f:
    secrets = json.load(f)
    app.config.update(secrets)


if 'REDIS_CLUSTER_URL' in secrets:
    startup_nodes = secrets['REDIS_CLUSTER_URL']
    redis_client = RedisCluster(startup_nodes=startup_nodes, decode_responses=False, skip_full_coverage_check=True)
else:
    redis_client = FlaskRedis(app)

# MONGO_USERNAME = secrets["MONGO_USERNAME"]
# MONGO_PASSWORD = secrets["MONGO_PASSWORD"]
# MONGO_HOST = secrets["MONGO_HOST"]
# MONGO_PORT = secrets["MONGO_PORT"]
# MONGO_DB = secrets["MONGO_DB_NAME"]


# Client = MongoClient(
#     host=MONGO_HOST,
#     port=MONGO_PORT,
#     username=MONGO_USERNAME,
#     password=MONGO_PASSWORD,
#     authSource="admin",
#     authMechanism="SCRAM-SHA-1"
# )


whitelist_userIDs_col = db["whitelist_userIDs"]
db_dynamic_pricing = db["dynamic_pricing"]
db_crm_order_revision = db["crm_order_revision"]


@app.route('/pushUserIDcron', methods = ['POST'])
def pushUserID_cron():
    if request.method == 'POST':
        data = request.get_json()
        count = 0
        for record in data:
            value = list(record.values())
            userID = value[0]
            whiteListed = value[1]
            if(whitelist_userIDs_col.find_one({"userID": userID}) == None):
                whitelist_userIDs_col.insert_one({"userID": userID,"whiteListed": whiteListed})
            else:
                # print("userID - ",userID," Already exits")
                pass
            count+=1
            # print("count - ",count,"/", len(data))
    return jsonify({"Response" : "Pushed the userIDs to corpus Successfully"})

@app.route('/updateUserID', methods = ['POST'])
def updatewhitelist_userIDs():
    if request.method == 'POST':
        inputs = request.get_json()
        userID = inputs["userID"]
        whiteListed = inputs["whiteListed"]
        query = {"userID": userID}
        if(whiteListed == "True") & (whitelist_userIDs_col.find_one({'userID': userID}) != None):
            new_values = {"$set": {"whiteListed": True}}
            whitelist_userIDs_col.update_one(query,new_values)
        elif(whiteListed == "False") & (whitelist_userIDs_col.find_one({'userID': userID}) != None):
            new_values = {"$set": {"whiteListed": False}}
            whitelist_userIDs_col.update_one(query,new_values)

    return jsonify({"Response": "successfully updated userID"})

@app.route('/addUserID', methods = ['POST'])
def addwhitelist_userIDs():
    if request.method == 'POST':
        inputs = request.get_json()
        userID = inputs["userID"]
        whiteListed = inputs["whiteListed"]

        if(whiteListed == "True") & (whitelist_userIDs_col.find_one({'userID': userID}) == None):
            whitelist_userIDs_col.insert_one({"userID": userID, "whiteListed": True})
        elif(whiteListed == "False") & (whitelist_userIDs_col.find_one({'userID': userID}) == None):
            whitelist_userIDs_col.insert_one({"userID": userID, "whiteListed": False})
    return jsonify({"Response": "successfully added userID"})


@app.route('/deleteUserID', methods = ['DELETE'])
def delete_userIDs():
    if request.method == 'DELETE':
        inputs = request.get_json()
        userID = inputs["userID"]
        whitelist_userIDs_col.delete_one({"userID": userID})

    return jsonify({"Response": "successfully deleted userID"})


def request_content_validation(validations, user_id):
    validation_response = {"validations": [], "aggregation": {}}
    for validation in validations:
        if validation['type'] == 'imageUrl':
            try:
                url = validation.get('url')
                validation_response["validations"].append({
                                    "type": "imageUrl",
                                    "passed": check_image_absurdity(url, user_id)
                                })
            except Exception as e:
                logging.error(e)
                validation_response["validations"].append({
                                    "type": "imageUrl",
                                    "passed": False})
        if validation['type'] == 'text':
            validation_response["validations"].append({"type": "text", "passed": classify(validation['text'])})

    validation_response["aggregation"]["validationOverall"] = True
    for validation in validation_response["validations"]:
        if not validation["passed"]:
            validation_response["aggregation"]["validationOverall"] = False
            break
    return validation_response


@app.route('/content/validation', methods=['POST'])
def user_content_validation():
    user_id = request.get_json().get('userID', "")
    validations = request.get_json().get('validations', [])
    response = request_content_validation(validations, user_id)
    return jsonify(response)


@app.route('/validatepost', methods=['GET', 'Post'])
def validatepost():
    #try:
        if request.method == 'POST':
            posts = request.get_json()
            posts = posts['post']
            results = []

            for post in posts:
                if isinstance(post, str):
                    result = classify(post)
                    results.append(result)
                else:
                    results.append(False)

            logging.info("results: " +str(results))

            return jsonify({"Response": results})
    #except:
     #   print("error")


@app.route('/updatecorp', methods = ['GET', 'Post'])
def updatecorp():
    if request.method == 'POST':
        inputs = request.get_json()
        words = inputs["words"]
        words = words.lower().split()
        flag = inputs["flag"]

        if(flag == "update"):
            for word in words:
                if(corp.find_one({'word': word}) == None):
                    corp.insert_one({"word": word})
        else:
            for word in words:
                if(corp.find_one({'word': word}) != None):
                    corp.delete_one({"word": word})

        if(flag == "update_spam"):
            for word in words:
                if(spam_words_collection.find_one({'word': word}) == None):
                    spam_words_collection.insert_one({"word": word})
        elif(flag == "delete_spam"):
            for word in words:
                if(spam_words_collection.find_one({'word': word}) != None):
                    spam_words_collection.delete_one({"word": word})

    return jsonify({"Response": "success"})

@app.route('/make_mongo', methods = ['GET', 'Post'])
def make_mongo():

    if request.method == 'GET':
        with open('mycorp.txt', 'r') as file:
            wordlist = file.read().split()

        WordList = []
        for word in wordlist:
            WordList.append({"word": word})

        for word in words.words():
            WordList.append({"word": word})

        corp.insert_many(WordList)

    return jsonify({"Response" : "Populated the word corpus"})

@app.route('/makeSpamCollection', methods = ['GET', 'Post'])
def make_spam_collection():
    if request.method == 'GET':
        with open('spam_words.txt', 'r', encoding='utf8') as file:
            wordlist = file.read().split(',')

        WordList = []
        for word in wordlist:
            WordList.append({"word": word})

        spam_words_collection.insert_many(WordList)

    return jsonify({"Response" : "Populated the word corpus"})

@app.route('/checkSpamCollection', methods = ['GET'])
def check_spam_collection():
    if request.method == 'GET':
        words = request.args.get("words")
        words = words.lower().split()
        flag = request.args.get("flag")
        results = []
        if(flag == "check_corp"):
            for word in words:
                if(corp.find_one({'word': word}) == None):
                    results.append(False)
                else:
                    results.append(True)
        elif(flag == "check_spam"):
            for word in words:
                if(spam_words_collection.find_one({'word': word}) == None):
                    results.append(False)
                else:
                    results.append(True)
    return jsonify({"Response" : results })


@app.route('/ping', methods = ['GET', 'Post'])
def foo():
    return jsonify({"bar":True})


@app.route('/article/tag/modification', methods=['GET'])
def get_article_tag_modifications():
    """
    tag modifications API for getting article tag modifications
    """
    page = request.args.get('page', 0)
    response = {
        "name": "OK",
        "status": True,
        "code": 200,
        "message": "Modifications added.",
        "data": []
    }
    try:
        response['data'] = TagModificationService.get_tag_modifications(page=int(page))
    except ValueError as e:
        response['message'] = e
    return jsonify(response)


@app.route('/article/tag/modification', methods=['POST'])
def update_article_tag_modifications():
    """
    tag modifications API for adding article tag modifications
    tag_modifications = [
        {
            "type": "stopword",
            "key": "example"
        },
        {
            "type": "substitution",
            "key": "example",
            "values": ["substitution"]
        },
        {
            "type": "association",
            "key": "example",
            "values": ["association"]
        }
    ]
    """
    tag_modifications = request.get_json()
    response = {
        "name": "OK",
        "status": True,
        "code": 200,
        "message": "Modifications added."
    }
    try:
        TagModificationService.add_tag_modifications(tag_modifications)
    except ValueError as e:
        response['message'] = e
    return jsonify(response)


@app.route('/article/tag/modification', methods=['DELETE'])
def delete_article_tag_modifications():
    """
    tag modifications API for deleting article tag modifications
    tag_modifications = [
        {
            "type": "stopword",
            "key": "example"
        },
        {
            "type": "substitution",
            "key": "example",
            "values": ["substitution"]
        },
        {
            "type": "association",
            "key": "example",
            "values": ["association"]
        }
    ]
    """
    tag_modifications = request.get_json()
    response = {
        "name": "OK",
        "status": True,
        "code": 200,
        "message": "Modifications deleted."
    }
    try:
        TagModificationService.delete_tag_modifications(tag_modifications)
    except ValueError as e:
        response['message'] = e
    return jsonify(response)


@app.route('/delivery/estimate', methods = ['POST'])
def delivery_estimate():
    """
    deploying a dummy response for EDD to start backend development
    """
    delivery_lines = request.get_json()
    response = {
        "name": "OK",
        "status": True,
        "code": 200,
        "message": "",
        "data": {
            "products": [],
            "overall": {}
        }
    }

    if isinstance(delivery_lines, list) and len(delivery_lines) > 0:
        pincode = None
        product_id = None
        min_days = None
        max_days = None
        extra_days = None
        edd_service = EddService()
        for delivery_line in delivery_lines:
            pincode = delivery_line.get("pincode", None)
            product_id = delivery_line.get("productId", None)
            vendor_code = delivery_line.get("vendorCode", request.args.get('vendorCode', 'mgp'))
            estimated_delivery_data = edd_service.get_estimated_delivery_data(pincode, product_id, vendor_code,
                                                                              request.args.get('countryFilter'))
            delivery_line_edd = {
                "pincode": pincode,
                "productId": product_id,
                "minDays": estimated_delivery_data.get('min', 5),
                "maxDays": estimated_delivery_data.get('max', 7),
                "extraDays": estimated_delivery_data.get('extra_days', 0),
                "message": ""
            }
            extra_days = delivery_line_edd.get("extraDays", None)
            if min_days is None or min_days > delivery_line_edd['minDays']:
                min_days = delivery_line_edd['minDays']
            if max_days is None or max_days < delivery_line_edd['maxDays']:
                max_days = delivery_line_edd['maxDays']
            response["data"]["products"].append(delivery_line_edd)
        response["data"]["overall"] = {
            "pincode": pincode,
            "productId": product_id,
            "minDays": min_days,
            "maxDays": max_days,
            "extraDays": extra_days,
            "message": ""
        }
    return jsonify(response)


@app.route('/community/feed', methods=['GET'])
def community_feed():
    """
    Community feed API
    """
    feed_service = FeedService()
    user_id = request.headers.get('userid')
    if user_id in ['community', 'public']:
        user_id = None
    response = feed_service.get_feed(user_id=user_id, feed_after=request.args.get('feedAfter'),
                                     variant=request.args.get('variant', 'default'),
                                     limit=int(request.args.get('limit', 8)),
                                     vendor_code=request.args.get('vendorCode', 'mgp'),
                                     country_filter=request.args.get('countryFilter', 'IND'),
                                     language_filter=request.args.get('languageFilter', 'EN'))
    response['userId'] = user_id if user_id else ""
    return jsonify(response)


@app.route('/community/feed/check', methods=['GET', 'POST'])
def community_feed_check():
    """
    Community feed check API
    """
    feed_service = FeedService()
    response = feed_service.check_feed_data(action=request.args.get('action', ""), key=request.args.get('key', ""),
                                            arg1=request.args.get('arg1', ""), arg2=request.args.get('arg2', ""))
    return jsonify(response)


@app.route('/community/trending', methods=['GET'])
def community_trending_item():
    """
    Community feed check API
    """
    feed_service = FeedService()
    response = feed_service.get_trending_data(entity_type=request.args.get('type', "question"),
                                              life_stage=request.args.get('lifeStage', None),
                                              vendor_code=request.args.get('vendorCode', 'mgp'),
                                              country_filter=request.args.get('countryFilter', 'IND'),
                                              language_filter=request.args.get('languageFilter', 'EN'))
    return jsonify(response)


@app.route('/rto/prediction', methods=['POST'])
def rto_prediction():
    """
    Community feed check API
    {
    "cart": {
     "items": [
       {"sku": "sku1", "brand": "brand1"}
     ]
    },
    "oldOrderStatus": {"rto": 2, "delivered": 1}
    }
    """
    user_data = request.get_json()
    logging.info("RTO User Data : " + str(user_data))
    rto_service = RtoService()
    rto_score, rto_flag, reason = rto_service.rto_prediction(vendor_code=request.args.get('vendorCode', 'mgp'),
                                           country_filter=request.args.get('countryFilter', 'IND'),
                                           language_filter=request.args.get('languageFilter', 'EN'),
                                           user_data=user_data)
    getRequestId = request_id.get_request_id(request)
    data = {
         "request_id" : getRequestId,
         "rto_flag" : rto_flag,
         "rto_score" : rto_score,
         "reason" : reason 
     }
    response = {
        "name": "OK",
        "status": True,
        "code": 200,
        "data": data
    }
    logging.info("RTO response : " + str(response))
    return jsonify(response)


@app.route('/crm/dynamic', methods=['GET'])
def crm_dynamic():
    """
    """
    crm_service = CrmService()
    response, status_code = crm_service.get_programmatic_crm(user_id=request.args.get('userId', None),
                                                             template_id=request.args.get('templateId', None),
                                                             sku=request.args.get('sku', None),
                                                             vendor_code=request.args.get('vendorCode', 'mgp'),
                                                             language_filter=request.args.get('languageFilter', 'EN'),
                                                             country_filter=request.args.get('countryFilter', 'IND'))
    response["userId"] = request.args.get('userId', None)
    response["templateId"] = request.args.get('templateId', None)
    response["sku"] = request.args.get('sku', None)
    return jsonify(response), status_code


@app.route('/crm/order/discount', methods=['POST'])
def crm_order_discount():
    """

    """
    order_data = request.get_json().get('order', {})
    crm_service = CrmService()
    response = crm_service.get_order_discount(order_data=order_data,
                                              vendor_code=request.args.get('vendorCode', 'mgp'),
                                              country_filter=request.args.get('countryFilter', 'IND'),
                                              language_filter=request.args.get('languageFilter', 'EN'),)
    return jsonify(response)


@app.route('/crm/order/revision', methods=['POST'])
def crm_order_revision():
    """

    """
    order_data = request.get_json().get('order', {})
    crm_service = CrmService()
    response = crm_service.add_order_revision(order_data=order_data,
                                              vendor_code=request.args.get('vendorCode', 'mgp'),
                                              country_filter=request.args.get('countryFilter', 'IND'),
                                              language_filter=request.args.get('languageFilter', 'EN'),)
    return jsonify(response)


@app.route('/sku/dynamic/coupon', methods=['POST'])
def sku_dynamic_coupon():
    """
    Community feed check API
    {
      "sku": "sku111",
      "coupons": {"default": "DS40"},
      "productName": "productName",
      "imageURL": "https://files.myglamm.com/site-images/400x400/INDG1.jpg",
      "url": "https://myglamm.in/S1b8vavS28",
      "productId": "<productId>",
      "similarProducts": [{}]
    }
    """
    sku_coupon_data = request.get_json()
    crm_service = CrmService()
    response = crm_service.update_sku_coupon(sku_coupon_data=sku_coupon_data,
                                             vendor_code=request.args.get('vendorCode', 'mgp'),
                                             country_filter=request.args.get('countryFilter', 'IND'),
                                             language_filter=request.args.get('languageFilter', 'EN'))
    return jsonify(response)


if __name__ == '__main__':
    app.run(debug=False, port=5000, host='0.0.0.0')
