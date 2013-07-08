# coding: utf-8
# --------------------------------------------
# HEADER: Interfaces for Site Application
# --------------------------------------------

from kernel import *
from utils import *
from const import *
from abc   import ABCMeta, abstractmethod, abstractproperty
import web, os, re, time
import config, sql, classes, random

import random

class DOArticles(DocObj):
    template = 'articles'

    def prepare(self, doc):
        q = sql.get_f('*', 'prop p, sysid s', ['p.id = s.id', 'p.id_group = %s'])
        articles = {}
        gid = db.pgbytr("articles")
        for row in db.fetchobj(q, [gid]):
            (section, name) = row.name.split('/', 2)
            row = classes.Prop(doc, row)
            row.name = name
            row.url  = doc.geturl([row.translit], alwaysext = True)
            row.new  = newmarker(row.addate)
            if section in articles:
                articles[section].append(row)
            else:
                articles[section] = [row]
        for lst in articles.itervalues():
            lst.sort(key = lambda x: x.addate, reverse = True)
        self.add(articles = articles)

class DOArticle(DocObj):
    template = 'article'

    def prepare(self, doc):
        doc.article.evalnote(self.ctx)

class DOProp(DocObj):
    template = 'prop'

    def prepare(self, doc):
        doc.prop.evalnote(self.ctx)

class DOLibOrder(DocObj):
    template = 'lib/order'
    inparams = []

    def prepare(self, doc):
        doc.title = 'Order'

class DOLibSearch(DocObj):
    template = 'lib/search'
    inparams = ['query', 'hl']

class DOLibNews(DocObj):
    template = 'lib/news'

    def prepare(self, doc):
        gid = db.pgbytr("news")
        t = ['prop p', 'sysid s']
        f = ['p.id = s.id', 'p.id_group = %s']
        q = sql.get_f('p.*, s.*', t, f)
        q = sql.order(q, 's.addate DESC')
        news = []
        for row in db.fetchobj(q, [gid]):
            row = classes.Prop(doc, row)
            row.new = newmarker(row.addate)
            news.append(row)
        self.add(news = news)

class DOLibIChain(DocObj):
    template = 'lib/ichain'
    inparams = ['mnf', 'mgroup', 'model', 'myear']

    def prepare(self, doc):
        fblock = Storage()
        filters = []
        ft = []
        fp = []
        params = {}
        filters = []
        URL = '/lib/ichain.html'
        for key in ['mnf', 'mgroup', 'model', 'myear']:
            val = self(key)
            if val:
                ft.append(key + '=%s')
                fp.append(val)
                params[key] = val
                f = Storage()
                f.url = URL
                f.key = key
                f.val = val
                f.params = "&amp;".join(map(lambda x: x[0] % urlquote(x[1]), zip(ft, fp[:-1])))
                filters.append(f)
            else:
                q = sql.get_f('DISTINCT ' + key, 'dc_chain', ft)
                q = sql.order(q, key)
                fblock.data = []
                for val in db.fetchvals(q, fp):
                    if not val:
                        continue
                    row = Storage()
                    row.name = val
                    purl = params.copy()
                    purl[key] = val
                    row.url = URL
                    row.params = dic2str(purl, "&amp;", "%s=%s")
                    fblock.data.append(row)
                fblock.key = key
                break
        if self('mgroup'):
            q = sql.get_f(['model', 'myear', 'chain', 'links'], 'dc_chain', ft)
            q = sql.order(q, 'model, myear')
            chains = db.fetchobj(q, fp)
            self.add(chains = chains)
        self.add(fblock = fblock, filters = filters, params = params)

# DOC OBJ: Blank
class DOBlank(DocObj):
    template = 'blank'

    def prepare(self, doc):
        arrow = None
        if isinstance(doc, DocStatic):
            arrow = "s-" + "-".join(doc.request.params)
        if isinstance(doc, DocLib):
            arrow = "s-" + doc.lib
        if isinstance(doc, DocArticle):
            arrow = "s-articles"
        elif isinstance(doc, DocCatalog):
            arrow = doc.cat.translit

        self.add(arrow = arrow)
        self.add(prodcount = formatnumber(site.config('PRODUCTS')))
        self.add(fichecount = formatnumber(site.config('PRODUCTS', 2)))

        q = sql.get_f("p.*", ['cat c', 'prop p'], ['c.id = p.id', 'c.visible = 1'])
        catlist = sorted(db.fetchobj(q), key = lambda x: x.name)
        for cat in catlist:
            cat.url = doc.geturl([cat.translit], addmod = False, addview = False)
        self.addshared(catlist = catlist)

    @classmethod
    def markers(cls, doc):
        doc.addmarker(DOLibSearch, 'search')
        doc.addmarker(DOMenu, 'menu')
        doc.addmarker(DOMain, 'body')

class DOMenu(DocObj):
    template = 'menu'
    inparams = ['static']

    def prepare(self, doc):
        if self('static'):
            pid = site.config('STATIC_PRODUCT')
        else:
            idl = site.config('RANDOM_PRODUCTS')
            idl = idl.split(",")
            idx = random.randint(0, len(idl) - 1)
            pid = idl[idx]
        pid = toint(pid)
        product = classes.Product(doc, pid)
        self.add(product = product)

        gid = db.pgbytr("news")
        t = ['prop p', 'sysid s']
        f = ['p.id = s.id', 'p.id_group = %s']
        q = sql.get_f('p.*, s.*', t, f)
        q = sql.order(q, 's.addate DESC')
        q = sql.limit(q, 0, 3)
        news = []
        for row in db.fetchobj(q, [gid]):
            row = classes.Prop(doc, row)
            row.new = newmarker(row.addate)
            news.append(row)
        self.add(news = news)

        gid = db.pgbytr("articles")
        t = ['prop p', 'sysid s']
        f = ['p.id = s.id', 'p.id_group = %s']
        q = sql.get_f('p.*, s.*', t, f)
        q = sql.order(q, 's.addate DESC')
        q = sql.limit(q, 0, 3)
        articles = []
        for row in db.fetchobj(q, [gid]):
            row = classes.Prop(doc, row)
            row.new = newmarker(row.addate)
            row.url = doc.geturl([MOD_ARTICLE, row.translit], alwaysext = True)
            articles.append(row)
        self.add(articles = articles)

class DOMain(DocObj):
    template = 'main'

    def prepare(self, doc):
        gid = db.pgbytr("advert")
        t = ['prop p', 'sysid s']
        f = ['p.id = s.id', 'p.id_group = %s']
        q = sql.get_f('p.*, s.*', t, f)
        q = sql.order(q, 's.addate DESC')
        q = sql.limit(q, 0, 1)
        adverts = []
        for row in db.fetchobj(q, [gid]):
            row = classes.Prop(doc, row)
            adverts.append(row)
        self.add(adverts = adverts)

# DOC OBJ: Static
class DOStatic(DocObj):
    template = 'static'

    def prepare(self, doc):
        self.add(page = doc.page)

# DOC OBJ: Catalog Filter
class DOCatFilter(DocObj):
    template = 'catfilter'
    inparams = ['chain', 'searchmap', 'frontdata']

    def getcolumns(self, avgwidth, cnt, b):
        kwidth = [1.0, 1.0, 1.3, 1.5, 1.7]
        columns = 1
        if avgwidth:
            columns = b.width / avgwidth
        if columns <= len(kwidth):
            columns = int(round(columns / kwidth[columns - 1]))
        columns = min(cnt / 3, columns)
        columns = min(columns, 3)
        columns = max(columns, 1)

        return columns

    def getfblocks(self, doc):
        # Creating filter blocks
        blocks = doc.view.blocks
        Q_IDPRP = 'ps.id_prop%d'

        fblocks = []
        i = 0
        for b in blocks:
            log.t_trace("Cat Filter.beforeblock")
            if b.show:

                t = doc.tpropset
                f = map(lambda x: (Q_IDPRP + ' = %d') % x, b.filter.iteritems())
                f.append("ps.pview = '%s'" % doc.view.pview)
                f.append(Q_IDPRP % b.propno + ' IS NOT NULL')
                f += doc.view.adfilter.sql(True)

                q = sql.get_f([Q_IDPRP % b.propno], t, f)
                f = ['ps.pview'] + map(lambda x: Q_IDPRP % x, b._group + [b.propno])
                q = sql.group(q, f)
                idl = db.fetchvals(q)
                proplist = []
                if idl:
                    f = ["id IN (%s)" % (", ".join(map(str, idl)))]
                    q = sql.get_f(['name', 'fname', 'translit', 'id_image'], 'prop', f)
                    q = sql.order(q, 'name')
                    proplist = db.fetchobj(q)

                b.hidden = b.hidden or not len(proplist)

                block = Storage()
                block.group = b.group
                block.active = False
                bd = []
                block.data = bd

                url = doc.geturl(b.params)

                bd.append(Storage(dict(url = url, name = LEX_ALL, st = 'ACT')))
                log.t_trace("Cat Filter.beforequery")
                avgwidth = 0
                for prop in proplist:
                    params = b.params[:]
                    params[i] = prop.translit

                    prop.url = doc.geturl(params)

                    if b.k and b.k.translit == prop.translit:
                        prop.st = 'ACT'
                        bd[0]['st'] = 'GEN'
                        block.active = True
                    else:
                        prop.st = 'GEN'

                    width = min(len(prop.name), 30) * 6

                    prop.image = doc.getimage(prop.id_image, prop, [prop.translit])
                    #if prop.image:
                    #    width = prop.image.width
                    avgwidth += width
                    bd.append(prop)

                if avgwidth:
                    avgwidth /= len(proplist)                

                log.t_trace("Cat Filter.afterequery")

                block.columns = self.getcolumns(avgwidth, len(bd), b)
                block.b = b                
                fblocks.append(block)
            i += 1 
            log.t_trace("Cat Filter.afterblock")
        return fblocks
    
    def prepare(self, doc):
        for view in doc.views:
            view.url = doc.geturl([doc.cat.translit], view = view)

        fblocks = self.getfblocks(doc)
        self.addshared(fblocks = fblocks)

        if self('frontdata'):
            rows = []
            if fblocks:
                for row in fblocks[0]['data']:
                    if row.name != LEX_ALL:
                        rows.append(row)

            i = 6
            rows2 = []
            while (i > 0) and len(rows):
                idx = random.randint(0, len(rows) - 1)
                rows2.append(rows[idx])
                del rows[idx]
                i -= 1
            rows.sort(key = lambda x: x.name)
            site.gvar.frontpage[doc.cat.translit] = rows2

        gchain = []
        i = 0
        for b in doc.view.blocks:
            if not b.show:
                url = {}
                url['url'] = doc.geturl(doc.request.params[:i])
                url['name_group'] = b.k.name_group
                url['name'] = b.k.name
                gchain.append(url)
            i += 1
            if b.k and b.k.id_group == site.gvar.params.mnf_gid:
                mnf = b.k
                mnf.url = doc.geturl(doc.request.params[:i])
                self.addshared(mnf = mnf)
        self.add(gchain = gchain)


# DOC OBJ: Abstract Catalog Products
class DOAbsCatProducts(DocObj):
    __metaclass__ = ABCMeta
    inparams  = ['show_all', 'sort', 'hl', 'list', 'maxq']
    outparams = ['show_all']
    lparams   = ['products']
    # For override!
    template = None

    def __getpages(self):
        return max((self.prodcount - 1) / self.ppg + 1, 1)

    def __getpage(self):
        return min(self.doc.request.page, self.pages)

    pages = property(__getpages) 
    page  = property(__getpage)

    @abstractmethod
    def prodlist(self, doc, qsort):
        pass

    def __init__(self, parent, marker, doc):
        self.prodcount = 0
        DocObj.__init__(self, parent, marker, doc)

    def getparams(self):
        return False

    def showproducts(self):
        return self.doc.view.show_products

    def prepare(self, doc):
        self.ppair = {}
        if doc.view:
            self.ppair = doc.view.ppair

        show_products = self.showproducts()

        self.add(show_store = doc('show_store'))
        self.add(price_min  = doc('price_min'))
        self.add(price_max  = doc('price_max'))
        self.add(list_view  = doc('list_view'))

        self.add(show_products = show_products)
        if not show_products:
            return

        # Количество товаров на страницу
        if self('show_all'):
            self.ppg = site.config('PROD_PER_PAGE', 2)
        elif doc("list_view") == "store":
            self.ppg = site.config('PROD_PER_PAGE', 3)
        else:
            self.ppg = site.config('PROD_PER_PAGE')

        if self('maxq') and isint(self('maxq')):
            self.ppg = min(self.ppg, self('maxq'))

        # SQL Фильтр товаров общий
   
        # SQL Сортировка товаров
        key = self('sort')
        if key == 'priceup':
            qsort = [('price', 'ASC')]
            usort = 'name'
        elif key == 'pricedown':
            qsort = [('price', 'DESC')]
            usort = 'priceup'
        else:
            qsort = [('name', 'ASC')]
            usort = 'pricedown'

        self.save('products', sort = key)
        self.add(sort = key, sort_url = self.ajaxhref({'sort': usort}))

        # Отображение списка товаров
        list_view = doc('list_view') or 'products'
        self.add(list_view = list_view)

        # Фильтр товаров
        self.add(store_url = self.ajaxhref({'show_store': 0 if doc('show_store') else 1}))
        self.add(price_url = self.ajaxfunc(form = 'price' + self.id))
        self.add(price_off = self.ajaxhref({'price_min': '', 'price_max': ''}))

        # Получение списка товаров
        prodlist = self.prodlist(doc, qsort)
        self.add(prodlist = prodlist, prodcount = formatnumber(self.prodcount))

        if self.prodcount:
            # Формирование линейки прокрутки страниц
            ps = (self.page - 1) * self.ppg + 1
            pe = min(ps + self.ppg - 1, self.prodcount)
            self.add(prodstart = formatnumber(ps), prodend = formatnumber(pe))
            pbar = self.__prodbar()
            self.add(pbar = pbar)
        else:
            if doc('show_store'):
                self.add(hide_store = self.ajaxhref({'show_store': False}))

    def __prodbar(self):
        doc   = self.doc
        page  = self.page
        pages = self.pages

        if pages == 1:
            return None
        LN = 5

        prev = max(page - 1, 1)
        next = min(page + 1, pages)

        if page == prev:
            prev = None

        if page == next:
            next = None

        beg = page - (LN / 2)
        end = beg + LN - 1

        if beg < 1:
            beg = 1
            end = LN

        if end > pages:
            end = pages
            beg = max(1, end - LN + 1)

        bbeg = max(beg + (end - beg) / 2 - LN, 1)
        bend = min(beg + (end - beg) / 2 + LN, pages)

        if beg == 1:
            bbeg = None

        if end == pages:
            bend = None

        def mu(page):
            if not page:
                return None

            return doc.geturl(doc.request.params, page, query = dict(
                    query = self('query'),
                    show_all = self('show_all'))) 

        return dict(bbeg = mu(bbeg), bend = mu(bend), 
                    prev = mu(prev), next = mu(next),
                    list = map(lambda i: (mu(i), i, i == page), xrange(beg, end + 1)),
                    all  = self.ajaxhref({'show_all' : True}))

    def ajaxdeps(self, ctx):
        ctx[DOCatFilter] = {}

# DOC OBJ: Catalog Products
class DOCatProducts(DOAbsCatProducts):
    template = 'catproducts'

    def __proddata(self, db, view, pids):
        doc = self.doc
        view = doc.view0
        fields = ['p.id', 'p.partno1']
        tables = [doc.tpropset]

        k = len(view.groups) + 1
        for i in xrange(1, k):
            tables.append('LEFT JOIN prop p%d ON ps.id_prop%d = p%d.id' % (i, i, i))
            fields.append('MAX(p%d.translit) AS t%d' % (i, i))

        tables = ["\n  ".join(tables)]

        fields += ['p.name, p.note, p.price, p.price_in, p.price_out, p.currency, p.eta']
        fields += ['img.id AS id_img']
        tables.append(doc.tproduct + ' LEFT JOIN ' + doc.timage + ' ON p.id_image = img.id')
        fq = sql.get_f(['ids.id_image'], 'image_deps ids', 'ids.id_obj = p.id')
        fq = sql.order(fq, 'ids.id')
        fq = sql.limit(fq, 0, 1)
        fq = '(%s) AS id_img_big' % fq
        fields.append(fq)

        fstore = sql.get_f('SUM(s.quantity)', 'store s', ['s.id_product = p.id', 's.quantity > 0'])
        fstore = '(%s) AS stored' % fstore
        fields += [fstore]

        f = [sql.fin('p.id', pids)]
        f.append("p.id = ps.id_product")
        f.append("ps.pview = '%s'" % view.pview)
        q = sql.get_f(fields, tables, f)
        q = sql.group(q, 'p.id')
        pl = {}
        iml = []
        for (key, row) in db.fetchdic(q).iteritems():
            param = []
            for prop in xrange(1, k):
                param.append(row['t' + str(prop)])
            row.param = param
            row.smallprice = doc('list_view') == "store"

            p = classes.Product(doc, row)
            p.hints = []
            p.rates = []
            p.view  = view
            pl[key] = p

            iml.append(p.id_img)
            iml.append(p.id_img_big)

        iml = notemptylist(iml)
        if iml:
            f = sql.fin('id', iml)
            q = sql.get_f(['id', 'name', 'type', 'width', 'height', 'size'], 'image', f)
            images = db.fetchdic(q)
        else:
            images = {}
        crclist = []

        for p in pl.itervalues():
            p.img = doc.getimage(images.get(p.id_img, None), p, p.param, crclist = crclist)
            p.img_big = doc.getimage(images.get(p.id_img_big, None), p, p.param, 1, crclist = crclist)

        img_addcrclist(db, crclist)

        return pl

    def __prodhint(self, db, view, pl):
        doc = self.doc
        fields = ['p.id']
        tables = [doc.tpropset]

        k = len(view.groups) + 1
        for i in xrange(1, k):
            tables.append('LEFT JOIN prop p%d ON ps.id_prop%d = p%d.id' % (i, i, i))
            fields.append('p%d.name AS n%d' % (i, i))
            fields.append('p%d.translit AS t%d' % (i, i))

        tables = ["\n  ".join(tables)]
        tables.append(doc.tproduct)

        f = [sql.fin('p.id', pl.keys())]
        f.append("p.id = ps.id_product")
        f.append("ps.pview = '%s'" % view.pview)
        f += doc.sqlppair(self.ppair)
        if doc('adfilter'):
            f += doc('adfilter')
        q = sql.get_f(fields, tables, f)
        kparams = map(lambda k: k.translit, doc.kseries)
        exc = eval(doc.cat.params('EXC_%s_HINTS' % view.pview) or '[]')
        for row in db.fetchobj(q):
            hints = []
            rate = 0
            for prop in xrange(1, k):
                if prop in exc:
                    continue
                s = str(prop)
                h = row['n' + s]
                p = row['t' + s]
                if p in kparams:
                    rate -= 1
                hints.append(h)

            hint = Storage()
            hint.name = formatname(hints[1:])
            hint.rate = rate
            pl[row.id].hints.append(hint)
        sz = 3
        for p in pl.itervalues():
            besthints = sorted(p.hints, key = lambda h: h.rate)[:sz]
            besthints = map(lambda h: h.name, besthints)
            if len(p.hints) > sz:
                besthints.append('...')
            p.hint = " / ".join(besthints)

    def sqlpids(self, pview, ppair, adfilter = None, usemem = False):
        if adfilter:
            adfilter = adfilter[:]
        else:
            adfilter = []

        adfilter += self.doc.view.adfilter.sql()

        res = self.doc.sqlpids(pview, ppair, adfilter, usemem)
        return res

    def prodlist(self, doc, qsort):
        # SQL запрос - временная таблица 1 с ID товарами фильтра
        sqlpids = self.sqlpids(self.doc.view.pview, self.ppair)
        q = sql.temp(sqlpids, 'plist', sql.get(['count(*)'], '%s'), ['id_product'])

        # Блокируем DB для выполнения пакета запросов в одной сессии
        db = site.db.self()
        try:
            # Задаем кол-во товаров и страницы
            self.prodcount = db.fetchval(q)

            t = [self.doc.tproduct, sql.tempname('plist') + ' ps']
            f = ['ps.id_product = p.id']
            q = sql.get_f(['p.id'], t, f)
            q = sql.order(q, qsort)
            q = sql.limit(q, self.ppg * (self.page - 1), self.ppg)
            pids = db.fetchvals(q)
            if not pids:
                return []
            pl = self.__proddata(db, doc.view, pids)
            if not doc.view.iss:
                self.__prodhint(db, doc.view, pl)
        finally:
            pass
            #db.shunlock()

        prodlist = map(lambda pid: pl[pid], pids)
        return prodlist

# DOC OBJ: Fiche with prices
class DOCatFiche(DOAbsCatProducts):
    template = 'catfiche'

    def prodlist(self, doc, qsort):
        q = doc.sqlpids(doc.view.pview, self.ppair)
        pid = db.fetchvals(q)
        if not pid:
            self.NotFound('Fiche not found')
        pid = pid[0]

        k = doc.kseries
        modellist = map(lambda k: k.name, (k[1], k[3], k[2]))
        translist = map(lambda k: k.translit, doc.kseries)

        fiche = db.fetchobject(doc.tproduct, pid)
        fiche.model = '%s %s %s' % tuple(modellist)
        fiche.img   = doc.geturl(translist, ext = 'gif')
        fiche.imgs  = doc.geturl(translist, img ='preview', ext = 'gif')
        img_addcrc(db, fiche.img, fiche.id_image)
        img_addcrc(db, fiche.imgs, fiche.id_image)
        self.add(fiche = fiche)

        q = sql.get_fval(['*'], doc.tprice, 'id_product')
        if qsort[0][0] == 'name':
            qsort[0] = ('CAST(num AS UNSIGNED)', 'ASC')

        q = sql.group(q, 'num, name')
        q = sql.order(q, qsort)
        prices = db.fetchobj(q, [pid])
        log.t_trace('DOCatFiche.Prepare.Price requested')
        for row in prices:
            row.price = float(row.price) * float(site.config("CURRENCY", 2))
            row.price = doc.getprice(row.price, True, row.currency)
            row.code  = formatnumber(row.id, 9)
            row.req = row.req or ''
        log.t_trace('DOCatFiche.Price formatted')

        self.add(show_all = True)
        self.ppg = site.config('PROD_PER_PAGE', 2)
        self.prodcount = len(prices)

        i = self.ppg * (self.page - 1)
        prices = prices[i:i + self.ppg]

        log.t_trace('DOCatFiche.Prepare.Before return')
        return prices

class DOCatSearch(DOCatProducts):
    template = 'catsearch'

    inparams  = ['show_all', 'sort', 'query', 'list', 'maxq']
    outparams = ['show_all', 'query']

    def showproducts(self):
        return True

    def sqlpids(self, pview, ppair):
        id   = self.doc.view.id
        smap = self('smap')
        adfilter = smap.filters[id].frow
        self.addshared(adfilter = adfilter)
        return DOCatProducts.sqlpids(self, pview, ppair, adfilter, True)

    def prodlist(self, doc, qsort):
        query = unicode(self("query"))
        smap = self('smap')

        if not smap or smap.text != query:
            smap = site.search(doc, query)
            self.save(force = True, smap = smap)

        if smap.product:
            p = smap.product
            product = classes.Product(doc, p.pid, p.source, p.psid)
            product.ppid = p.ppid
            product.hl = p.ppid or query
            doc.redirect(product.url)

        self.prodcount = 0

        searchres = Storage()
        searchres.count = formatnumber(smap.count)
        searchres.filters = []
        self.add(searchres = searchres)
        if not smap.filters:
            return []

        view0 = None
        for view in sorted(smap.filters.values(), key = lambda v: v.count, reverse = True):
            if not view0:
                view0 = view
            row = Storage()
            row.count = formatnumber(view.count)
            row.name = "%s / %s" % (view.k[0].name, view.name)
            row.url = doc.geturl([view.k[0].translit], query = dict(query = query), view = view)

            searchres.filters.append(row)

        if view0:
            url = doc.geturl([view0.k[0].translit], query = dict(query = query), view = view0, addmod = False)
            if not doc.view:
                doc.redirect(url)
            elif doc.view.id not in smap.filters:
                doc.redirect(url)
        else:
            return []

        return DOCatProducts.prodlist(self, doc, qsort)

    def prepare(self, doc):
        if not isinstance(doc, DocCatalog):
            doc.view = None
        DOCatProducts.prepare(self, doc)

# DOC OBJ: Product page
class DOProduct(DocObj):
    template = 'product'

    def prepare(self, doc):
        if doc.opt.pid:
            pid = doc.opt.pid
        else:
            pid = doc.getpid()
        if not pid:
            self.NotFound('Product not found')
        product = classes.Product(doc, pid)
        product.sethintmap()

        prodparams = []
        for k in doc.k:
            if k:
                prodparams.append(k)
        if product.partno1:
            k = Storage()
            k.name_group = const.LEX_PARTNO
            k.name = product.partno1
            prodparams.append(k)

        self.add(product = product, prodparams = prodparams)
        doc.title = product.name

        paras = split_para(product.fnote)
        mid = len(paras) / 2
        product.note1 = "".join(paras[:mid])
        product.note2 = "".join(paras[mid:])

        pdata = []
        for k in doc.kseries:
            pdata += k.params.getlist('FLOAT', None)

        def adfloats(f):
            floats = []
            tlist = dict(map(lambda x: (x.val1, x), filter(f, pdata)))
            keys = tlist.keys()
            if tlist:
                q = sql.get_f('*', 'prop', sql.fin('translit', keys, True))
                for row in db.fetchobj(q, keys):
                    prop = classes.Prop(doc, row)
                    prop.evalname(self.ctx)
                    prop.evalnote(self.ctx)
                    prop.para = tlist[prop.translit]
                    floats.append(prop)
            return floats

        self.add(top_floats = adfloats(lambda x: x.val2 == 'top'))
        self.add(bot_floats = adfloats(lambda x: x.val2 != 'top'))

# ---------------------------------
# DOCUMENT: Prototype
# ---------------------------------

class Document(AbsDocument):
    def __init__(self, request):
        self.catalog = isinstance(self, DocCatalog)
        self.view = None
        self.opt = Storage()
        self.opt.check = True
        self.__chain = [dict(url = '/', name = const.LEX_MAIN)]
        AbsDocument.__init__(self, request)

    def checkk(self, dk, flist):
        if not self.opt.check:
            return
        if len(dk) != len(flist):
            self.NotFound("Count of K in URL is not equal to count of K in database")

    def getk(self, params, field = 'translit'):
        log.t_trace('dyna.params.check1')

        flist = []
        for par in params:
            if par and par != '0':
                flist.append(par)

        q = ['p.id_group = pg.id', 'p.%s IN (%s)' % (field, sql.f(flist))]
        q = sql.get_f(['pg.name AS name_group', 'p.*'], 'prop p, prop_group pg', q)
        dk = db.fetchobj(q, flist)
        self.opt.dk = dk
        log.t_trace('dyna.params.check2')
        self.checkk(dk, flist)
        k = [None] * len(params)
        for row in dk:
            prop = classes.Prop(self, row)
            index = params.index(prop[field])
            prop.index = index + 1
            k[index] = prop

        return k

    def getprops(self, row):
        idl = map(lambda i: row['id_prop' + str(i + 1)], xrange(8))
        f = sql.fin('id', vallist(idl))

        props = db.fetchdic(sql.get_f(['id', 'translit'], 'prop', f))
        dk = []
        for id in idl:
            if id in props:
                dk.append(props[id]['translit'])
            else:
                dk.append(None)
        return dk

    def getimage(self, id, parent, params, img = None, crclist = None):
        if not id:
            return None
        image = classes.ImageInfo(self, id, parent, params, img)
        if crclist != None:
            crclist.append((image.url, image.id))
        return image

    def getprice(self, price, small = False, currency = None):
        disc = self.request('disc')
        cdef = self.request('cdef')
        adpr = parse_price(self.request('adpr'))

        if not currency:
            currency = site.config('CURRENCY')
        if disc and isnum(disc):
            price = float(price) * (100 - float(disc)) / 100

        if adpr:
            price += getprice(site.config, adpr[0], adpr[1], currency)
        f = lambda curdef, fmt: formatprice(site.config, price, currency, curdef, fmt)
        p1 = f(cdef, '%.0f')
        if cdef == 'USD':
            p2 = ('', '')
        else:
            p2 = f('USD', '%.2f')
        if small:
            fsz = '_small'
        else:
            fsz = ''
        res = PRICE_FORMAT % (fsz, p1[0], p1[1], p2[1], p2[0])
        return res

    def sqlppair(self, ppair):
        return map(lambda s: "ps.id_prop%d = %d" % s, ppair.iteritems())

    def sqlpids(self, pview, ppair, adfilter = [], usemem = False):
        f = self.sqlppair(ppair)
        f += ["ps.id_product = p.id"]
        f += ["ps.pview = '%s'" % pview] + adfilter
        if self.request('show_store'):
            fstore = sql.get_f('s.id', 'store s', ['s.id_product = p.id', 's.quantity > 0'])
            fstore = sql.exists(fstore)
            f += [fstore]
        if usemem:
            tpropset = const.MEM_SEARCH + ' ps'
        else:
            tpropset = self.tpropset
        field = 'ps.id_product'
        if not self.cat.isfiche:
            field = 'DISTINCT ' + field
        q = sql.get_f([field], tpropset + ', ' + self.tproduct, f) 
        return q

    def chain(self, chain):
        pass

    def addchain(self, name, url):
        self.__chain.append(dict(name = name, url = url))

    def prepare(self):
        if self.request('query'):
            self.addmarker(DOCatSearch, 'body')

        rq = self.request
        if rq.module in const.SITE_MAP:
            title   = None
            params = []
            for p in rq.params:
                params.append(p)
                path = "/".join(params)
                smap = const.SITE_MAP[rq.module]
                if path in smap:
                    title = smap[path]
                    self.__chain.append(dict(url = self.geturl(params, alwaysext = True), name = title))
            if title:
                self.title = title

        self.chain(self.__chain)
        self.add(chain = self.__chain)

                                        
# ---------------------------------
# DOCUMENT: Static page
# ---------------------------------
class DocStatic(Document):
    def params(self, params):
        if len(params) == 0:
            self.NotFound("No static page param found")
        self.page = 'static/' + '/'.join(params) + '.html'
        fullpath = os.path.join(config.TEMPLATE_DIR, self.page)
        if not os.path.exists(fullpath):
            self.NotFound("Static page path '%s' not found" % fullpath)

    def markers(self):
        self.addmarker(DOBlank)
        self.addmarker(DOStatic, 'body')

# ---------------------------------
# DOCUMENT: Simple Ajax Module Page
# ---------------------------------
class DocLib(Document):
    def params(self, params):
        if len(params) == 0:
            self.NotFound("No lib page param found")
        self.lib = params[0]

        if self.lib == 'order':
            self.addmarker(DOLibOrder, 'body')
        elif self.lib == 'search':
            self.addmarker(DOLibSearch, 'body')
        elif self.lib == 'news':
            self.addmarker(DOLibNews, 'body')
        elif self.lib == 'ichain':
            self.addmarker(DOLibIChain, 'body')
        else:
            self.NotFound("No lib '%s' found" % lib)
        self.title = const.SITE_MAP[self.request.module][params[0]]

    def markers(self):
        self.addmarker(DOBlank)

class DocMain(Document):
    def params(self, params):
        pass

    def markers(self):
        self.addmarker(DOBlank)

# ---------------------------------
# DOCUMENT: Site Catalog page
# ---------------------------------
class DocCatalog(Document):
    inparams = ['show_store', 'price_min', 'price_max', 'list_view']

    def markers(self):
        self.addmarker(DOBlank)
        self.addmarker(DOCatFilter, 'menu')

    def params(self, params):
        log.t_trace('dyna.params.start')
        if len(params) == 0:
            self.NotFound("Params length = 0")

        ptranslit = None
        if len(params) > 1:
            q = ['pv.id_cat = p.id', 'p.translit = %s', 'pv.translit = %s']
            q = sql.get_f('pv.translit', 'pview pv, prop p', q)
            ptranslit = db.fetchval(q, params[:2])
            if ptranslit:
                params.pop(1)


        self.opt.check = False
        self.k = self.getk(params)
        self.cat = classes.Cat(self, self.k[0])

        self.__settables()       
        self.__tryproduct(params)
        self.checkk(self.opt.dk, params)

        # Fetching view's information
        q = sql.get_fval(['*'], 'pview', 'id_cat')
        q = sql.order(q, 'num')
        log.t_trace('dyna.params.check3')

        self.view = None
        self.view0 = None
        self.views = []
        for row in db.fetchobj(q, [self.cat.id]):
            view = classes.View(self, row)

            self.views.append(view)
            
            if self.opt.pid:
                if view.main:
                    self.view = view
            elif ptranslit:
                if row.translit == ptranslit:
                    self.view = view
            else:
                if row.num == 1:
                    self.view = view

            if not self.view0 and (view.main or (self.cat.isfiche)):
                self.view0 = view

        if not self.view:
            self.NotFound("View is None (not found)")

        if not self.view0:
            self.NotFound("Default view is None (not found)")

        self.view.putk()
        self.view.parsemap()
        self.__markers()

        tlist = []
        exc = eval(self.cat.params('EXC_%s_HINTS' % self.view.pview) or '[]')
        for i in xrange(len(self.k)):
            if i in exc:
                continue
            tlist.append(self.k[i])
        self.title = formatname(tlist, lambda s: s.fname)

        plist = {}
        for k in self.kseries:
            p = k.params
            for row in p.data:
                plist[str(row.name)] = p(row.name, 1)
        self.addshared(**plist)

        self.add(price_min = parse_price_def(self.site.config, self('price_min')))
        self.add(price_max = parse_price_def(self.site.config, self('price_max')))

        self.savelist('show_store', 'price_min', 'price_max', 'list_view')
        log.t_trace('dyna.params.end')

    def getpid(self):
        ppair = {}
        i = 1
        for k in self.k:
            if k:
                ppair[i] = k.id
            i += 1
        q = self.sqlpids(self.view.pview, ppair)
        pid = db.fetchval(q)
        return pid

    def __tryproduct(self, params):
        self.opt.check = True
        self.opt.pid = None
        if len(params) != const.PRODUCT_URL_LEN + 1 or self.cat.isfiche:
            return
        klist = self.k[:const.PRODUCT_URL_LEN]
        if None in klist:
            return
        klist = map(lambda k: k.id, klist)
        fields = map(lambda x: 'ps.id_prop%s' % x, xrange(1, 9))
        fields.append('p.id')
        tables = [self.tproduct, self.tpropset]
        f = ['ps.id_product = p.id', 'p.partno1 = %s']
        q = sql.get_f(fields, tables, f)
        for row in db.fetchobj(q, params[-1]):
            found = 0
            props = []
            for (key, val) in row.iteritems():
                if key[:7] == 'id_prop':
                    props.append(val)
                    if val in klist:
                        found += 1
            if found == const.PRODUCT_URL_LEN:
               #del self.k[-1]
               self.k = self.getk(props, 'id')
               self.opt.pid = row.id
               self.opt.check = False

    def __markers(self):
        if self.cat.isfiche:
            self.addmarker(DOCatFiche, 'body')
#        elif self.opt.pid or self.view.issingle():
        elif self.opt.pid:
            self.addmarker(DOProduct, 'body')
        else:
            self.addmarker(DOCatProducts, 'body')

    def __settables(self):
        s = self.cat.source
        self.tpropset = gettable(s, 'propset')
        self.tproduct = gettable(s, 'product')
        self.timage   = gettable(s, 'image')
        self.tprice   = gettable(s, 'price')

    def chain(self, chain):
        #i = 0
        #for prop in self.kseries[:len(self.view.blocks)]:
        #    params = map(lambda k: k.translit, self.kseries[:i + 1])
        #    url = {}
        #    url['url']  = self.geturl(params)
        #    url['name'] = prop.name
        #    chain.append(url)
        #    i += 1

        i = 0
        params = []
        for b in self.view.blocks:
            if b.k:
                params.append(b.k.translit)
                iscat = b.k.id_group == site.gvar.params.cat_gid
                iscat = iscat and len(params) == 1
                url = Storage()
                url.name = b.k.name
                url.url  = self.geturl(params, addview = not iscat)
                chain.append(url)

# ---------------------------------
# DOCUMENT: Property page
# ---------------------------------
class DocProp(Document):
    def params(self, params):
        self.prop = None
        if params:
            self.prop = classes.Prop(self, self.getk(params)[0].id)
            self.addmarker(DOProp, 'body')

    def markers(self):
        self.addmarker(DOBlank)
        self.addmarker(DOProp, 'body')

    def chain(self, chain):
        if self.prop:
            self.addchain(self.prop.name, self.geturl([self.prop.translit], alwaysext = True))

# ---------------------------------
# DOCUMENT: Articles page
# ---------------------------------
class DocArticle(DocProp):
    def markers(self):
        self.addmarker(DOBlank)
        self.addmarker(DOArticles, 'body')

    def chain(self, chain):
        self.addchain(const.LEX_ARTICLES, self.geturl([]))
        DocProp.chain(self, chain)

# ---------------------------------
# IMAGE: Catalogue image
# ---------------------------------
class ImgCatalog(Image, DocCatalog):
    def __fastid(self, params):
        # deleting '/image' prefix
        param = self.request.url[6:]
        crc = getcrc(param)
        q = sql.get_fval(['id_image'], 'mem_image_crc', 'crc')
        id = db.fetchval(q, [crc])
        return id

    def __slowid(self, params):
        img = self.request.img
        url = self.request.url

        p = self.request.params
        # IMAGE - Property
        if len(p) == 1:
            q = sql.get_fval('id_image', 'prop', 'translit')
            id = db.fetchval(q, p[0])
            # Prop image by num
            if not id:
                mo = re.search(r'\-([a-z0-9])$', p[0])
                if mo:
                    f = ['p.id = id.id_obj', 'p.translit = %s', 'id.num = %s']
                    q = sql.get_f('id.id_image', ['image_deps id', 'prop p'], f)
                    plist = [p[0][:-len(mo.group(0))], mo.group(1)]
                    id = db.fetchval(q, plist)
            if id:
                url = url[6:]
        # IMAGE - Product
        else:
            pid = None
            if len(p) == const.IMAGE_URL_LEN + 1:
                pid = db.fetchval(sql.get_fval('id', 'product', 'partno1'), params[-1])
                if pid:
                    params.pop()
            DocCatalog.params(self, params)
            if not pid:
                pid = self.getpid()

            # Full Image
            if isint(img):
                q = sql.get_fval(['id_image'], 'image_deps', 'id_obj')
                q = sql.order(q, 'id_obj')
                idl = db.fetchvals(q, [pid])
                if (img > 0) and img <= len(idl):
                     id = idl[img - 1]
                else:
                     self.NotFound('Image Index %d out of range' % img)
            # Preview
            else:
                q = sql.get_fval(['id_image'], self.tproduct, 'id')
                id = db.fetchval(q, [pid])
        img_addcrc(db, url, id)
        return id

    def __ficheimage(self, id):
        self.ext = self.request.ext
        self.format = self.ext
        if self.request.img == 'preview':
            self.data = readurl(config.FICHE_IMAGE % ('preview', id))
        else:
            self.data = readurl(config.FICHE_IMAGE % ('full', id))
            
    def params(self, params):
        if len(params) == 0:
            self.NotFound()

        id = self.__fastid(params)
        if id:
            pass
            #log('FAST ID for %s' % (params))
        else:
            #log('SLOW ID for %s' % (params))
            id = self.__slowid(params)
        if not id:
            self.NotFound("Can't find image ID")
        if 'oem' in params[:2]:
            return self.__ficheimage(id)

        q = sql.get_f(['i.type, i.image, s.eddate'], ['image i', 'sysid s'], ['s.id = i.id', 'i.id = %s'])
        obj = db.fetchrowobj(q, [id])

        if not obj:
            self.NotFound()

        self.ext = img_typ2ext(obj.type)
        self.format = self.ext
        self.data = obj.image
	web.http.lastmodified(obj.eddate)

    def get(self):
        return self.data

# ====================================
# MAIN: Site Map
# ====================================

class SiteMap(object):
    def __rewrite(self, url):
        params = []
        for param in re.split('[/_]', url):
            if param != '':
                params.append(param)
        if params:
            if params[0] in self.catlist:
                return '/catalog' + url
        else:
            return '/main'
        return url

    def addurl(self, url):
        self.parent = url
        self.oldurls.append(url)
        try:
            request = Request(self.__rewrite(url), dict(static = True))
            data = request.getdata()
        except Exception, e:
            log(e, M_ERR)
            return
        log((url, len(data), 'P = %s' % self.urls[url]))
        crc = getcrc(data.encode('utf-8'))
        row = classes.DBRecord(site, url, 'sitemap', 'url')
        row.status = 1
        row.url  = url
        row.lastmod = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        if row.hash != crc:
            row.hash = crc
            log("MODIFIED!")
            row.save()
        else:
            row.save(['status'])

    def traceurl(self, url):
        if url not in self.oldurls and url not in self.newurls:
            mo = re.search(r'\.([a-z0-9]+)$', url)
            if not mo or mo.group(1) == const.DEFAULT_EXT:
                self.newurls[url] = self.parent

    def index(self):
        self.oldurls = []
        self.newurls = {}
        self.parent = None
        self.catlist = db.fetchvals(sql.get_f('p.translit', 'prop p, cat c', 'c.id = p.id'))
        site.gvar.traceurl = self.traceurl

        db.execute(sql.update('status', 'sitemap'), [0])

        for (mod, data) in const.SITE_MAP.iteritems():
            for path in data:
                url = geturl(None, [mod, path], alwaysext = True)
                self.traceurl(url)

        q = sql.get_f('*', 'prop', 'id_group = getpgbytr("articles")')
        for row in db.fetchobj(q):
            url  = geturl(None, [const.MOD_ARTICLE, row.translit], alwaysext = True)
            self.traceurl(url)

        while True:
            self.urls = self.newurls.copy()
            if not self.urls:
                break
            self.newurls.clear()
            for url in self.urls.iterkeys():
                self.addurl(url)
        return

        site.gvar.traceurl = None

        db.execute(sql.delete('sitemap', 'status = 0'), commit = True)

# ====================================
# MAIN: Request Module/Class mapping
# ====================================
site.urlmap = {
    MOD_IMAGE   : ImgCatalog,
    MOD_CATALOG : DocCatalog,
    MOD_STATIC  : DocStatic,
    MOD_MAIN    : DocMain,
    MOD_LIB     : DocLib,
    MOD_ARTICLE : DocArticle,
    MOD_PROP    : DocProp
}

# ====================================
# MAIN: Site Crontab
# ====================================

def f():
    site.search.reload()
    q = sql.get(['COUNT(id)'], 'product')
    site.config.set('PRODUCTS', db.fetchval(q))
    q = sql.get(['COUNT(id)'], 'fiche_prop_set')
    site.config.set('PRODUCTS', db.fetchval(q), 2)

    q = sql.get_f('p.translit', 'prop p, cat c', 'c.id = p.id')
    f = open(config.CAT_MAP, "w")
    for row in db.fetchvals(q):
        f.write('%s %s\n' % (row, row))
    f.close()

site.cron.add('Products Search / Count', 0, 300, f)

def f():
    q = sql.get_f('s.id', 'store s', ['p.id = s.id_product', 's.quantity > 0'])
    q = sql.get_f('p.id', 'product p', sql.exists(q))
    q = sql.order(q, 'p.id')
    pids = db.fetchvals(q)
    idmax = len(pids) - 1
    idl = map(lambda x: str(pids[random.randint(0, idmax)]), xrange(10))
    idl = ",".join(idl)
    site.config.set("RANDOM_PRODUCTS", idl)
    site.config.set("STATIC_PRODUCT", pids[0])

site.cron.add('Random products list', 0, 300, f)

def f():
    dt = time.localtime(time.time() - config.FASTID_LIFETIME)
    dt = time.strftime("%Y-%m-%d %H:%M:%S", dt)
    q = "DELETE FROM mem_image_crc WHERE dt < '%s'" % dt
    db.execute(q)

site.cron.add('mem_image_crc', 0, config.FASTID_LIFETIME, f)

def f():
    f = ['CASE']
    curdef = getcurdef(site.config)[5:]
    rate = float(site.config('CURRENCY', 2))
    field = 'IFNULL(price_out, price * %.5f)' % rate
    for key in site.config.getlist('CURR_'):
       currency = key[5:]
       rate = float(site.config(key))
       f.append('WHEN currency = "%s" THEN %s * %.5f' % (currency, field, rate))
    f.append('END')
    f = "\n".join(f)
    q = sql.update('price', 'product') % f
    db.execute(q)

    f = ['CASE']
    f.append('WHEN price BETWEEN 200 AND 900 THEN FLOOR((price + 4.99999) / 5) * 5')
    f.append('WHEN price > 900 THEN ROUND(price + 5, -1)')
    f.append('ELSE price')
    f.append('END')
    f = "\n".join(f)
    q = sql.update('price', 'product') % f
    db.execute(q)

site.cron.add('Update DEFAULT product prices', 0, 300, f)

def f():
    f = ['ps.id_product = p.id', 'pr.id_prop = ps.id_prop1', 'pr.name = "ETA"']
    q = sql.get_f('pr.val1', ['prop_set ps', 'param pr'], f)
    q = '(%s)' % sql.limit(q, 0, 1)
    q = sql.update('eta', 'product p') % q
    db.execute(q)

    f = ['s.id_product = p.id', 'pr.id_prop = s.id_store', 'pr.name = "ETA"']
    q = sql.get_f('pr.val1', ['store s', 'param pr'], f)
    q = sql.order(q, 'pr.val1')
    q = '(%s)' % sql.limit(q, 0, 1)
    fu = sql.get_f('id', 'store s', 's.id_product = p.id')
    fu = sql.exists(fu)
    q = sql.update('eta', 'product p', filter = fu) % q
    db.execute(q)
    db.commit()

site.cron.add('Update products ETA', 0, 300, f)

def f():
    params = site.gvar.params
    params.mnf_gid = db.fetchval(sql.get("getpgbytr('mnf')"))
    params.cat_gid = db.fetchval(sql.get("getpgbytr('cat')"))

site.cron.add('Runtime params INIT', -1, 3600, f)

def f():
    q = sql.get_f("p.*", ['cat c', 'prop p'], ['c.id = p.id', 'c.visible = 1'])
    for cat in db.fetchobj(q):
        url = '/catalog/%s'
        if cat.translit == 'masla':
            url += '/brand'
        request = Request(url % cat.translit, dict(static = True, marker = 'menu', frontdata = True))
        request.getdata()

site.cron.add('Frontpage Data', -1, 3600, f)
