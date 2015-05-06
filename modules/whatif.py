from bs4 import BeautifulSoup
from utils.scraper import Scraper
import pdfkit
import os
import re


class WhatIf(Scraper):
    def __init__(self, base_dir, url_header, log_file):
        super().__init__(log_file)
        self._base_dir = base_dir
        self._url_header = url_header

    def get_latest(self):
        """
        Parse `http://what-if.xkcd.com` and get the id of the newest book
        :return: id of the newest item
        """
        print(self.log("##\tGetting newest upload id..."))
        url = "http://what-if.xkcd.com/"
        # get the html from the url
        html = self.get_html(url, self._url_header)
        if not html:
            return 0
        soup = BeautifulSoup(html)
        max_id = int(soup.find("li", {"class": "nav-prev"}).a['href'].split('/')[1])
        max_id += 1
        print(self.log("##\tNewest upload: " + str(max_id)))
        return max_id

    def parse(self, id_):
        """
        Using BeautifulSoup, parse the page for the comic and its data
        :param id_: id of the comic on `http://what-if.xkcd.com`
        :return:
        """
        prop = {}
        prop['id'] = str(id_)
        url = "http://what-if.xkcd.com/" + prop['id']

        # get the html from the url
        html = self.get_html(url, self._url_header)
        if not html:
            return False
        soup = BeautifulSoup(html)

        article = soup.find("article", {"class": "entry"})

        prop['title'] = article.find_all("h1")[0].get_text()
        prop['question'] = article.find("p", {"id": "question"}).get_text()

        #####
        # Download images
        #####
        file_name = prop['id'] + "-" + prop['title']
        prop['save_path'] = self._base_dir + "/" + prop['id'][-1] + "/"
        prop['save_path'] += self.sanitize(file_name) + ".pdf"

        self.save_props(prop)
        if not os.path.isfile(prop['save_path']):
            pdfkit.from_url(url, prop['save_path'])


        # Everything was successful
        return True