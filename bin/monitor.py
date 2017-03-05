#!/usr/bin/env python
import logging
import os
import re
import subprocess
import time

from collections import deque, OrderedDict
from datetime import date
import inotify.adapters
from inotify.constants import IN_MODIFY, IN_CREATE, IN_ISDIR
from tinydb import TinyDB

_DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
_LOGGER = logging.getLogger(__name__)

MASK = (IN_MODIFY | IN_CREATE)
MASK_NEWDIR = (IN_CREATE | IN_ISDIR)
WAIT_TIME = 10  # in seconds


#def _configure_logging():
_LOGGER.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter(_DEFAULT_LOG_FORMAT)
ch.setFormatter(formatter)
_LOGGER.addHandler(ch)


def process(paths2process, db, wait=WAIT_TIME):
    cmd = 'echo heudiconv {0}'
    #if paths2process and time.time() - os.path.getmtime(paths2process[0]) > WAIT_TIME:
    processed = []
    for path, mod_time in paths2process.items():
        if time.time() - mod_time > wait:
            #process_me = paths2process.popleft().decode('utf-8')
            process_me = path
            cmd_ = cmd.format(process_me)
            try:
                print("Time to process {0}".format(process_me))
                subprocess.check_call(cmd_.split())
                _LOGGER.info("Done running {0}".format(cmd_))
                # here we should inspect output and then store additional info
                db.insert({'input_path': process_me, 'success': 1, 'subject_id': 'TODO', 'output_path': 'TODO'})
            except subprocess.CalledProcessError:
                _LOGGER.error("{0} failed".format(cmd_))
                db.insert({'input_path': process_me, 'success': 0})
            # if we processed it, or it failed, we need to remove it to avoid running it again
            processed.append(path)
    for processed_path in processed:
        del paths2process[processed_path]


def inspect_heudiconv_output(heudiconv_output):
    pass


def monitor(topdir='/tmp/new_dir', check_ptrn='/20../../..', db=None):
    #paths2process = deque()
    paths2process = OrderedDict()
    # watch only today's folder
    path_re = re.compile("(%s%s)/?$" % (topdir, check_ptrn))
    i = inotify.adapters.InotifyTree(topdir.encode())#, mask=MASK)
    for event in i.event_gen():
        if event is not None:
            (header, type_names, watch_path, filename) = event
            _LOGGER.info("WD=(%d) MASK=(%d) COOKIE=(%d) LEN=(%d) MASK->NAMES=%s "
                         "WATCH-PATH=[%s] FILENAME=[%s]",
                         header.wd, header.mask, header.cookie, header.len, type_names,
                         watch_path.decode('utf-8'), filename.decode('utf-8'))
            if header.mask == MASK_NEWDIR and path_re.match(watch_path.decode('utf-8')):
                # we got our directory, now let's do something on it
                newpath2process = os.path.join(watch_path, filename).decode('utf-8')
                #paths2process.append(newpath2process)
                # update time
                paths2process[newpath2process] = time.time()
                print(newpath2process, time.time()) 
            # check if we need to update the time
            for path in paths2process.keys():
                if path in watch_path.decode('utf-8'):
                    paths2process[path] = time.time()
                    print("Updating {0}: {1}".format(path, paths2process[path]))
                
        # check if there's anything to process
        process(paths2process, db)


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(prog='monitor.py', description='Small monitoring script to detect new directories and process them', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('path', help='Which directory to monitor')
    parser.add_argument('--check_ptrn', '-p', help='regexp pattern for which subdirectories to check', default='/20../../..')
    parser.add_argument('--database', '-d', help='database location', default='database.json')

    return parser.parse_args()


if __name__ == '__main__':
    _configure_logging()
    parsed = parse_args()
    # open database
    db = TinyDB(parsed.database, default_table='heudiconv')
    monitor(parsed.path, parsed.check_ptrn, db)
