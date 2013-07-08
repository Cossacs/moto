# coding: utf-8
# --------------------------------------------
# HEADER: Interface Classes
# --------------------------------------------

from utils import *
from const import *
import web
import config, sql

MOD_INS = "INSERT"
MOD_UPD = "UPDATE"

class DBTable(object):
    def __init__(self, site, tabname):
        self.name   = tabname
        self.fields = site.db.fetchvals('SHOW FIELDS FROM %s' % self.name)

class DBRecord(Storage):
    tabname = None

    def load(self):
        pass

    def NotCreated(self):
        pass

    def newid(self, db):
        pass

    def __init__(self, site, id, tabname = None, keyfield = 'id'):
        self.site = site
        self.db   = site.db
        self.id   = None
        self.mode = MOD_INS
        self.__table = None
        if tabname:
            self.tabname = tabname
        self.keyfield = keyfield

        if 'tabname' in self:
            tabname = self['tabname']
        else:
            tabname = self.tabname

        key = tabname + DBTable.__name__

        if key in site.cache:
            self.table = site.cache[key]
        else:
            self.table = DBTable(site, tabname)
            site.cache.set(key, self.table, True)

        if isinstance(id, Storage) and 'keyfield' in id:
            self.keyfield = id.keyfield
            id = id.id

        if isinstance(id, Storage):
            data = id
        else:
            self.id  = id
            keyfield = 'p.' + self.keyfield
            table = '%s p LEFT OUTER JOIN sysid s ON %s = s.id' 
            table = table % (self.table.name, keyfield)
            data = self.db.fetchobject(table, id, keyfield)
        if data:
            for (key, val) in data.iteritems():
                if val != None:
                    self[key] = val
            self.mode = MOD_UPD
        else:
            self.NotCreated()

        if self.addate:
            self.date = self.addate.strftime("%d.%m.%Y %X")
        self.load()

    def save(self, afields = None):
        if afields:
            fields = afields
        else:
            fields = self.table.fields

        key = self.keyfield
        tab = self.table.name
        exists = self.id and self.db.fetchval(sql.get_fval(key, tab, key), [self.id])
        db = self.db.self()
        try:
            # UPDATE
            if exists:
                self.mode = MOD_UPD
                q = sql.update(fields, tab, key)
                vals = map(lambda field: self.get(field, None), fields) + [self.id]
            # INSERT
            else:
                self.mode = MOD_INS
                self.newid(db)
                q = sql.insert(fields, tab)
                vals = map(lambda field: self.get(field, None), fields)
            db.execute(q, vals, commit = True)
        finally:
            pass

class DBObject(DBRecord):
    def NotCreated(self):
        raise Exception("Could not create DBObject, %s[%s]" % (self.table.name, self.id))

    def newid(self, db):
        self.id = getnewid(db, self.table.name)

    def __init__(self, doc, id):
        self.doc  = doc
        DBRecord.__init__(self, doc.site, id)

class View(DBObject):
    tabname = 'pview'

    def load(self):
        self.prodcount = 0
        groups = []
        for (key, val) in sorted(self.items()):
            if key[:8] == 'id_group':
                if val:
                    groups.append(val)
                else:
                    break
        self.groups = groups
        self.iss = self.pview == 'S'
        self.ist = self.pview == 'T'
        self.isdefault = self.num == 1
        self.adfilter = ADFilter(self)

    def __loadmap(self):
        q = 'pview_map pm LEFT JOIN prop_group pg ON pg.id = pm.id_group'
        q = sql.get_fval(['pg.name', 'pm.*'], q, 'pm.id_pview')
        q = sql.order(q, 'pm.num')
        self.map = self.db.fetchobj(q, [self.id])

    def parsemap(self, klist = None):
        self.__loadmap()
        # Step-by-step pass throw view map (VIEW MAP)
        # Creating list of filters
        self.blocks = []
        self.ppair = {}
        self.show_products = False
        self.nofollow = False

        if klist:        
            dk = klist
        else:
            dk = self.doc.k
        i_expand = None
        adfilter = {}
        groups   = []
        expand   = False
        gindex   = None
        stop     = False
        bfloat   = False
        b = None

        i = 0

        def getgroup(id):
            q = sql.get_fval(['name'], 'prop_group', 'id')
            return self.db.fetchval(q, [id])

        for row in self.map:
            if row.type =='F':
                propno = toint(row.val1)
                index  = propno - 1
                groups.append(propno)

                if row.val2[:2] == 'K=':
                    t = row.val2[2:]
                    k = self.doc.getk([t])[0]
                    dk[propno - 1] = k

                if gindex != row.val2:
                    if stop: break
                    gindex = row.val2

                b = Storage()
                b.show     = False
                b.propno   = propno
                b.gi       = gindex
                b.filter   = adfilter.copy()
                b._group   = []
                b.params   = []
                b.index    = i
                b.width    = 180

                if bfloat:
                    b.float = b and True
                    b.width = 600

                if (index < len(dk)) and dk[index]:
                    k = dk[index]
                    #if self.groups[b.propno - 1] != k.id_group:
                    #    self.doc.NotFound('View Map: Incorrect component "%s"' % k.translit)
                    b.k = k
                if b.k:
                    self.ppair[b.propno] = b.k.id
                else:
                    stop = True

                if expand and not i_expand:
                    i_expand = i
                self.blocks.append(b)
                i += 1
            elif row.type =='A':
                if row.val1 == 'SHOWPROD':
                    self.show_products = b and b.k
                elif row.val1 == 'EXPAND':
                    expand = True
                elif row.val1 == 'NOFOLLOW':
                    self.nofollow = True
                    if self.site.gvar.traceurl:
                        break
                elif row.val1 == 'FILTER':
                    propno = toint(row.val2[1:2])
                    t = row.val2[3:]
                    k = self.doc.getk([t])[0]
                    adfilter[propno] = k.id
                    self.ppair[propno] = k.id
                elif row.val1 == 'HIDELAST':
                    b.hidden = b and not b.k
                elif row.val1 == 'FLOAT':
                    bfloat = True


        for b in self.blocks:
            expanded = i_expand and b.index >= i_expand
            if expanded:
                b.show = True
            if b.gi == gindex:
                b.show = True
            if b.gi == 'no':
                b.show = False
            stop = False

            for old in self.blocks:
                if old.gi != b.gi:
                    if stop: break
                elif old.gi == b.gi:
                    stop = True
                if (old != b) and old.k:
                    # COMMENT: Этот IF запрещает сворачивать блоки с одинаковым Group Index
                    #if (old.gi != b.gi) and (not expanded or b.gi > old.gi):
                    #if (old.gi != b.gi):
                    b.filter[old.propno] = old.k.id
                    b.params.append(old.k.translit)
                else:
                    b.params.append(None)
            b._group = groups[:len(b.filter)]
            if b.show:
                b.group = getgroup(self.groups[b.propno - 1])

        if not self.doc.catalog:
            self.rooturl = None
        else:
            self.rooturl = self.doc.geturl([self.doc.cat.translit])

    def issingle(self):
        if self.doc.cat.isfiche:
            return False

        f = []
        i = 1
        for k in self.doc.k:
            if k:
                f.append("ps.id_prop%d = %d" % (i, k.id))
            i += 1
        f.append('ps.pview = %s')
        q = sql.get_f('*', self.doc.tpropset, f)
        q = sql.limit(q, 0, 2)

        data = self.db.fetchobj(q, [self.pview])
        if len(data) == 1:
            klist      = self.doc.getprops(data[0])
            self.doc.k = self.doc.getk(klist)
            return True
        else:
            return False

    def putk(self):
        klist = []
        kl = {}
        for k in self.doc.k:
            if k:
                kl[k.id_group] = k
        index = 0
        for id_group in self.groups:
            k = kl.get(id_group, None)
            if k:
                k.index = index
            klist.append(k)
            index += 1
        self.doc.k = klist
        self.doc.kseries = notemptylist(klist)

    def nonssql(self, pids):
        fields = ['p.id']
        tables = [self.doc.tpropset]

        k = len(self.groups) + 1
        for i in xrange(1, k):
            tables.append('LEFT JOIN prop p%d ON ps.id_prop%d = p%d.id' % (i, i, i))
            fields.append('p%d.name AS n%d' % (i, i))
            fields.append('p%d.translit AS t%d' % (i, i))

        tables = ["\n  ".join(tables)]
        tables.append(self.doc.tproduct)

        f = [sql.fin('p.id', pids)]
        f.append("p.id = ps.id_product")
        f.append("ps.pview = '%s'" % self.pview)
        return(fields, tables, f)

class Product(DBObject):
    def __init__(self, doc, id, source = 'N', psid = None):
        self.source = source
        self.tabname  = gettable(source, 'product', False)

        self.tpropset = gettable(source, 'propset')
        self.timage   = gettable(source, 'image')
        self.ppid = None
        self.hl   = None
        self.psid = psid
        DBObject.__init__(self, doc, id)

    def attr(self, name):
        if name == 'url':
            r = self.doc.request
            query = dict(hl = self.hl, disc = r('disc'), adpr = r('adpr'), cdef = r('cdef'))
            if isfiche(self.source):
                return self.doc.geturl(self.param[:1] + self.param[2:], 
                                       query = query, view = self.view, addmod = False)
            else:
                return self.doc.geturl(self.param[:const.PRODUCT_URL_LEN] + [self.partno1], 
                                       query = query, addview = False, addmod = False)
        elif name == 'image':
            return self.doc.getimage(self.id_image, self, self.param)

        elif name == 'imagebig':
            if isproduct(self.source) and self.images:
                return self.images[0]

        elif name == 'images':
            q = sql.get_fval(['id_image'], 'image_deps', 'id_obj')
            q = sql.order(q, 'id')
            res = []
            i = 1
            for id in self.db.fetchvals(q, [self.id]):
                img = self.doc.getimage(id, self, self.param, i)
                res.append(img)
                i += 1
            return res

        elif name == 'stored':                	
            qstore = sql.get_fval('SUM(quantity)', 'store', 'id_product')
            return self.db.fetchval(qstore, [self.id])

        elif name == 'store':
            fields = ['SUM(s.quantity) AS quantity', 'pr.val1 AS eta', 'peta.name AS etaname']
            f = ['p.id = s.id_store', 'id_product = %s']
            f.append('pr.id_prop = p.id')
            f.append('pr.name = "ETA"')
            f.append('peta.translit = pr.val1')
            qstore = sql.get_f(fields, ['store s', 'prop p', 'param pr', 'prop peta'], f)
            qstore = sql.group(qstore, 'eta')
            qstore = sql.order(qstore, 'eta')
            res = Storage()
            res.data = self.db.fetchobj(qstore, [self.id])
            res.quantity = self.stored
            res.available = True if self.stored else False
            q = sql.get_f('p.*', ['param pr', 'prop p'], ['pr.id_prop = %s', 'pr.name = "ETA"', 'p.translit = pr.val1'])
            res.default = self.db.fetchrowobj(q, [self.view.id_cat])
            return res

        return None

    def load(self):
        if not 'param' in self:
            f = ['pv.pview = ps.pview']
            f.append('ps.id_product = %s')
            f.append('ps.id_prop1 = pv.id_cat')
            p = [self.id]

            if self.psid:
                f.append('ps.id = %s')
                p.append(self.psid)
            else:
                f.append('ps.pview = %s')
                p.append(const.DEFAULT_PVIEW)

            q = sql.get_f('pv.id AS id_view, ps.*', ['pview pv', self.tpropset], f)
            row = self.db.fetchrowobj(q, p)

            self.param = self.doc.getprops(row)
            self.view = View(self.doc, row.id_view)

        if isproduct(self.source):
            self.price = self.doc.getprice(self.price, self.smallprice)

        self.code = formatnumber(self.id)
        self.note = self.note or ''

    def sethintmap(self):
        views = self.doc.views
        self.hintmap = []
        cnt = 0
        for view in views:
            if view.iss:
                continue
            mapitem = Storage()
            mapitem.hints = []
            mapitem.view  = view
            (fields, tables, f) = view.nonssql([self.id])
            q = sql.get_f(fields, tables, f)
            exc = eval(self.doc.cat.params('EXC_%s_HINTS' % view.pview) or '[]')
            for row in self.db.fetchobj(q):
                hints = []
                for prop in xrange(1, len(view.groups) + 1):
                    if prop in exc:
                        continue
                    s = str(prop)
                    hints.append(row['n' + s])
                hint = formatname(hints[1:])
                mapitem.hints.append(hint)
                cnt += 1
            self.hintmap.append(mapitem)
        if not cnt:
            self.hintmap = None


class ImageInfo(DBObject):
    tabname = 'image'

    def __init__(self, doc, id, parent, params, img = None):
        self.parent = parent
        self.params = params
        self.img = img
        DBObject.__init__(self, doc, id)
        if not isinstance(id, Storage):
            self.addcrc()

    def load(self):
        self.ext = img_typ2ext(self.type)
        params = self.params
        if self.parent.partno1:
            params = params[:const.IMAGE_URL_LEN] + [self.parent.partno1]
        self.url = self.doc.geturl(params, img = self.img, ext = self.ext, alwaysext = True, addmod = False,
        addview = False)

    def addcrc(self):
        img_addcrc(self.db, self.url, self.id)

class PropParams(object):
    def __init__(self, site, idp):
        self.data = None
        self.idp = idp
        self.site = site
        self.db   = site.db
        self.load()

    def __call__(self, key, paramno = 1):
        for par in self.data:
            if par.name == key:
                if paramno:
                    val = par['val' + str(paramno)]
                    return toint(val)
                else:
                    return par

        return None

    def getdic(self, lsub, paramno = 1):
        res = {}
        ln = len(lsub)
        for key in self.data:
            if key[:ln] == lsub:
                res[key] = self(key, paramno)
        return res

    def getlist(self, key, paramno = 1):
        res = []
        for row in self.data:
            if row.name == key:
                res.append(self(key, paramno))
        return res


    def load(self):
        q = sql.get_fval(['name', 'val1', 'val2', 'val3', 'val4'], 'param', 'id_prop')
        self.data = self.site.db.fetchobj(q, [self.idp]) or []

    def clear(self):
        self.data = None

class Prop(DBObject):
    tabname = 'prop'

    #def __setimage(self, value):
    #    self.__image = value

    def load(self):
        self.fname = self.fname or self.name
        self.__image = None
        self.note = self.note or ""
        self.fname = bestname(self.name, self.fname)

    def attr(self, name):
        if name == 'params':
            return PropParams(self.site, self.id)
        elif name == 'image':
            if self.id_image:
                return ImageInfo(self.doc, self.id_image, self, [const.MOD_IMAGE, self.translit])

        return None

    def evalnote(self, ctx):
        self.note = self.site.render.evaluate(self.note, ctx)

    def evalname(self, ctx, fname = True):
        self.name = self.site.render.evaluate(self.name, ctx)
        if fname:
            self.fname = self.site.render.evaluate(self.fname, ctx)

class Cat(Prop):
    def NotCreated(self):
        doc.NotFound("Could not create Category, param K[0] is None")

    def load(self):
        Prop.load(self)

        if not 'source' in self:
            q = sql.get_fval(['prod_source'], 'cat', 'id')
            self.source = self.db.fetchval(q, [self.id])

        if self.source == None:
            self.doc.NotFound("Category prod_source is None")

        self.isproduct = isproduct(self.source)
        self.isfiche   = isfiche(self.source)
        self.isprice   = isprice(self.source)

class ADFilter(object):
    def __init__(self, view):
        self.price_min = None
        self.price_max = None
        self.store = False
        self.view = view

    def sql(self, full = False):
        if not self.view.doc.cat.isproduct:
            return []
        self.params()
        f = []
        if self.price_min:
            f.append('p.price >= %.5f' % (self.price_min - 0.5))
        if self.price_max:
            f.append('p.price < %.5f' % (self.price_max + 0.5))
        if self.store:
            f.append(self.__sqlstore())
        if full and f:
            f += ['ps.id_product = p.id']
            f = sql.get_f('p.id', self.view.doc.tproduct, f)
            f = ['ps.id_product IN (%s)' % f]
        return f

    def params(self):
        doc = self.view.doc
        self.store     = doc('show_store')
        self.price_min = doc('price_min')
        self.price_max = doc('price_max')

    def __sqlstore(self):
        fstore = sql.get_f('s.id', 'store s', ['s.id_product = p.id', 's.quantity > 0'])
        fstore = sql.exists(fstore)
        return fstore