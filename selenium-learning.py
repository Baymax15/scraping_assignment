from datetime import datetime

from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from pg_python import pg_python as pg_py


# Website and limits
website_url = 'https://www.ndtv.com/india'
PAGE_LIMIT = 10
IMPLICIT_WAIT_SECONDS = 5
EXPLICIT_WAIT_SECONDS = 15
DEBUG = False

# Selenium driver
driver = webdriver.Firefox()
driver.implicitly_wait(IMPLICIT_WAIT_SECONDS)

closed_popup = False

# pg_python - database and setup
db_name = 'postgres'
username = 'postgres'
password = 'postgres'
host_address = 'localhost'
table_name = 'ndtv_india'
pgs = pg_py.pg_server(db_name, username, password, host_address)


class NewsItem:
    def __init__(self, title: str, link: str):
        self.title = title
        self.link = link
        self.date = None
        self.author = None
        self.place = None
        self.description = None
        self.content = None

    def to_dict(self):
        result = {'title': self.title, 'link': self.link}

        # Setting each attribute if it exists, else empty string
        for attribute in ['date', 'author', 'place', 'description', 'content']:
            result[attribute] = getattr(self, attribute, '')

        return result

    def set_date(self, date: str):
        try:
            d = datetime.strptime(date, '%A %B %d %Y')
            self.date = d.strftime('%d-%m-%Y')
            return True
        except ValueError as error:
            if DEBUG:
                print('Error NewsItem:', error)
            return False


def close_popup(timeout=20):
    global closed_popup

    if closed_popup:
        return
    try:
        popup = WebDriverWait(driver, timeout).until(
            ec.presence_of_element_located((By.CLASS_NAME, 'notnow'))
        )
        popup.click()
        closed_popup = True
    except exceptions.TimeoutException:
        if DEBUG:
            print('DEBUG close_popup timed out')


def populate_content(news: NewsItem):
    driver.get(news.link)

    content_main = driver.find_element(By.ID, 'ins_storybody')
    if content_desc := driver.find_element(By.CSS_SELECTOR, 'div.sp-hd > h2.sp-descp'):
        news.description = content_desc.text.strip()

    if content_main:
        paras = content_main.find_elements(By.XPATH, './p[not(i)]')
        content_list = [x.text for x in paras if x.text]
        if content_list:
            news.content = '\t'.join(content_list)


def get_page(url: str, page_number: int = 1):
    result = []
    try:
        web_url = f'{url}/page-{page_number}'

        if DEBUG:
            print('DEBUG get_page:', web_url)
        driver.get(web_url)
        if DEBUG:
            print('got page.')

        page_listing = driver.find_element(By.CLASS_NAME, 'listng_pagntn')
        driver.execute_script("arguments[0].scrollIntoView(true);", page_listing)

        close_popup()

        listing_news: WebElement = WebDriverWait(driver, EXPLICIT_WAIT_SECONDS).until(
            ec.presence_of_element_located((By.CLASS_NAME, 'lisingNews'))
        )

        driver.execute_script("arguments[0].scrollIntoView(true);", listing_news)

        for item in listing_news.find_elements(By.CSS_SELECTOR, '.lisingNews > .news_Itm:not(.adBg)'):
            item_cont = item.find_element(By.CLASS_NAME, 'news_Itm-cont')

            # get anchor for title and link
            anchor = item_cont.find_element(By.TAG_NAME, 'a')
            news_item = NewsItem(title=anchor.text.strip(), link=anchor.get_attribute('href'))

            span = item_cont.find_element(By.TAG_NAME, 'span')

            # set author
            if auth_anchor := span.find_element(By.TAG_NAME, 'a'):
                news_item.author = auth_anchor.text.strip()

            # set place and date
            if len(posted_by := span.text.split('|')):
                date_place = posted_by[-1].split()
                # ['week', 'long_month', 'date,', 'year,', 'place'...]
                news_item.place = ' '.join(date_place[4:])

                date = date_place[:4]
                news_item.set_date(' '.join(x.strip(',') for x in date))

            result.append(news_item)

    except exceptions.TimeoutException:
        print('Timed out while waiting for element.')
    finally:
        return result


try:
    for pg_no in range(1, PAGE_LIMIT+1):
        news_items = get_page(website_url, pg_no)
        print('Got page list:', pg_no)
        for n_item in news_items:
            populate_content(n_item)
            pg_py.write(table_name, n_item.to_dict())
except Exception as err:
    print('Error occurred:', err)
finally:
    if not DEBUG:
        driver.close()
