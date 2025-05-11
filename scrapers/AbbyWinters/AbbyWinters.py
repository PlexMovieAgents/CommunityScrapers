import base64
import os
import json
import sys
import re
from urllib.parse import urlparse, urlencode
from datetime import datetime

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(
    os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    from py_common import log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

try:
    from bs4 import BeautifulSoup # requires v4.10.0 and above
except ModuleNotFoundError:
    print("You need to install the BeautifulSoup module (v4.10.0+). (https://pypi.org/project/beautifulsoup4/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install beautifulsoup4", file=sys.stderr)
    sys.exit()

def scrape_gallery_url(url, result):
    result['performers'] = []
    response = requests.get(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'
    }, timeout=(3, 6))
    # log.debug(response.text)
    soup = BeautifulSoup(response.text, 'html.parser')
    result['url'] = response.url

    result['title'] = soup.title.string.replace(' | abbywinters.com', '') # type: ignore

    if node_description := soup.find('div', {'class': 'description'}):
        details = []
        for p in node_description.find_all('p'): # type: ignore
            details.append(p.getText())
        result['details'] = "\n".join(details)

    if table_summary := soup.find('table', {'class': 'table-summary'}):
        rows = table_summary.find_all('tr') # type: ignore
        for row in rows:
            header = row.find('th')
            if not header:
                continue
            if 'Girls in this Scene' in header.text:
                links = row.find_all('a')
                for link in links:
                    result['performers'].append({
                        'name': link.text, 
                        'disambiguation': 'AbbyWinters',
                        'url': link.get('href')
                    })
            if 'Release date' in header.text:
                date_str = row.find('td').text
                parsed_date = datetime.strptime(date_str, "%d %b %Y")
                formatted_date = parsed_date.strftime("%Y-%m-%d")
                result['date'] = formatted_date

    return result

def validate_url(url):
    if url is None or not re.match('^https?://', url):
        return False

    if 'abbywinters.com' in url:
        return True

    return False

def scrape_gallery(data):
    log.debug(data)
    result = {}
    title = data['title']
    gallery_title = ''
    request_url = ''
    if match := re.match(r'(\d+-\d+-\d+)_xl_(\w+).zip', title):
        gallery_title = match.group(2)
        # result['date'] = match.group(1)
        request_url = f'https://www.abbywinters.com/nude_girls/{gallery_title}'

    if match := re.match(r'(\d+-\d+-\d+)_xl_T3_(\w+).zip', title):
        gallery_title = match.group(2)
        # result['date'] = match.group(1)
        request_url = f'https://www.abbywinters.com/girl_girl/{gallery_title}'

    if not request_url:
        return {}

    result = scrape_gallery_url(request_url, result)

    return result

scraper_input = sys.stdin.read()
i = json.loads(scraper_input)
log.debug(f"Started with input: {scraper_input}")

ret = {}
if sys.argv[1] == "scrape":
    if sys.argv[2] == "gallery":
        ret = scrape_gallery_url(i['url'], i)
elif sys.argv[1] == "query":
    if 'url' in i and validate_url(i['url']):
        if sys.argv[2] == "gallery":
            ret = scrape_gallery_url(i['url'], i)

    if ret is None or ret == {}:
        if sys.argv[2] == "gallery":
            ret = scrape_gallery(i)
# elif sys.argv[1] == 'search':
#     if i.get('title') is not None or i.get('name') is not None:
#         ret = search(sys.argv[2], i['title'] if 'title' in i else i['name'])

if ret is not None:
    output = json.dumps(ret)
    print(output)
else:
    print("{}")
    # log.debug(f"Send output: {output}")
