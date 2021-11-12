from bs4 import BeautifulSoup
import time
from datetime import datetime
import requests

from pg_python.pg_python import *

# Provided url
url = 'https://www.ndtv.com/india#pfrom=home-ndtv_mainnavgation'

# No. of pages
page_limit = 10

# seconds of sleep time to wait after a fetch
SLEEP_TIME = 1

# Output file
output = 'output/output.csv'

# Headers to be used while fetching
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:94.0) Gecko/20100101 Firefox/94.0'
}

db_name = 'postgres'
username = 'postgres'
password = 'postgres'
host_address = 'localhost'
table_name = 'ndtv_india'
pgs = pg_server(db_name, username, password, host_address, server='default', application_name='pg_python')

############################################################################################

class News_item:
    """News item, consisting of news title, link to news, date,
    and some optional attributes.
    """

    def __init__(self, title: str, link: str, date: str):
        self.title = title
        self.link = link
        self.date = date

    def set_author(self, author: str):
        self.author = author

    def set_place(self, place: str):
        self.place = place

    def set_description(self, desc: str):
        self.description = desc

    def set_content(self, content: str):
        self.content = content

    def to_dict(self) -> dict:
        result = {'title': self.title, 'link': self.link, 'date': self.date}

        # Setting each attribute if it exists, else empty string
        for attribute in ['author', 'place', 'description', 'content']:
            result[attribute] = getattr(self, attribute, '')

        return result


def get_soup(url, header):
    """Returns the soup object from given url
    """
    page = requests.get(url, headers=header)
    time.sleep(SLEEP_TIME)
    return BeautifulSoup(page.content, 'html5lib')


def get_main_page_list(soup, page_limit):
    """Returns a list of links from the given soup page
    """
    page_list = []
    pageline = soup.find('div', attrs={'class': 'listng_pagntn'})

    for item in pageline.find_all('a'):
        # if 'button' to next or previous page, ignore
        if 'btnLnk' in item.attrs.get('class', []):
            continue

        # since only first {limit} pages
        if int(item.contents[0]) > page_limit:
            break

        # if href not empty, add to list
        if href := item.attrs.get('href', ''):
            page_list.append(href)

    return page_list


def get_news_items(soup):
    """Returns news items from given soup
    """
    # To store results
    news_items = []

    # The news items will be in a div under class: .lisingNews
    news_list = soup.find('div', attrs={'class': 'lisingNews'})

    for item in news_list.find_all('div', attrs={'class': 'news_Itm'}):
        # ignore the adBg items
        if 'adBg' in item.attrs.get('class', []):
            continue

        item_content = item.find('div', attrs={'class': 'news_Itm-cont'})
        anchor = item_content.find('h2', attrs={'class': 'newsHdng'}).find('a')

        span = item_content.find('span', attrs={'class': 'posted-by'})
        author = ''
        date = ''
        place = ['']

        if span.find('a'):
            author = span.find('a').get_text().strip()

        tmp = span.get_text().split('|')
        if len(tmp):
            date_place = span.get_text().split('|')[len(tmp) - 1].strip()
            date_temp, year, *place = [x.strip() for x in date_place.split(', ', maxsplit=2)]
            date = datetime.strptime(f'{date_temp} {year}', '%A %B %d %Y').strftime('%Y-%m-%d')
        news_item = News_item(
            title=anchor.get_text().strip(),
            link=anchor.attrs.get('href', ''),
            date=date
        )

        news_item.set_author(author.replace('\n', ''))
        news_item.set_place(', '.join(place).replace('\n', ''))
        news_items.append(news_item)

    return news_items


def fill_news_content(soup, news):
    """Returns the contents from a news page"""

    if content_desc := soup.find('h2', attrs={'class': 'sp-descp'}):
        news.set_description(content_desc.get_text().strip())

    if content_main := soup.find('div', attrs={'id': 'ins_storybody'}):
        if paras := content_main.findChildren('p', recursive=False):
            content_list = [x.get_text() for x in paras if x.contents]
            news.set_content('\t'.join(content_list))


##########################################################################


print('Task started.')

# Getting main page item list from url
main_page_soup = get_soup(url, headers)

# Contains list of news items from list,
# each to be later populated later with content body from the page
news_items = get_news_items(main_page_soup)

# Getting rest of list pages from main page index and fetch list from each
for page in get_main_page_list(main_page_soup, page_limit):
    page_soup = get_soup(page, headers)
    news_items += get_news_items(page_soup)

# Fetched all items from {page_limit} pages.
print(f'Total news items found: {len(news_items)}')
# Now, filling each with content from the said page

print('Fetching contents...')
for index, news in enumerate(news_items):
    content_soup = get_soup(news.link, headers)
    fill_news_content(content_soup, news)

    if index % 15 == 14:
        print(f'Items in Page {int(index / 15) + 1} fetched.')
# {news_items} contains every required data


# Writing to output.csv file
print(f'Fetching completed.\nWriting to file: {output}')
data_rows = [x.to_dict() for x in news_items]

for row in data_rows:
    write(table_name, row)

print('Printing a sample:')
print(data_rows[0])
print('Task ended.')
