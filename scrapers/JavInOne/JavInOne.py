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
            return scrape_mini_profile(soup, url)
        else:
            return scrape_full_profile(soup, url)


def scrape_mini_profile(soup, url):
    performer = {}
    birthdate_prefix = 'birthdate: '
    birthplace_prefix = 'birthplace: '
    measurements_prefix = 'measurements: '
    height_prefix = 'height: '

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
            if birthdate_full != 'unknown':
                performer['birthdate'] = datetime.strptime(birthdate_full, '%B %d, %Y').strftime('%Y-%m-%d')
        if birthplace_node := details_node.find('p', string=lambda t: birthplace_prefix in str(t)):
            birthplace_full = birthplace_node.text.split(birthplace_prefix)[1]
            if ', ' in birthplace_full:
                birthplace = birthplace_full.split(', ')[0]
            else:
                birthplace = birthplace_full
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
        performer['country'] = country
        if country == 'Japan' or country == '日本':
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

def scrape_scene_by_javlibrary(frag):
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
            'name': genre.a.get_text()
        })
    scene['tags'] = tags

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
    scene['code'] = id.lower()
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

def scrape_scene_by_url(scene):
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

            if label == 'DMM CID':
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
        backgroundUrl = base_site + details.find('div', {'id': 'fiche-film-trailer'}).video.get('poster')
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
    else:
        old_title = scene.get('title', '')
        log.info("Processing old title: %s" % old_title)
        if match := re.search(' - pt(\d+)|(?:hhb|SD|HD|CD)(\d+)', old_title):
            tags.append({'name': 'MULTIPART'})
            scene['movies'] = [movie]
            if match.group(1):
                title = title + ' - pt' + match.group(1)
            elif match.group(2):
                title = title + ' - pt' + match.group(2)
        if match := re.search('^\w+-\d+-[cC]\.', old_title):
            tags.append({'name': 'EDITION: Subbed-C'})
        elif match := re.search('(?:\d+|\])-?([A-H]|[1-8])\.', old_title):
            tags.append({'name': 'MULTIPART'})
            scene['movies'] = [movie]
            if ord(match.group(1)) >= ord('A'):
                title += ' - pt' + chr(ord(match.group(1)) - (ord('A') - ord('1')))
            else:
                title += ' - pt' + match.group(1)
        if match := re.search('\{edition-(.+?)\}', old_title):
            tags.append({'name': 'EDITION: %s' % match.group(1)})
        if match := re.search('^\w+-\d+-(\d+)-[cC]', old_title):
            tags.append({'name': 'MULTIPART'})
            tags.append({'name': 'EDITION: Subbed-C'})
            title = title + ' - pt' + match.group(1)

    scene['title'] = title

    log.info("Final info: %s" % json.dumps(scene))
    return scene

def scrape_scene(frag):
    log.info(json.dumps(frag))

    if not 'title' in frag:
        return frag
    title = frag['title']

    if url := frag.get('url'):
        log.info('Scrape by URL: %s' % url)
        return scrape_scene_by_url(frag)

    import re

    log.info('******SEARCH WAPdb CALLED*******')

    title = title.replace('!', '！')
    title = title.replace('~', '〜')
    title = title.replace('&', '＆')
    title = title.replace('%20', ' ')
    #title = title.replace('20', ' ')

    match = re.search('^(\d{6})[^\d](\d{3})', title)
    if match:
        if '1pon' in title:
            title = match.group(1) + "_" + match.group(2)
        if 'Carib' in title:
            title = match.group(1) + "-" + match.group(2)
        log.info('REFORMAT TITLE %s ' % title)

    if match := re.search('\[?NoDRM\]?-([a-zA-Z]+)(?:00)?(\d{3})', title):
        title = match.group(1) + '-' + match.group(2)
        log.info('REFORMAT TITLE %s ' % title)
    if match := re.search('\[?NoDRM\]?-(\d*[a-zA-Z]+)(?:00)?(\d{3})', title):
        title = match.group(1) + match.group(2)
        log.info('REFORMAT TITLE %s ' % title)
    if match := re.search('([a-zA-Z]+)(?:00)?(\d{3})(?:\.|hhb)', title):
        title = match.group(1) + match.group(2)
        log.info('REFORMAT TITLE %s ' % title)
    if match := re.search('h_\d+([a-zA-Z]+)00?(\d+)', title):   #h_068mxgs00009
        title = match.group(1) + '-' + match.group(2)
        log.info('REFORMAT TITLE %s ' % title)
    
    title = title.lower()

    match = re.search('^[Cc]arib[^\d]+(\d{6})[^\d](\d{3})', title)
    if match:
        title = match.group(1) + "-" + match.group(2)
        log.info('REFORMAT TITLE %s ' % title)

    match = re.search('^(\w+[\s-]\d+)', title)
    if match:
        title = match.group(1).replace(' ', '-')
        log.info('REFORMAT TITLE %s ' % title)

    match = re.search('^([a-zA-Z]+)(\d+)(?:[\._]|[A-Z]\.)', title)
    if match:
        title = (match.group(1) + '-' + match.group(2))
        log.info('REFORMAT TITLE %s ' % title)
    
    log.info('SEARCH TITLE is %s ' % title)

    data = { 
        "recherche_critere":"v",
        "recherche_valeur":title,
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

                frag['url'] = url

                scene = scrape_scene_by_url(frag)
                return scene
            else:
                log.warning(f'Failed to match {title} with bandid={bandid} or curtitle={curtitle}')

    #fall back to tpdb
    try:
        API_BASE_URL = 'https://api.metadataapi.net'
        API_SEARCH_URL = API_BASE_URL + '/jav?parse=%s'
        API_SCENE_URL = API_BASE_URL + '/jav/%s'
        API_SITE_URL = API_BASE_URL + '/sites/%s'

        tpdb_search_url = API_SEARCH_URL % (urllib.parse.quote(title))
        
        headers = {
            'User-Agent': 'ThePornDBJAV.bundle',
        }

        headers['Authorization'] = 'Bearer %s' % 'eJqarOQyVcWUmxdHqJ8kvS7eVI1O5XT4lsIkNG0dda651c80'
        resp = requests.get(tpdb_search_url, headers=headers, timeout=30)
        results = resp.json()
        for result in results['data']:
            if result['external_id'] != title:
                continue

            log.info(f'Fallback hit with tpdb id {result["id"]}')

            result['code'] = result['external_id']
            result['studio'] = {'name': result['site']['name']}

            title = result['title']
            old_title = frag.get('title', '')
            if match := re.search(' - pt(\d+)|(?:hhb|SD|HD|CD)(\d+)', old_title):
                result['tags'].append({'name': 'MULTIPART'})
                if match.group(1):
                    title = title + ' - pt' + match.group(1)
                elif match.group(2):
                    title = title + ' - pt' + match.group(2)
            if match := re.search('\d+([A-H])\.', old_title):
                result['tags'].append({'name': 'MULTIPART'})
                title = title + ' - pt' + chr(ord(match.group(1)) - (ord('A') - ord('1')))
            if match := re.search('\{edition-(.+?)\}', old_title):
                result['tags'].append({'name': 'EDITION: %s' % match.group(1)})

            if 'r18' in result['image']:
                result['image'] = result.get('background', {}).get('full', '')

            result['title'] = title
            return result
            
            performers = []
            for performer in entry['performers']:
                performers.append({
                    'name': performer['name']
                })

            scene = {
                'title': entry['title'],
                'details': entry['description'],
                'code': entry['external_id'],
                'director': entry['director'],
                'url': API_SCENE_URL % entry['id'],
                'date': entry['date'],
                'image': entry['image'],
                'studio': {'name': entry['site']['name']},
                'performers': []
            }

            
        # return json_decode(make_request(url, headers))
    except Exception as e:
        log.warning(f'Fallback failed with {str(e)}')
        pass

    return frag

def search_scene(frag):
    merged_results = []

    wapdb_hit = False
    try:
        query = frag['name']
        part = None
        if match := re.match('(.+?) - pt(\d+)', query):
            query = match.group(1)
            part = match.group(2)

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

def main():
    check_compat()
    # workaround for cp1252
    sys.stdin = io.TextIOWrapper(sys.stdin.detach(), encoding='utf-8')
    frag = json.loads(sys.stdin.read())
    log.info(str(frag))
    arg = sys.argv[-1]
    if arg == 'performerByName':
        performers = search_performer(frag)
        result = json.dumps(performers)
        print(result)
    if arg in ['performerByFragment', 'performerByURL']:
        performer = scrape_performer(frag['url'])
        result = json.dumps(performer)
        print(result)
    if arg == 'sceneByFragment':
        scene = scrape_scene(frag)
        result = json.dumps(scene)
        print(result)
    if arg == 'sceneByName':
        if 'https://www.javlibrary.com/ja/?v=' in frag['name']:
            scene = scrape_scene_by_javlibrary({'url': frag['name']})
            result = json.dumps([scene])
            print(result)
        elif 'https://www.jav321.com/video/' in frag['name']:
            scene = scrape_scene_by_jav321({'url': frag['name']})
            result = json.dumps([scene])
            print(result)
        else:
            scenes = search_scene(frag)
            result = json.dumps(scenes)
            print(result)
    if arg == 'sceneByQueryFragment':
        if 'warashi' in frag['url']:
            scene = scrape_scene_by_url(frag)
            result = json.dumps(scene)
            print(result)
        
        for url in frag['urls']:
            if 'metadataapi' in url:
                scene = get_metadata_api(url)
                result = json.dumps(scene)
                print(result)
            if 'javlibrary' in url:
                scene = scrape_scene_by_javlibrary({'url': url})
                result = json.dumps(scene)
                print(result)
            if 'jav321' in url:
                scene = scrape_scene_by_jav321({'url': url})
                result = json.dumps(scene)
                print(result)
    if arg == 'sceneByURL':
        if 'warashi' in frag['url']:
            scene = scrape_scene_by_url(frag)
            result = json.dumps(scene)
            print(result)
        if 'javlibrary' in frag['url']:
            scene = scrape_scene_by_javlibrary(frag)
            result = json.dumps(scene)
            print(result)
        if 'jav321' in frag['url']:
            scene = scrape_scene_by_jav321(frag)
            result = json.dumps(scene)
            print(result)
    if arg == 'movieByURL':
        frag['is_movie'] = True
        scene = scrape_scene_by_url(frag)
        result = json.dumps(scene)
        print(result)

if __name__ == '__main__':
    main()
