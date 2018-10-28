#!/usr/bin/env python

import os

IMG_ROOT_ENV = 'MY_IMAGE_DB_ROOT'
FALLBACK_IMG_ROOT = '/run/media/alex/Seagate Expansion Drive/backup.rsync.win/Pictures'

class Config(object):
    """Most common config parameters
    """
    DB_HOST = '192.168.1.102'
    DB_NAME = 'my_image_db'
    USERNAME = 'my_image_db'
    PASSWD = 'oj4VXLA4nDFAdt7k'
    IMG_ROOT = os.environ.get(IMG_ROOT_ENV, FALLBACK_IMG_ROOT)
