import logging
import requests

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



if __name__ == '__main__':
    app.run(debug=False, port=5000, host='0.0.0.0')
