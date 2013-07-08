# coding: utf-8
# --------------------------------------------
# HEADER: Main configuration file
# --------------------------------------------

import os
isremote = os.name == 'posix'

DEBUG = True
DEBUG = False
RELOAD = True

SITE = "moto.gyrolab.net"
EMAIL = "info@moto.gyrolab.net"

ROOT = '/home/motofortuna/www/'
LOG  = '/home/motofortuna/logs/mf.log'

DB = '<db>'

DB_USER = '<dbuser>'
DB_PASS = '<dbpass>'
DB_HOST = 'localhost'
DB_MAXCON = 3

TEMPLATE_DIR = ROOT + 'templates/'
CAT_MAP      = ROOT + '.catmap'
URL_FOLDERS  = 3

TITLE_FMT = u'%s / Мотофортуна'

CACHE         = False
CACHE_SIZE    = 100000
CACHE_TIMEOUT = 3600

FASTID_LIFETIME = 1800
CRON_DEADLINE = 300
NEWS_LIFETIME = 72

if isremote:
    FICHE_IMAGE = 'http://moto.gyrolab.net/php/fiche_image.php?size=%s&id=%d'
    GOOGLE_KEY  = 'ABQIAAAAsDF9uDWmuFTdrmUMU6y6LBTPQFKkm4RMD9JoEzCtmRBxK6jglRREVtBHZWzABotO6AJRASwHjZ3_Dg'
    DEBUG = False
    RELOAD = False
else:
    FICHE_IMAGE = 'http://motofortuna.localhost/php/fiche_image.php?size=%s&id=%d'
    GOOGLE_KEY  = 'ABQIAAAAsDF9uDWmuFTdrmUMU6y6LBSueK_cYS-_pt_-S58oOkX2CMFyIhTXOzyDgMggE8W8wU3Kcp690YJRwA'
