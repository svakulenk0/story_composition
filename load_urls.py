# retrieve relevant pages using a web search engine
import requests
import urllib.parse
from lxml import html
from newspaper import Article
from collections import Counter
import json
import argparse


WIKI_API = "https://en.wikipedia.org/w/api.php?format=json&"
GET_SECTIONS = WIKI_API + "action=parse&page=%s&prop=sections"
general_sections = ['External links', 'Bibliography', 'Gallery', 'Notes and references', 'Citations',
                    'References and sources', 'References', 'Further reading', 'See also', 'Footnotes', 'Sources',
                    'Notes', 'General']
endpoint = "https://duckduckgo.com/html/"
skip_domains = ["wikipedia", "instagram", "facebook", "goodreads", "youtube", "wikiart", "wikimedia",
                "pinterest", "amazon", "linkedin", "jstor", "kinopoisk", "tumblr"]


def count_headers(filename):
    # load data from file
    titles, pages = [], []
    headers = Counter()
    with open('./data/%s.jsonl'%filename, 'r') as infile:
        lines = infile.readlines()
        for line in lines:
            entry = json.loads(line)
            if 'sections' in entry:
                headers.update([section for section in entry['sections'] if section not in general_sections])
            if 'title' in entry:
                titles.append(entry['title'])
            if 'page' in entry:
                pages.append(entry['page'])

    # show top most headers            
    for header, count in headers.most_common(10):
        print(header, count)
    
    return titles, pages, headers



# artists = [artists[0]]


def get_pages(artist, header, pool):
    '''
    Search the web and crawl result pages
    '''
    query = ' '.join([artist, header])
    print(query)
    # Construct a request
    params = { 'q': query, 'mkt': 'en-US' }

    # get and parse URLs to web pages from the search results
    try:
        response = requests.get(endpoint, params=params, headers={'user-agent': 'my-app/0.0.1'})
        response.raise_for_status()
        doc = html.fromstring(response.text)
        urls = []
        for a in doc.cssselect('#links .links_main a'):
            url = a.get('href')
            if url not in urls:
                urls.append(url)
        print("found %d unique urls"%len(urls))
        
        # retrieve and parse web pages from the search results
        texts = []
        for j, url in enumerate(urls):
            url = url[len("/l/?kh=-1&uddg="):]
            url = urllib.parse.unquote(url)
            domain = url.split('//')[-1].split('/')[0].split('.')[1]
            
            if url not in pool and domain not in skip_domains:
                print(url)
                # parse page
                text = ""
                a = Article(url, language='en')
                try:
                    a.download()
                    a.parse()
                    title = a.title
                    text = a.text
                    texts.append(text)
                except:
                    pass
                pool[url] = text

    except Exception as ex:
        raise ex

    print("loaded %d texts from %d web results"%(len(texts), len(urls)))
    return pool


def load_urls(filename, n_top_headers):
    artists, artists_pages, artists_section_counter = count_headers(filename)

    with open('./data/%s_urls.jsonl'%filename, 'w') as outfile:
        for i, artist in enumerate(artists):
            wiki_title = artists_pages[i]
            # start crawling pages by querying only by the page title
            pool = get_pages(artist, "", {})

            for header, count in artists_section_counter.most_common(n_top_headers):
                if count > 1:
                    pool = get_pages(artist, header, pool)
            print('\n')

            # store data into a json file
            json.dump({"page": wiki_title, "urls": list(pool.items())}, outfile)
            outfile.write('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', type=str)
    parser.add_argument('n_top_headers', type=int)
    args = parser.parse_args()
    load_urls(args.filename, args.n_top_headers)
