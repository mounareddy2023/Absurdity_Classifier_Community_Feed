import nltk
from string import printable
from nltk.tokenize import word_tokenize
from autocorrect import Speller
import re
from emot.emo_unicode import UNICODE_EMO, EMOTICONS
from nltk.corpus import words
from nltk.stem import WordNetLemmatizer
import json
from pymongo import MongoClient
import logging
from urlextract import URLExtract
from PIL import Image
from skimage import io
import requests
import warnings
warnings.filterwarnings('ignore')

import pytesseract
import wordninja
from collections import Counter

# from dotenv import load_dotenv
with open('config.json') as f:
    secrets = json.load(f)

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

def get_db_connection():
    try:
        Client = MongoClient(secrets['documentdbConnectionURI'])
        db = Client.get_default_database()
        db['corpus'].count_documents({})
        print("Connection Established through DocumentDB")
    except:
        print("Connection to documentdbConnectionURI Failed")
        Client = MongoClient(secrets['mongodbConnectionURI'])
        db = Client.get_default_database()
        db['corpus'].count_documents({})
        print("Connection Established through MongoDB")
    return db

db = get_db_connection()
corp = db.corpus
spam_words_collection = db.spam_words

spell = Speller(lang='en')
lemmatizer = WordNetLemmatizer()

stop_words = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
              'v', 'w', 'x', 'y', 'z', 'an', 'll', 've', 're', 'ma']
greeting_words = ['hi', 'hey', 'hello', 'hey there', 'hi everyone', 'hello there', 'hi there', 'hey everyone',
                  'hey all']

CS_WHITELISTED_COMMENTS = [
    "Hey! Our Beauty Advisors can help you with your concern. Connect with our experts under the personalized beauty advise banner on the MyGlamm app (Monday to Sunday | 10 am to 7 pm) to get a personalized advice.",
    "Hey! Our Customer care team can help with your concern. Please drop an email on hello@myglamm.com or connect with us on Chat option available in Help & Support. We are available between Monday to Sunday (10 am to 7 pm)."
]


def demoji(string):
    '''
    Removing emojis present in a text
    '''
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002500-\U00002BEF"  # chinese char
                               u"\U00002702-\U000027B0"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r' ', string)


def demoticon(text):
    '''
    Removing demoticons present in a text
    '''
    emoticon_pattern = re.compile(u'(' + u'|'.join(k for k in EMOTICONS) + u')')
    return emoticon_pattern.sub(r' ', text)


def deurls(text):
    '''
    Removing URLs present in a text
    '''
    url_pattern = re.compile(r'https?://\S+|www\.\S+')
    return url_pattern.sub(r' ', text)


def utils(text):
    '''
    1. converting text to lower case
    2. removing punctuations and special characters
    3. removing numbers
    4. tokenizing the entire text
    5. removing duplicate words
    6. removing stop words
    6. lemmatizing each word in tokenized list
    '''

    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub('[^A-Z a-z]+', ' ', text)
    text = ' '.join(dict.fromkeys(text.split()))
    return text


def preprocess(text):
    return utils(demoji(demoticon(deurls(text))))


def tokenize(text):
    text_list = word_tokenize(text)
    text_list = [lemmatizer.lemmatize(w) for w in text_list]
    text_list = [w for w in text_list if not w in stop_words]
    return text_list


def valid_whitelisted_comments(post):
    '''
       check if the post has a prefix text with is present in prefix_text_array then return true
    '''
    for whitelisted_comments in CS_WHITELISTED_COMMENTS:
        if whitelisted_comments.lower() == post.lower():
            return True
    return False


def spam_word_in_spam_array(post):
    post_array = list(map(lambda x: x.lower(), post.split()))
    if (spam_words_collection.count_documents({'word': {"$in": post_array}}) > 0) and not valid_whitelisted_comments(
            post):
        return False
    return True


def check_digits(post, printable_digits=2, digits=4, digit_letters=2):
    if (len(set(post).difference(printable))) > printable_digits or len(re.findall('\d', post)) > digits or \
            len(re.findall('(:zero:|:one:|:two:|:three:|:four:|:five:|:six:|:seven:|:eight:|:nine:)',
                           post)) > digit_letters or \
            len(re.findall('(zero|one|two|three|four|five|six|seven|eight|nine)', post, re.IGNORECASE)) > digit_letters:
        return False
    return True


def check_emojis(post):
    if isinstance(post, str):
        try:
            post = preprocess(post)
        except:
            return False
    else:
        return False
    return True


def remove_mentions(post):
    post = re.sub(r"@[\da-z]{24}\b", "", post)
    return post


def remove_hashtags_ids(post):
    post = re.sub(r"#[\da-z]{24}\b", "", post)
    return post


def remove_hashtags_comments(post):
    post = " ".join(filter(lambda x: x[0] != '#', post.split()))
    return post


def whitelisting_emojis(post):
    emojis_pattern = re.compile(pattern="["
                                        u"\U0001F600-\U0001F64F"  # emoticons
                                        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                        u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                        "]+", flags=re.UNICODE)
    post = emojis_pattern.sub(r'', post)
    return post


# function to validate the hashtags in a post
def validate_hashtags_comments(post):
    post = remove_hashtags_ids(post)
    # initializing hashtag_list variable
    hashtag_list = []
    # splitting the post into words
    if len(post.split()) == 1:
        for word in post.split('#'):
            # checking the first character of every word
            # adding the word to the hashtag_list
            hashtag_list.append(word)
    else:
        for word in post.split():
            # checking the first character of every word
            if word[0] == '#':
                # adding the word to the hashtag_list
                hashtag_list.append(word[1:])

    hashtag_list = list(filter(None, hashtag_list))
    # print("Hashtags: ",hashtag_list)
    validation_list = []
    for j in range(0, len(hashtag_list)):
        items = hashtag_list[j]
        if spam_word_in_spam_array(items) == True and check_digits(items, printable_digits=6, digits=6,
                                                                   digit_letters=6) == True and check_emojis(
                items) == True:
            validation_list.append(1)
        else:
            validation_list.append(0)
    if all(validation_list) == True:
        return True
    else:
        return False


def basic_text_check(post):
    if not spam_word_in_spam_array(post):
        return False

    if not check_digits(post, printable_digits=6, digits=6, digit_letters=6):
        return False

    if not check_emojis(post):
        return False

    return True

def rotate_image_manualy(imgGray):
    rtext=''
    for i in range(0,360,15):
        rotated_image = imgGray.rotate(i)
        txt = pytesseract.image_to_string(rotated_image)
        rtext+=txt
    return rtext

def cleaned_text(image_text):
    cleaned_text = wordninja.split(image_text)
    cleaned_text = ' '.join(cleaned_text)
    #cleaned_text = " ".join(w for w in nltk.wordpunct_tokenize(cleaned_text) if w.lower() in set(nltk.corpus.words.words()) or not w.isalpha())
    cleaned_text = ' '.join( [w for w in cleaned_text.split() if len(w) >1] )
    cleaned_text = cleaned_text.split(" ")
    cleaned_text = Counter(cleaned_text)
    cleaned_text = " ".join(cleaned_text.keys())
    return cleaned_text

def check_image_absurdity(url, user_id):
    from app import whitelist_userIDs_col
    try:
        logging.info("Read image from url: "+url)
        image = requests.get(url, stream=True, timeout=1).raw
        image = Image.open(image)
        imgGray = image.convert('L')
        image_text = pytesseract.image_to_string(imgGray).replace("\n", "")
        image_text = cleaned_text(image_text)
        logging.info("Initial pytesseract text_detection: " + str(image_text))
        if len(image_text) > 0 and not basic_text_check(image_text):
            logging.info("pytesseract  basic_text_check- Image is Invalid : " + str(image_text))
            return False
        elif len(image_text) > 0 and image_text.replace(' ','').isdigit():
            logging.info("pytesseract  isdigit- Image is Invalid : " + str(image_text))
            return False
        elif len(image_text) > 0 and basic_text_check(image_text):
            logging.info("pytesseract  basic_text_check- Image is valid : " + str(image_text))
            return True
        elif len(image_text) == 0:
            image_text = rotate_image_manualy(imgGray)
            logging.info("rotate_image_manualy image_text: "+image_text)
            image_text = cleaned_text(image_text)
            logging.info("cleaned_text image_text: "+image_text)
            if len(image_text) > 0 and not basic_text_check(image_text):
                logging.info("rotate_image_manualy  basic_text_check- Image is Invalid : " + str(image_text))
                return False
            elif len(image_text) > 0 and image_text.replace(' ','').isdigit():
                logging.info("rotate_image_manualy  isdigit- Image is Invalid : " + str(image_text))
                return False
            elif len(image_text) > 0 and basic_text_check(image_text):
                logging.info("rotate_image_manualy  basic_text_check- Image is valid : " + str(image_text))
                return True 
            elif len(image_text) == 0:
                try:
                    user_id_data = whitelist_userIDs_col.find_one({'userID': user_id})
                    if user_id_data and user_id_data.get('userID') and (user_id_data.get('whiteListed') == "True"
                                                                        or user_id_data.get('whiteListed')):
                        return True
                    logging.info("  user valiadtion - Image is Invalid : " + str(image_text))
                    return False
                except Exception as e:
                    logging.info("user validation failed for image text : " + str(image_text)+ "and image url: "+str(url)+" and Exception: "+str(e))
                    return False
        else:
            logging.info("  - Image is Valid : " + str(image_text))
            return True
    except Exception as e:
        logging.error("Image Validation Failed : " + str(e))
        return False


def classify(post):
    # Main classification function

    '''
    True: Non-Spam
    False: Spam
    '''

    '''
    Logic 1: If post text is string type, then it preprocessing is applied to the entire post text
             otherwise it is marked as spam

    '''

    # identifying hashtag comments and validating them:
    if "#" in post:
        if validate_hashtags_comments(post) == True:
            post = remove_hashtags_comments(post)
            post = remove_hashtags_ids(post)
        else:
            logging.info("Invalid Hashtags in post: " + str(post))
            return False

    urls = URLExtract().find_urls(post)
    if len(urls) > 0:
        if len(post.split()) == 1:
            return True
        else:
            for url in urls:
                post = post.replace(url, '')

    post = remove_mentions(post)

    if len(post.strip()) > 0:
        # whitelisting important emojis
        post = whitelisting_emojis(post)

        if valid_whitelisted_comments(post):
            logging.info("Valid Post: " + str(post))
            return True

        correct_text = spell(post)
        if correct_text in greeting_words:
            logging.info("Greeting words in Post: " + str(post))
            return False

        if basic_text_check(post):
            logging.info("Valid Post: " + str(post))
            return True
        else:
            logging.info("Failed basic check for post: " + str(post))
            return False
    else:
        logging.info("Valid Post: " + str(post))
        return True
