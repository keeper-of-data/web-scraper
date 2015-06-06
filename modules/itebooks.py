from utils.exceptions import *
from utils.scraper import Scraper
import re


class ItEbooks(Scraper):

    def __init__(self, base_dir, url_header, log_file):
        super().__init__(log_file)
        self._base_dir = base_dir
        self._url_header = url_header

    def get_latest(self):
        """
        Parse `http://it-ebooks.info/` and get the id of the newest book
        :return: id of the newest item
        """
        print(self.log("##\tGetting newest upload id..."))
        url = "http://it-ebooks.info/"
        # get the html from the url
        try:
            soup = self.get_site(url, self._url_header)
        except RequestsError as e:
            return 0
        max_id = soup.find("td", {"width": 120}).find("a")['href'].split('/')[-2]
        print(self.log("##\tNewest upload: " + max_id))
        return int(max_id)

    def parse(self, id_):
        """
        Using BeautifulSoup, parse the page for the wallpaper and its properties
        :param id_: id of the book on `http://it-ebooks.info/book/`
        :return:
        """
        prop = {}
        prop['id'] = str(id_)

        url = "http://it-ebooks.info/book/" + prop['id']
        # get the html from the url
        try:
            soup = self.get_site(url, self._url_header)
        except RequestsError as e:
            return
        # Check for 404 page, not caught in get_html because the site does not throw a 404 error
        if soup.find("img", {"alt": "Page Not Found"}):
            self.log("Error [parse]: 404 " + url)
            return False

        # Find data
        prop['cover_img'] = "http://it-ebooks.info" + soup.find("img", {"itemprop": "image"})['src'].strip()
        prop['title'] = soup.find("h1", {"itemprop": "name"}).getText().strip()
        prop['description'] = soup.find("span", {"itemprop": "description"}).getText().strip()
        prop['publisher'] = soup.find(attrs={"itemprop": "publisher"}).getText().strip()
        prop['author'] = soup.find(attrs={"itemprop": "author"}).getText().strip().split(', ')
        prop['isbn'] = soup.find(attrs={"itemprop": "isbn"}).getText().strip()
        prop['year'] = soup.find(attrs={"itemprop": "datePublished"}).getText().strip()
        prop['pages'] = soup.find(attrs={"itemprop": "numberOfPages"}).getText().strip()
        prop['language'] = soup.find(attrs={"itemprop": "inLanguage"}).getText().strip()
        prop['format'] = soup.find(attrs={"itemprop": "bookFormat"}).getText().strip().lower()
        prop['dl_link'] = soup.find("a", {"href": re.compile('http://filepi.com')})['href']

        # sanitize data
        prop['publisher'] = self.sanitize(prop['publisher'])
        prop['title'] = self.sanitize(prop['title'])

        # Download images and save
        file_name = prop['publisher'] + " - " + prop['title']
        file_ext_cover = self.get_file_ext(prop['cover_img'])

        path_title = prop['title']
        if len(path_title) > 32:
            path_title = path_title[0:32] + "%"

        prop['save_path'] = self._base_dir + "/" + prop['publisher'] + "/" + path_title + "/"
        prop['save_path_cover'] = prop['save_path'] + file_name + file_ext_cover
        prop['save_path'] += file_name + "." + prop['format']
        self._url_header['Referer'] = url
        if not self.download(prop['cover_img'], prop['save_path_cover'], self._url_header):
            self.log("Failed to save cover image: " + prop['save_path_cover'])
        if not self.download(prop['dl_link'], prop['save_path'], self._url_header):
            self.log("Failed to save ebook: " + prop['save_path_cover'])
        self.save_props(prop)

        # Everything was successful
        return True
