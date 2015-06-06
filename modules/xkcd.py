import requests
from bs4 import BeautifulSoup
from utils.scraper import Scraper


class Xkcd(Scraper):

    def __init__(self, base_dir, url_header, log_file):
        super().__init__(log_file)
        self._base_dir = base_dir
        self._url_header = url_header

    def get_latest(self):
        """
        Parse `http://xkcd.com` and get the id of the newest book
        :return: id of the newest item
        """
        print(self.log("##\tGetting newest upload id..."))
        url = "http://xkcd.com/info.0.json"
        # Get the json data
        data = requests.get(url).json()
        max_id = data['num']
        print(self.log("##\tNewest upload: " + str(max_id)))
        return int(max_id)

    def parse(self, id_):
        """
        Using BeautifulSoup, parse the page for the comic and its data
        :param id_: id of the comic on `http://xkcd.com`
        :return:
        """
        url = "http://xkcd.com/" + str(id_) + "/info.0.json"
        prop = requests.get(url).json()
        # prop Needs an id field
        prop['id'] = str(prop['num'])

        # #####
        # # Download images
        # #####
        file_ext = self.get_file_ext(prop['img'])
        file_name = prop['id']
        prop['save_path'] = self._base_dir + "/" + prop['id'][-1] + "/"
        prop['save_path'] += self.sanitize(file_name) + file_ext
        if self.download(prop['img'], prop['save_path'], self._url_header):
            self.save_props(prop)

        # Everything was successful
        return True
