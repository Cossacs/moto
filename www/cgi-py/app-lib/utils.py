# coding: utf-8
# --------------------------------------------
# HEADER: Utils Module
# --------------------------------------------

import os, web, time, re, zlib, hashlib, urllib, string, PIL.Image, datetime
import config, const, sql
from cStringIO import StringIO
import threading

LOG_FORMAT_TIME = '%H:%M:%S'
LOG_FORMAT      = '%(time)s %(mclass)08s | %(message)s'
LOG_LINE_WIDTH  = 105

M_ERR  = 'ERROR'
M_WARN = 'WARNING'
M_INFO = 'INFO'

# Reloadint source code modules
def recompile(lpath):
    if not config.RELOAD:
        return
    import debugmonitor
    web.config.debug = True
    debugmonitor.start(interval = 1.0)
    if os.path.exists(lpath):
        for f in os.listdir(lpath):
            f = os.path.join(lpath, f)
            if os.path.splitext(f)[1] == '.py':
                debugmonitor.track(f)

class Log(object):
    def __getmessages(self): return self.__messages
    def __getquiet(self): return self.__quiet
    def __setquiet(self, value): self.__quiet = value
    messages = property(__getmessages)
    quiet    = property(__getquiet, __setquiet)    
    
    def clear(self):
        self.__messages = []
        
    def save(self, path): 
        file = open(path, 'a+w')
        file.writelines(map(lambda s: s + '\n', self.__messages))
    
    def __init__(self):
        self.clear()
        self.__quiet = config.isremote
        self.__state = False
        self.t_started = False
        
    def __call__(self, message = '', mclass = M_INFO, bl = True, fl = False):
        message = str(message).replace('\\n', '\n')
        messages = message.split('\n')
        if len(messages) > 1:
            for line in messages:
                self(line, mclass, bl, fl)
            return
        if bl and (len(message) > LOG_LINE_WIDTH - 2):
            spos = message.rfind(' ', 0, LOG_LINE_WIDTH - 2)
            if spos < 0:
               spos = LOG_LINE_WIDTH - 2
            if spos != -1:
                self(message[:spos], mclass, bl, fl)
                self('> ' + message[spos + 1:], mclass, bl, False)
                return
        
        stime = time.strftime(LOG_FORMAT_TIME)
        sline = LOG_FORMAT % {'time'   : stime,
                              'mclass' : mclass,
                              'message': message}
        if not fl and (len(self.__messages) == 0):
            self.__messages.append('')
            __sline = time.strftime('============== | %d.%m.%Y | =============')
            self(__sline, M_INFO, False, True)
        self.__messages.append(sline)

        sline = '[%s] %s' % (threading.current_thread().ident, sline)

        if fl:
            log = open(config.LOG, 'w')
        else:
            log = open(config.LOG, 'a')
        print >> log, sline
        log.close()
        if not self.__quiet:
            print sline

    def t_start(self):
        if not config.DEBUG:
            return
        self.t_started = True
        time.clock()
        self.time_now = time.clock()
        self.time_delta = 0.0
        self.t_trace('START')

    def t_trace(self, s):
        if not config.DEBUG or not self.t_started:
            return
        #if web.ctx.path[:8] != '/catalog': return
        delta = time.clock() - self.time_now
        delta2 = delta - self.time_delta
        self.time_delta = delta
        self("%02.03f / %02.03f | %s" % (delta * 1000, delta2 * 1000, s))

class Storage(web.storage):
    def attr(self, name):
        return None

    def __getattr__(self, name):
        if name in self:
            return web.storage.__getattr__(self, name)
        else:
            value = self.attr(name)
            self[name] = value
            return value

def rtrimlist(lst):
    for i in xrange(len(lst) -1, -1, -1):
        if not(lst[-1]):
            del lst[-1]

def notemptylist(lst):
    res = []
    for item in lst:
        if item:
            res.append(item)
    return res


def geturl(doc, params, page = 1, img = None, ext = const.DEFAULT_EXT, query = None,
           alwaysext = False, safequery = True, view = None, addmod = True, addview = True):
    if not params: 
        params = []
    else:
        params = notemptylist(params)

    folders = config.URL_FOLDERS
    view = view or (doc and doc.view)
    if addview and view and params:
        if not view.isdefault:
            params.insert(1, view.translit)
            folders += 1

    pref = []
    suff = params[folders:]
    if doc and doc.request.module not in const.DEFAULT_MODS and addmod:
        pref.append(doc.request.module)

    pref += params[:folders]

    myext = None
    if (len(params) >= folders) or alwaysext:
        if ext:
            myext = ext
        else:
            ext = doc.ext

    if page and (page != 1):
        suff.append('page' + str(page))

    if img:
        if isint(img):
            img = 'img' + str(img)
        suff.append(img)

    res = '/' + '/'.join(pref)

    if suff:
        res += '_' + '_'.join(suff)

    if myext:
        res += '.' + myext

    res = res.lower()
 
    if query:
        dmt = "&"
        if safequery:
            dmt = "&amp;";
        s = dic2str(query, dmt, "%s=%s")
        if s:
            res += '?' + s

    return res

def formatparams(delim, **kwargs):
    res = delim.join(map(lambda s: '%s=%s' % s, kwargs.iteritems()))
    return res

def isint(val, strict = True):
    if strict:
        return re.match('^\-?[1-9]\d*$', str(val))
    else:
        return re.match('^\d+$', str(val))

def isnum(val):
    return re.match('^\-?\d+(\.\d+)?$', str(val))

def islist(val):
    return type(val).__name__ == "list"

def isstr(val):
    return type(val).__name__ == "str"

def isfloat(val):
    return type(val).__name__ == "float"

def toint(val):
    if re.match('^\d+$', unicode(val)):
        return int(val)
    else:
        return val

def vallist(nlist, func = None):
    my = []
    for x in nlist:
        if x: 
            if func: x = func(x)           
            my.append(x)
    return my

def firstworld(text):
    if text == None:
        return None
    mo = re.match('\S+', text.lstrip())
    if mo:
        return mo.group(0)
    else:
        return text

def getcurdef(config, curdef = None):
    if curdef:
       return 'CURR_%s' % curdef
    else:
       return 'CURR_%s' % config('CURRENCY')

def getprice(config, price, currency, curdef = None):
    curdef = getcurdef(config, curdef)
    rate = config('CURR_%s' % currency)
    ratedef = config(curdef)
    rate = float(rate) / float(ratedef)
    return float(price) * rate

def formatprice(config, price, currency, curdef = None, fmt = '%.2f', rnd = False):
    price = getprice(config, price, currency, curdef)
    return (formatnumber(fmt % price), config(getcurdef(config, curdef), 2))

def formatname(names, func = None):
    return ' '.join(vallist(names, func))

def formatnumber(s, lead =  1, tSep = ' ', dSep = '.'):
    if isfloat(s):
        s = ('%0' + str(lead) + '.2f') % s
    elif isint(s):
        s = ('%0' + str(lead) + 'd') % int(s)

    if s == None: 
        return 0 
    if not isinstance(s, str): 
        s = str(s) 
 
    cnt = 0 
    numChars = dSep + '0123456789' 
    ls = len(s) 
    while cnt < ls and s[cnt] not in numChars: cnt += 1 
 
    lhs = s[0:cnt] 
    s = s[cnt:] 
    if dSep == '': 
        cnt = -1 
    else: 
        cnt = s.rfind(dSep) 
    if cnt > 0: 
        rhs = dSep + s[cnt + 1:] 
        s = s[:cnt] 
    else: 
        rhs = '' 
 
    splt = '' 
    while s != '': 
        splt = s[-3:] + tSep + splt 
        s = s[:-3] 
 
    return lhs + splt[:-1] + rhs 

def bestname(name, namefull):
    if namefull:
        return namefull
    else:
        return name

def img_typ2ext(atyp):
    if not atyp:
        return None
    atyp = atyp.upper()
    for (typ, ext) in const.IMAGE_TYPES:
        if typ == atyp:
            return ext
    return None

def img_ext2typ(aext):
    if not aext:
        return None
    aext = aext.lower()
    for (typ, ext) in const.IMAGE_TYPES:
        if ext == aext:
            return typ
    return None

def getcrc(param):
    m = hashlib.md5()
    m.update(param)
    return m.digest()

def getcrc32(params):
    s = ''.join(map(str, params))
    return zlib.crc32(s) & 0xffffffff

def img_addcrc(db, param, id):
    crc = getcrc(param)

    q = sql.get_fval('crc', 'mem_image_crc', 'crc')
    if not db.fetchval(q, [crc]):
        q = sql.insert(['crc', 'id_image'], 'mem_image_crc')
        db.execute(q, [crc, id])

def img_addcrclist(db, alist):
    if not alist:
        return
    lst = {}
    for (param, id) in alist:
        lst[getcrc(param)] = id

    crclist = lst.keys()
    q = sql.get_f('crc', 'mem_image_crc', sql.fin('crc', crclist, True))
    crclist = db.fetchvals(q, crclist)
    for crc in crclist:
        if crc in lst:
            del lst[crc]
    q = sql.insert(['crc', 'id_image'], 'mem_image_crc')
    for (crc, id) in lst.iteritems():
        db.execute(q, [crc, id])

def quote(text):
    return "<pre>" + web.net.htmlquote(str(text)) + "</pre>"

def adduniq(lst, elem):
    for val in lst:
        if val == elem: return
    lst.append(elem)

def urlquote(val):
    return urllib.quote(val.encode('utf-8'))

def dic2str(dic, delim, fmt):
    lst = []
    for (key, val) in dic.iteritems():
        if val != '' and val != None:
            lst.append(fmt % (key, val))
    return delim.join(lst)

def dicifquote(dic, key, val, force = False):
    if val or force:
        if val == True:
            val = '1'
        if not val:
            val = '0'
        val = unicode(val)
        dic[key] = urlquote(val)

# Внутренняя функция, полноценный транслит
# Таблица идентична используемой в PHP админке
def real_translit(s):
    res = ''
    for sym in s:
        if sym in const.SYS_TRANSTABLE:
            res += const.SYS_TRANSTABLE[sym]
        else:
            res += sym
    #    sym = const.TRANSTABLE.get(sym, sym)
    #for (key, val) in const.TRANSTABLE.iteritems():
        #pass
        #k = s.replace(key, val)
    #    k = 1
    return res

# Функция возвращает отформатированную строку, готовую для записи
# в поле translit
def translit(s):
    s = real_translit(s).lower()
    return '-'.join(re.findall('[a-z0-9]+', s))

def getnewid(db, tabname = ''):
    return db.fetchval("SELECT getnewid('%s')" % tabname)

def readurl(url):
    f = urllib.urlopen(url)
    res = f.read()
    return res

def words(text, expr = u'[a-zа-я0-9]{2,}'):
    res = []
    while True:
        mo = re.search(expr, text)        
        if mo:
            text = text[mo.end():]
            w = mo.group(0).lower()
            res.append(w)
        else:
            break

    return res

def isword(word):
    if re.search(u'[a-zа-я]{2,}', word.lower()):
        return True
    else:
        return False

def list_compare(list1, list2):
    list1 = sorted(list1)
    list2 = sorted(list2)
    return list1 == list2

def list_update(src, dst):
    for x in src:
        if not x in dst:
            dst.append(x)

def gettable(source, typ, alias = True):
    if source == 'F':
        prefix = 'fiche_'
    else:
        prefix = ''

    res = None
    #if   typ == 'propset': return const.MEM_SEARCH + ' ps'
    if   typ == 'propset': res = 'prop_set' + (' ps'  if alias else '')
    elif typ == 'product': res = 'product'  + (' p'   if alias else '')
    elif typ == 'image'  : res = 'image'    + (' img' if alias else '')
    elif typ == 'price'  : res = 'price'    + (' prc' if alias else '')

    if res:
        return prefix + res
    else:
        return None

def img_resizebox(data, size):
    try:
        img = PIL.Image.open(StringIO(data))
        (sx, sy) = img.size
        if max(sx, sy) < size:
            return (data, sx, sy)
        if sx > sy:
            sy = size * sy / sx
            sx = size
        else:
            sx = size * sx / sy
            sy = size
        img = img.convert('RGB')
        img = img.resize((sx, sy), PIL.Image.ANTIALIAS)
        buf = StringIO()
        img.save(buf, "JPEG", quality = 98, optimize = True)
        #img.save(buf, "PNG")
        res = (buf.getvalue(), sx, sy)
        return res
    except Exception, e:
        return None

def parse_price(text):
    if not text:
        return None

    text = real_translit(unicode(text)).lower();
    text = text.replace(' ', '')
    mo = re.search(r'^(\d+)[\.,]?(\d+)?(.*)', text)
    if mo:
        cur = 'UAH'
        val = mo.group(1)
        if mo.group(2):
            val += "." + mo.group(2)[:2]
        val = float(val)

        if re.search(r'grn|uah|hrn|griv', mo.group(3)):
            cur = 'UAH'
        elif re.search(r'e', mo.group(3)):
            cur = 'EUR' 
        elif re.search(r'usd|dol|baks|zel|\$', mo.group(3)):
            cur = 'USD'
        if val and cur:
            return (val, cur)
    return None

def parse_price_def(config, text):
    if not text:
        return None
    res = parse_price(unicode(text))
    if not res:
        return None
    (price, currency) = res
    price = getprice(config, price, currency)
    return int(price)

def webheader(key, val):
    if 'headers' in web.ctx:
        web.header(key, val)

def split_para(text):
    text = text.strip()
    res = []
    r = re.compile(u'<p>[\s\S]*?</p>', re.M)
    while True:
        mo = r.search(text)
        if mo:
            if mo.start() > 1:
                res.append(text[:mo.start()])
            res.append(mo.group(0))
            text = text[mo.end():]
        else:
            break
    if text:
        res.append(text)
    return res

def newmarker(addate):
    now = datetime.datetime.now() - datetime.timedelta(hours = config.NEWS_LIFETIME)
    return addate > now

def writefile(filename, data, mode = "wb"):
    f = open(filename, mode)
    f.write(data)
    f.close()

def isfiche(source)  : return source == 'F'
def isproduct(source): return source == 'N'
def isprice(source)  : return source == 'P'

log = Log()