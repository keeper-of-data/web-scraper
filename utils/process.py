import os
import queue
import logging
import threading
import traceback
from utils.scraper import Scraper


class Process(Scraper):

    def __init__(self, site, base_dir, search_term, parse_count=10, threads=1):
        self._search_term = search_term
        self._base_dir = base_dir
        self._progress_file = os.path.join(self._base_dir, "progress" + self._search_term)
        self.log_file = os.path.join(self._base_dir, "logs" + self._search_term)
        self._url_header = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}
        self._last_id = 0
        self._max_id = 0
        self._parse_count = parse_count
        self._threads = threads
        self._q = queue.Queue()
        super().__init__(self.log_file)

        # Get logger
        self.logger = logging.getLogger('root')

        if self._search_term != '':
            self.site = site(self._base_dir, self._url_header, self.log_file, self._search_term)
        else:
            self.site = site(self._base_dir, self._url_header, self.log_file)

    def start(self):
        self._max_id = self.site.get_latest()
        start_val = 0
        # Get start val from progress file if exist
        if os.path.isfile(self._progress_file):
            with open(self._progress_file, 'r') as outfile:
                start_val = int(outfile.read())
        self.cprint("##\tStarting at: " + str(start_val) + "\n", log=True)

        # Find out where to stop
        end_val = start_val + self._parse_count
        if self._parse_count == 0 and self._max_id != 0:
            end_val = self._max_id
        # If the end_val larger then the max_id, set end to max id
        #   Run the last id in case it is a page and there is new content on the page
        if self._max_id < end_val:
            end_val = self._max_id
            start_val = end_val
            self._last_id = self._max_id

        for i in range(self._threads):
            t = threading.Thread(target=self._thread_setup)
            t.daemon = True
            t.start()

        for item_id in range(start_val, end_val+1):
            self._q.put(item_id)
        self._q.join()

        self._done()

    def _thread_setup(self):
        while True:
            num = self._q.get()
            self.cprint("Processing: " + str(num), log=True)
            try:
                self.site.parse(num)
            except Exception as e:
                self.log("self.site.parse: " + str(e) + str(traceback.format_exc()), level='critical')
            # Having self._last_id here, it may reparse the same thing on next run
            #   because the last item processed may not have been the last item in the list because it is async
            self._last_id = num
            self._q.task_done()

    def _done(self):
        """
        Done parsing/downloading, clean up and save progress
        :return:
        """
        print("\n")  # Since we are using `\r` above, we need to enter down when exiting the script
        self.save_progress(self._progress_file, self._last_id)

    def stop(self):
        # not sure what is the last thread to run since it is async, so reparse all current threads on next start
        self._last_id -= self._threads
        self._done()
