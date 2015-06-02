from bs4 import BeautifulSoup
from utils.scraper import Scraper
import math
import re
import json
import unicodedata

class HowStuffWorks(Scraper):
    def __init__(self, base_dir, url_header, log_file):
        super().__init__(log_file)
        self._base_dir = base_dir
        # Use mobile header, the mobile site it much simpler to parse
        self._url_header = {'User-Agent': 'Mozilla/5.0 (Linux; Android 4.4.4; en-us; Nexus 4 Build/JOP40D) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2307.2 Mobile Safari/537.36'}

    def get_latest(self):
        """
        Will always be 0 because we the parent loop to only run once
        All processing is done below in parse()
        :return: id of the newest item
        """
        print(self.log("##\tGetting newest upload id..."))
        return 0

    def parse(self, id_):
        """
        Using BeautifulSoup, parse the page for links then will dig into found links
        :param id_: id of the first page (always 1 in this case)
        :return:
        """
        prop = {}
        prop['id'] = str(id_)

        # Get number of pages to loop through
        url = "http://www.howstuffworks.com/big.htm?page=1"
        # get the html from the url
        html = self.get_html(url, self._url_header)
        if not html:
            return False
        soup = BeautifulSoup(html)
        num_pages = int(soup.find("div", {"class": "content"}).h3.get_text().split(' ')[-1].replace(',', ''))
        num_pages = math.ceil(num_pages/500)  # There are 500 results per page
        num_pages = 1
        # Now loop through each page to start parsing the links
        # for i in range(1, num_pages+1):
        #     print("Processing: " + str(i), end="\n")
        #     url = "http://www.howstuffworks.com/big.htm?page=" + str(i)
        #     # get the html from the url
        #     html = self.get_html(url, self._url_header)
        #     if not html:
        #         return False
        #     soup = BeautifulSoup(html)

        #     links = soup.find("ol").find_all("li")
        #     for link in links:

        #         try:
        #             print( "Processing: " + link.get_text().strip() + " "*10, end="\n" )
        #         except Exception as e:
        #             # Pass thrown because it cannot prit a char to the terminal
        #             pass


        #         # TODO: based on name, check if we have it already


        #         link_url = link.a["href"]
        #         # get the html from the url
        #         link_html = self.get_html(link_url, self._url_header)
        #         if not link_html:
        #             return False
        #         link_soup = BeautifulSoup(link_html)

        #         # See what type of post it is
        #         top10 = link_soup.find("div", {"class": "main mainTop10"})
        #         article = link_soup.find("div", {"class": "main mainArticle"})
        #         if top10:
        #             pass
        #             # self.parse_top10(top10)
        #         elif article:
        #             pass
        #             # self.parse_article(article)
        #         else:
        #             self.log("Unknown post type: " + link_url)
        ##TESTING

        # See what type of post it is
        # url = "http://money.howstuffworks.com/10-jobs-that-will-take-you-on-wild-adventures.htm"
        # url = "http://science.howstuffworks.com/nature/natural-disasters/sharknado.htm"
        url = "http://science.howstuffworks.com/nature/natural-disasters/sharknado.htm"
        test_data = self.parse_article(url)

        # Everything was successful
        return True

    def get_soup(self, url):
        """
        :param url: page url
        :return: BeautifulSoup object
        """
        html = self.get_html(url, self._url_header)
        soup = BeautifulSoup(html)
        return soup

    def parse_article(self, url):
        """
        Using BeautifulSoup, parse the article for its data
        :param url: url of the article
        :return:
        """
        page_soup = self.get_soup(url)

        # Get links for each page in the article
        links = []  
        page_links = page_soup.find("select", {"id": "pageSelector"}).find_all("option")
        for page_link in page_links:
            page_number = int(page_link.get_text().split(' ')[0])-1
            page_url = page_link['value']
            links.insert(page_number, page_url)

        article = {}
        # Get bread crumbs
        article['bread_crumbs'] = []
        for crumb in page_soup.find("div", {"class": "breadcrumb"}).find_all("a"):
            article['bread_crumbs'].append(crumb.get_text().strip())
        
        # Get title & author
        header_soup = page_soup.find("div", {"id": "content-header"})
        article['title'] = header_soup.find("h1").get_text().strip()
        author = header_soup.find("span", {"class": "content-author"}).a.get_text()
        article['author'] = " ".join(author.split())


        article['content'] = []  # List of content on each page
        # Parse each page in the article
        for idx, url in enumerate(links):
            print(idx, len(links))
            if idx is not 0:  # We do not need the first page because we got that soup above
                page_soup = self.get_soup(url)
                header_soup = page_soup.find("div", {"id": "content-header"})

            # Parse current page
            page_content = {}
            # If we are on the last page, parse a bit different
            if idx + 1 == len(links):
                print("last page")
                page_content['title'] = "Last page"
            # If we are not on the last page
            else:
                page_content['title'] = header_soup.find("h2").get_text().strip()
                media_soup = page_soup.find("div", {"class": "lead-image"})
                if media_soup:  # if there is an image
                    page_content['image_orig'] = media_soup.find("img")['src']
                    page_content['image_caption'] = media_soup.find("div", {"class": "media-body"}).get_text().strip()
                    page_content['image_credit'] = media_soup.find("div", {"class": "media-sub"}).get_text().strip()
                content = str(page_soup.find("div", {"class": "editorial-body"}))
                content = content.replace('<div class="editorial-body">', '')  # Remove the parent tag
                content = self.rreplace(content, '</div>', '', 1)  # Remove the parents div (last div in the string)
                page_content['page_content'] = content.strip()
            article['content'].insert(idx, page_content)

        with open("article.json", 'w') as f:
            json.dump(article, f, sort_keys=True, indent=4)
        
        return article
