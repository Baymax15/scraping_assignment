FROM ubuntu:focal

RUN apt-get update && apt install python3 python3-pip -y

COPY pn_scraper.py requirements.txt /

RUN python3 -m pip install -r requirements.txt

CMD [ "python3", "./pn_scraper.py" ]