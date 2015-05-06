from bs4 import BeautifulSoup
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
        html = self.get_html(url, self._url_header)
        if not html:
            return 0
        soup = BeautifulSoup(html)
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

        # url = "https://www.iconfinder.com/ajax/search/?page="+prop['id']+"&price=free&q="+self._search_term
        # # get the html from the url
        # html = self.get_html(url, self._url_header)
        # if not html:
        #     return False
        # soup = BeautifulSoup(html)
        # # Check for 404 page, not caught in get_html because the site does not throw a 404 error
        # if self._is_page(id_) is False:
        #     return False
        #
        # self._page_icons = []
        # # Find data
        # icons = soup.find_all("div", {"class": "downloadlinks"})
        # for icon in icons:
        #     links = icon.find_all("a", {"class": "downloadlink"})
        #     for link in links:
        #         icon_id = link['data-icon-id']
        #         dl_link = "https://www.iconfinder.com" + link['href']
        #         format = link['data-format']
        #         try: size = link['data-size']
        #         except Exception as e: size = ''
        #
        #         # save dl_link and path
        #         file = self._search_term + "-" + icon_id + "-" + size + "." + format
        #         save_path = self._base_dir + "/" + self._search_term + "/" + icon_id +"/"+ file
        #
        #         if not os.path.isfile(save_path):
        #             self._page_icons.append([dl_link, save_path])
        #
        #
        # # Done processing page
        # # Download all icons on page
        # print("")  # Add linebreak to output to not over write 'Processing: n'
        # q = queue.Queue()
        # threads = 10
        # for i in range(threads):
        #     t = threading.Thread(target=self._dl_setup, args = (q,))
        #     t.daemon = True
        #     t.start()
        #
        # # end_val need +1 so we can run the loop on that value
        # for item_id in range(len(self._page_icons)):
        #     q.put(item_id)
        # q.join()


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
