import os
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from utils.exceptions import *


class Scraper:

    def __init__(self, log_file):
        self._errors = {}
        # Set default log path
        self.log_file = log_file
        # Store string of last line printed
        self.prev_cstr = ''

    def download(self, url, file_path, header={}):
        self.log("Starting download: " + url)
        self.create_dir(file_path)
        try:
            response = requests.get(url, headers=header, stream=True)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content():
                        f.write(chunk)
                return_value = True
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            return_value = False
            self.log("Error [download]: " + str(e.response.status_code) + " " + url)
        except requests.exceptions.ConnectionError as e:
            return_value = False
            self.log("Exception [download]: " + str(e) + " " + url)

        return return_value

    def get_file_ext(self, url):
        file_name, file_extension = os.path.splitext(url)
        return file_extension

    def create_hashed_path(self, base_path, name):
        """
        Create a directory structure using the hashed filename
        :return: string of the path to save to not including filename/ext
        """
        name_hash = hashlib.md5(name.encode('utf-8')).hexdigest()
        if base_path.endswith('/') or base_path.endswith('\\'):
            save_path = base_path
        else:
            save_path = base_path + "/"
        depth = 2  # will have depth of n dirs (MAX of 16 because length of md5 hash)
        for i in range(1, depth+1):
            end = i*2
            start = end-2
            save_path += name_hash[start:end] + "/"
        return save_path, name_hash

    def get_site(self, url, header={}, is_json=False):
        """
        Try and return soup or json content, if not throw a RequestsError
        """
        try:
            response = requests.get(url, headers=header)
            if response.status_code == requests.codes.ok:
                if is_json:
                    data = response.json()
                else:
                    data = BeautifulSoup(response.text)

                return data 
                
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            self.log("HTTPError [get_site]: " + str(e.response.status_code) + " " + url)
            raise RequestsError(str(e))
        except requests.exceptions.ConnectionError as e:
            self.log("ConnectionError [get_site]: " + str(e) + " " + url)
            raise RequestsError(str(e))

    def cprint(self, cstr, log=False):
        """
        Clear then print on same line
        :param cstr: string to print on current line
        """
        # Blank out whole line
        print(" "*len(self.prev_cstr), end='\r')
        self.prev_cstr = cstr
        try:
            print(cstr, end='\r')
        except UnicodeEncodeError:
            print('Processing...', end='\r')
        if log:
            self.log(cstr)

    def rreplace(self, s, old, new, occurrence):
        """
        Taken from: http://stackoverflow.com/questions/2556108/how-to-replace-the-last-occurence-of-an-expression-in-a-string
        """
        li = s.rsplit(old, occurrence)
        return new.join(li)

    def sanitize(self, string):
        """
        Catch and replace and invalid path chars
        [replace, with]
        """
        replace_chars = [
            ['\\', '-'], [':', '-'], ['/', '-'],
            ['?', ''], ['<', ''], ['>', ''],
            ['`', '`'], ['|', '-'], ['*', '`'],
            ['"', '\''], ['.', ''], ['&', 'and']
        ]
        for ch in replace_chars:
            string = string.replace(ch[0], ch[1])
        return string

    def get_time(self):
        """
        :return: Timestamp as a string
        """
        return str(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))

    def create_dir(self, path):
        try:
            os.makedirs(os.path.dirname(path))
        except Exception as e:
            pass
        return path

    def save_props(self, data):
        self.log("Saving metadata: " + data['id'])
        self.create_dir(data['save_path'])
        with open(data['save_path'] + ".json", 'w') as outfile:
            json.dump(data, outfile, sort_keys=True, indent=4)

    def error(self, error, data):
        """
        Save error to self._errors dict
        :param error: Error name
        :param data: Command/value that caused the error
        :return:
        """
        if error not in self._errors.keys():
            self._errors[error] = []
        self._errors[error].append(data)

    def save_errors(self, file):
        """
        Save errors into json file for review
        :return:
        """
        if self._errors:
            if not os.path.exists(os.path.dirname(file)):
                os.makedirs(os.path.dirname(file))
            with open(file + ".json", 'a') as errorfile:
                json.dump(self._errors, errorfile, sort_keys=True, indent=4)

    def log(self, data):
        """
        :param data: Data to save to file
        :return: Data as a string to print to console
        """
        if not os.path.exists(os.path.dirname(self.log_file)):
            os.makedirs(os.path.dirname(self.log_file))
        with open(self.log_file, 'a') as log_file:
            log_file.write( self.get_time() + "\t" + str(data) + "\n")

        return str(data)

    def save_progress(self, file, count):
        """
        Save the last id checked
        :return:
        """
        if not os.path.exists(os.path.dirname(file)):
            os.makedirs(os.path.dirname(file))
        with open(file, 'w') as outfile:
            if count < 0:
                count = 0
            outfile.write(str(count))