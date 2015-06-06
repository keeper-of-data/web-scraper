from utils.exceptions import *
from utils.scraper import Scraper


class Tuebl(Scraper):

    def __init__(self, base_dir, url_header, log_file):
        super().__init__(log_file)
        self._base_dir = base_dir
        self._url_header = url_header

    def get_latest(self):
        """
        Parse `http://tuebl.ca/browse/new` and get the id of the newest book
        :return: id of the newest item
        """
        self.cprint("##\tGetting newest upload id...\n", log=True)
        url = "http://tuebl.ca/browse/new"
        # get the html from the url
        try:
            soup = self.get_site(url, self._url_header)
        except RequestsError as e:
            return 0
        max_id = soup.find("h2", {"class": "book-title"}).a['href'].split('/')[-1]
        self.cprint("##\tNewest upload: " + max_id + "\n", log=True)
        return int(max_id)

    def parse(self, id_):
        """
        Using BeautifulSoup, parse the page for the wallpaper and its properties
        :param id_: id of the book on `tuebl.ca`
        :return:
        """
        prop = {}
        prop['id'] = str(id_)

        url = "http://tuebl.ca/books/" + prop['id']
        # get the html from the url
        try:
            soup = self.get_site(url, self._url_header)
        except RequestsError as e:
            return

        # Find data
        prop['title'] = soup.find("h2", {"class": "section-title"}).getText().strip()
        if prop['title'] == "Sorry This Book Has Been Removed":
            # If the book has been removed, move on to the next
            self.log("DCMA: " + prop['id'])
            return True

        content = soup.findAll("h3", {"class": "section-title"})
        series = content[0]
        author = content[1]
        if series.contents:
            prop['series_name'] = series.find("a").getText().strip()
            prop['series_id'] = series.a['href'].split('/')[-1]

        # book must have an author
        prop['author_name'] = author.find("a").contents[0].strip()
        prop['author_id'] = author.a['href'].split('/')[-1]

        content = soup.find("div", {"class": "row book-summary"})
        prop['summary'] = content.find("div", {"class": "col-3-4"}).getText().strip()

        book_cover_url = content.find("img", {}).get('src')

        # sanitize data
        prop['author_name'] = self.sanitize(prop['author_name'])
        prop['title'] = self.sanitize(prop['title'])

        # Download images and save
        book_dl_url = "http://tuebl.ca/books/" + prop['id'] + "/download"
        file_ext_book = ".epub"  # assume all books are epubs
        file_ext_cover = self.get_file_ext(book_cover_url)

        file_name = prop['author_name'] + " - " + prop['title']
        first_letter = prop['author_name'][0]
        first_two_letters = prop['author_name'][0:2].replace(' ', '_')

        path_title = prop['title']
        if len(path_title) > 32:
            path_title = path_title[0:32] + "%"

        prop['save_path'] = self._base_dir + "/" + first_letter + "/" + first_two_letters + "/"
        prop['save_path'] += prop['author_name'] + "/" + path_title + "/"
        prop['save_path'] += file_name + file_ext_book
        prop['save_path_cover'] = prop['save_path'] + file_name + file_ext_cover

        if not self.download(book_cover_url, prop['save_path_cover'], self._url_header):
            self.log("Failed to save cover image: " + prop['save_path_cover'])
        if not self.download(book_dl_url, prop['save_path'], self._url_header):
            self.log("Failed to save ebook: " + prop['save_path_cover'])
        self.save_props(prop)

        # Everything was successful
        return True

    def parse_author(self, id_):
        """
        Using BeautifulSoup, parse the page for the tag information
        :param id_: id of the author
        :return:
        """
        # TODO: create list of authors
        pass

    def parse_series(self, id_):
        """
        Using BeautifulSoup, parse the page for the tag information
        :param id_: id of the series
        :return:
        """
        # TODO: create list of series
        pass
