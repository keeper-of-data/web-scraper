import os
from bs4 import BeautifulSoup
from utils.scraper import Scraper
import re


class Hubble(Scraper):
    def __init__(self, base_dir, url_header, log_file):
        super().__init__(log_file)
        self._base_dir = base_dir
        self._url_header = url_header

    def get_latest(self):
        """
        Will always be 1 because we are viewing all content on a single page
        :return: id of the newest item
        """
        print(self.log("##\tGetting max page number..."))
        return 1

    def parse(self, id_):
        """
        Using BeautifulSoup, parse the page for the image links
          then get all versions of that image from `http://hubblesite.org/gallery/album/entire/npp/all/`
        :param id_: page number, not used here since all images are listed on a single page
        :return:
        """
        prop = {}
        prop['id'] = str(id_)
        url_base = "http://hubblesite.org"
        url = url_base + "/gallery/album/entire/npp/all/"
        # get the html from the url
        html = self.get_html(url, self._url_header)
        if not html:
            return False
        soup = BeautifulSoup(html)

        # Find all sidebar data
        image_block = soup.find("div", {"id": "ListBlock"})
        image_list = image_block.find_all("a", {"class": "icon"})

        for image in image_list:
            img_url = url_base + image['href']
            img_html = self.get_html(img_url, self._url_header)
            if not img_html:
                continue
            img_soup = BeautifulSoup(img_html)
            # img_list = img_soup.find("ul", {"class": "inline-links screen"}).find_all("li")

            ##  TODO:
            ##    Split here for the 2 different pages it may bring you to
            img_list = img_soup.find("div", {"id": "download-links-holder"})  # New site
            if img_list is None:
                # Old Site
                self._old_site(img_soup, url_base, image)
            else:
                # New Site
                self._new_site(img_soup, url_base, image)

        # Everything was successful
        return True

    def _new_site(self, soup, url_base, image):
        img_list = soup.find("div", {"id": "download-links-holder"})

        # Check to if high res pics are linked
        img_hires_link = img_list.find("a", text=re.compile('Highest-quality download options'))
        if img_hires_link is not None:
            self.log("[NEW] Get high res")
            hires_url = img_hires_link['href']
            hires_html = self.get_html(url_base + hires_url, self._url_header)
            hires_soup = BeautifulSoup(hires_html)
            hires_list = hires_soup.find("div", {"id": "download-links-holder"})
            hires_links = hires_list.find_all("li")
            for hires_link in hires_links:
                hires_dl_url = hires_link.a['href']
                # Download here
                self._download(hires_dl_url, image)

        self.log("[NEW] Get other")
        # Get all other images
        img_links = img_list.find_all("li")
        for img_link in img_links:
            link_url = img_link.a['href']
            img_dl_url = link_url
            if link_url.endswith('/'):
                link_html = self.get_html(url_base + link_url, self._url_header)
                link_soup = BeautifulSoup(link_html)
                img_dl_url = link_soup.find("div", {"class": "subpage-body"}).img['src']
            # Download here
            self._download(img_dl_url, image)

    def _old_site(self, soup, url_base, image):
        img_list = soup.find("div", {"class": "image-formats"})  # Old site

        # Check to if high res pics are linked
        img_hires_link = img_list.find("a", text=re.compile('Highest-quality download options'))
        if img_hires_link is not None:
            self.log("[OLD] Get high res")
            hires_url = img_hires_link['href']
            hires_html = self.get_html(url_base + hires_url, self._url_header)
            hires_soup = BeautifulSoup(hires_html)
            hires_list = hires_soup.find("div", {"id": "image-format-container"})
            hires_links = hires_list.find_all("li")
            for hires_link in hires_links:
                hires_dl_url = hires_link.a['href']
                # Download here
                self._download(hires_dl_url, image)

        self.log("[OLD] Get other")
        # Get all other images 
        img_links = img_list.find_all("a", {"class": "button"})     
        for link in img_links:
            link_url = link['href']
            img_dl_url = link_url
            if link_url.endswith('/'):
                link_html = self.get_html(url_base + link_url, self._url_header)
                link_soup = BeautifulSoup(link_html)
                img_dl_url = link_soup.find("div", {"class": "image-view"}).img['src']
            # Download here
            self._download(img_dl_url, image)

    def _download(self, url, image):
        # The `" "*n` is to blank the rest of the line
        print(self.log("Downloading: " + url + " "*10), end='\r')
        file_name = url.split('/')[-1]
        save_path = self._base_dir + "/" + image['id'] + "/"
        self.download(url, save_path + file_name, self._url_header)
        title_file = save_path + self.sanitize(image['title']) + ".txt"
        open(title_file, 'a').close()

