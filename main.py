import os
import sys
import argparse
import configparser
from utils.log import setup_custom_logger
from utils.process import Process
# They are imported as all lowercase
#   so it is case insensitive in the config file
from modules.tuebl import Tuebl as tuebl
from modules.itebooks import ItEbooks as itebooks
from modules.wallhaven import Wallhaven as wallhaven
from modules.hubble import Hubble as hubble
from modules.iconfinder import IconFinder as iconfinder
from modules.findicons import FindIcons as findicons
from modules.xkcd import Xkcd as xkcd
from modules.whatif import WhatIf as whatif
from modules.howstuffworks import HowStuffWorks as howstuffworks
from modules.questionablecontent import QuestionableContent as questionablecontent


parser = argparse.ArgumentParser()
parser.add_argument('config', help='custom config file', nargs='?', default='./config.ini')
args = parser.parse_args()

config = configparser.ConfigParser()


def stop():
    """
    Save any data before exiting
    """
    for site in scrape:
        print(scrape[site]['class'].log("Exiting..."))
        scrape[site]['class'].stop()
    sys.exit(0)

if __name__ == "__main__":
    # Read config file
    if not os.path.isfile(args.config):
        print("Invalid config file")
        sys.exit(0)
    config.read(args.config)

    # Parse config file
    scrape = {}
    for site in config.sections():
        if config[site]['enabled'].lower() == 'true':
            try:  # If it not a class skip it
                site_class = getattr(sys.modules[__name__], site.lower())
            except AttributeError as e:
                print("\nThere is no module named " + site + "\n")
                continue
            dl_path = os.path.expanduser(config[site]['download_path'])
            # Create dl path if not there
            try:
                os.makedirs(dl_path)
            except Exception as e:
                pass
            num_files = int(config[site]['number_of_files'])
            threads = int(config[site]['threads'])
            log_file = os.path.join(dl_path, site + '.log')
            logger = setup_custom_logger('root', log_file)
            try:
                search = config[site]['search'].split(',')
            except KeyError as e:
                search = []
            if search:
                for term in search:
                    site_term = site + ":" + term
                    scrape[site_term] = Process(site_class, dl_path, term, num_files, threads)
            else:
                scrape[site] = Process(site_class, dl_path, '', num_files, threads)

    # Start site parser
    try:
        for site in scrape:
            print("#### Scrapeing: " + site)
            scrape[site].start()
    except Exception as e:
        print("Exception [main]: " + str(e))
        stop()
