import requests
import logging
from lxml.html import fromstring, tostring
from pprint import pprint
import re
import json
import os

logging.basicConfig(format='%(levelname)s-%(asctime)s:%(message)s')
logger = logging.getLogger(__name__)
logger.setLevel('INFO')

BASE_URL = "http://www.nujij.nl/Default.lynkx?pageStart="
DOMAIN   = "http://www.nujij.nl/"

OUTPUT_FOLDER = 'json'

if not OUTPUT_FOLDER in os.listdir('.'):
    os.mkdir(OUTPUT_FOLDER)

session = requests.Session()

first_or_non = lambda x: len(x) > 0 and x[0] or ''
parse_markup_url = lambda x: x.xplit("'")[1]
good_url = lambda x : x.replace('//','http://',1)

def extract_fb(element):
    try:
        return re.search(r"(http://www.facebook.com/plugins/[^&]*)", str(tostring(element[0]))).group()
    except:
        return ''
    
def extract_TW(element):
    try:
        return re.search(r'(ref="//www.nujij.nl/Retweet.lynkx[^"]+)', str(tostring(element[0]))).group()
    except:
        return ''
        
def get_overview(pagenum=0):
    url = BASE_URL+'%s' %pagenum
    logger.info("at page {url}".format(**locals()))
    page = session.get(url, timeout=60)
    dom  = fromstring(page.content)
    berichten = dom.xpath("//*[@class='columnLeft']//*[@class='bericht']")
    for bericht in berichten:
        if good_url(first_or_non(bericht.xpath(".//*[@class='title']/*/@href"))).split('.')[-2] in os.listdir(OUTPUT_FOLDER):
            logger.info("message already recovered, skipping")
            continue
        bericht = get_item(bericht)
        with open(os.path.join(OUTPUT_FOLDER, bericht['id']),'w') as f:
            json.dump(bericht, f)
    if berichten:
        get_overview(pagenum+20)
    logger.info("Finished collecting pages")

def get_item(bericht_element):
    bericht = {}
    bericht['preview'] ={
        'title': first_or_non(bericht_element.xpath(".//*[@class='title']/*/text()")),
        'title_url': good_url(first_or_non(bericht_element.xpath(".//*[@class='title']/*/@href"))),
        'source': first_or_non(bericht_element.xpath(".//*[@class='bericht-link']//text()")),
        'source_url': good_url(first_or_non(bericht_element.xpath(".//*[@class='title']//@href"))),
        'thumb_url': good_url(first_or_non(bericht_element.xpath(".//*[@class='bericht-image-thumb-div']/@style"))),
        'text': first_or_non(bericht_element.xpath(".//*[@class='text']//text()")),
        'by_user': first_or_non(bericht_element.xpath(".//*[@class='persoon']//text()")),
        'timestamp': first_or_non(bericht_element.xpath(".//*[@class='tijdsverschil']//@publicationdate")),
        'category': first_or_non(bericht_element.xpath(".//*[@class='category']//text()")),
        'reactions_string': first_or_non(bericht_element.xpath(".//*[@class='bericht-reacties']//text()")),
        'clicks_string': first_or_non(bericht_element.xpath(".//*[@class='bericht-clicks']//text()")),
        'votes_string': first_or_non(bericht_element.xpath(".//*[@class='count']//text()"))
    }
    bericht['nujij_url'] = bericht['preview']['title_url']
    bericht_page = session.get(bericht['preview'].get('title_url',''), timeout=60)
    bericht['raw'] = str(bericht_page.content)
    bericht_dom = fromstring(bericht_page.content)
    bericht['id'] = bericht_page.url.split('.')[-2]
    
    bericht['page'] = {
        'title' : first_or_non(bericht_dom.xpath('//*[@class="content-main bericht-detail"]//h1[@class="title"]/*/text()')),
        'source' : first_or_non(bericht_dom.xpath('//*[@class="content-main bericht-detail"]//div[@class="bericht-link"]/*/text()')),
        'source_url' : first_or_non(bericht_dom.xpath('//*[@class="content-main bericht-detail"]//div[@class="bericht-link"]/*/@href')),
        'text' : ''.join(bericht_dom.xpath('//*[@class="content-main bericht-detail"]//div[@class="articlebody"]//text()')),
        'thumb_url': good_url(first_or_non(bericht_dom.xpath('//*[@class="content-main bericht-detail"]//span/img/@src'))),
        'thumb_alt_text': good_url(first_or_non(bericht_dom.xpath('//*[@class="content-main bericht-detail"]//span/img/@alt'))),
        'tags': [str(tag) for tag in bericht_dom.xpath('//*[@class="content-main bericht-detail"]//span[@class="bericht-tags-links"]/*/text()')],
        'title' : first_or_non(bericht_dom.xpath('//*[@class="content-main bericht-detail"]//h1[@class="title"]/*/text()')),
        'section' : first_or_non(bericht_dom.xpath('//*[@class="content-main bericht-detail"]//a[@class="section"]//text()') ),
        'reaction_count_string' : first_or_non(bericht_dom.xpath('//*[@class="content-main bericht-detail"]//span[@class="bericht-reacties"]//text()') ),
        'click_count_string' : first_or_non(bericht_dom.xpath('//*[@class="content-main bericht-detail"]//span[@class="bericht-clicks"]//text()') ),
        'publicationdate_string' : first_or_non( bericht_dom.xpath('//*[@class="articlecontent"]//span[@class="tijdsverschil"]//@publicationdate') ),
        'FB_like_link': extract_fb(bericht_dom.xpath('//*[@class="articlecontent"]//div[@class="optin optin-social"]')),
        'Retweet_link': extract_TW(bericht_dom.xpath('//*[@class="articlecontent"]//div[@class="optin optin-social"]')),
        'added_by_user': first_or_non(bericht_dom.xpath('//*[@class="articlecontent"]//div[@class="bericht-details"]//a/text()'))
    }

    bericht['comments'] = get_comments(bericht_page)
    bericht['voters']   = get_voters(bericht_page)
    return bericht

def get_comments(bericht_page):
    comments = [] 
    bericht_dom = fromstring(bericht_page.content)
    for element in bericht_dom.xpath('//ol[@class="reacties"]/li[@class="hidenum  "]'):
        if 'Reageer als eerste op dit bericht' in element.text_content(): break
        if element.text_content() == '\r\n\t\t\t\t\r\n\t\t\t\t\t door jou\xa0\r\n\t\t\t\t\r\n\t\t\t\t\t\t\t\t\t\r\n\t\t\t\t\r\n\t\t\t': continue
        comment = {
            'pos' : first_or_non( element.xpath('.//*[@class="reactie-nummer"]//text()') ),
            'by_user' : first_or_non( element.xpath('.//div/strong//text()') ),
            'timestamp_string' : first_or_non( element.xpath('.//*[@class="tijdsverschil"]/@publicationdate') ),
            'upvote_string' : element.xpath('.//*[@class="reactie-saldo"]//text()')[1],
            'downvote_string' : element.xpath('.//*[@class="reactie-saldo"]//text()')[0],
            'text' : ' '.join(element.xpath('.//div[@class="reactie-body "]/text()')),
            'raw'  : str(tostring(element)),
            'reply_to_strings' : [str(reply_str) for reply_str in element.xpath('.//div[@class="reactie-body "]//span//text()')],
            'reply_to_id_str' : [str(reply_ids).split(' ')[-2] for reply_ids in element.xpath('.//div[@class="reactie-body "]//span//@onmouseover')]
        }
        comments.append(comment)
    next_comments = first_or_non(bericht_dom.xpath('//div[@class="pages"]//a[@class="prev"]//@href'))
    if next_comments:
        next_bericht_page = session.get(DOMAIN+next_comments)
        comments.extend(get_comments(next_bericht_page))
    return comments

def get_voters(bericht_page):
    bericht_dom = fromstring(bericht_page.content)
    voters_url  = good_url( first_or_non( bericht_dom.xpath('//*[contains(text(),"Stemmers...")]/@href')))
    voter_page  = session.get(voters_url)
    voters_dom  = fromstring(voter_page.content)
    voters  = []
    for voter in voters_dom.xpath('//div[@class="bericht-subsectie"]/ul/li'):
        voters.append({
            'username': first_or_non( voter.xpath('.//*[@class="persoon-name"]/text()')),
            'user_id' : first_or_non( voter.xpath('.//*[@class="persoon-name"]/@href')),
            'user_thumb_url' : first_or_non( voter.xpath('.//*[@class="persoon-image-link"]/img/@src')),
            'user_descript'  : first_or_non( voter.xpath('.//*[@class="persoon-details"]/text()') ) 
        })
    return voters

if __name__ == '__main__':
    get_overview()
