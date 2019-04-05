#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
svakulenko
5 Apr 2019

Get Wikipedia articles for WikiData entities and parse them into story trees
'''

# to scrape the links from Wikipedia article
import scrape_trees
import requests, json
from SPARQLWrapper import SPARQLWrapper, JSON
from pymongo import MongoClient


DB_NAME = 'wiki_stories'
COL_NAME = 'biographies_trees'  # 'all'

WIKIDATA_SPARQL_API = 'https://query.wikidata.org/sparql'
# filter out biography Wiki pages for entities that are humans
GET_PAGES_QUERY = '''
                    PREFIX schema: <http://schema.org/>
                    PREFIX wikibase: <http://wikiba.se/ontology#>
                    PREFIX wd: <http://www.wikidata.org/entity/>
                    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
                    SELECT DISTINCT ?cid ?label ?article WHERE {
                          ?cid rdfs:label ?label filter (lang(?label) = "en") .
                          ?cid wdt:P31 wd:Q5 .
                          ?article schema:about ?cid .
                          ?article schema:inLanguage "en" .
                          ?article schema:isPartOf <https://en.wikipedia.org/> .
                    } 
                    LIMIT 100000
                     '''

def get_results(endpoint_url, query):
    sparql = SPARQLWrapper(endpoint_url)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()


GET_ENTITIES_CALL = "https://www.wikidata.org/w/api.php?action=wbgetentities&sites=enwiki&format=json&titles=%s"

def link_wiki_data(url):
    '''
    Get WikiData ID
    '''
    label = url.strip('/').split('/')[-1]
    response = requests.get(GET_ENTITIES_CALL%label)
    # print(json.loads(response.text)['entities'].keys())
    URI = list(json.loads(response.text)['entities'].keys())[0]
    return label, URI


# collect story trees with the corresponding WikiData IDs
def get_wiki_tree(scraper):
    '''
    scraper is a function extracting links from a Wiki page
    '''
    p_links = scraper(page)
#     print(p_links)
    story_tree = {}
    for i, paragraph in enumerate(p_links):
        for j, sentence in enumerate(paragraph):
            URIs = []
            for link in sentence:
                # WikiData ID
                # _, URI = link_wiki_data(link['url'])
                # Wikipedia article title
                URI = link['title']
                # skip entities missing from WikiData
                if URI != '-1':
                    URIs.append(URI)
    #                 print(URI)
            if len(URIs) > 0:
                if i not in story_tree:
                    story_tree[i] = {}
                story_tree[i][j] = URIs
    return story_tree


def extract_story_tree(url):
    # get the corresponding Wiki page
    page = requests.get(url).text
    # get only the links from the article summary
    summary_tree = get_wiki_tree(page, scrape.extract_summary_links)
    # print(summary_URIs)
    print("Summary tree with %d branches extracted"%len(summary_tree))
    # get only the links from the article without the summary
    story_tree = get_wiki_tree(page, scrape.extract_story_links)
    print("Story URIs with %d branches extracted"%len(story_tree))
    return summary_tree, story_tree


if __name__ == '__main__':
    mongo_client = MongoClient()
    # get WikiData entities with the corresponding Wikipedia article
    # url = "https://en.wikipedia.org/wiki/Pieter_Bruegel_the_Elder"
    results = get_results(WIKIDATA_SPARQL_API, GET_PAGES_QUERY)
    for result in results["results"]["bindings"]:
        url = result['article']['value']
        result['_id'] = url
        summary_tree, story_tree = extract_story_tree(url)
        result['article']['summary'] = summary_tree
        result['article']['story'] = story_tree
        # db = mongo_client[DB_NAME][COL_NAME].insert_one(result)
        print(result)
