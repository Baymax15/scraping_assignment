from datetime import datetime

from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from pg_python import pg_python as pg_py

Month_INDEX = {'sunday'}

# Website and limits
website_url = 'https://www.ndtv.com/india'
PAGE_LIMIT = 10
IMPLICIT_WAIT_SECONDS = 2
EXPLICIT_WAIT_SECONDS = 10
DEBUG = True

# Selenium driver
driver = webdriver.Firefox()
driver.implicitly_wait(IMPLICIT_WAIT_SECONDS)


# pg_python - database and setup
# db_name = 'postgress'
# username = 'postgres'
# password = 'postgres'
# host_address = 'localhost'
# table_name = 'ndtv_india'
# pgs = pg_py.pg_server(db_name, username, password, host_address)


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

        return result

    def set_date(self, date: str):
        try:
            d = datetime.strptime(date, '%A %B %d %Y')
            self.date = d.strftime('%d-%m-%Y')
            return True
        except ValueError as err:
            if DEBUG:
                print('Error NewsItem:', err)
            return False


def get_page(url: str, page_number: int = 1):
    try:
        web_url = f'{url}/page-{page_number}'

        if DEBUG:
            print('DEBUG get_page:', web_url)

        driver.get(web_url)
        print('got page.')

        page_listing = driver.find_element(By.CLASS_NAME, 'listng_pagntn')
        driver.execute_script("arguments[0].scrollIntoView(true);", page_listing)

        popup = WebDriverWait(driver, 20).until(
            ec.presence_of_element_located((By.CLASS_NAME, 'notnow'))
        )
        popup.click()

        listing_news: WebElement = WebDriverWait(driver, EXPLICIT_WAIT_SECONDS).until(
            ec.presence_of_element_located((By.CLASS_NAME, 'lisingNews'))
        )

        WebDriverWait(driver, 5)
        driver.execute_script("arguments[0].scrollIntoView(true);", listing_news)

        for item in listing_news.find_elements(By.CLASS_NAME, 'news_Itm'):
            # ignore the ad items
            if 'adBG' in item.get_attribute('class').split():
                continue
            item_cont: WebElement = item.find_element(By.CLASS_NAME, 'news_Itm-cont')

            try:
                anchor = item_cont.find_element(By.TAG_NAME, 'a')
                news_item = NewsItem(title=anchor.text.strip(), link=anchor.get_attribute('href'))

                span: WebElement = item_cont.find_element(By.TAG_NAME, 'span')

                # set author
                if auth_anchor := span.find_element(By.TAG_NAME, 'a'):
                    news_item.author = auth_anchor.text.strip()

                # set place and date
                if len(posted_by := span.text.split('|')):
                    date_place = posted_by[-1].split()
                    # ['week', 'long_month', 'date,', 'year,', 'place'...]
                    news_item.place = date_place[4:]

                    date = date_place[:4]
                    news_item.set_date(' '.join(x.strip(',') for x in date))

                print(news_item.to_dict())

            except Exception as err:
                if DEBUG:
                    print('Error get_page:', err)

            # <div class ="news_Itm-cont" >
            #     <h2 class ="newsHdng" >
            #       <a href="{link_here}">{heading_here}</a>
            #     </h2>
            #     <span class="posted-by">
            #       <a href="{author_link_here}">{author_here}</a>|{date_here(week month date, year)}, {place_here}
            #     </span>
            #     <p class ="newsCont">{description_here}</p> </div>
    except exceptions.TimeoutException:
        print('Timed out while waiting for element.')


try:
    get_page(website_url, 1)
except Exception as e:
    print('An error Occurred.\nError:', e)
# finally:
    # driver.close()
