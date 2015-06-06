from utils.exceptions import *
from utils.scraper import Scraper
import os
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
        url_base = "http://hubblesite.org"
        url = url_base + "/gallery/album/entire/npp/all/"
        # get the html from the url
        try:
            soup = self.get_site(url, self._url_header)
        except RequestsError as e:
            return

        image_block = soup.find("div", {"id": "ListBlock"})
        image_list = image_block.find_all("a", {"class": "icon"})

        for image in image_list:
            path_base = self._base_dir + "/" + image['id'] + "/"
            file_name = image['id'] + " - " + self.sanitize(image['title']) + ".txt"
            title_file = path_base + file_name
            # The `" "*n` is to blank the rest of the line
            print(self.log("Checking: " + image['id'] + " "*20), end='\r')

            # Check to see if we already have the data
            if not os.path.isfile(title_file):
                img_url = url_base + image['href']
                try:
                    img_soup = self.get_site(img_url, self._url_header)
                except RequestsError as e:
                    return
                # Check to see if we are on the new or the old site
                img_list = img_soup.find("div", {"id": "download-links-holder"})  # New site
                if img_list is None:  # Old Site
                    dl_file_list = self._old_site(img_soup, url_base)
                else:  # New Site
                    dl_file_list = self._new_site(img_soup, url_base)

                # Download list of images
                for image in dl_file_list:
                    self._download(image, path_base, title_file)

                # Create a file with the image title as its filename
                open(title_file, 'a').close()

        # Everything was successful
        return True

    def _new_site(self, soup, url_base):
        """
        Parse for images on the new site
        :return: List of files to download
        """
        dl_list = []
        img_list = soup.find("div", {"id": "download-links-holder"})

        # Check to if high res pics are linked
        img_hires_link = img_list.find("a", text=re.compile('Highest-quality download options'))
        if img_hires_link is not None:
            self.log("[NEW] Get high res")
            hires_url = url_base + img_hires_link['href']
            try:
                hires_soup = self.get_site(hires_url, self._url_header)
            except RequestsError as e:
                self.log("Skipping image: " + str(hires_url))
            else:
                hires_list = hires_soup.find("div", {"id": "download-links-holder"})
                hires_links = hires_list.find_all("li")
                for hires_link in hires_links:
                    hires_dl_url = hires_link.a['href']
                    # Add to download list
                    dl_list.append(hires_dl_url)

        self.log("[NEW] Get other")
        # Get all other images
        img_links = img_list.find_all("li")
        for img_link in img_links:
            link_url = img_link.a['href']
            img_dl_url = link_url
            if link_url.endswith('/'):
                link_url = url_base + link_url
                try:
                    link_soup = self.get_site(link_url, self._url_header)
                except RequestsError as e:
                    self.log("Skipping image: " + str(link_url))
                else:
                    img_dl_url = link_soup.find("div", {"class": "subpage-body"}).img['src']
            # Add to download list
            dl_list.append(img_dl_url)

        return dl_list

    def _old_site(self, soup, url_base):
        """
        Parse for images on the old site
        :return: List of files to download
        """
        dl_list = []
        img_list = soup.find("div", {"class": "image-formats"})

        # Check to if high res pics are linked
        img_hires_link = img_list.find("a", text=re.compile('Highest-quality download options'))
        if img_hires_link is not None:
            self.log("[OLD] Get high res")
            hires_url = url_base + img_hires_link['href']
            try:
                hires_soup = self.get_site(hires_url, self._url_header)
            except RequestsError as e:
                self.log("Skipping image: " + str(hires_url))
            else:
                hires_list = hires_soup.find("div", {"id": "image-format-container"})
                hires_links = hires_list.find_all("li")
                for hires_link in hires_links:
                    hires_dl_url = hires_link.a['href']
                    # Download this
                    dl_list.append(hires_dl_url)

        self.log("[OLD] Get other")
        # Get all other images
        img_links = img_list.find_all("a", {"class": "button"})
        for link in img_links:
            link_url = link['href']
            img_dl_url = link_url
            if link_url.endswith('/'):
                link_url = url_base + link_url
                try:
                    link_soup = self.get_site(link_url, self._url_header)
                except RequestsError as e:
                    self.log("Skipping image: " + str(link_url))
                else:
                    img_dl_url = link_soup.find("div", {"class": "image-view"}).img['src']
            # Download this
            dl_list.append(img_dl_url)

        return dl_list

    def _download(self, url, path_base, title_file):
        # The `" "*n` is to blank the rest of the line
        print(self.log("Downloading: " + url + " "*10), end='\r')
        file_name = url.split('/')[-1]
        self.download(url, path_base + file_name, self._url_header)
