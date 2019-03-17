#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
svakulenko
17 Mar 2019

Get Wikipedia articles for WikiData entities and parse them into story sequences
'''

# to scrape the links from Wikipedia article
import scrape
import requests, json
from SPARQLWrapper import SPARQLWrapper, JSON
from pymongo import MongoClient


DB_NAME = 'wiki_stories'
COL_NAME = 'all'

WIKIDATA_SPARQL_API = 'https://query.wikidata.org/sparql'
# 'http://wikidata.communidata.at/wikidata/query'
GET_PAGES_QUERY = '''
                    PREFIX schema: <http://schema.org/>
                    PREFIX wikibase: <http://wikiba.se/ontology#>
                    PREFIX wd: <http://www.wikidata.org/entity/>
                    PREFIX wdt: <http://www.wikidata.org/prop/direct/>

                    SELECT DISTINCT ?cid ?label ?article WHERE {
                          ?cid rdfs:label ?label filter (lang(?label) = "en") .
                          ?article schema:about ?cid .
                          ?article schema:inLanguage "en" .
                          ?article schema:isPartOf <https://en.wikipedia.org/> .
                    } 
                    LIMIT 100
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


# collect the sequence of URLs, the corresponding WikiData URIs and HDT IDs
def get_wiki_sequence(page, scraper):
    '''
    Scraper function extracting links from a Wiki page
    '''
    URIs, labels = [], []
    links = scraper(page)
    for link in links:
        label, URI = link_wiki_data(link['url'])
        # skip entities missing from WikiData
        if URI != '-1':
            labels.append(label)
            URIs.append(URI)
    return labels, URIs


def extract_story_sequence(url):
    # get the corresponding Wiki page
    page = requests.get(url).text
    # get only the links from the article summary
    summary_labels, summary_URIs = get_wiki_sequence(page, scrape.extract_summary_links)
    # print(summary_URIs)
    print("%d summary URIs extracted"%len(summary_URIs))
    # get only the links from the article without the summary
    story_labels, story_URIs = get_wiki_sequence(page, scrape.extract_story_links)
    print("%d story URIs extracted"%len(story_URIs))
    return summary_labels, summary_URIs, story_labels, story_URIs


if __name__ == '__main__':
    mongo_client = MongoClient()
    # get WikiData entities with the corresponding Wikipedia article
    # url = "https://en.wikipedia.org/wiki/Pieter_Bruegel_the_Elder"
    results = get_results(WIKIDATA_SPARQL_API, GET_PAGES_QUERY)
    for result in results["results"]["bindings"]:
        url = result['article']['value']
        result['_id'] = url
        summary_labels, summary_URIs, story_labels, story_URIs = extract_story_sequence(url)
        result['article']['summary'] = {}
        result['article']['story'] = {}
        result['article']['summary']['labels'] = summary_labels
        result['article']['summary']['URIs'] = summary_URIs
        result['article']['story']['labels'] = story_labels
        result['article']['story']['URIs'] = story_URIs
        db = mongo_client[DB_NAME][COL_NAME].insert_one(result)
        print(result)
