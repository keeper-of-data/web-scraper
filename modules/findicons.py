from utils.exceptions import *
from utils.scraper import Scraper
import os
import queue
import threading

class FindIcons(Scraper):
    def __init__(self, base_dir, url_header, log_file):
        super().__init__(log_file)
        self._base_dir = base_dir
        self._url_header = url_header
        self._page_icons = []

    def get_latest(self):
        """
        Parse `findicons.com` and get the id of the newest icons
        :return: id of the newest item
        """
        print(self.log("##\tGetting last page of content..."))
        url = "http://findicons.com/pack"
        # get the html from the url
        try:
            soup = self.get_site(url, self._url_header)
        except RequestsError as e:
            return 0
        max_id = soup.find("div", {"class": "pages"}).findAll("a")[-2].getText()
        print(self.log("##\tLast Page: " + max_id))
        return int(max_id)

    def parse(self, id_):
        """
        Using BeautifulSoup, parse the page for the wallpaper and its properties
        :param id_: id of the book on `findicons.com`
        :return:
        """
        prop = {}
        prop['id'] = str(id_)

        # Everything was successful
        return True

    def _dl_setup(self, q):
        while True:
            num = q.get()
            dl_link = self._page_icons[num][0]
            save_path = self._page_icons[num][1]
            print("Downloading: " + dl_link, end='\r')
            self.download(dl_link, save_path, self._url_header)

            q.task_done()
