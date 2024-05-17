FROM python:3.8

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN apt-get update \
    && apt-get install tesseract-ocr -y 

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

ADD . /code

RUN python3 -m nltk.downloader punkt

RUN python3 -m nltk.downloader words

RUN python3 -m nltk.downloader wordnet

RUN chmod -R 777 /code/gunicorn_conf.py
RUN chmod -R 777 /code/app.py

CMD ["gunicorn", "--conf", "gunicorn_conf.py", "--bind", "0.0.0.0:5000", "app:app"]
