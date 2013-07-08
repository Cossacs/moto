# coding: utf-8
# --------------------------------------------
# HEADER: Text search module
# --------------------------------------------

from utils import *
import re, const, sql, classes, web

REPLACEWORDS = {
    u'r1': u'yzfr1',
    u'р1': u'yzfr1',
    u'джиксер': u'gsx-r',
    u'кавасаки': u'kawasaki'
}

STOPWORDS = [
    u'а', u'без', u'более', u'бы', u'был', u'была', u'были', u'было', u'быть', u'в', u'вам', u'вас',
    u'весь', u'во', u'вот', u'все', u'всего', u'всех', u'вы', u'где', u'да', u'даже', u'для', u'до',
    u'его', u'ее', u'если', u'есть', u'еще', u'же', u'за', u'здесь', u'и', u'из', u'или', u'им', u'их',
    u'к', u'как', u'ко', u'когда', u'кто', u'ли', u'либо', u'мне', u'может', u'мы', u'на', u'надо',
    u'наш', u'не', u'него', u'нее', u'нет', u'ни', u'них', u'но', u'ну', u'о', u'об', u'однако', u'он',
    u'она', u'они', u'оно', u'от', u'очень', u'по', u'под', u'при', u'с', u'со', u'так', u'также', u'такой',
    u'там', u'те', u'тем', u'то', u'того', u'тоже', u'той', u'только', u'том', u'ты', u'у', u'уже', u'хотя',
    u'чего', u'чей', u'чем', u'что', u'чтобы', u'чье', u'чья', u'эта', u'эти', u'это', u'я']

class ExitLoop(Exception):
    pass

class Stemmer:
    cacheLevel = 1
    cache = {}
    
    vovel = u"аеиоуыэюя"
    perfectiveground = u"((ив|ивши|ившись|ыв|ывши|ывшись)|((?<=[ая])(в|вши|вшись)))$"
    reflexive = u"(с[яь])$"
    adjective = u'(ее|ие|ые|ое|ими|ыми|ей|ий|ый|ой|ем|им|ым|ом|его|ого|ему|ому|их|ых|ую|юю|ая|яя|ою|ею)$';
    participle = u'((ивш|ывш|ующ)|((?<=[ая])(ем|нн|вш|ющ|щ)))$';
    verb = u'((ила|ыла|ена|ейте|уйте|ите|или|ыли|ей|уй|ил|ыл|им|ым|ен|ило|ыло|ено|ят|ует|уют|ит|ыт|ены|ить|ыть|ишь|ую|ю)|((?<=[ая])(ла|на|ете|йте|ли|й|л|ем|н|ло|но|ет|ют|ны|ть|ешь|нно)))$';
    noun = u'(а|ев|ов|ие|ье|е|иями|ями|ами|еи|ии|и|ией|ей|ой|ий|й|иям|ям|ием|ем|ам|ом|о|у|ах|иях|ях|ы|ь|ию|ью|ю|ия|ья|я)$';
    rvre = u'^(.*?[аеиоуыэюя])(.*)$';
    derivational = u'[^аеиоуыэюя][аеиоуыэюя]+[^аеиоуыэюя]+[аеиоуыэюя].*(?<=о)сть?$';
    
    def __init__(self, cache = 1):
        pass
    
    def s(self, pattern, repl,  str):
        return re.sub(pattern, repl, str) == str
    
    def stemWord(self,  word):
        word = word.lower().replace(u'ё', u'е')
        
        if self.cacheLevel and word in self.cache:
            return self.cache[word]
        
        stem = word
        
        try:
            matches = re.match(self.rvre, word)
            if not matches:
                raise ExitLoop()
            
            start,  RV = matches.groups()
            
            if not RV:
                raise ExitLoop()
            
            # Step 1
            if self.s(self.perfectiveground, '', RV):
                RV = re.sub(self.reflexive, '', RV)
                
                if not self.s(self.adjective, '', RV):
                    RV = re.sub(self.adjective, '', RV)
                    RV = re.sub(self.participle, '', RV)
                else:
                    if self.s(self.verb, '', RV):
                        RV = re.sub(self.noun, '', RV)
                    else:
                        RV = re.sub(self.verb, '', RV)
            else:
                RV = re.sub(self.perfectiveground, '', RV)
            
            # Step 2
            RV = re.sub(u'и$', '', RV)
            
            # Step 3
            if re.search(self.derivational, RV):
                RV = re.sub(u'ость?$', '', RV)
            
            # Step 4
            if self.s(u'ь$', '', RV):
                RV = re.sub(u'ейше?', '', RV)
                RV = re.sub(u'нн$', u'н', RV)
            else:
                RV = re.sub(u'ь$', '', RV)
            
            stem = start + RV
        except ExitLoop:
            pass
        
        if self.cacheLevel:
            self.cache[word] = stem
        
        return stem

class ProdSearchRes(object):
    def __init__(self):
        self.text    = ''
        self.count   = 0
        self.filters = {}
        self.product = Storage()

    def fillprod(self, pid, source, psid = None, ppid = None):
        self.product.pid    = pid
        self.product.source = source
        self.product.psid   = psid
        self.product.ppid   = ppid

class ProdSearch(object):
    def __init__(self, site):
        self._props = {}
        self._stemmer = Stemmer()
        self._site = site
        self._db = site.db

    def reload(self):
        self._db.execute(const.SQL_SEARCH)
        q = sql.get_f(['id', 'name', 'fname', 'id_group'], 'prop', 'id < 10000000')
        self._props = self._db.fetchdic(q, 'id')

        re_w = re.compile(u'[a-z0-9]+')
        for (id, data) in self._props.iteritems():
            name = data.name
            if data.fname and data.fname != name:
                name += data.fname
            name = real_translit(name).lower()
            name = u''.join(re_w.findall(name))
            self._props[id] = (name, data.id_group, 0)

    def _getrank(self, cnt, ln, id):
        propname = self._props[id][0]
        k_ln   = 1 - float(ln) / len(propname)
        r_base = cnt * 300
        r_ad = 1900 * ((k_ln + 0.1)**18) + (k_ln + 0.1) * 100
        rank = r_base + r_ad
        return rank

    def _getprops(self, text):
        text = text.lower()
        #log(text.encode('utf-8'))
        wl = words(text)

        matches = {}
        props = self._props.copy()
        cnt = 0
        for w in wl:
            if w in STOPWORDS:
                continue
            if w in REPLACEWORDS:
                w = REPLACEWORDS[w]
            w = self._stemmer.stemWord(w)
            w = real_translit(w)
            matches[w] = []
            found = False
            for (id, (name, gid, cnt)) in props.iteritems():
                if w in name:
                    #log((w, name))
                    found = True
                    name = name.replace(w, '')
                    props[id] = [name, gid, cnt + 1]
                    matches[w].append(id)
            if not found:
                return None

        res = {}
        for (w, idl) in matches.iteritems():
            groups = {}
            for id in idl:
                (name, gid, cnt) = props[id]
                rank = self._getrank(cnt, len(name), id)
                if gid in groups:
                    g = groups[gid]
                    g[0] += rank
                    g[1].append((id, rank))
                else:
                    groups[gid] = [rank, [(id, rank)]]
            for (gid, (grank, idl)) in groups.iteritems():
                idl = sorted(idl, key = lambda x: x[1], reverse = True)[:20]
                idl = map(lambda x: x[0], idl)
                groups[gid][1] = idl
            gdata = []
            for (gid, (grank, idl)) in sorted(groups.iteritems(), key = lambda x: x[1], reverse = True):
                gdata.append((gid, idl))
            res[w] = gdata

        #log(res)
        #log(matches)
        #print props
        return res

    def _getfrow(self, props, view):
        frow = []

        def kd(keydata):
            return map(lambda s: s[0], keydata)

        #log('::::::::VIEW = %s' % view.id)
        for (key, groups) in props.iteritems():
            log
            found = False
            keydata = []
            for (gid, idl) in groups:
                if gid in view.groups:
                    found = True
                    k = (view.groups.index(gid) + 1)
                    field = 'id_prop%d' % k
                    #log((k, view.id_cat, idl))
                    row = sql.fin(field, idl)
                    row = (field, idl)
                    keydata.append(row)
            if not found:
                return None
            newkd = True
            #list1 = kd(keydata)
            #for keydata0 in frow:
            #    if list_compare(list1, kd(keydata0)):
            #        newkd = False
            #        for i in xrange(len(keydata)):
            #            pass
                        #list_update(keydata[i][1], keydata0[i][1])
            #        break

            if newkd:
                frow.append(keydata)
            #log('----------- KEYDATA FOR %s -------------' % key)
            #log(keydata)
            #log('----------- END KEYDATA ----------------------')
        f = map(lambda x: sql.f_or(map(lambda y: sql.fin(y[0], y[1]), x)), frow)
        f.append('pview = "%s"' % view.pview)
        f.append('id_prop1 = %d' % view.id_cat)
        return f

    def __getdata(self, doc, text):
        if not text:
            return None
        props = self._getprops(text)
        if not props:
            return None

        q = sql.get_f(['pv.*'], 'pview pv, cat c', 'pv.id_cat = c.id')

        data = {}
        for row in self._db.fetchobj(q):
            view = classes.View(doc, row)
            frow = self._getfrow(props, view)
            if not frow:
                continue

            #else:
            #    frow.append('id_prop1 = "%s"' % view.id_cat)
            view.k = doc.getk([view.id_cat], 'id') + [None] * 7
            view.parsemap(view.k)
            frow += map(lambda s: "id_prop%d = %d" % s, view.ppair.iteritems())

            view.frow = frow
            view.q    = sql.get_f(['COUNT(DISTINCT id_product)'], const.MEM_SEARCH, frow)
            view.qpid = sql.get_f(['DISTINCT id_product'], const.MEM_SEARCH, frow)

            skip = False
            for (id, aview) in data.iteritems():
                if (aview.id_cat == view.id_cat) and (aview.groups == view.groups):
                    if view.num < aview.num:
                        del data[aview.id]
                    else:
                        skip = True

            if not skip:
                data[view.id] = view

        return data

    def trim(self, text):
        text = unicode(text)
        text = text.strip().lower()
        text = re.sub('\s+', ' ', text)
        return text

    def SearchText(self, res, doc):
        data = self.__getdata(doc, res.text)
        found = False
        if data:
            for (id, view) in data.iteritems():
                view.count = self._db.fetchval(view.q)
                if view.count:
                    found = True
                    res.count += view.count
                    res.filters[id] = view
            if res.count == 1:
                view = res.filters.values()[0]
                pid = self._db.fetchval(view.qpid)
                res.fillprod(pid, 'N')
        return found

    def SearchProducts(self, res, doc):
        keys = []
        for key in re.split(r'[,;\s]+', res.text):
            if key:
                keys.append(real_translit(key))
        qlist = []
        params = []
        db = self._db
        for field in ('id', 'partno1', 'partno2'):
            qlist.append(sql.get_f('id', 'product', sql.fin(field, keys, True)))
            params += keys
        idl = db.fetchvals(sql.union(qlist), params)
        if not idl:
            return False
        res.count = len(idl)

        f = ['ps.id_product = p.id', 'pv.id_cat = ps.id_prop1']
        q = sql.get_f('pv.id', ['pview pv', 'prop_set ps'], f)
        q = sql.order(q, 'pv.num')
        q = sql.limit(q, 0, 1)
        q = sql.get_f(['id', '(%s) AS id_view' % q], 'product p', sql.fin('id', idl))
        for (idp, id) in db.fetchall(q):
            if id in res.filters:
                view = res.filters[id]
            else:
                view = classes.View(doc, id)
                view.k = doc.getk([view.id_cat], 'id') + [None] * 7
                view.parsemap(view.k)
                view.products = []
                res.filters[id] = view
            view.products.append(idp)
        for view in res.filters.itervalues():
            view.frow = [sql.fin('id_product', view.products)]
            view.count = len(view.products)

    def SearchProduct(self, res, doc):
        db = self._db
        val = res.text.replace(' ', '').upper()
        val = real_translit(val)

        def getpid(field, value):
            q = sql.get_fval('id', 'product', field)
            return db.fetchval(q, [value])

        pid = None

        if isint(val, False):
            pid = pid or getpid('id', toint(val))
        pid = pid or getpid('partno1', val)
        pid = pid or getpid('partno2', val)
        if pid:
            res.fillprod(pid, 'N')
            return True

        def getfid(field, value):
            t = 'fiche_price pc, fiche_prop_set ps'
            f = ['pc.id_product = ps.id_product']
            f.append('ps.id_prop2 = %s')
            f.append('pc.%s = ' % field + '%s')
            q = sql.get_f('pc.id_product, ps.id, pc.id', t, f)
            return db.fetchrow(q, [idbb, value])

        q = sql.get_fval('id', 'prop', 'translit')
        idbb = db.fetchval(q, 'bikebandit')
        if isint(val, False):
            pid = pid or getfid('id', toint(val))
        pid = pid or getfid('partno1', val)
        pid = pid or getfid('partno2', val)
        if pid:
            res.fillprod(pid[0], 'F', pid[1], pid[2])
            return True
        return False

    def __call__(self, doc, text):
        text = unicode(text)
        res = ProdSearchRes()
        res.text = self.trim(text)

        flag = self.SearchProduct(res, doc)
        flag = flag or self.SearchProducts(res, doc)
        flag = flag or self.SearchText(res, doc)
        return res