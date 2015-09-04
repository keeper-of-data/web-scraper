from utils.exceptions import *
from utils.scraper import Scraper
from bs4 import BeautifulSoup
import urllib.request
import os
import re
import json
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
        If number of lines in self._completed_articles_csv is less then total articles - 500
            then run through all pages, other wise return 1
        :return: id of the newest item
        """
        self.cprint("##\tGetting newest upload id...\n", log=True)
        articles_per_page = 500

        # Get number of lines in articles.csv
        downloaded_articles = 0
        with open(self._completed_articles_csv) as f:
            for i, l in enumerate(f):
                downloaded_articles += 1

        url = "http://www.howstuffworks.com/big.htm?page=1"
        try:
            soup = self.get_site(url, self._url_header)
        except RequestsError as e:
            return 1
        num_articles = int(soup.find("div", {"class": "content"}).h3.get_text().split(' ')[-1].replace(',', ''))
        # Check if we need to scan more then the first page
        if abs(downloaded_articles - num_articles) <= 500:
            num_pages = 1
        else:
            num_pages = math.ceil(num_articles / articles_per_page)

        self.cprint("##\tGo to page: " + str(num_pages) + "\n", log=True)
        return num_pages

    def parse(self, id_):
        """
        Using BeautifulSoup, parse the page for links then will dig into found links
        :param id_: id of the page to parse
        :return:
        """
        # There is no 0 page
        if id_ == 0:
            return
        self.cprint("Processing links page: " + str(id_), log=True)
        url = "http://www.howstuffworks.com/big.htm?page=" + str(id_)
        # get the html from the url
        try:
            soup = self.get_site(url, self._url_header)
        except RequestsError as e:
            self.log("Failed to get html of links page: " + str(id_), level='warning')
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

            if url.split('//')[1].startswith('recipes.'):
                # Recipes do not have a mobile format, so the html is different
                whole_article = self.parse_article_recipe(url)
            else:
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
        try:
            with open(self._completed_articles_csv, 'a') as f:
                f.write(url + "," + article_path + "," + title + "\n")
        except UnicodeEncodeError:
            with open(self._completed_articles_csv, 'a') as f:
                f.write(url + "," + article_path + ",[UnicodeEncodeError]\n")

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
                article['content'][idx]['image_rel'] = "./assets/" + article['content'][idx]['image_abs'].split("/assets/")[-1]

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
            page_soup = BeautifulSoup(page['page_content'], "html5lib")
            # Download images and replace src to local file
            images = page_soup.find_all("img")
            if len(images) > 0:
                for image in images:
                    base_img_url = "http://s.hswstatic.com/"

                    img_dl_link = image['src']
                    if not image['src'].startswith(base_img_url):
                        img_dl_link = base_img_url + image['src']
                    self.cprint("Saving Image: " + image['src'], log=True)
                    abs_src = self.download_image(article, img_dl_link)
                    # Replace the src of downloaded image
                    article['content'][idx_page]['page_content'] = article['content'][idx_page]['page_content'].replace(image['src'], abs_src)

            # Replace HSW links with local path to file, create pdf of external sites and link locally
            # Options: http://wkhtmltopdf.org/usage/wkhtmltopdf.txt
            pdfkit_options = {
                                'quiet': '',
                                'no-background': '',
                                'disable-javascript': ''
                                }

            links = page_soup.find_all("a")
            if len(links) > 0:
                # Should remove duplicate links so we do not have to process the same thing twice
                links = set(links)
                for idx, link in enumerate(links):
                    if 'href' not in link:
                        continue

                    if re.match('.*howstuffworks\.com.*', link['href']):
                        try:
                            abs_path, full_path = self.get_save_path(link['href'])
                        except CrumbsError as e:
                            self.log("external link CrumbError: " + str(e) + " in url " + link['href'], level='warning')
                            continue
                        new_link = abs_path
                    else:
                        link_name = link.get_text().replace(' ', '_')
                        pdf_path = os.path.join(article['abs_path'], "assets", "link-" + str(idx) + ".pdf")
                        new_link = pdf_path

                        # Create pdf of external page
                        pdf_file = self._base_dir + pdf_path
                        if not os.path.isfile(pdf_file):
                            if link['href'].endswith('pdf'):
                                self.cprint("Downloading pdf: " + pdf_path, log=True)
                                # If it is linking to a pdf, then just download it
                                if not self.download(link['href'], pdf_file, self._url_header):
                                    self.log("pdf download failed: " + link_name , level='warning')
                            else:
                                self.cprint("Creating pdf: " + pdf_path, log=True)
                                try:
                                    pdfkit.from_url(link['href'], pdf_file, options=pdfkit_options)
                                except IOError as e:
                                    self.log("pdfkit IOError: [" + link_name + "] " + str(e), level='warning')
                                    continue
                                except Exception as e:
                                    self.log("pdfkit Exception: [" + link_name + "] " + str(e), level='warning')
                                    continue

                    # Convert to web safe path
                    abs_path = urllib.request.pathname2url(new_link)
                    # Replace link with link to article or a pdf
                    article['content'][idx_page]['page_content'] = article['content'][idx_page]['page_content'].replace(link['href'], new_link)

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
                raise CrumbsError("Cannot get_site")
        else:
            return []

        crumbs = []
        try:
            for crumb in page_soup.find("div", {"class": "breadcrumb"}).find_all("a"):
                crumbs.append(crumb.get_text().strip())
        except AttributeError:
            raise CrumbsError("No bread crumbs found")

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
            self.log("Failed to get soup of article: " + str(url), level='warning')
            return False

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

            article['url'] = url

            try:
                # Get bread crumbs
                article['bread_crumbs'] = self.get_crumbs(soup=page_soup)
            except CrumbsError as e:
                self.log("CrumbError: " + str(e) + " in url " + url, level='warning')
                return False

            # Get save path
            article['abs_path'], article['save_path'] = self.get_save_path(url, article['bread_crumbs'])

            # Get title & author
            header_soup = page_soup.find("div", {"id": "content-header"})
            article['title'] = header_soup.find("h1").get_text().strip()

            # I need to have a ['id'], just use the end of the url
            article['id'] = url.split('/')[-1]

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
                        self.log("Failed to get html of article page: " + str(idx+1) + " of " + str(url), level='warning')
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

    def parse_article_recipe(self, url):
        """
        Using BeautifulSoup, parse the article for recipe data
        :param url: url of the article
        :return:
        """
        try:
            page_soup = self.get_site(url, self._url_header)
        except RequestsError as e:
            self.log("Failed to get soup of article: " + str(url), level='warning')
            return False

        try:
            article = {}

            article['url'] = url

            try:
                # Get bread crumbs
                crumbs = page_soup.find("div", {"id": "BreadCrumb"}).find_all("li")
                # Only want the first 2 crumbs (excluding "Home")
                #   Reason: The mobile articles only have 2 crumbs
                article['bread_crumbs'] = [crumbs[1].get_text().strip(),
                                           crumbs[2].get_text().strip()]
            except AttributeError as e:
                self.log("CrumbError: " + str(e) + " in url " + url, level='error')
                return False

            # Get save path
            article['abs_path'], article['save_path'] = self.get_save_path(url, article['bread_crumbs'])

            # Get title & author
            header_soup = page_soup.find("div", {"id": "title"})
            article['title'] = page_soup.find("h1", {"class": "articleTitle"}).get_text().strip()

            # I need to have a ['id'], just use the end of the url
            article['id'] = url.split('/')[-1]

            try:
                article['author'] = page_soup.find("p", {"class": "articleByLine"}).a.get_text()
            except AttributeError:
                article['author'] = ''

            article['content'] = []  # List of content on each page

            self.cprint("Processing recipe page - " + article['title'])

            # Parse current page
            page_content = {}

            page_content['title'] = ''

            content = str(page_soup.find("div", {"id": "RecipeWell"}))
            page_content['page_content'] = content.strip()

            # Add page to article content
            article['content'].insert(0, page_content)
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
                html += '<img src="' + page['image_rel'] + '" />'
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
            with open(article['save_path'] + "index.json", 'w') as f:
                json.dump(article, f)
        except UnicodeEncodeError:
            self.log("UnicodeEncodeError: " + article['save_path'])
            with open(article['save_path'] + "index.html", 'w') as f:
                f.write("<h1>Failed to create html file. ERROR: UnicodeEncodeError</h1>")
