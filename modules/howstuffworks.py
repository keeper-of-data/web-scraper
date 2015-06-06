from utils.exceptions import *
from utils.scraper import Scraper
from bs4 import BeautifulSoup
import os
import math
import pdfkit


class HowStuffWorks(Scraper):

    def __init__(self, base_dir, url_header, log_file):
        super().__init__(log_file)
        self._base_dir = base_dir
        self._completed_urls = []
        self._failed_urls = []
        self._completed_articles_csv = os.path.join(self._base_dir, "articles.csv")
        self._failed_articles_csv = os.path.join(self._base_dir, "articles_failed.csv")

        # Make sure file exists before we try and read form it
        open(self.create_dir(self._completed_articles_csv), 'a').close()
        # Fill self._completed_urls from articles.csv
        for line in open(self._completed_articles_csv, 'r'):
            self._completed_urls.append(line.split(',')[0])

        # Make sure file exists before we try and read form it
        open(self.create_dir(self._failed_articles_csv), 'a').close()
        # Fill self._failed_urls from articles.csv
        for line in open(self._failed_articles_csv, 'r'):
            self._failed_urls.append(line)

        # Use mobile header, the mobile site it much simpler to parse
        #   Reasons:
        #     - Both the Top10 and normal articles have the same html structure
        #     - The Top10 page on the desktop version has broken html and does not parse correctly
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
        # Get number of pages to loop through
        url = "http://www.howstuffworks.com/big.htm?page=1"
        # get the html from the url
        try:
            soup = self.get_site(url, self._url_header)
        except RequestsError as e:
            return

        num_pages = int(soup.find("div", {"class": "content"}).h3.get_text().split(' ')[-1].replace(',', ''))
        num_pages = math.ceil(num_pages/500)  # There are 500 results per page

        # Now loop through each page to start parsing the links
        for i in range(1, num_pages + 1):
            self.cprint("Processing link page: " + str(i), log=True)
            url = "http://www.howstuffworks.com/big.htm?page=" + str(i)
            # get the html from the url
            try:
                soup = self.get_site(url, self._url_header)
            except RequestsError as e:
                return

            links = soup.find("ol").find_all("li")
            # Loop through each link on the page
            for link in links:
                url = link.a["href"]

                # Check if url is a quiz (we do not want these, they are interactive flash objects)
                if str(url).endswith('quiz.htm'):
                    continue

                # Check if we already have this article
                if str(url) in self._completed_urls or str(url) in self._failed_urls:
                    continue

                self.cprint("Processing: " + url.split('/')[-1], log=True)

                whole_article = self.parse_article(url)
                # Something went wrong, so skip it
                if whole_article is False:
                    self.log("Something Failed: " + url)
                    self.add_failed(url)
                    continue

                self.cprint("Saving assets: " + whole_article['id'], log=True)
                # Download/save images
                whole_article = self.save_article_images(whole_article)

                # Parse page content for links to make local
                #   - External links will be saved in pdf form
                #   - How Stuff Works links will be changed into a local path to the article
                whole_article = self.process_content_links(whole_article)

                # Save json data in case we need to rebuild the article
                self.save_props(whole_article)

                # Create html file from article
                self.html_template(whole_article)

                # Add article to completed list
                self.add_completed(url, whole_article['abs_path'], whole_article['title'])

        # Everything was successful
        return True

    def add_completed(self, url, article_path, title):
        self._completed_urls.append(url)
        with open(self._completed_articles_csv, 'a') as f:
            f.write(url + "," + article_path + "," + title + "\n")

    def add_failed(self, url):
        self._completed_urls.append(url)
        with open(self._failed_articles_csv, 'a') as f:
            f.write(url + "\n")

    def save_article_images(self, article):
        """
        Saves main image in header of page
        :param article: dict of all article data
        :return: update article dict
        """
        for idx, page in enumerate(article['content']):
            if 'image_orig' in page:
                article['content'][idx]['image_abs'] = self.download_image(article, page['image_orig'])

        return article

    def download_image(self, article, image_url):
        """
        :return: absolute path for image
        """
        abs_image_path = article['abs_path'] + "assets/" + image_url.split('/')[-1]
        self.download(image_url, self._base_dir + abs_image_path, self._url_header)
        return abs_image_path

    def process_content_links(self, article):
        """
        Parse page content for links to make local
          - External links will be saved in pdf form
          - How Stuff Works links will be changed into a local path to the article
        :param article: dict of all article data
        :return: update article dict
        """
        for idx_page, page in enumerate(article['content']):
            page_soup = BeautifulSoup(page['page_content'])
            # Download images and replace src to local file
            images = page_soup.find_all("img")
            if len(images) > 0:
                for image in images:
                    abs_src = self.download_image(article, image['src'])
                    # Replace the src of downloaded image
                    article['content'][idx_page]['page_content'] = article['content'][idx_page]['page_content'].replace(image['src'], abs_src)

            # Replace HSW links with local path to file, create pdf of external sites and link locally
            # TODO: catch pdfkit errors/timeouts and try a few times before giving up
            # links = page_soup.find_all("a")
            # if len(links) > 0:
            #     for link in links:
            #         if re.match('.*howstuffworks\.com.*', link['href']):
            #             abs_path, full_path = self.get_save_path(link['href'])
            #             new_link = abs_path
            #         else:
            #             pdf_path = article['abs_path'] + "assets/" + link.get_text().replace(' ', '_') + ".pdf"
            #             new_link = pdf_path
            #             # Create pdf of external page
            #             try:
            #                 pdf_file = self._base_dir + pdf_path
            #                 if not os.path.isfile(pdf_file):
            #                     pdfkit.from_url(link['href'], pdf_file)
            #             except Exception as e:
            #                 # If it did not work, put the link back
            #                 new_link = link['href']

            #         # Convert to web safe path
            #         abs_path = urllib.request.pathname2url(new_link)
            #         # Replace link with link to article or a pdf
            #         article['content'][idx_page]['page_content'] = article['content'][idx_page]['page_content'].replace(link['href'], new_link)

        return article

    def get_save_path(self, url, crumbs=None):
        """
        Pass in the url of the article and crumbs list if you have them
        :param url: url of the article
        :param curmbs: list of bread crumbs, if not passed, a request will be sent to parse them
        :return: relative path & save path as a string
        """
        if crumbs is None:
            crumbs = self.get_crumbs(url)

        abs_path = '/articles'
        # Add crumbs to path
        for crumb in crumbs:
            crumb = self.sanitize(crumb.replace(' ', '_'))
            abs_path = os.path.join(abs_path, crumb)

        # Add article title to path
        title = url.split('/')[-1].split('.')[0]
        abs_path = os.path.join(abs_path, title)
        abs_path += '/'
        abs_path = os.path.normcase(abs_path)
        # Create full path
        full_save_path = os.path.normpath(os.path.join(self._base_dir, '.' + abs_path)) + '/'
        full_save_path = os.path.normcase(full_save_path)
        return (abs_path, full_save_path)

    def get_crumbs(self, url=None, soup=None):
        """
        Use soup if you have it, that way les requests are made to the site.
        :param url: url of article
        :param soup: soup of the page
        :return: list of crumbs
        """
        # Only request site if needed
        if soup is not None:
            page_soup = soup
        elif url is not None:
            try:
                page_soup = self.get_site(url, self._url_header)
            except RequestsError as e:
                return
        else:
            return []

        crumbs = []
        for crumb in page_soup.find("div", {"class": "breadcrumb"}).find_all("a"):
            crumbs.append(crumb.get_text().strip())

        return crumbs

    def parse_article(self, url):
        """
        Using BeautifulSoup, parse the article for its data
        :param url: url of the article
        :return:
        """
        try:
            page_soup = self.get_site(url, self._url_header)
        except RequestsError as e:
            return

        # Get links for each page in the article
        links = []
        page_links = page_soup.find("select", {"id": "pageSelector"})

        # Check if article has multipal pages
        if page_links:
            page_links = page_links.find_all("option")
            for page_link in page_links:
                page_number = int(page_link.get_text().split(' ')[0])-1
                page_url = page_link['value']
                links.insert(page_number, page_url)
        else:
            # If article is a single page
            links.append(url)

        try:
            article = {}

            # Get bread crumbs
            article['bread_crumbs'] = self.get_crumbs(soup=page_soup)

            # Get save path
            article['abs_path'], article['save_path'] = self.get_save_path(url, article['bread_crumbs'])

            # Get title & author
            header_soup = page_soup.find("div", {"id": "content-header"})
            article['title'] = header_soup.find("h1").get_text().strip()
            # I need to have a ['id']
            article['id'] = article['title'] if len(article['title']) > 1 else url.split('/')[-1]
            try:
                author = header_soup.find("span", {"class": "content-author"}).a.get_text()
                article['author'] = " ".join(author.split())
            except AttributeError:
                article['author'] = ''

            article['content'] = []  # List of content on each page
            # Parse each page in the article
            for idx, url in enumerate(links):
                self.cprint("Processing page: " + str(idx+1) + " of " + str(len(links)) + " - " + article['title'])
                if idx is not 0:  # We do not need the first page because we got that soup above
                    try:
                        page_soup = self.get_site(url, self._url_header)
                    except RequestsError as e:
                        continue
                    header_soup = page_soup.find("div", {"id": "content-header"})

                # Parse current page
                page_content = {}
                # If we are on the last page, parse a bit different
                if idx + 1 == len(links) and len(links) > 1:
                    # last page, skip it
                    continue
                # If we are not on the last page
                else:
                    try:
                        page_content['title'] = header_soup.find("h2").get_text().strip()
                    except AttributeError:
                        page_content['title'] = ''

                    media_soup = page_soup.find("div", {"class": "lead-image"})
                    if media_soup:  # if there is an image
                        page_content['image_orig'] = media_soup.find("img")['src']
                        try:
                            page_content['image_caption'] = media_soup.find("div", {"class": "media-body"}).get_text().strip()
                        except AttributeError:
                            page_content['image_caption'] = ''
                        try:
                            page_content['image_credit'] = media_soup.find("div", {"class": "media-sub"}).get_text().strip()
                        except AttributeError:
                            page_content['image_credit'] = ''

                    content = str(page_soup.find("div", {"class": "editorial-body"}))
                    # Remove the parent tag
                    content = content.replace('<div class="editorial-body">', '')
                    # Remove the parents div (last div in the string)
                    content = self.rreplace(content, '</div>', '', 1)
                    page_content['page_content'] = content.strip()
                article['content'].insert(idx, page_content)
        except Exception as e:
            # Something went wrong scraping the page
            self.log("Exception [" + url + "]: " + str(e))
            return False

        return article

    def html_template(self, article):
        """
        """
        html = '<html><head><title>' + article['title'] + '</title>'
        html += '<link rel="stylesheet" type="text/css" href="/assets/style.css"></head>'
        html += '<body>'
        html += '<div id="bread_crumbs">' + ' | '.join(article['bread_crumbs']) + '</div>'
        html += '<div id="title"' + article['title'] + '</div>'
        html += '<div id="author"' + article['author'] + '</div>'
        html += '<div id="content">'
        for idx, page in enumerate(article['content']):
            html += '<div id="page-' + str(idx) + '">'
            html += '<div class="page-title">' + page['title'] + '</div>'
            if 'image_abs' in page:
                html += '<div class="main-image">'
                html += '<img src="' + page['image_abs'] + '" />'
                html += '<div class="caption">' + page['image_caption'] + '</div>'
                html += '<div class="credit">' + page['image_credit'] + '</div>'
                html += '</div>'
            html += page['page_content']
            html += '</div>'

        html += '</div>'
        html += '</body></html>'

        try:
            with open(article['save_path'] + "index.html", 'w') as f:
                f.write(html)
        except UnicodeEncodeError:
            self.log("UnicodeEncodeError: " + article['save_path'])
            with open(article['save_path'] + "index.html", 'w') as f:
                f.write("<h1>Failed to create html file. ERROR: UnicodeEncodeError</h1>")
