from utils.exceptions import *
from utils.scraper import Scraper
import os


class Wallhaven(Scraper):

    def __init__(self, base_dir, url_header, log_file):
        super().__init__(log_file)
        self._base_dir = base_dir
        self._url_header = url_header

    def get_latest(self):
        """
        Parse `http://alpha.wallhaven.cc/latest` and get the id of the newest book
        :return: id of the newest item
        """
        self.cprint("##\tGetting newest upload id...\n", log=True)
        url = "http://alpha.wallhaven.cc/latest"
        # get the html from the url
        try:
            soup = self.get_site(url, self._url_header)
        except RequestsError as e:
            # TODO: if we cant get the data from the site
            #       skip for now because it may just be a connection issue
            return 0
        max_id = soup.find("section", {"class": "thumb-listing-page"}).find("li").a['href'].split('/')[-1]
        self.cprint("##\tNewest upload: " + max_id + "\n", log=True)
        return int(max_id)

    def parse(self, id_):
        """
        Using BeautifulSoup, parse the page for the wallpaper and its properties
        :param id_: id of the book on `http://alpha.wallhaven.cc/wallpaper/`
        :return:
        """
        prop = {}
        prop['id'] = str(id_)

        url = "http://alpha.wallhaven.cc/wallpaper/" + prop['id']
        # get the html from the url
        try:
            soup = self.get_site(url, self._url_header)
        except RequestsError as e:
            return False

        # Find all sidebar data
        sidebar = soup.find("aside", {"id": "showcase-sidebar"})

        #####
        # Get colors
        #####
        prop['colors'] = []
        wp_colors = sidebar.find("ul", {"class": "color-palette"})
        for li in wp_colors.find_all("li"):
            prop['colors'].append(li['style'].split(':')[1])

        #####
        # Get tags
        #####
        prop['tags'] = []
        wp_tags = sidebar.find("ul", {"id": "tags"})
        for li in wp_tags.find_all('li'):
            tag = {}
            tag['purity'] = li.get("class", [])[1]
            tag['id'] = li['data-tag-id']
            tag['name'] = li.find("a", {"class": "tagname"}).getText().strip()
            prop['tags'].append(tag)

        #####
        # Get purity
        #####
        prop['purity'] = sidebar.find("fieldset", {"class": "framed"}).find("label").getText()

        #####
        # Get properties
        #####
        wp_prop = sidebar.find("dl")
        for dt in wp_prop.findAll('dt'):
            prop_name = dt.getText().strip()
            dd = dt.findNext("dd")
            if prop_name == 'Favorites':
                prop_value = dd.getText().strip()
            elif prop_name == 'Uploaded by':
                prop_value = dd.find(attrs={"class": "username"}).getText().strip()
            elif prop_name == "Added":
                prop_value = dd.find("time").get("datetime")
            else:
                prop_value = dd.getText().strip()

            prop[prop_name] = prop_value

        #####
        # Get image
        #####
        img_src = "http:" + soup.find("img", {"id": "wallpaper"}).get('src')

        #####
        # Download images
        #####
        file_ext = self.get_file_ext(img_src)
        file_name = "alphaWallhaven-" + prop['id']

        wallpaper_base_dir = os.path.join(self._base_dir, "wallpapers")
        prop['save_path'], prop['hash'] = self.create_hashed_path(wallpaper_base_dir, file_name)
        prop['save_path'] = os.path.join(prop['save_path'], file_name + file_ext)
        prop['rel_path'] = prop['save_path'].replace(self._base_dir, "")

        if self.download(img_src, prop['save_path'], self._url_header):
            self.save_props(prop)

        # Everything was successful
        return True

    def parse_tag(self, id_):
        """
        Using BeautifulSoup, parse the page for the tag information
        :param id_: id of the tag on `wallhaven.cc`
        :return:
        """
        # TODO: create list of tags
        pass
