# --------------------------------------------
# HEADER: Python MotoFortuna application
# --------------------------------------------

import os, sys

# Add app lib path to python PYTHONLIBS ------
from os.path import \
    basename, splitext, dirname, abspath
ldir  = basename(__file__)
ldir  = splitext(ldir)[0] + '-lib'
lpath = dirname(abspath(__file__))
lpath = os.path.join(lpath, ldir)
if os.path.exists(lpath) and (lpath not in sys.path):
    sys.path.append(lpath)

import utils
utils.recompile(lpath)

# --------------------------------------------
# BODY: APPLICATION CODE
# --------------------------------------------

import web
import interface

urls = (
    '.*', 'interface.Request'
    )


#from dozer import Dozer

app = web.application(urls, globals())
interface.site.load(app)
application = app.wsgifunc()

#application = Dozer(app.wsgifunc())
#application = web.application(urls, globals())
#application.run()