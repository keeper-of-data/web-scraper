from utils.exceptions import *
from utils.scraper import Scraper


class Xkcd(Scraper):

    def __init__(self, base_dir, url_header, log_file):
        super().__init__(log_file)
        self._base_dir = base_dir
        self._url_header = url_header

    def get_latest(self):
        """
        Uses xkcd's api at https://xkcd.com/json.html
        :return: id of the newest item
        """
        self.cprint("##\tGetting newest upload id...\n", log=True)
        url = "http://xkcd.com/info.0.json"
        # Get the json data
        try:
            data = self.get_site(url, self._url_header, is_json=True)
        except RequestsError as e:
            return 0
        max_id = data['num']
        self.cprint("##\tNewest upload: " + str(max_id) + "\n", log=True)
        return int(max_id)

    def parse(self, id_):
        """
        Using the json api, get the comic and its info
        :param id_: id of the comic on `http://xkcd.com`
        :return:
        """
        # There is no 0 comic
        # 404 does not exists
        if id_ == 0 or id_ == 404:
            return

        url = "http://xkcd.com/" + str(id_) + "/info.0.json"
        try:
            prop = self.get_site(url, self._url_header, is_json=True)
        except RequestsError as e:
            return
        # prop Needs an id
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
