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
        url = "http://xkcd.com/archive/"
        # get the html from the url
        html = self.get_html(url, self._url_header)
        if not html:
            return 0
        soup = BeautifulSoup(html)
        list = soup.find("div", {"id": "middleContainer"})
        max_id = list.find_all("a")[0]['href'].split('/')[1]
        print(self.log("##\tNewest upload: " + max_id))
        return int(max_id)

    def parse(self, id_):
        """
        Using BeautifulSoup, parse the page for the comic and its data
        :param id_: id of the comic on `http://xkcd.com`
        :return:
        """
        prop = {}
        prop['id'] = str(id_)
        url = "http://xkcd.com/" + prop['id']
        # get the html from the url
        html = self.get_html(url, self._url_header)
        if not html:
            return False
        soup = BeautifulSoup(html)

        prop['title'] = soup.find("div", {"id": "ctitle"}).get_text()

        comic = soup.find("div", {"id": "comic"})

        prop['image'] = comic.img['src']

        if prop['image'].startswith('//'):
            prop['image'] = 'http:' + prop['image']
        else:
            prop['image'] = 'http://xkcd.com' + prop['image']

        try:
            prop['hover_text'] = comic.img['title']
        except Exception as e:
            prop['hover_text'] = ''

        #####
        # Download images
        #####
        file_ext = self.get_file_ext(prop['image'])
        file_name = prop['id'] + "-" + prop['title']
        prop['save_path'] = self._base_dir + "/" + prop['id'][-1] + "/"
        prop['save_path'] += self.sanitize(file_name) + file_ext
        if self.download(prop['image'], prop['save_path'], self._url_header):
            self.save_props(prop)

        # Everything was successful
        return True
