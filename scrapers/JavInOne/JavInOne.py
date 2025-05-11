# type: ignore

import json
import io
import sys
import os
import re
import urllib.parse

from datetime import datetime

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
    
try:
    from py_common import log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()
    
def check_compat():
    from bs4 import __version__ as ver
    major, minor, _ = ver.split('.')
    if (int(major) == 4 and int(minor) >= 10) or (int(major) > 4):
        return
    print(f'This scraper requires BeautifulSoup 4.10.0 and above. Your version: {ver}', file=sys.stderr)
    sys.exit(1)

def process_name(name):
    name_map = {
        'Ô': 'ou',
        'ô': 'ou',
        'û': 'uu',
        'Û': 'uu',
        'î': 'ii',
        'Î': 'ii'
    }
    for k, v in name_map.items():
        name = name.replace(k, v)
    return name.title()


def get_gender(url):
    if 'female-pornstar' in url:
        return 'female'
    if 'male-pornstar' in url:
        return 'male'


def scrape_performer(url):
    resp = requests.get(url)
    if resp.ok:
        soup = BeautifulSoup(resp.text, 'html.parser')
        if soup.find('div', {'id': 'casting-profil-mini-infos'}):
            profile = scrape_mini_profile(soup, url)
            log.info(str(profile))
            return profile
        else:
            return scrape_full_profile(soup, url)


def scrape_mini_profile(soup, url):
    performer = {}
    birthdate_prefix = '生年月日: '
    birthplace_prefix = '出身地: '
    measurements_prefix = 'スリーサイズ: '
    height_prefix = '身長: '

    performer['url'] = url
    if gender := get_gender(url):
        performer['gender'] = gender

    if soup.find(string=lambda t: 'pornstar is not yet in our database' in t):
        print('Performer not in database', file=sys.stderr)
        return

    if profile := soup.find('div', {'id': 'casting-profil-mini-infos'}):
        if alphabet_name := profile.find('meta', {'itemprop': 'name'}):
            name = alphabet_name.attrs['content']
            performer['aliases'] = name
        if additional_name := profile.find('meta', {'itemprop': 'additionalName'}):
            name = additional_name.attrs['content']
            performer['name'] = process_name(name)
            japanese_name = performer['name']

    if details_node := soup.find('div', {'id': 'casting-profil-mini-infos-details'}):
        if birthdate_node := details_node.find('p', string=lambda t: birthdate_prefix in str(t)):
            birthdate_full = birthdate_node.text.split(birthdate_prefix)[1]
            try:
                if birthdate_full != 'unknown':
                    performer['birthdate'] = datetime.strptime(birthdate_full, '%Y年%m月%d日').strftime('%Y-%m-%d')
            except:
                pass
        if birthplace_node := details_node.find('p', string=lambda t: birthplace_prefix in str(t)):
            birthplace_full = birthplace_node.text.split(birthplace_prefix)[1]
            if ', ' in birthplace_full:
                birthplace = birthplace_full.split(', ')[0]
            else:
                birthplace = birthplace_full
            if birthplace == '日本':
                birthplace = 'Japan'
            if birthplace != 'unknown':
                performer['country'] = birthplace
            if birthplace == 'Japan':
                performer['ethnicity'] = 'asian'
        if measurements_node := details_node.find('p', string=lambda t: measurements_prefix in str(t)):
            measurements = measurements_node.text.split(measurements_prefix)[1]
            if measurements != 'unknown':
                performer['measurements'] = measurements
        if height_node := details_node.find('p', string=lambda t: height_prefix in str(t)):
            height = height_node.text.split(height_prefix)[1].split()[0]
            if height != 'unknown':
                performer['height'] = height
    if image_node := soup.find('div', {'id': 'casting-profil-preview'}):
        image_url = image_node.find('img', {'itemprop': 'image'}).attrs['src']
        if '/WAPdB-img/par-defaut/' not in image_url:
            performer['image'] = f'http://warashi-asian-pornstars.fr{image_url}'
    return performer


def scrape_full_profile(soup, url):
    performer = {}
    measurements_prefix = 'スリーサイズ: '
    activity_prefix = 'ポルノ·AV活動期間: '
    cupsize_prefix = 'カップ: '

    if alphabet_name := soup.find('span', {'itemprop': 'name'}):
        alphabet_name = alphabet_name.text

    japanese_name = None
    if additional_name := soup.find('span', {'itemprop': 'additionalName'}):
        japanese_name = additional_name.text
    performer['name'] = japanese_name
    performer['url'] = url
    if gender := get_gender(url):
        performer['gender'] = gender
    if gender_node := soup.find('meta', {'property': 'og:gender'}):
        performer['gender'] = gender_node.attrs['content']
    if twitter_node := soup.find(string='official Twitter'):
        performer['twitter'] = twitter_node.parent.attrs['href']
    if birthday_node := soup.find('time', {'itemprop': 'birthDate'}):
        performer['birthdate'] = birthday_node.attrs['content']
    if height_node := soup.find('p', {'itemprop': 'height'}):
        if height_value_node := height_node.find('span', {'itemprop': 'value'}):
            performer['height'] = height_value_node.text
    if weight_node := soup.find('p', {'itemprop': 'weight'}):
        if weight_value_node := weight_node.find('span', {'itemprop': 'value'}):
            performer['Weight'] = weight_value_node.text
    if measurements_node := soup.find(string=lambda t: measurements_prefix in str(t)):
        measurements = measurements_node.text.split(measurements_prefix)[1]
        if measurements != 'unknown':
            measurements = measurements_node.text.split(measurements_prefix)[1]
            if mm := re.search('JP (\d+)(-\d+-\d+) \(US (\d+)(-\d+-\d+)\)', measurements):
                if cupsize_node := soup.find(string=lambda t: cupsize_prefix in str(t)):
                    if cm := re.search(cupsize_prefix + '(\w+)\s*\(=\s*(\w+)\s*\)', cupsize_node.text):
                        measurements = measurements.replace(mm.group(1) + mm.group(2), mm.group(1) + cm.group(1) + mm.group(2)).replace(mm.group(3) + mm.group(4), mm.group(3) + cm.group(2) + mm.group(4))
                    elif cm := re.search(cupsize_prefix + '(\w+)\s*$', cupsize_node.text):
                        measurements = measurements.replace(mm.group(1) + mm.group(2), mm.group(1) + cm.group(1) + mm.group(2))
                    
            performer['measurements'] = measurements

    if activity_node := soup.find(string=lambda t: activity_prefix in str(t)):
        performer['career_length'] = activity_node.text.split(activity_prefix)[1].strip()

    if image_container_node := soup.find('div', {'id': 'pornostar-profil-photos-0'}):
        if image_node := image_container_node.find('img', {'itemprop': 'image'}):
            image_url = image_node.attrs['src']
            if '/WAPdB-img/par-defaut/' not in image_url:
                performer['image'] = f'http://warashi-asian-pornstars.fr{image_url}'

    if len(country_nodes := soup.find_all('span', {'itemprop': 'addressCountry'})) > 1:
        country = country_nodes[1].text
        if country == '日本':
            country = 'Japan'
        performer['country'] = country
        if country == 'Japan':
            performer['ethnicity'] = 'asian'

    aliases = [process_name(alphabet_name)]
    # if japanese_name:
        # aliases.append(japanese_name)
    if alias_node := soup.find('div', {'id': 'pornostar-profil-noms-alternatifs'}):
        for couple in alias_node.find_all('li'):
            alias = process_name(couple.text)
            if alias == alphabet_name or alias == str(japanese_name):
                continue
            if alias not in aliases:
                aliases.append(alias)
    performer['aliases'] = ', '.join(set(aliases))

    if tags_node := soup.find('p', {'class': 'implode-tags'}):
        for tag in tags_node.find_all('a'):
            if tag.text == 'breast augmentation':
                performer['fake_tits'] = 'Y'
            if tag.text == 'tatoos':
                performer['tattoos'] = 'Y'
            if tag.text == 'piercings':
                performer['piercings'] = 'Y'

    if physical_characteristics := soup.find('p', string=lambda t: 'distinctive physical characteristics' in str(t)):
        dpc = physical_characteristics.text
        if 'breast augmentation' in dpc:
            performer['fake_tits'] = 'Y'
        if 'tattoo(s)' in dpc:
            performer['tattoos'] = 'Y'
        if 'piercing(s)' in dpc:
            performer['piercings'] = 'Y'

    return performer


def search_performer(frag):
    data = {
        'recherche_critere': 'f',
        'recherche_valeur': frag['name'],
        'x': '20',
        'y': '17'
    }
    base_site = 'http://warashi-asian-pornstars.fr'
    performers = []
    resp = requests.post(f'{base_site}/ja/s-12/search', data=data)
    if resp.ok:
        soup = BeautifulSoup(resp.text, 'html.parser')
        entries = []
        already_seen = []
        if exact_match := soup.find('div', {'class': 'correspondance_exacte'}):  # process exact matches first
            entries.append(exact_match)
        for e in soup.find_all('div', {'class': 'resultat-pornostar'}):
            entries.append(e)
        for entry in entries:
            p = {}
            if n := entry.find('span', {'class': 'correspondance-lien'}):
                name = n.parent.text.strip()
                p['name'] = process_name(name)
                p['url'] = f'{base_site}{n.parent.attrs["href"]}'
            elif len(n := entry.find_all('a')) > 1:
                p['name'] = process_name(n[1].text.strip())
                p['url'] = f'{base_site}{n[1].attrs["href"]}'
            if p:
                if p['url'] not in already_seen:
                    performers.append(p)
                    already_seen.append(p['url'])
        return performers

def get_metadata_api(url):
    try:
        headers = {
            'User-Agent': 'ThePornDBJAV.bundle',
        }

        headers['Authorization'] = 'Bearer %s' % 'eJqarOQyVcWUmxdHqJ8kvS7eVI1O5XT4lsIkNG0dda651c80'
        resp = requests.get(url, headers=headers, timeout=30)
        result = resp.json()['data']
        result['urls'] = [
            url,
            result['url']
        ]
        result['code'] = result['external_id']
        result['studio'] = {'name': result['site']['name']}
        if result['director']:
            result['director'] = result['director']['name']
        if 'r18' in result['image']:
            result['image'] = result.get('background', {}).get('full', '')
        return result
    except Exception as e:
        log.warning(f'Fallback failed with {str(e)}')
        pass

def scrape_scene_by_javlibrary(frag, soup = None):
    if not soup:
        JAV_HEADERS = {
            "User-Agent":
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
            "Referer": "http://www.javlibrary.com/"
        }
        resp = requests.get(frag['url'], headers=JAV_HEADERS)
        soup = BeautifulSoup(resp.text, 'html.parser')

    title_with_id = soup.find('h3', {'class': "post-title"}).a.get_text()
    id = soup.find('div', {'id': 'video_id'}).find('td', {'class': 'text'}).get_text()
    title = title_with_id.split(id)[1].strip()

    tags = []
    if match := re.search('#pt(\d+)$', frag['url']):
        title += ' - pt%s' % match.group(1)
        tags.append({'name': 'MULTIPART'})

    scene = {}

    scene['title'] = title
    scene['code'] = id.lower()
    if director := soup.find('span', {'class': 'director'}):
        scene['director'] = director.a.get_text()
    scene['url'] = frag['url']
    scene['date'] = soup.find('div', {'id': 'video_date'}).find('td', {'class': 'text'}).get_text()
    if studio := soup.find('span', {'class': 'maker'}):
        scene['studio'] = {
            'name': studio.a.get_text()
        }
    if image := soup.find('img', {'id': 'video_jacket_img'}):
        scene['image'] = image.get('src')
    scene['performers'] = []
    for cast in soup.find_all('span', {'class': 'cast'}):
        scene['performers'].append({
            'name': cast.span.a.get_text()
        })
    
    for genre in soup.find_all('span', {'class': 'genre'}):
        tags.append({
            'name': genre.a.get_text().replace('、', '・')
        })
    scene['tags'] = tags

    try:
        scene = fulfill_scene_by_dmm_cid(id.lower(), scene)
        scene['urls'].insert(0, frag['url'])
    except:
        pass

    return scene

def scrape_scene_by_jav321(frag):
    JAV_HEADERS = {
        "User-Agent":
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
        "Referer": "http://www.jav321.com/"
    }
    resp = requests.get(frag['url'], headers=JAV_HEADERS)
    soup = BeautifulSoup(resp.text, 'html.parser')

    
    id = soup.h3.small.text
    soup.h3.small.decompose()
    title_with_id = soup.h3.text
    
    title = title_with_id

    tags = []
    if match := re.search('#pt(\d+)$', frag['url']):
        title += ' - pt%s' % match.group(1)
        tags.append({'name': 'MULTIPART'})

    scene = {}

    scene['title'] = title
    id_splits = id.lower().split()
    if id_splits:
        scene['code'] = id_splits[0]
        scene['performers'] = []
        for name in id_splits[1:]:
            scene['performers'].append({'name': name})
    # if director := soup.find('span', {'class': 'director'}):
    #     scene['director'] = director.a.get_text()
    scene['url'] = frag['url']

    for br in soup.find_all("br"):
        br.replace_with("\n")
    infobox = soup.find('div', {'class': 'col-md-9'}).get_text()
    if match := re.search('配信開始日:\s+(\d+-\d+-\d+)', infobox):
        scene['date'] = match.group(1)
    if match := re.search('メーカー:\s*(\w+)', infobox):
        scene['studio'] = {
            'name': match.group(1)
        }
    if image := soup.select_one('.col-xs-12.col-md-12'):
        scene['image'] = image.p.a.img['src']

    # scene['performers'] = []
    # for cast in soup.find_all('span', {'class': 'cast'}):
    #     scene['performers'].append({
    #         'name': cast.span.a.get_text()
    #     })
    
    # for genre in soup.find_all('span', {'class': 'genre'}):
    #     tags.append({
    #         'name': genre.a.get_text()
    #     })
    # scene['tags'] = tags

    return scene

def scrape_scene_by_dmm(frag):
    JAV_HEADERS = {
        "User-Agent":
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
        "Referer": "http://www.dmm.com/"
    }
    resp = requests.get(frag['url'], headers=JAV_HEADERS)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    scene = {}
    scene['performers'] = []
    scene['tags'] = []

    scene['title'] = soup.find('h1', {'id': 'title'}).text
    scene['details'] = soup.find('p', {'class': 'mg-b20'}).text

    infobox = soup.find('table', {'class': 'mg-b20'})
    for tr in infobox.find_all('tr'):
        label = tr.find('td', {'class': 'nw'})
        if not label:
            continue
        if '発売日' in label.text:
            date = tr.find('td', width=True).text.replace('/', '-')
            if not date == '----':
                scene['date'] = date
        if '出演者' in label.text:
            for a in tr.find('td', width=True).find_all('a'):
                scene['performers'].append({'name': a.text})
        if '監督' in label.text:
            scene['director'] = tr.find('td', width=True).text
            if scene['director'] == '----':
                del scene['director']
        if 'メーカー' in label.text:
            scene['studio'] = {'name': tr.find('td', width=True).text}
        if 'ジャンル' in label.text:
            for a in tr.find('td', width=True).find_all('a'):
                scene['tags'].append({'name': a.text})
        if '品番' in label.text:
            scene['code'] = tr.find('td', width=True).text

    if package_image := soup.find('a', {'name': 'package-image'}):
        scene['image'] = package_image['href']
    elif img_tdmm := soup.find('img', {'class': 'tdmm'}):
        scene['image'] = img_tdmm['src']

    return scene

def scrape_scene_by_dmm_adult(frag):
    JAV_HEADERS = {
        "User-Agent":
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
        "Referer": "http://www.dmm.co.jp/"
    }
    log.info(f'scrape scene by dmm url {frag["url"]}')
    resp = requests.get(frag['url'], headers=JAV_HEADERS)
    log.debug(f'DMM Response {resp.text}')

    soup = BeautifulSoup(resp.text, 'html.parser')
    
    ageCheckDIV = soup.find('div', {'class': 'fill'})
    if 'age_check' in resp.url and ageCheckDIV:
        log.debug("AGE CHECK " + resp.text)
        ageCheckLink = ageCheckDIV.a.get('href')
        JAV_HEADERS["Referer"] = resp.url
        log.info(f'scrape scene by dmm url age checked {ageCheckLink}')
        resp = requests.get(ageCheckLink, headers=JAV_HEADERS)
        soup = BeautifulSoup(resp.text, 'html.parser')
    
    scene = {}
    scene['performers'] = []
    scene['tags'] = []

    scene['title'] = soup.find('h1', {'id': 'title'}).text
    for detail_node in soup.find_all('p', {'class': 'mg-b20'}) + soup.find_all('div', {'class': 'mg-b20'}):
        detail_node_text = detail_node.text
        if '価格は全て税込み表示です' in detail_node_text:
            continue
        if 'イメージを拡大' in detail_node_text:
            continue
        if '音声オフで自動再生する機能が使えます' in detail_node_text:
            continue
        scene['details'] = detail_node_text.strip()
        break

    infobox = soup.find('table', {'class': 'mg-b20'})
    for tr in infobox.find_all('tr'):
        label = tr.find('td', {'class': 'nw'})
        if not label:
            continue
        if '発売日' in label.text or '配信開始日' in label.text or '商品発売日' in label.text:
            date = tr.find('td', align=False).text.strip().replace('/', '-')
            if not date == '----':
                scene['date'] = date
        if '出演者' in label.text:
            for a in tr.find('td', align=False).find_all('a'):
                scene['performers'].append({'name': a.text})
        if '監督' in label.text:
            scene['director'] = tr.find('td', align=False).text
            if scene['director'] == '----':
                del scene['director']
        if 'メーカー' in label.text:
            scene['studio'] = {'name': tr.find('td', align=False).text}
        if 'ジャンル' in label.text:
            for a in tr.find('td', align=False).find_all('a'):
                scene['tags'].append({'name': a.text})
        if '品番' in label.text:
            scene['code'] = tr.find('td', align=False).text

    if sample_video := soup.find('div', {'id': 'sample-video'}):
        if a := sample_video.a:
            scene['image'] = a.get('href')
    # scene['image'] = soup.find('a', {'name': 'package-image'})['href']

    return scene

def scrape_scene_by_carib(frag):
    JAV_HEADERS = {
        "User-Agent":
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
        "Referer": "https://www.caribbeancom.com/"
    }

    log.info(f'Requesting carib {frag["url"]}')

    resp = requests.get(frag['url'], headers=JAV_HEADERS, timeout=10000)
    soup = BeautifulSoup(resp.content, 'html.parser', from_encoding="euc-jp")
    
    scene = {}
    scene['performers'] = []
    scene['tags'] = [{'name': '無修正'}]
    scene['urls'] = [frag['url']]

    movie_info = soup.find('div', {'class': 'movie-info'})

    scene['title'] = movie_info.find('h1').text
    scene['details'] = movie_info.find('p').text
    for li in movie_info.find_all('li', {'class': 'movie-spec'}):
        label = li.find('span', {'class': 'spec-title'}).text
        if not label:
            continue
        if '配信日' in label:
            scene['date'] = li.find('span', {'class': 'spec-content'}).text.replace('/', '-')
        if '出演' in label:
            for a in li.find_all('a'):
                scene['performers'].append({'name': a.text})
    #     if '監督' in label.text:
    #         scene['director'] = tr.find('td', width=True).text
    #         if scene['director'] == '----':
    #             del scene['director']
        if 'スタジオ' in label:
            scene['studio'] = {'name': li.find('span', {'class': 'spec-content'}).text.strip()}
        if 'タグ' in label:
            for a in li.find_all('a'):
                scene['tags'].append({'name': a.text})
    #     if '品番' in label.text:
    #         scene['code'] = tr.find('td', width=True).text

    # scene['image'] = soup.find('a', {'name': 'package-image'})['href']
    if match := re.search(r'/(\d{6}-\d{3})/', frag['url']):
        scene['code'] = match.group(1)
        scene['image'] = 'https://www.caribbeancom.com/moviepages/' + match.group(1) + '/images/l_l.jpg'
        if md := re.search(r'(\d{2})(\d{2})(\d{2})', scene["code"]):
            scene['date'] = f'20{md.group(3)}-{md.group(1)}-{md.group(2)}'

    if 'studio' not in scene:
        scene['studio'] = {'name': 'カリビアンコム'}

    return scene

def scrape_scene_by_caribpr(frag):
    JAV_HEADERS = {
        "User-Agent":
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
        "Referer": "https://www.caribbeancompr.com/"
    }

    log.info(f'Requesting caribpr {frag["url"]}')

    resp = requests.get(frag['url'], headers=JAV_HEADERS, timeout=10000)
    log.info(f'caribpr resp.headers={resp.headers}')
    # soup = BeautifulSoup(resp.content, 'html.parser', from_encoding="euc-jp")
    soup = BeautifulSoup(resp.content.decode('euc-jp', errors='backslashreplace'), 'html.parser')

    log.debug("caribpr " + soup.prettify())

    scene = {}
    scene['performers'] = []
    scene['tags'] = [{'name': '無修正'}]
    scene['urls'] = [frag['url']]

    movie_info = soup.find('div', {'class': 'movie-info'})

    scene['title'] = movie_info.find('h1').text
    scene['details'] = movie_info.find('p').text
    for li in movie_info.find_all('li', {'class': 'movie-spec'}):
        label = li.find('span', {'class': 'spec-title'}).text
        if not label:
            continue
        if '販売日' in label:
            scene['date'] = li.find('span', {'class': 'spec-content'}).text
        if '出演' in label:
            for a in li.find_all('a'):
                scene['performers'].append({'name': a.text})
    #     if '監督' in label.text:
    #         scene['director'] = tr.find('td', width=True).text
    #         if scene['director'] == '----':
    #             del scene['director']
        if 'スタジオ' in label:
            scene['studio'] = {'name': li.find('span', {'class': 'spec-content'}).text.strip()}
        if 'タグ' in label:
            for a in li.find_all('a'):
                scene['tags'].append({'name': a.text})
    #     if '品番' in label.text:
    #         scene['code'] = tr.find('td', width=True).text

    # scene['image'] = soup.find('a', {'name': 'package-image'})['href']
    if match := re.search(r'/(\d{6}_\d{3})/', frag['url']):
        scene['code'] = match.group(1)
        scene['image'] = 'https://www.caribbeancompr.com/moviepages/' + match.group(1) + '/images/l_l.jpg'
        if md := re.search(r'(\d{2})(\d{2})(\d{2})', scene["code"]):
            scene['date'] = f'20{md.group(3)}-{md.group(1)}-{md.group(2)}'
    return scene

import urllib3
import ssl
from urllib3.util.ssl_ import create_urllib3_context

class CustomHttpAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = create_urllib3_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        ctx.load_default_certs()
        # ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT  # Enable legacy renegotiation
        ctx.options |= ssl.OP_NO_SSLv2
        ctx.options |= ssl.OP_NO_SSLv3
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections, maxsize=maxsize,
            block=block, ssl_context=ctx)

def scrape_scene_by_1pondo(frag):
    sid = frag['url']
    if match := re.search('(\d{6}_\d{3})', sid):
        sid = match.group(1)
    else:
        return frag

    JAV_HEADERS = {
        "User-Agent":
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
        'Referer': 'https://www.1pondo.tv/movies/' + sid + '/'
    }

    url = f'https://www.1pondo.tv/dyn/phpauto/movie_details/movie_id/{sid}.json'
    session = requests.Session()
    session.mount('https://', CustomHttpAdapter())

    # resp = requests.get(url, headers=JAV_HEADERS, timeout=10000)
    resp = session.get(url, headers=JAV_HEADERS, timeout=10000)

    scene = {}
    scene['performers'] = []
    scene['tags'] = [{'name': '無修正'}]
    scene['urls'] = [frag['url']]

    scene['code'] = sid

    data = resp.json()    #json.loads(resp.data)

    scene['title'] = data.get('Title', '')
    scene['details'] = data.get('Desc', '')
    scene['date'] = data.get('Release', '')
    # metadata.year = metadata.originally_available_at.year
    scene['studio'] = {'name': "一本道"}
    # metadata.original_title = sid
    
    try:
        # movieActors.clearActors()
        #actorName = data.get('Actor')
        for actorName in data.get('ActressesJa'):
            log.info('ACTOR ' + actorName)
            # movieActors.addActor(actorName, portraits.get(actorName, ''))
            scene['performers'].append({'name': actorName})
    except Exception as e:
        log.error('ACTOR ERROR %s' % str(e))
        pass

    try:
        genreElems = data.get('UCNAME')
        for genreName in genreElems:
            # movieGenres.addGenre(genreName)
            if re.match(r'\d+p|\d+fps', genreName):
                continue
            scene['tags'].append({'name': genreName})
    except Exception as e:
        log.error('GENRE ERROR %s' % str(e))
        pass

    # try:
    #     avgRating = data.get('AvgRating')
    #     metadata.rating = float(avgRating) * 2
    #     cmtData = HTTP.Request('https://www.1pondo.tv/dyn/phpauto/new_movie_reviews/movie_id/' + sid + '.json', headers={'Referer': 'https://www.1pondo.tv/movies/' + sid + '/'}).content
    #     cmt = json.loads(cmtData)
    #     metadata.rating_count = len(cmt.get('Rows'))
    # except Exception as e:
    #     Log('RATING ERROR %s' % str(e))
    #     pass

    try:
        backgroundUrl = data.get('ThumbUltra')
        scene['image'] = backgroundUrl
        # if not PAsearchSites.posterAlreadyExists(backgroundUrl,metadata):
        #     metadata.art[backgroundUrl] = Proxy.Media(HTTP.Request(backgroundUrl, headers={'Referer': url}).content, sort_order = 1)

        # imgURLs = []
        # try:
        #     gallery_url = "https://www.1pondo.tv/dyn/dla/json/movie_gallery/" + sid + ".json"
        #     gallery_data = HTTP.Request(gallery_url, headers={'Referer': 'https://www.1pondo.tv/movies/' + sid + '/'}).content
        #     gallery_json = json.loads(gallery_data)

        #     for row in gallery_json.get('Rows'):
        #         if row.get('Protected'):
        #             break
        #         imgSrc = 'https://www.1pondo.tv/dyn/dla/images/' + row.get('Img')
        #         imgURLs.append(imgSrc)
        # except Exception as e:
        #     for img in range(1,10):
        #         imgSrc = 'https://www.1pondo.tv/assets/sample/' + sid + '/popu/' + str(img) + '.jpg'
        #         imgURLs.append(imgSrc)

        # so = 1
        # for imgSrc in imgURLs:
        #     imgSrcLarge = imgSrc
        #     Log(imgSrcLarge)
        #     if not PAsearchSites.posterAlreadyExists(imgSrcLarge,metadata):
        #         req = HTTP.Request(imgSrcLarge, headers={'Referer': url})
        #         #Log('HTTP.Request %s' % str(req.headers()))
        #         if '<html' in req.content:
        #             Log('HTTP.Request likely not jpeg')
        #             #Log('HTTP.Request %s' % repr(req.content))
        #             break
        #         if '<HTML' in req.content:
        #             Log('HTTP.Request likely not jpeg')
        #             #Log('HTTP.Request %s' % repr(req.content))
        #             break
        #         metadata.posters[imgSrcLarge] = Proxy.Preview(req.content, sort_order = so)
        #         so = so + 1
    except Exception as e:
        log.warning('IMG ERROR %s' % str(e))
        pass

    return scene

def scrape_scene_by_wapdb(scene):
    base_site = 'http://warashi-asian-pornstars.fr'
    
    url = scene['url']
    resp = requests.get(url)
    details = BeautifulSoup(resp.text, 'html.parser')

    dmm_cid = None
    dmm_digital_cid = None
    dmm_physical_cid = None
    
    date = None
    director = None
    studio = None
    duration = 0
    tags = []
    # for p in details.xpath('.//div[@id="fiche-film-infos"]/p | .//div[@id="fiche-contenu-web-infos"]/p'):
    for elem in details.find_all('div', {'id': ["fiche-film-infos", "fiche-contenu-web-infos"]}):
        for p in elem.find_all('p', recursive=False):
            pContent = p.get_text()
            ss = pContent.split(':')
            if len(ss) < 2:
                log.info('MISSING VALUE: ' + str(ss))
                continue
            else:
                label = ss[0]
                value = ss[1].strip()

            if label == 'DVD品番':
                log.info('METADATA %s:%s' % (label, value))

            if label == 'DMM CID' or label == '品番':
                log.info('METADATA %s:%s' % (label, value))
                dmm_cid = value

            if label == 'DMMデジタルメディア品番':
                log.info('METADATA %s:%s' % (label, value))
                dmm_digital_cid = value

            if label == 'DMM物理メディア品番':
                log.info('METADATA %s:%s' % (label, value))
                dmm_physical_cid = value

            if label == '発売日':
                date = value
                date = date.replace('年', '-').replace('月', '-').replace('日', '')

            if label == 'メーカー' or label == 'ウェブサイト':
                studio = value

            if label == '監督':
                director = value

            if label == '収録時間':
                duration = re.search('\d+', value).group(0)
            # if label == 'シリーズ':
            #     metadata.collections.clear()
            #     for mentions in details.xpath('.//span[@itemprop="mentions"]'):
            #         metadata.collections.add(mentions.text_content())

            # if label == 'レーベル':
            #     metadata.tagline = value
            if label == 'ウェブサイト':
                tags.append({'name': '無修正'})

            if label == 'タグ':
                for genre in details.find_all('span', {'itemprop': 'keywords'}):
                    tags.append({'name': genre.get_text()})

    if dmm_cid is None:
        return scene
    
    scene['code'] = dmm_cid
    
    if date:
        scene['date'] = date
    if director:
        scene['director'] = director
    if studio:
        scene['studio'] = {}
        scene['studio']['name'] = studio

    backgroundUrl = None
    try:
        backgroundUrl = base_site + details.find('div', {'id': ['fiche-film-trailer', 'fiche-contenu-web-trailer']}).video.get('poster')
        scene['image'] = backgroundUrl
    except:
        pass

    posterUrl = None
    try:
        posterUrl = base_site + details.find('div', {'id': ['fiche-film-jaquette', 'fiche-contenu-web-jaquette']}).figure.img.get('src')
        if 'image' not in scene:
            scene['image'] = posterUrl
    except:
        pass
    

    scene['performers'] = []
    for pornostar in details.find('div', {'id': 'casting-f'}).find_all('figure', {'itemprop': 'actor'}):
        log.debug(pornostar.prettify())
        url_node = pornostar.find('a', {'itemprop': 'url'})
        try:
            performer = {}
            performer["name"] = pornostar.find('figcaption').find('p', {'itemprop': 'name'}).get_text()
            performer["url"] = base_site + url_node.get('href')
            performer["image"] = base_site + url_node.find('img', {'itemprop': 'image'}).get('src')
            performer["gender"] = "FEMALE"
            scene['performers'].append(performer)
        except:
            pass
    
    scene['tags'] = tags

    title = details.find('span', class_='breadcrumb-last-no-transform').get_text()
    
    movie = {}
    movie['name'] = title
    movie['duration'] = duration
    movie['date'] = date
    movie['director'] = director
    movie['studio'] = {'name': studio}
    movie['url'] = url
    movie['front_image'] = posterUrl
    movie['back_image'] = backgroundUrl
    
    if scene.get('is_movie'):
        scene = movie
    elif match := re.search('#pt(\d+)$', url):
        title += ' - pt%s' % match.group(1)
        tags.append({'name': 'MULTIPART'})
    elif old_title := scene.get('title', ''):
        log.info("Processing old title: %s" % old_title)
        if match := re.search(' - pt(\d+)|(?:hhb|SD|HD|CD|cd)(\d+)', old_title):
            tags.append({'name': 'MULTIPART'})
            scene['movies'] = [movie]
            if match.group(1):
                title = title + ' - pt' + match.group(1)
            elif match.group(2):
                title = title + ' - pt' + match.group(2)
        if match := re.match('\w+-\d+-[cC]\.', old_title):
            tags.append({'name': 'EDITION: Subbed-C'})
        elif match := re.search('(?:\d+|\])-?([A-H])\.', old_title):
            tags.append({'name': 'MULTIPART'})
            scene['movies'] = [movie]
            title += ' - pt' + chr(ord(match.group(1)) - (ord('A') - ord('1')))
        elif match := re.search('(?:\d+|\])-([1-8])\.', old_title):
            tags.append({'name': 'MULTIPART'})
            scene['movies'] = [movie]
            title += ' - pt' + match.group(1)
        if match := re.search('\{edition-(.+?)\}', old_title):
            tags.append({'name': 'EDITION: %s' % match.group(1)})
        if match := re.search('^\w+-\d+-(\d+)-[cC]', old_title):
            tags.append({'name': 'MULTIPART'})
            tags.append({'name': 'EDITION: Subbed-C'})
            title = title + ' - pt' + match.group(1)

    scene['title'] = title

    try:
        scene = fulfill_scene_by_dmm_cid(dmm_cid, scene, dmm_digital_cid)
        scene['urls'].insert(0, url)
    except:
        pass

    log.info("Final info: %s" % json.dumps(scene))
    return scene

def fulfill_scene_by_dmm_cid(cid, scene, dcid):
    digital_cid = cid
    if match := re.match(r'^(\w+)-0(\d{3})$', cid):
        cid = match.group(1) + match.group(2)
        digital_cid = match.group(1) + '00' + match.group(2)
    else:
        digital_cid = cid.replace("-", "00")
        cid = cid.replace("-", "")
    
    if not 'urls' in scene:
        scene['urls'] = []

    try:
        dmm_url = f'https://www.dmm.co.jp/mono/dvd/-/detail/=/cid={cid}/'
        dmm_scene = scrape_scene_by_dmm_adult({'url': dmm_url})
        if dmm_details := dmm_scene.get('details'):
            scene['details'] = dmm_details
            scene['urls'].append(dmm_url)
    except:
        pass
    
    try:
        dmm_url = f'https://www.dmm.co.jp/digital/videoa/-/detail/=/cid={dcid if dcid else digital_cid}/'
        dmm_scene = scrape_scene_by_dmm_adult({'url': dmm_url})
        if dmm_details := dmm_scene.get('details'):
            scene['details'] = dmm_details
            scene['urls'].append(dmm_url)
    except:
        pass

    return scene

def scrape_scene(frag):
    log.info(json.dumps(frag))

    if not 'title' in frag:
        return frag
    
    search_titles = []

    title = frag['title']

    log.info('******SEARCH WAPdb CALLED*******')

    title = title.replace('!', '！')
    title = title.replace('~', '〜')
    title = title.replace('&', '＆')
    title = title.replace('%20', ' ')
    #title = title.replace('20', ' ')

    part = None
    uncen = None
    if match := re.search('^(\d{6})[^\d](\d{3})', title):
        if '1pon' in title:
            title = match.group(1) + "_" + match.group(2)
            uncen = '1pondo'
        if 'Carib' in title:
            title = match.group(1) + "-" + match.group(2)
            uncen = 'carib'
        if uncen is None and re.search(r'^\d{6}-\d{3}\.', title):
            title = match.group(1) + "-" + match.group(2)
            uncen = 'carib'     ## fallback to carib
        if uncen is None and re.search(r'^\d{6}_\d{3}\.', title):
            title = match.group(1) + "_" + match.group(2)
            uncen = 'caribpr'     ## fallback to caribpr
        log.info('REFORMAT TITLE T1 %s ' % title)

    if match := re.search('\[?NoDRM\]?-([a-zA-Z]+)(?:00|-)?(\d{3})', title):
        title = match.group(1) + '-' + match.group(2)
        log.info('REFORMAT TITLE T2 %s ' % title)
    if match := re.search('\[?NoDRM\]?-(\d*[a-zA-Z]+)(?:00|-)?(\d{3})', title):
        title = match.group(1) + match.group(2)
        log.info('REFORMAT TITLE T3 %s ' % title)
    if match := re.search('([a-zA-Z]+)(?:00)?(\d{3})(?:\.|hhb)', title):
        title = match.group(1) + match.group(2)
        log.info('REFORMAT TITLE T4 %s ' % title)
    if match := re.search('h_\d+([a-zA-Z]+)00?(\d+)', title):   #h_068mxgs00009
        title = match.group(1) + '-' + match.group(2)
        log.info('REFORMAT TITLE T5 %s ' % title)

    if match := re.fullmatch('(\w+)-(\d+)-U?C\.\w+', title):
        title = f'{match.group(1)}{match.group(2)}'
        search_titles.append('%s-%s' % (match.group(1), match.group(2)))
        log.info('REFORMAT TITLE T6 %s ' % title)
    elif match := re.fullmatch('[\s\d]*(\w+)[\s\-]*(\d+)\s*.*?([A-H])\.\w+', title):
        title = f'{match.group(1)}{match.group(2)}'
        part = chr(ord(match.group(3)) - (ord('A') - ord('1')))
        log.info('REFORMAT TITLE T7 %s %s' % (title, part))
    elif match := re.match(r'[\s\d]*(\w+)[\s\-]*(\d+)\s+.+?-(\d+)\.', title):
        title = f'{match.group(1)}{match.group(2)}'
        part = match.group(3)
        search_titles.append('%s-%s' % (match.group(1), match.group(2)))
        log.info('REFORMAT TITLE T8-1 %s ' % title)
    elif match := re.match('[\s\d]*(\w+)[\s\-]*(\d+)\s+', title):
        title = f'{match.group(1)}{match.group(2)}'
        search_titles.append('%s-%s' % (match.group(1), match.group(2)))
        log.info('REFORMAT TITLE T8 %s ' % title)
    elif match := re.match('\d+-\d+-\d+\s+(\w+)[\s\-]*(\d+)', title):
        title = f'{match.group(1)}{match.group(2)}'
        search_titles.append('%s-%s' % (match.group(1), match.group(2)))
        log.info('REFORMAT TITLE T9 %s ' % title)

    if match := re.search('^[Cc]arib[^\d]+(\d{6})[^\d](\d{3})', title):
        title = match.group(1) + "-" + match.group(2)
        log.info('REFORMAT TITLE CARIB %s ' % title)
        uncen = 'carib'

    if match := re.search('^1pon-(\d{6})_(\d{3})', title):
        title = match.group(1) + "_" + match.group(2)
        log.info('REFORMAT TITLE 1PON %s ' % title)
        uncen = '1pondo'

    if match := re.search(r'^(\w+[\s-]\d+)[\s-](?:CD|cd|PT|pt)(\d+)', title):
        title = match.group(1).replace(' ', '-')
        part = match.group(2)
        log.info('REFORMAT TITLE TB %s %s' % (title, part))
    elif match := re.search(r'^(\w+[\s-]\d+)', title):
        title = match.group(1).replace(' ', '-')
        log.info('REFORMAT TITLE TC %s ' % title)

    if match := re.search('^([a-zA-Z]+)(\d+)(?:[\._]|[A-Z]\.)', title):
        title = (match.group(1) + '-' + match.group(2))
        log.info('REFORMAT TITLE TD %s ' % title)
    
    if uncen == '1pondo':
        frag['title'] = f'1Pondo {title}'
        frag['url'] = f'https://www.1pondo.tv/movies/{title}/'
        return scrape_scene_by_1pondo(frag)

    if uncen == 'carib':
        frag['title'] = f'Carib {title}'
        frag['url'] = f'https://www.caribbeancom.com/moviepages/{title}/index.html'
        return scrape_scene_by_carib(frag)

    if uncen == 'caribpr':
        frag['title'] = f'Caribpr {title}'
        frag['url'] = f'https://www.caribbeancompr.com/moviepages/{title}/index.html'
        return scrape_scene_by_caribpr(frag)

    search_titles.append(title)
    if match := re.fullmatch(r'([a-zA-Z]+)([0-9]+)', title):
        search_titles.append(match.group(1) + '-' + match.group(2))

    for title in search_titles:
        title = title.lower()

        log.info('SEARCH TITLE is %s ' % title)

        data = { 
            "recherche_critere":"v",
            "recherche_valeur":title,
            "x":"15",
            "y":"19"
        }
        
        base_site = 'http://warashi-asian-pornstars.fr'
        resp = requests.post(f'{base_site}/ja/s-12/%E6%A4%9C%E7%B4%A2', data=data)

        log.debug('WAPdb SEARCH VIDEO HTML ' + resp.text)
        
        searchResultsArray = [(resp.url, BeautifulSoup(resp.text, 'html.parser'))]

        data = { 
            "recherche_critere":"w",
            "recherche_valeur":title,
            "x":"15",
            "y":"19"
        }
        resp = requests.post(f'{base_site}/ja/s-12/%E6%A4%9C%E7%B4%A2', data=data)

        log.debug('WAPdb SEARCH WEB HTML ' + resp.text)
        searchResultsArray.append((resp.url, BeautifulSoup(resp.text, 'html.parser')))

        for searchURL, searchResults in searchResultsArray:
            # for searchResult in searchResults.xpath('//div[@class="resultat-film"]'):
            divs = searchResults.find_all('div', {'class': 'resultat-film'})
            if len(divs) == 0:
                log.warning(f'Failed to locate search entry from {searchURL}')
                continue
            for searchResult in divs:
                log.info("**GOT ITEM**")
                log.debug(searchResult.prettify())
                # a = searchResult.xpath('./p/a')[0]
                a = searchResult.p.a
                href = a.get('href')
                log.info("**HREF**" + href)
                match = re.search('(/ja/s-\d-0/.+)', href)
                if match is None:
                    log.warning(f"Failed to locate entry from search {href}")
                    continue

                curid = match.group(1)
                log.info("****GOT ID****" + curid)
                #for corr in searchResults.xpath('.//span[@class="correspondance"'):
                curtitle = "NOT_FOUND"
                bandid = "UNKNKOWN"
                for p in searchResult.find_all('p'):
                    pContent = p.get_text()
                    #log.info(str(pContent))
                    if pContent.startswith('オリジナル·タイトル: '):
                        curtitle = pContent[12:]
                        log.info("****CURTITLE****" + curtitle)
                    if pContent.startswith('品番:'):
                        bandid = pContent[4:]
                        log.info("****BANDID****" + bandid)
                        
                if curtitle == "NOT_FOUND":
                    curtitle = a.get_text().strip()
                    log.info("****CURTITLE****" + curtitle)
                
                if bandid == title or curtitle == title:
                    curpath = curid
                    curpath = curpath.replace('ポルノ·av映画', '%E3%83%9D%E3%83%AB%E3%83%8E%C2%B7av%E6%98%A0%E7%94%BB')
                    curpath = curpath.replace('ウェブ·コンテンツ', '%E3%82%A6%E3%82%A7%E3%83%96%C2%B7%E3%82%B3%E3%83%B3%E3%83%86%E3%83%B3%E3%83%84')
                    log.info('CURPATH: ' + curpath)
                    url = base_site + curpath
                    log.info('CURURL: ' + url)

                    if part:
                        url += '#pt' + part
                
                    frag['url'] = url

                    scene = scrape_scene_by_wapdb(frag)
                    return scene
                else:
                    log.warning(f'Failed to match {title} with bandid={bandid} or curtitle={curtitle}')

    #fallback to javlibrary
    try:
        #https://www.javlibrary.com/ja/vl_searchbyid.php?keyword=Ssis541
        JAV_HEADERS = {
            "User-Agent":
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
            "Referer": "http://www.javlibrary.com/"
        }
        for title in search_titles:
            url = 'https://www.javlibrary.com/ja/vl_searchbyid.php?list&keyword=%s' % urllib.parse.quote(title)
            log.info("fallback to javlibrary search " + url)

            resp = requests.get(url, headers=JAV_HEADERS)
            log.debug(f'Fallback javlibrary with {resp.status_code}')
            log.debug(f'Fallback javlibrary with {resp.text}')
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            if 'javlibrary.com/ja/?v=' in resp.url:
                frag['url'] = resp.url
                if part:
                    frag['title'] += ' - pt%s' % part
                    frag['url'] += "#pt%s" % part
                return scrape_scene_by_javlibrary(frag, soup)
            
            video = soup.find('table', {'class': 'videotextlist'})

            for a in video.find_all('a', id=False):
                jav_entry = {
                    'title': a['title'],
                    'url': 'https://www.javlibrary.com/ja/' + a['href'].replace('./', '', 1)
                }
                if part:
                    jav_entry['title'] += ' - pt%s' % part
                    jav_entry['url'] += "#pt%s" % part
                try:
                    return scrape_scene_by_javlibrary(jav_entry)
                except:
                    pass
    except Exception as e:
        log.warning(f'Fallback javlibrary failed with {str(e)}')

    return frag

def search_scene(frag):
    merged_results = []

    wapdb_hit = False
    try:
        query = frag['name']
        part = None
        if match := re.fullmatch(r'(.+?) - pt(\d+)', query):
            query = match.group(1)
            part = match.group(2)
        elif match := re.fullmatch(r'(.+?) cd(\d+)', query):
            query = match.group(1)
            part = match.group(2)
        elif match := re.fullmatch('\s*(\w+)\s*(\d+)\s*.*?([a-h])', query):
            query = '%s%s' % (match.group(1), match.group(2))
            part = chr(ord(match.group(3)) - (ord('a') - ord('1')))
        elif match := re.match('\s*(\w+)\s*(\d+)\s+', query):
            query = '%s%s' % (match.group(1), match.group(2))

        log.info('WAPdb SEARCH query=%s part=%s' % (query, part))

        data = { 
            "recherche_critere":"v",
            "recherche_valeur":query,
            "x":"15",
            "y":"19"
        }

            # searchHTML = HTTP.Request(PAsearchSites.getSearchSearchURL('WAPdb'), searchValues, cacheTime = 0.0)
        base_site = 'http://warashi-asian-pornstars.fr'
        resp = requests.post(f'{base_site}/ja/s-12/%E6%A4%9C%E7%B4%A2', data=data)

        log.debug('WAPdb SEARCH VIDEO HTML ' + resp.text)

        searchResultsArray = [(resp.url, BeautifulSoup(resp.text, 'html.parser'))]

        data = { 
            "recherche_critere":"w",
            "recherche_valeur":query,
            "x":"15",
            "y":"19"
        }
        resp = requests.post(f'{base_site}/ja/s-12/%E6%A4%9C%E7%B4%A2', data=data)

        log.debug('WAPdb SEARCH WEB HTML ' + resp.text)
        searchResultsArray.append((resp.url, BeautifulSoup(resp.text, 'html.parser')))

        for searchURL, searchResults in searchResultsArray:
            # for searchResult in searchResults.xpath('//div[@class="resultat-film"]'):
            divs = searchResults.find_all('div', {'class': 'resultat-film'})
            if len(divs) == 0:
                log.warning(f'Failed to locate search entry from {searchURL}')
                continue
            for searchResult in divs:
                log.info("**GOT ITEM**")
                log.debug(searchResult.prettify())
                # a = searchResult.xpath('./p/a')[0]
                a = searchResult.p.a
                href = a.get('href')
                log.info("**HREF**" + href)
                match = re.search('(/ja/s-\d-0/.+)', href)
                if match is None:
                    log.warning(f"Failed to locate entry from search {href}")
                    continue

                curid = match.group(1)
                log.info("****GOT ID****" + curid)
                #for corr in searchResults.xpath('.//span[@class="correspondance"'):
                curtitle = "NOT_FOUND"
                bandid = "UNKNKOWN"
                for p in searchResult.find_all('p'):
                    pContent = p.get_text()
                    #log.info(str(pContent))
                    if pContent.startswith('オリジナル·タイトル: '):
                        curtitle = pContent[12:]
                        log.info("****CURTITLE****" + curtitle)
                    if pContent.startswith('品番:'):
                        bandid = pContent[4:]
                        log.info("****BANDID****" + bandid)
                        
                if curtitle == "NOT_FOUND":
                    curtitle = a.get_text().strip()
                    log.info("****CURTITLE****" + curtitle)
                
                curpath = curid
                curpath = curpath.replace('ポルノ·av映画', '%E3%83%9D%E3%83%AB%E3%83%8E%C2%B7av%E6%98%A0%E7%94%BB')
                curpath = curpath.replace('ウェブ·コンテンツ', '%E3%82%A6%E3%82%A7%E3%83%96%C2%B7%E3%82%B3%E3%83%B3%E3%83%86%E3%83%B3%E3%83%84')
                log.info('CURPATH: ' + curpath)
                    
                url = base_site + curpath
                log.info('CURURL: ' + url)

                result = {}
                result['title'] = curtitle
                result['url'] = url
                result['code'] = bandid
                result['image'] = searchResult.a.img.get('src')

                if part:
                    result['title'] += ' - pt%s' % part
                    result['url'] += "#pt%s" % part

                merged_results.append(result)

            wapdb_hit |= bandid == query or curtitle == query
    except Exception as e:
        log.warning(f'WAPdb failed with {str(e)}')
        pass

    if wapdb_hit:
        return merged_results

     #fallback to javlibrary
    try:
        #https://www.javlibrary.com/ja/vl_searchbyid.php?keyword=Ssis541
        JAV_HEADERS = {
            "User-Agent":
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
            "Referer": "http://www.javlibrary.com/"
        }
        url = 'https://www.javlibrary.com/ja/vl_searchbyid.php?list&keyword=%s' % urllib.parse.quote(query)
        log.info("fallback to javlibrary search " + url)

        resp = requests.get(url, headers=JAV_HEADERS, allow_redirects=False)
        log.info(f'Fallback javlibrary with {resp.status_code}')
        # log.debug(f'Fallback javlibrary with {resp.text}')

        soup = BeautifulSoup(resp.text, 'html.parser')

        if resp.status_code == 302 and './?v=' in resp.headers.get('Location', ''):
            redirect_url = resp.headers['Location']
            jav_entry = {
                'url': 'https://www.javlibrary.com/ja/' + redirect_url.replace('./', '', 1)
            }
            if part:
                jav_entry['url'] += "#pt%s" % part
            merged_results.append(jav_entry)
        else:
            video = soup.find('table', {'class': 'videotextlist'})
            for a in video.find_all('a', id=False):
                jav_entry = {
                    'title': a['title'],
                    'url': 'https://www.javlibrary.com/ja/' + a['href'].replace('./', '', 1)
                }
                if part:
                    jav_entry['title'] += ' - pt%s' % part
                    jav_entry['url'] += "#pt%s" % part
                merged_results.append(jav_entry)
        
    except Exception as e:
        log.warning(f'Fallback javlibrary failed with {str(e)}')

    return merged_results

    try:
        API_BASE_URL = 'https://api.metadataapi.net'
        API_SEARCH_URL = API_BASE_URL + '/jav?parse=%s'
        API_SCENE_URL = API_BASE_URL + '/jav/%s'
        API_SITE_URL = API_BASE_URL + '/sites/%s'

        tpdb_search_url = API_SEARCH_URL % (urllib.parse.quote(query))
        
        headers = {
            'User-Agent': 'ThePornDBJAV.bundle',
        }

        headers['Authorization'] = 'Bearer %s' % 'eJqarOQyVcWUmxdHqJ8kvS7eVI1O5XT4lsIkNG0dda651c80'
        resp = requests.get(tpdb_search_url, headers=headers, timeout=30)
        results = resp.json()['data']
        for result in results:
            result['urls'] = [
                API_SCENE_URL % result['id'],
                result['url']
            ]
            if 'r18' in result['image']:
                result['image'] = result.get('background', {}).get('full', '')

        merged_results += results
        # return results
    except Exception as e:
        log.warning(f'Fallback failed with {str(e)}')
        pass

    return merged_results

def scrape_scene_by_url(frag):
    if 'warashi' in frag['url']:
        scene = scrape_scene_by_wapdb(frag)
    if 'javlibrary' in frag['url']:
        scene = scrape_scene_by_javlibrary(frag)
    if 'jav321' in frag['url']:
        scene = scrape_scene_by_jav321(frag)
    if 'dmm.com' in frag['url']:
        scene = scrape_scene_by_dmm(frag)
    if 'dmm.co.jp' in frag['url']:
        scene = scrape_scene_by_dmm_adult(frag)
    if 'caribbeancompr.com' in frag['url']:
        scene = scrape_scene_by_caribpr(frag)
    if 'caribbeancom.com' in frag['url']:
        scene = scrape_scene_by_carib(frag)
    if '1pondo' in frag['url']:
        scene = scrape_scene_by_1pondo(frag)

    performers = scene.get('performers')
    tags = scene.get('tags')

    if len(performers) > 1:
        filtered_tags = [tag for tag in tags if 'レズ' in tag['name'] or 'ベスト' in tag['name']]
        if not filtered_tags:
            tags.append({
                'name': '共演作品'
            })

    log.info("****scrape_scene_by_url****" + json.dumps(scene))
    return scene

def main():
    check_compat()
    # workaround for cp1252
    sys.stdin = io.TextIOWrapper(sys.stdin.detach(), encoding='utf-8')
    frag = json.loads(sys.stdin.read())
    arg = sys.argv[-1]
    log.info(f'main arg={arg} frag={frag}')
    if arg == 'performerByName':
        performers = search_performer(frag)
        result = json.dumps(performers)
        print(result)
    if arg in ['performerByFragment', 'performerByURL']:
        performer = scrape_performer(frag['url'])
        result = json.dumps(performer)
        print(result)
    if arg == 'sceneByFragment':
        if url := frag.get('url'):
            for key, value in os.environ.items():
                log.debug(f'ENV {key}: {value}')
            log.info('sceneByFragment Scrape by URL: %s' % json.dumps(frag))

            #return [scrape_scene_by_url(frag)]
            # result = scrape_scene_by_wapdb(frag)
            scene = scrape_scene_by_url(frag)
            # scene['performers'].extend([p for p in frag['performers'] if not p in scene['performers']])
            # scene['tags'].extend([t for t in frag['tags'] if not t in scene['tags']])

            result = json.dumps(scene)
            log.info("scrape_scene url result: " + result)
            print(result)
        else:
            scene = scrape_scene(frag)
            if len(scene.get('performers', [])) > 1:
                filtered_tags = [tag for tag in scene['tags'] if 'レズ' in tag['name'] or 'ベスト' in tag['name']]
                if not filtered_tags:
                    scene['tags'].append({
                        'name': '共演作品'
                    })
            result = json.dumps(scene)
            print(result)
    if arg == 'sceneByName':
        if 'http://warashi-asian-pornstars.fr/ja/s-4-0/' in frag['name']:
            print(json.dumps([{'url': frag['name']}]))
        elif 'https://www.javlibrary.com/ja/?v=' in frag['name']:
            print(json.dumps([{'url': frag['name']}]))
        elif 'https://www.jav321.com/video/' in frag['name']:
            print(json.dumps([{'url': frag['name']}]))
        elif 'https://www.dmm.com/' in frag['name']:
            print(json.dumps([{'url': frag['name']}]))
        elif 'https://www.dmm.co.jp/' in frag['name']:
            print(json.dumps([{'url': frag['name']}]))
        elif 'https://www.caribbeancompr.com/' in frag['name']:
            print(json.dumps([{'url': frag['name']}]))
        elif 'https://www.caribbeancom.com/' in frag['name']:
            print(json.dumps([{'url': frag['name']}]))
        elif match := re.search(r'caribpr\s*(\d{6})\s*(\d{3})', frag['name']):
            print(json.dumps([{'url': f'https://www.caribbeancompr.com/moviepages/{match.group(1)}_{match.group(2)}/index.html'}]))
        elif match := re.search(r'(\d{6})_(\d{3})[\-\s]*caribpr', frag['name']):
            print(json.dumps([{'url': f'https://www.caribbeancompr.com/moviepages/{match.group(1)}_{match.group(2)}/index.html'}]))
        elif match := re.search(r'carib\s*(\d{6})\s*(\d{3})', frag['name']):
            print(json.dumps([{'url': f'https://www.caribbeancom.com/moviepages/{match.group(1)}-{match.group(2)}/index.html'}]))
        else:
            scenes = search_scene(frag)
            result = json.dumps(scenes)
            print(result)
    if arg == 'sceneByQueryFragment':
        if 'warashi' in frag['url']:
            scene = scrape_scene_by_wapdb(frag)
            result = json.dumps(scene)
            print(result)
        
        for url in frag['urls']:
            scene = scrape_scene_by_url({'url': url})
            result = json.dumps(scene)
            print(result)
    if arg == 'sceneByURL':
        log.info(f'sceneByURL {frag}')
        scene = scrape_scene_by_url(frag)
        result = json.dumps(scene)
        print(result)
    if arg == 'movieByURL':
        frag['is_movie'] = True
        scene = scrape_scene_by_wapdb(frag)
        result = json.dumps(scene)
        print(result)

if __name__ == '__main__':
    main()
