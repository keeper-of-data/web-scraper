from utils.exceptions import *
from utils.scraper import Scraper


class QuestionableContent(Scraper):

    def __init__(self, base_dir, url_header, log_file):
        super().__init__(log_file)
        self._base_dir = base_dir
        self._url_header = url_header

    def get_latest(self):
        """
        Parse `http://questionablecontent.net/` and get the id of the newest comic
        :return: id of the newest item
        """
        self.cprint("##\tGetting newest upload id...\n", log=True)
        url = "http://questionablecontent.net/archive.php"
        # get the html from the url
        try:
            soup = self.get_site(url, self._url_header)
        except RequestsError as e:
            return 0
        max_id = int(soup.find("div", {"id": "archive"}).a['href'].split('=')[-1])
        self.cprint("##\tNewest upload: " + str(max_id) + "\n", log=True)
        return max_id

    def parse(self, id_):
        """
        Using BeautifulSoup, parse the page for the comic and its data
        :param id_: id of the comic on `http://questionablecontent.net/`
        :return:
        """
        prop = {}
        prop['id'] = str(id_)
        base_url = "http://questionablecontent.net"
        url = base_url + "/view.php?comic=" + prop['id']

        # get the html from the url
        try:
            soup = self.get_site(url, self._url_header)
        except RequestsError as e:
            return

        src = soup.find("img", {"id": "strip"})['src']
        prop['img'] = base_url + src

        #####
        # Download comic
        #####
        file_ext = self.get_file_ext(prop['img'])
        file_name = prop['id']
        prop['save_path'] = self._base_dir + "/" + prop['id'][-1] + "/"
        prop['save_path'] += self.sanitize(file_name) + file_ext
        self.download(prop['img'], prop['save_path'], self._url_header)

        # Everything was successful
        return True
