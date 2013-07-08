# coding: utf-8
# --------------------------------------------
# HEADER: Kernel classes for Site Application
# --------------------------------------------

import sys, types, re, trace, threading, time, datetime, hashlib
import web, jinja2
import config, sql, database, search
import utils

from abc import ABCMeta, abstractmethod, abstractproperty
from jinja2 import contextfunction
from utils import *
from const import *

__all__ = [
  "Request", "AbsDocument", "Image", "DocObj",
  "site", "db"
]

ALL_INPARAMS = ['ajax_from', 'ajax_id', 'query']

SHARED = 'shared'

class DocObjException(Exception):
    def __init__(self, message, mclass):
        self.message = message
        self.mclass = mclass
        Exception(message)

class KThread(threading.Thread):
    def __init__(self, *args, **keywords):
        threading.Thread.__init__(self, *args, **keywords)
        self.name = self.__class__.__name__
        self.killed = False

    def start(self):
        self.__run_backup = self.run
        self.run = self.__run
        threading.Thread.start(self)

    def __run(self):
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, why, arg):
        if why == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, why, arg):
        if self.killed:
            if why == 'line':
                log('System Exit (Killed)')
                raise SystemExit()
        return self.localtrace

    def kill(self):
        self.killed = True

"""
  Thread-safe access to functions of global objects:
  1. Locking
  2. Function execution
  3. Unlocking
"""

class Shared(object):
    def __init__(self, cls, *clsargs):
        self.__obj = cls(*clsargs)
        self.__function = {}
        self.__lock = threading.RLock()
        self.shlocked = False

    def __getattr__(self, name):
        attr = getattr(self.__obj, name)

        if isinstance(attr, types.MethodType):
            self.shlock()
            try:
                tid = threading.current_thread().ident
                self.__function[tid] = attr
                return self.__wrapper
            finally:
                self.shunlock()
        else:
            return attr

    def __wrapper(self, *args, **kwargs):
        self.shlock()
        try:
            tid = threading.current_thread().ident
            flist = self.__function
            res = flist[tid](*args, **kwargs)
            return res
        finally:
            if tid in flist:
                del flist[tid]
            self.shunlock()

    def shlock(self):
        self.__lock.acquire()
        self.shlocked = True
        return self

    def shunlock(self):
        self.__lock.release()
        self.shlocked = False

    def self(self):
        return self

class SharedPool (object):
    def __init__(self, cls, *clsargs):
        self.shpool = []
        self.shdefcon = 1
        self.shmaxcon = 1
        self.__timeout = 30
        self.__con = 0

        self.__cls = cls
        self.__clsargs = clsargs
        self.__lock = threading.RLock()

    def __getattr__(self, name):
         self.__lock.acquire()
         try:
             pooler = self.getpooler()
             return getattr(pooler, name)
         finally:
             self.__lock.release()

    def __call__(self, *args):
        return self.__getattr__('__call__')(*args)

    def __contains__(self, *args):
        return self.__getattr__('__contains__')(*args)

    def __getitem__(self, *args):
        return self.__getattr__('__getitem__')(*args)

    def __setitem__(self, *args):
        return self.__getattr__('__setitem__')(*args)

    def getpooler(self):
        pooler = None
        for row in self.shpool:
            obj = row['obj']
            if not obj.shlocked:
                if not pooler:
                    pooler = obj
                if (pooler != obj) and (time.time() - row['time'] >= self.__timeout):
                    self.delpooler(row)
        if pooler:
            return pooler

        if self.__con < self.shmaxcon:
            return self.addpooler()
        else:
            return self.shpool[-1]['obj']
                        

    def addpooler(self):
        obj = Shared(self.__cls, *self.__clsargs)
        pooler = dict(
            obj  = obj,
            time = time.time()
        )
        self.shpool.append(pooler)
        self.__con += 1
        return obj

    def delpooler(self, pooler):
        if self.__con > self.shdefcon:
            self.shpool.remove(pooler)
            self.__con -= 1

# Global jinja2 template engine
class PRender(object):
    def __init__(self):
        cache  = jinja2.FileSystemBytecodeCache('/tmp')
        loader = jinja2.FileSystemLoader(
            config.TEMPLATE_DIR,
            encoding = 'utf-8')

        self.__engine = jinja2.Environment(
            loader = loader,
            bytecode_cache = cache,
            extensions = ['jinja2.ext.do', 'jinja2.ext.loopcontrols'],
            line_statement_prefix = '#'
        )

    def __call__(self, template, ctx = None):
        if not ctx:
            ctx = {}
        robj = self.__engine.get_template(template + '.html')
        return robj.render(ctx)

    def evaluate(self, expression, ctx):
        robj = self.__engine.from_string(expression)
        return robj.render(ctx)

# Global cache
class PCache(object):
    def __init__(self):
        self.__cache = {}
        self.__maxsize = config.CACHE_SIZE

    def __contains__(self, key):
        return key in self.__cache

    def __getitem__(self, key):
        if key in self:
            return self.get(key)
        return None

    def __setitem__(self, key, value):
        self.set(key, value)

    def __delold(self):
        def cachesize():
            sz = sys.getsizeof(self.__cache)
            for row in self.__cache.itervalues():
                sz += sys.getsizeof(row[0]) + 16
            return sz

        d = sorted(self.__cache.items(), key = lambda x: x[1][1])
        keys = [row[0] for row in d]
        while (cachesize() > self.__maxsize) and keys:
            key = keys.pop(-1)
            del self.__cache[key]            

    def set(self, key, value, sysdata = False):
        if not config.CACHE and not sysdata:
            return None
        self.__delold()
        self.__cache[key] = [value, time.time()]        

    def get(self, key):
        if key in self.__cache:
            row = self.__cache[key]
            row[1] = time.time()
            return row[0]
        else:
            return None

class PConfig(object):
    def __init__(self):
        self.__data = None
        self.idp = None
        self.load()

    def __call__(self, key, paramno = 1):            
        if key in self.__data:
            val = self.__data[key]['val' + str(paramno)]
            return toint(val)
        else:
            return None

    def getlist(self, lsub, paramno = 1):
        res = {}
        ln = len(lsub)
        for key in self.__data:
            if key[:ln] == lsub:
                res[key] = self(key, paramno)
        return res

    def load(self):
        self.idp = db.propbytr("sparams")
        q = sql.get_fval(['name', 'val1', 'val2', 'val3', 'val4'], 'param', 'id_prop')
        self.__data = site.db.fetchdic(q, 'name', [self.idp])

    def set(self, key, value, paramno = 1):
        field = 'val' + str(paramno)
        d = self.__data
        if key in d:
            q = sql.update([field], 'param', filter = ['name = %s', 'id_prop = %s'])
            db.execute(q, [value, key, self.idp], commit = True)
        else:
            q = sql.insert(['id_prop', 'name', field], 'param')
            db.execute(q, [self.idp, key, value], commit = True)
            d[key] = [None] * 4
        d[key] = list(d[key])
        d[key][paramno - 1] = value

    def clear(self):
        self.__data = None

class PGvar(Storage):
    def __init__(self):
        self.traceurl = False
        self.nocron = False
        self.frontpage = {}
        self.params = Storage()

# -------------------------------------------
# CRON Section
# -------------------------------------------

class CronTimer(KThread):
    def __init__(self, cron, ptid):
        self.__cron = cron
        self.__exec = None
        self.__ptid = ptid
        KThread.__init__(self)

    def run(self):
        while True:
            time.sleep(5)
            self.check_zombie()
            if self.__exec and self.__exec.isAlive():
                log('CronTimer: Previous execer found, deadline %d sec..' % config.CRON_DEADLINE)
                t = config.CRON_DEADLINE
                while self.__exec.isAlive():
                    if t <= 0:
                        self.__exec.kill()
                        self.__exec = None
                        log('CronTimer: Execer killed')
                        break
                    t = t - 2
                    time.sleep(2)

            tasklist = []
            t = time.time()

            #  CRON   
            cron = site.cron.shlock()
            try:
                for (name, task) in cron.tab.iteritems():
                    if t > task.nextrun:
                        tasklist.append((name, task))
                        task.nextrun = task.nextrun + task.interval
                    #else:
                    #    log('CronTimer[%s]: Skipping %s' % (self.ident, name))
            finally:
                cron.shunlock()

            if tasklist:
                self.__exec = CronExec(tasklist)
                self.__exec.start()

    def check_zombie(self):
        for t in threading.enumerate():
            if isinstance(t, threading._MainThread):
                if t._Thread__stopped:
                    log("Thread [%s] Stopped" % self.ident)
                    self.stop()

    def stop(self):
        if self.__exec:
            self.__exec.kill()
        for t in threading.enumerate():
            try:
                t.kill()
            except Exception, e:
                pass

class CronExec(KThread):
    def __init__(self, tasklist):
        self.__tasklist = tasklist
        KThread.__init__(self)     
                                            
    def run(self):
        i = 0
        k = 0
        for (name, task) in self.__tasklist:
            i += 1
            log('Cron [%d of %d], executing "%s"...' % (i, len(self.__tasklist), name))
            try:
                task.func(*task.args)
            except Exception, e:
                k += 1
                log('Cron error for "%s": %s' % (name, e), M_ERR)

        log('Cron: Completed (%d=OK, %d=ERR)' % (i - k, k))
 
class PCron(object):
    def __init__(self):
        self.tab = {}
        if not site.gvar.nocron:
            self.timer = CronTimer(self, None)
            self.start()

    def add(self, name, firstrun, interval, func, *args):
        if firstrun == -1:
            log('Cron: Task [INIT], executing "%s"...' % name)
            try:
                func(*args)
            except Exception, e:
                log('Cron error for "%s": %s' % (name, e), M_ERR)
            firstrun = interval

        task = Storage()
        task.interval = interval
        task.func     = func
        task.args     = args
        if not firstrun:
            firstrun = 0
        task.nextrun  = time.time() + firstrun
        self.tab[name] = task

    def inittasks(self, tasklist):
        i = 0
        k = 0
        for (name, task) in self.__tasklist:
            if firstrun == -1:
                func(*args)
                firstrun = interval
            i += 1
            log('Cron [%d of %d], executing "%s"...' % (i, len(self.__tasklist), name))
            try:
                task.func(*task.args)
            except Exception, e:
                k += 1
                log('Cron error for "%s": %s' % (name, e), M_ERR)

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()


# -------------------------------------------
# Sessions
# -------------------------------------------
class SessionStore(web.session.Store):
    table = 'session'

    def __init__(self):
        self.__dict = {}
        self.__cnt  = 1

    def __contains__(self, key):
        return key in self.__dict

    def __getitem__(self, key):
        if key in self:
            return self.__dict[key][0]
        return None

    def __setitem__(self, key, value):
        if key in self:
            self.__dict[key][0] = value
        else:
            self.__dict[key] = [value, time.time(), web.ctx.ip, self.__cnt]
            if self.__cnt >= 0xFFFF:
                self.__cnt = 1
            else:
                self.__cnt += 1

    def clientid(self, key):
        if key in self.__dict:
            return self.__dict[key][3]
        return None

    def cleanup(self, timeout):
        d = self.__dict
        for key in d.keys():
            if time.time() - timeout > d[key][1]:
                del d[key]

# -------------------------------------------
# SITE Section
# -------------------------------------------

class Site(object):
    def __init__(self):
        global site
        site = self

        self.session = None      
        self.app     = None
        self.urlmap  = None
        self.gvar    = PGvar()

        self.db = SharedPool(database.Database)
        self.db.shmaxcon = config.DB_MAXCON

        self.render = PRender()
        self.cache  = SharedPool(PCache)
        self.config = SharedPool(PConfig)
        self.search = SharedPool(search.ProdSearch, self)
        self.cron   = SharedPool(PCron)

    def load(self, app):
        self.app = app
        #self.session = web.session.Session(self.app, web.session.DiskStore('sessions'))
        store = SharedPool(SessionStore)
        self.session = web.session.Session(self.app, store, dict(shared = {}))

class Context(object):
    inparams  = []
    outparams = []
    lparams   = []

    def __getctxall(self):
        ctxall = {}
        ctxall.update(self.ctxshared)
        ctxall.update(self.ctx)
        return ctxall

    ctxall = property(__getctxall)

    def __init__(self, parent):
        self.site      = site
        self.db        = site.db
        self.parent    = parent
        self.root      = None
        self.childs    = []
        self.ctx       = Storage()

        self.loadses()
        if parent:
            parent.childs.append(self)
            self.root = self.parent.root
            self.ctxshared = parent.ctxshared
            self.updatectx(parent.ctx)
            self.updatectx(parent.root.ctx)
        else:
            self.root = self
            self.ctxshared = Storage()
            self.loadctx()

    def __call__(self, key, default = None):
        if key in self.ctx:
            return self.ctx[key]
        elif key in self.ctxshared:
            return self.ctxshared[key]
        else:
            return default

    def childlist(self, obj = None, lst = None):
        if not obj:
            obj = self
            lst = []
        lst.append(obj)
        for child in obj.childs:
            self.childlist(child, lst)
        return lst

    def loadctx(self):
        pass

    def updatectx(self, actx):
        for key in self.inparams:
            if key in actx:
                self.ctx[key] = actx[key]

    def add(self, **kwargs):
        for (key, val) in kwargs.iteritems():
            self.ctx[key] = val

    def addshared(self, **kwargs):
        self.add(**kwargs)
        for (key, val) in kwargs.iteritems():
            self.ctxshared[key] = val

    def save(self, dest = None, force = False, **kwargs):
        if not site.session:
            return
        if self.root('static') and not force:
            return
        if dest == None:
            c = self.__class__.__name__
        else:
            c = dest

        if c not in site.session:
            site.session[c] = Storage()

        ctx = site.session[c]

        for (key, val) in kwargs.iteritems():
            if val != None:
                ctx[key] = val
                self.ctx[key] = val
                if c == SHARED:
                    self.ctxshared[key] = val
            else:
                ctx.pop(key, None)
                self.ctx.pop(key, None)
                if c == SHARED:
                    self.ctxshared.pop(key, None)

    def savelist(self, *lst):
        kwargs = {}
        for key in lst:
            kwargs[key] = self(key)
        self.save(**kwargs)

    def loadses(self):
        if not site.session:
            return
        lst = []
        lst.append(self.__class__.__name__)
        lst.append(SHARED)
        for c in self.lparams:
            lst.append(c)
        for c in lst:
            if c in site.session:
                self.ctx.update(site.session[c])

class Request(Context):
    def __init__(self, path = None, inparams = None):
        self.path      = path
        self.inparams  = inparams
        self.params    = None
        self.module    = None
        self.ajax      = False
        self.ajaxmulti = False
        self.ext       = DEFAULT_EXT

        self.k   = None
        self.cat = None
        s = site.session
        if s and 'session_id' in s:
            self.clientid = s.store.clientid(s.session_id)
        else:
            self.clientid = None
        Context.__init__(self, None)

    def loadctx(self):
        if self.inparams:
            params = self.inparams
        elif 'env' in web.ctx:
            params = web.input()
        else:
            return
        for (key, val) in params.iteritems():
            self.ctx[key] = toint(val)

    def GET(self):
        return self.getdata()

    def POST(self):
        return self.getdata()

    def getdata(self):
        log.t_start()
        log.t_trace("Request INIT")
        #------------------------------------------------------
        url = self.path or web.ctx.path
        self.url = re.sub('^/catalog', '', url)

        m = hashlib.md5()
        m.update(real_translit(url))
        m.update(str(self.ctx))
        self.crc = m.digest()

        log.t_trace("Ask cache")
        result = site.cache.get(self.crc)
        if result:
            log.t_trace("Return from cache")
            return result

        site.config.load()
        if 'marker' in self.ctx:
            self.ajax = True
            self.ajaxmulti = 'ajax_tree' in self.ctx

        mo = re.search(r'^(.*)\.([a-z]*)$', url)
        if mo:
            url = mo.group(1)
            self.ext = mo.group(2)

        if not re.match(r'^[a-zA-Z0-9_\-/\.]*$', url):
            self.NotFound('Url do not passed regexpr control!')

        if url[:1]  == '/': url = url[1:]
        if url[-1:] == '/': url = url[:-1]
        self.params = re.split('[/_]', url)

        if len(self.params) == 0:
            self.NotFound("Params length = 0")

        self.module = self.params.pop(0)

        if not self.module in site.urlmap:
            self.NotFound("No module in url")

        self.img  = None
        self.page = 1

        res = self.__LastParam('preview', MOD_IMAGE, lambda s: s == '')
        if res == '':
            self.img = 'preview'

        res = self.__LastParam('img', MOD_IMAGE, isint)
        if res:
            self.img = toint(res)

        res = self.__LastParam('page', MOD_CATALOG, isint)
        if res:
            self.page = toint(res)

        cls = site.urlmap[self.module]
        if self.module in site.urlmap:
            cls = site.urlmap[self.module]
        else:
            self.NotFound("No module '%s' in urlmap" % self.module)

        if not issubclass(cls, RequestObj):
            self.NotFound("Module '%s' is not RequestObj class" % self.module)

        request = cls(self)
        log.t_trace("BEFORE REQUEST")
        result = request.getall()
        site.cache.set(self.crc, result)
        #for c in self.childlist():
        #    c.saveses()
        log.t_trace("AFTER REQUEST")
        return result

    def __LastParam(self, prefix, module, check = None):
        res = None
        if self.params:
            last = str(self.params[-1])
            pos = len(prefix)
            if last and (last[:pos] == prefix):
                if self.module != module:
                    self.NotFound("Module '%s' not found" % module)
                res = last[pos:]
                if check and not check(res):
                    self.NotFound("Param '%s' not passed" % last)
                del self.params[-1]
        if self.params:
           return res
        elif self.module not in const.ROOT_MODS:
            self.NotFound("Params is empty")

    def NotFound(self, message = None):
        message = site.render('sys/error404', dict(message = message))

        status = '404 Not Found'
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        raise web.HTTPError(status, headers, message)

    def redirect(self, url):
        if self.ajax:
            status  = "200 OK"
            headers = {'Content-Type': 'text/html; charset=utf-8'}
            message = "<script>document.location = '%s'</script>" % url
        else:
            status  = "301 Moved Permanently"
            headers = {'Content-Type': 'text/html; charset=utf-8', 'Location': url}
            message = ""
        raise web.HTTPError(status, headers, message)

class RequestObj(Context):
    __metaclass__ = ABCMeta
    ext = None
    db  = False

    def __init__(self, request):
        Context.__init__(self, request)
        self.NotFound = request.NotFound
        self.redirect = request.redirect
        self.request  = request

    @abstractmethod
    def params(self, params):
        pass

    # Virtual method
    def prepare(self):
        pass

    @abstractmethod
    def get(self):
        pass

    def getall(self):
        res = self.params(self.request.params)
        log.t_trace('request.params done')
        if res:
            return res
        else:
            res = self.prepare()
            if res:
                return res
        log.t_trace('request.prepare done')
        if self.ext != self.request.ext:
            self.NotFound()
        #if not self.request('static'):
        #    dt = db.fetchval(sql.get_fval('lastmod', 'sitemap', 'url'), [self.request.url])
        #    if dt:
        #        web.http.lastmodified(dt)
        return self.get()

class AbsDocument(RequestObj):
    ext = DEFAULT_EXT

    def __gethead(self):
        return self.__head

    def __gettitle(self):
        return self.__title

    def __settitle(self, value):
        if value:
            self.__head  = value
            self.__title = config.TITLE_FMT % value

    head  = property(__gethead)
    title = property(__gettitle, __settitle)

    def __init__(self, request):
        RequestObj.__init__(self, request)
        self.__markers = {}
        self.__title = ''
        self.__head  = ''
        self.meta_kw   = None
        self.meta_desc = None
        self.markers()
        self.ai = AjaxInterface(self)
        webheader('Content-Type', 'text/html; charset=utf-8')

        self.addshared(params = self.request.params)
        self.addshared(doc = self)

    @abstractmethod
    def markers(self):
        pass

    def meta(self):
        pass

    def addmarker(self, classinfo, marker = 'root'):
        self.__markers[marker] = classinfo
        classinfo.markers(self)

    def getclass(self, marker):
        if marker in self.__markers:
            return self.__markers[marker]
        else:
            return None

    def getmarker(self, cls):
        for (key, val) in self.__markers.iteritems():
            if val == cls:
                return key
        return None

    def get(self):
        self.__rstring = []
        if self.request.ajax:
            marker = self.request('marker')
        else:
            marker = 'root'

        ajax_manual = self.request('ajax_manual')

        self.ai.load()
        log.t_trace('SYS.ai loaded')
        self.render(self, marker, self.ai.ajaxid)
        log.t_trace('SYS.site rendered')
        rstring = "\n".join(self.__rstring)
        log.t_trace('SYS.join context +')
        if not ajax_manual:
            rstring = self.ai.addmodel(rstring)
            log.t_trace('SYS.ai.addmodel +')
            rstring = self.__addtitle(rstring)
            log.t_trace('SYS.title parsed')
            rstring = self.__addmeta(rstring)
            log.t_trace('SYS.meta parsed')
        return rstring

    def render(self, parent, marker, sysid):
        obj = self.newobj(parent, marker, sysid)
        self.__rstring.append(obj.render())
        if self.request.ajaxmulti:
            depctx  = {}
            obj.ajaxdeps(depctx)
            if depctx:
                for (dest, params) in depctx.iteritems():
                    obj.ctx.update(params)
                    marker = self.ai.findmarker(dest, obj)
                    sysid = self.ai.findid(marker, obj)
                    if sysid:
                        self.render(obj, marker, sysid)

    def newobj(self, parent, marker, sysid = None):
        cls = self.__markers[marker]

        obj = cls(parent, marker, self)
        if sysid:
            obj.sysid = sysid
        obj.sysid  = self.ai.add(obj)
        obj.id     = const.SYS_DOCOBJ_ID % obj.sysid
        return obj

    def geturl(self, *args, **kwargs):
        url = geturl(self, *args, **kwargs)
        if site.gvar.traceurl:
            site.gvar.traceurl(url)
        return url

    def __addtitle(self, rstring):
        if not self.__title:
            return rstring
        if self.request.ajax:
            t = '<head><title>%s</title></head>\n' % self.__title
            return t + rstring
        else:
            t = '<title>%s</title>\n' % self.__title
            return re.sub(r'<title>(.*?)</title>', t, rstring)

    def __addmeta(self, rstring):
        self.meta()
        sdef = self.__head if self.__head else const.MSG_DESC
        s = self.meta_kw if self.meta_kw else sdef
        kw = []
        for word in words(s.lower(), expr = u'[a-zа-я0-9\-]{2,}'):
            if word not in search.STOPWORDS:
                kw.append(word)
        rstring = rstring.replace('%KEYWORDS%', ", ".join(kw))

        if self.meta_desc:
            rstring = rstring.replace('%DESC%', self.meta_desc)
        else:
            rstring = rstring.replace('%DESC%', sdef)
        return rstring


class DocObj(Context):
    template = None

    @contextfunction
    def __newobj(self, ctx, marker):
        obj = self.doc.newobj(self, marker)
        rstring = obj.render()
        obj.updatectx(ctx)
        return rstring

    @contextfunction
    def __message(self, context, message, head = None, mclass = M_INFO, style = "block"):
        ctx = dict(head = head, message = message, mclass = mclass, style = style)
        return site.render('sys/message', ctx)

    @contextfunction
    def __findid(self, context, marker):
        return SYS_DOCOBJ_ID % self.doc.ai.findid(marker, self)

    @contextfunction
    def __title(self, context, title):
        self.doc.title = title
        return ''

    @contextfunction
    def __eval(self, context, expression):
        if expression:
            return site.render.evaluate(expression, context)
        else:
            return None

    @classmethod
    def markers(cls, doc):
        pass

    def __init__(self, parent, marker, doc):
        log.t_trace("DocObj %s created" % self.__class__.__name__)
        Context.__init__(self, parent)
        self.sysid  = None
        self.doc    = doc
        self.marker = marker
        self.ajax   = False
        self.NotFound = doc.NotFound
        self.title    = doc.title

        self.add(obj = self, doc = self.doc, site = site, config = config, db = site.db)
        self.add(utils = utils, sql = sql)
        self.add(kernel = sys.modules[__name__])
        self.add(title = self.__title)
        self.add(sys_new    = self.__newobj)
        self.add(sys_msg    = self.__message)
        self.add(sys_findid = self.__findid)
        self.add(sys_eval   = self.__eval)

    # Virtual method
    def prepare(self, doc):
        pass

    # Virtual method, should returns dict with marker list for dependensy search
    def ajaxdeps(self, ctx):
        pass

    def ajaxfunc(self, *args, **kwargs):
        return self.doc.ai.getfunc(self, *args, **kwargs)

    def ajaxhref(self, *args, **kwargs):
        res = self.doc.ai.getfunc(self, *args, **kwargs)
        return 'href="#" onclick = "%s"' % res

    # Virtual method
    def render(self):
        log.t_trace("DocObj %s preparation start" % self.__class__.__name__)
        try:
            res = self.prepare(self.doc)
            log.t_trace("DocObj %s preparation end" % self.__class__.__name__)
            if res:
                rstring = res
            else:
                rstring = site.render(self.template, self.ctxall)
        except DocObjException, e:
            rstring = self.__message(None, e.message, mclass = e.mclass)

        log.t_trace("DocObj %s rendered" % self.__class__.__name__)

        if not self.doc.request('ajax_manual'):
            if self.ajax:
                rstring = const.AJAX_REPLY % (self.id, rstring, self.id)
            elif self.marker != 'root':
                rstring = const.AJAX_BLOCK % (self.id, rstring)
        return rstring

    def error(self, message, mclass):
        raise DocObjException(message, mclass)

class AjaxInterface(object):
    def __init__(self, doc):
        self.__doc    = doc
        self.__tree   = {}
        self.__lastid = 0
        self.__ajaxfirst = doc.request.ajax
        self.ajaxid = None

    def load(self):
        if not self.__doc.request.ajaxmulti:
            return False
        ctx = self.__doc.request.ctx
        lst = ctx['ajax_tree'].split('-')
        del(ctx['ajax_tree'])
        while len(lst):
            marker   = lst.pop(0)
            sysid    = toint(lst.pop(0))
            parentid = toint(lst.pop(0))
            self.__tree[sysid] = (marker, parentid)
        self.__lastid = toint(ctx['ajax_lastid'])
        del(ctx['ajax_lastid'])
        if 'ajax_id' in ctx:
            self.ajaxid = ctx['ajax_id']
            del(ctx['ajax_id'])
        return True

    def add(self, docobj):
        docobj.ajax = self.__ajaxfirst
        self.__ajaxfirst = False

        sysid = self.__getid(docobj)
        if sysid in self.__tree:
            docobj.ajax = True
            self.__delchilds(sysid) 
        else:
            myid = docobj.parent.sysid if isinstance(docobj.parent, DocObj) else 0
            self.__tree[sysid] = (docobj.marker, myid)
        return sysid

    def findmarker(self, dest, docobj):
        if isstr(dest):
            marker = dest
        else:
            if not dest:
                dest = docobj.__class__
            marker = self.__doc.getmarker(dest) or dest
            if not marker:
                raise Exception("Marker: Not found %s" % marker)
        return marker

    def findid(self, marker, docobj):
        def getparent(marker, sysid):
            if sysid == 0:
                return None
            t = self.__tree[sysid] 
            if t[0] == marker:
                return sysid
            else:
                return getparent(marker, t[1])        

        sysid = getparent(marker, docobj.sysid)
        if not sysid:
            for (key, val) in self.__tree.iteritems():
                if val[0] == marker:
                    sysid = key
                    break
        if not sysid:
            return None
            #raise Exception("Marker: ID not found in tree for %s" % marker)

        return sysid

    def __getid(self, docobj):
        if docobj.sysid:
            sysid = docobj.sysid
        else:
            self.__lastid += 1
            sysid = self.__lastid
        return sysid

    def __delchilds(self, sysid, root = True, lst = None):
        if not lst: lst = []
        for key, val in self.__tree.iteritems():
            if val[1] == sysid:
                lst.append(key)
                self.__delchilds(key, False, lst)
        if root:
            for key in lst:
                del(self.__tree[key])

    def __getmodel(self):
        req = self.__doc.request
        if req.ajax and not req.ajaxmulti:
            return ''
        idlist = ["'dom':'dom'"]
        idtree = []
        for (key, val) in self.__tree.iteritems():
            idlist.append("'i%s':'i%s'" % (key, key))
            idtree.append(val[0])
            idtree.append(str(key))
            idtree.append(str(val[1]))
        ftree   = "-".join(idtree)
        fidlist = ",".join(idlist)
        model = const.AJAX_MODEL % (fidlist, self.__doc.request.url, ftree, self.__lastid)
        return model

    def getfunc(self, docobj, params = {}, dest = None, url = None, form = None, fx = None, noparams = []):
        args = {}
        if url:
            args['url']    = url
            args['idcont'] = docobj.sysid
            marker = dest or None
            if not isstr(dest) and dest:
                raise Exception("Marker: waiting for string or None, got %s" % marker)
            myparams = params.copy()
            args['id'] = docobj.sysid
            s = ''
        else:
            url = self.__doc.request.url
            marker = self.findmarker(dest, docobj)
            sysid = self.findid(marker, docobj)
            args['id'] = sysid

            # Setting input params
            myparams = {}

            for key in self.__doc.getclass(marker).outparams:
                if key not in noparams:
                    dicifquote(myparams, key, docobj(key))

            for (key, val) in params.iteritems():
                if key not in noparams:
                    dicifquote(myparams, key, val, True)

        if form:
            args['form'] = form

        myparams['marker'] = marker

        args['params'] = dic2str(myparams, "&amp;", "%s=%s")
        if fx:
            args['fx']  = 1;
        s = dic2str(args, ", ", "'%s': '%s'")
        return const.AJAX_LINK % s

    def addmodel(self, html):
        req = self.__doc.request
        if req.ajax:
            if not req.ajaxmulti:
                return html
            model = AJAX_REPLY % ('dom', self.__getmodel(), 'dom')
            html = model + html
        else:
            pos = html.find("<body>")
            if pos != -1:
                model = AJAX_BLOCK % ('dom', self.__getmodel())
                html = html[:pos] + "<body>\n" + model + html[pos + 6:]
        return html

class Image(RequestObj):
    def prepare(self):
        webheader('Content-Type', 'image/%s' % self.format)

Site()
db = site.db