# coding:  utf-8
# --------------------------------------------
# HEADER: Store import interfaces
# Created by: Cossacs, 2011
# --------------------------------------------
#
# Скрипт для автоматического обновления данных о наличии
# товаров на складах поставщиков. Скрипт запускается 
# периодически из CronTab (1 раз в сутки). Используются три
# источника данных (интерфейсов):
#  1) Почта с Excel-вложением
#  2) Электронная таблица Google Documents
#  3) DBF-файл на сайте поставщика, упакованный в zip-архив
# 
# Словарь интерфейсов (источников данных) и соответсвующих им
# интерфейсных классов определен в конце файла
#
# Скрипт использует функционал движка <сайт>:
#   - ORM-библиотеку classes.py
#   - функции верстки SQL - sql.py
#   - вспомогательные утилиты utils.py
#   - объект для работы с базой данных
#   - логгирование

from iutils import *
from utils import *
from abc import ABCMeta, abstractmethod, abstractproperty
from dbfpy import dbf
from cStringIO import StringIO

import os, sys, re, string, datetime, time, random
import sql, classes
import xlrd, web, zipfile, tempfile

class Product(DBObject):
    """Объект <Товар>"""
    tabname = 'product'

class Store(DBObject):
    """Объект <Единица хранения товара>"""
    tabname = "store"

class IStore():
    """Абстрактный класс-скелет загрузки данных из внешнего источника

    Скелет для описания класса-наследника, который загружает данные
    о наличие товаров из любого внешнего источника.
    У класса-наследника должны быть переопределены абстрактные методы,
    вызывая которые, загрузчик StoreLoader получает данные.

    Для определения абстрактного класса используется метакласс ABCMeta,
    для определения абстрактных методов - декоратор abstractmethod
    """

    __metaclass__ = ABCMeta
    def __init__(self, source = None):
        # Источник данных
        self.source = source

        # Если источник данных - временный файл, удалить
        self.clearsource = False

    def load(self, loader):
        self.loader = loader
        self.source = self.source or self.getsource()
        self.loadsource()

    # Загружает данные из внешнего источника
    def getsource(self): return None

    # Подготовка загруженных данных
    def loadsource(self): pass

    # Список категорий (массив, транслиты)
    @abstractmethod
    def getcats(self): pass

    # Возврат строки-фильтра для очистки данных
    @abstractmethod
    def getfilter(self): pass

    # Возврат данных, на входе - объект/категория
    @abstractmethod
    def getdata(self, cat): pass

    # Возвращает кол-во записей для загрузки
    @abstractmethod
    def getrows(self, cat): pass

class StoreLoader():
    """Загрузчик наличия товаров на складах. Создает согласно заданному 
    внизу файла словарю классы-интерфейсы, получает из них данные,
    сохраняет эти данные в базу
    """

    def __init__(self):
        # Склад по умолчанию
        self.whdef = None

        # Список объектов-интерфейсов данных
        self.interfaces = []

        # Инициализация - разобрать опции командной строки
        self.parseparams()

        # Запуск загрузки
        self.run()

    def parseparams(self):
        """Разбор параметров командной строки"""

        # Если параметры командной строки неверные - написать ошибку
        # и вывести описание команды
        def err(message):
            print "ERROR: %s" % message
            gvar.parser.print_help()
            sys.exit(0)

	# Список интерфейсов для загрузки
        gvar.parser.usage = "%prog [options]"
        gvar.parser.add_option('', '--import',
            dest    = 'ifaces', 
            help    = 'Comma-separated list of import interfaces: %s' % ', 
                '.join(interfaces.keys()))

	# Удалять наличие товара без подтверждения
        gvar.parser.add_option('', '--no-prompt',
            dest    = 'prompt', 
            action  = 'store_false',
            default = True,
            help    = 'Do not prompt for store cleaning')

	# Выводить детальную отладочную информацию в консоль
        gvar.parser.add_option('', '--debug',
            dest    = 'debug', 
            action  = 'store_true',
            default = False,
            help    = 'Detailed output to console')

        (self.o, self.args) = gvar.parser.parse_args()

	# Дублирование лога в консоль
        log.quiet = not self.o.debug

	# Интерфейсы не перечислены
        if not self.o.ifaces:
            err("No import interfaces specified")

	# Использовать все интерфейсы
        if self.o.ifaces == "all":
            self.o.ifaces = ",".join(interfaces.keys())

	# Создание объектов классов-источников данных
        for key in re.split(r',\s*', self.o.ifaces):
            if key in interfaces.keys():
                interface = interfaces[key]()
                interface.name = key
                self.interfaces.append(interface)
            else:
                err("Interface '%s' not found" % iface)

    def setcat(self, translit):
	"""Устанавливает объект-категорию товара и его главное представление"""

        q = sql.get_f('c.id', 'prop p, cat c',
            ['p.translit = %s', 'c.id = p.id'])
        gvar.id_cat = db.fetchval(q, [translit])

        # Установка категории (через создание объекта <Категория товара>)
        gvar.cat = classes.Cat(gvar.doc, gvar.id_cat)
        f = ['v.id_cat = c.id', 'v.pview = "S"', 'c.id = %s']
        q = sql.get_f('v.id', 'pview v, cat c', f)
     
        # Установка представления (через создание объекта 
        # <Представление товара>)  
        gvar.view  = classes.View(gvar.doc, db.fetchval(q, gvar.id_cat))

    def run(self):
	"""Запуск загрузчика наличия товаров"""

	# использовать единичное подключение к БД вместо пула подключений
        gvar.singledb()

	# Ссылка на пустой документ-заглушку (особенность архитектуры)
        gvar.doc       = FakeDoc()
        gvar.images    = {}

	# Цикл по загрузочным интерфейсам (источникам данных)
        for iface in self.interfaces:
            log("")
            log("LOADING '%s'" % iface.name)
            iface.load(self)

            # Для каждого источника данных - цикл по категориям товара
            for cat in iface.getcats():
                self.setcat(cat)
                self.clear(iface.getfilter())
                nloaded = 0
                nall = iface.getrows(cat)
   
                ok   = 0
                skip = 0
                for pdata in iface.getdata(cat):   
                    if self.load_store(pdata):
                        db.commit()
                        ok += 1
                    else:
                        skip += 1
                    nloaded += 1
   
                    log('LOADED %d of %d, OK = %d, SKIP = %d' % 
                        (nloaded, nall, ok, skip))

            # Если источник - файл с данными, и стоит флаг удаления,
            # то удалить файл
            if iface.clearsource and os.path.exists(iface.source):
                log("removing %s" % iface.source)
                os.remove(iface.source)

        # Уведомление об обновлении наличия товаров - на почту
        sendmail(u"Склады загружены: %s" % self.o.ifaces, "\n".join(log.messages))

    def parsefilter(self, ftext):
        """Метод, преобразовывающий метаописание в набор SQL-фильтров

	Функция преобразует созданный по определенным правилам текстовый шаблон
	в фильтр SQL-запроса (where), который обнулит наличие некоторых товаров
	на складе. Используется для удобного описания правил в заголовках Excel
	и Google Doc таблиц, по которым обновляется наличие товаров
	"""

        # список строк SQL-фильтра для отбора товаров
        # K - компоненты (свойства), характеризующие товар. 
        # Таких свойств может быть до 7 на каждое представление (View) товара.
        # Например, товар относится к категории "звезды" (k1=zvezdi),
        # и характеризуется некоторыми свойствами k2-k7 - цвет, размер и т.п.
        # Один товар может иметь несколько представлений, т.е. обладать разным
        # набором свойств K
        kfilter = []

        # список строк SQL-фильтра для отбора складов товаров
        sfilter = []

        cat = False
        ftext = real_translit(ftext.lower())

        # Объект <группа складов> - получается из базы вызовом
        # функции Get Property Group By Translit - 
        # получить группу свойств по коду свойства
        whgroup = db.fetchval('SELECT getpgbytr("stores")')

        for val in re.split(r'\,\s*', ftext):
            # Если в метаописании найдена инструкция по компонентному фильтру,
            # накладываемому для ограничения выборки товаров - расшифровать эту
            # инструкцию, и привести ее к виду строк SQL-фильтра
            if re.match(r'k\d=', val):
                propindex = toint(val[1:2])
                if propindex == 1:
                    cat = True
                propname = val[3:]
                propt    = real_translit(propname)
                prop = db.fetchobject('prop', propt, 'translit')
                if prop:
                    log("FILTER [K%d], ID %d = %s" % 
                        (propindex, prop.id, translit(propname)))
                else:
                    raise Exception("Property %s not found" % translit(propname))
                kfilter.append('ps.id_prop%d = %s' % (propindex, prop.id))

            # Если в метаописании найдена инструкция по очистке единиц хранения
            # товара перед загрузкой новых товаров - добавить ее в фильтр,
            # ограничивающий выбор товаров
            elif re.match(r'clear=', val):
                slist = []
                for store in re.split(r';\s*', val[6:]):
                    slist.append('translit RLIKE "%s"' % store)
                f = [sql.f_or(slist), 'id_group = %s' % whgroup]
                q = sql.get_f('id', 'prop', f)
                sfilter = db.fetchvals(q)

            # Если в метаописании найдена инструкция склада по умолчанию,
            # то установить склад по умолчанию
            elif re.match(r'default=', val):
                t = real_translit(val[8:])
                self.whdef = db.fetchobject('prop', t, 'translit')

        # Ограничить список товаров их главным представлением
        kfilter.append('ps.pview = "%s"' % gvar.view.pview)
        if not cat:
            kfilter.append('ps.id_prop1 = %s' % gvar.cat.id)

        # Список строк итогового SQL-фильтра
        f = []

        # Если есть ограничение по складам товаров - добавить его
        if sfilter:
            f.append(sql.fin('s.id_store', sfilter))

        # Если есть ограничение по компонентному фильтру - добавить его
        if kfilter:
            q = sql.get_f('ps.id', 'prop_set ps', 
                kfilter + ['ps.id_product = s.id_product'])
            f.append(sql.exists(q))
            self.kfilter = kfilter

        return f

    def clear(self, ftext):
	"""Очистка наличия товаров на складе перед загрузкой
        новых данных о наличии"""

	# Получение идентификаторов товаров, данные о наличии которых
        # будут обновлятся
        f = self.parsefilter(ftext)    
        q = sql.get_f('DISTINCT s.id_product', 'store s', f)
        idl = db.fetchvals(q)
        pcnt = len(idl)
        if pcnt:
            log("Found %d products" % pcnt)
        else:
            log("No products found, nothing to clear!", M_WARN)
            return
    
	# Вывод 5-ти случайных товаров из того списка, данные о наличии
        # которых будут очищены
        log('----------------------------')
        imax = min(pcnt, 5)
        for i in xrange(imax):
            index = random.randint(0, pcnt - 1)
            product = Product(None, idl[index])
            log("Random product (%d of %d): %s" %
                (i + 1, imax, real_translit(product.name)))
        log('----------------------------')
        log('%d products will be deleted from store. Continue? (y/n)' % pcnt)

	# Подтверждение об удалении наличия (если требуется)
        if self.o.prompt:
            res = raw_input()
        else:
            res = "y"

	# Очистка наличия товаров из базы
        if res == 'y':
            idl = db.fetchvals(sql.get_f('id', 'store s', f))
            q = sql.delete('store', sql.fin('id', idl))
            db.execute(q)
            db.commit()
            log("Store records deleted")
        else:
            log("User abort, exiting...")
            sys.exit(0)
 
    def load_store(self, pdata):
	"""Загрузка единицы хранения товара из данных хэша pdata.
	Если единица товара создана/обновлена - возвращает True, иначе False
	"""

	# Поиск серийного номера товара в хэше (ошибочно назван partno)
	# Если нет серийного номера товара - выходим
        if 'partno2' in pdata:
            key = 'partno2'
        elif 'partno1' in pdata:
            key = 'partno1'
        else:
            return False

        partno = pdata[key]
        quantity = toint(pdata['quantity'])

	# Поиск объекта-склада, если не найден,
        # использовать склад по умолчанию
        if 'store'in pdata and pdata['store']:
            storeobj = db.fetchobject('prop', pdata['store'], 'translit')
        else:
            storeobj = self.whdef

	# Если нет информации о количестве товара для единицы хранения - выход
        if not quantity:
            return False

	# Поиск в базе идентификатора товара, если товар не найден - выход
        f = ['p.id = ps.id_product']
        f.append(key + ' = %s')
        f += self.kfilter
        q = sql.get_f('p.id', 'product p, prop_set ps', f)
        pid = db.fetchval(q, [partno])
        if pid == None:
            return False

	# Создание и сохранение единицы хранение товара
        store = Store(pdata)
        store.id_product = pid
        store.id_store   = storeobj.id
        store.quantity   = quantity

        store.save()

        return True

    def addprod(self, pdata):
        pid = self.getpid(pdata)
        if pid:
            pc.addtobuf('iface')

class ISAbstractExcel(IStore):
    """Абстрактный класс-загрузчик из Excel-таблицы. Структура таблицы
    должна подчинятся определенным правилам

    Правила Excel-файла
      - Вся информация хранится в первом листе
      - В ячейке 0,0 должно быть метаописание (склад по умолчанию, категория,
        фильтр) в виде текста store=<store>, cat=<category>, k[x]=<translit>.
        Если такого метаописания нет, оно должно быть определено в методе
        parseheader
      - В 1-й строке должны быть ячейки с названиями колонок:
            - partno1(2) - код товара
            - quantity - количество товара на складе
        Регистр игнорируется. Если таких названий нет - они должны быть 
        определены в методе parsenames
      - Сканирование файла идет слева-направо сверху вниз. Категория товара
        может быть переопределена в любой ячейке текстом cat=<code>.
    """

    def parseheader(self, header):
        """Виртуальный метод, пропускающий через себя заголовок таблицы,
         в котором содержатся доп. инструкции"""
         return header

    def parsenames(self, cx, name):
        """Виртуальный метод для перевода номера и названия колонок
         в ожидаемые названия"""
         return name

    def loadsource(self):
        """Разбор тела таблицы, создание хэш-массива с данными
        о наличие товаров"""

	# Поиск категории товара в тексте по ее коду
        def parsecat(text):
            mo = re.search('cat=([a-z0-9\-_]{3,})', real_translit(text.lower()))
            if mo:
                return mo.group(1)
            return None

        # Открываем таблицу
        book = xlrd.open_workbook(self.source)
        sh = book.sheet_by_index(0)
        
        # Получаем текст заголовка с метаописанием
        header = self.parseheader(sh.cell(0, 0).value)
        self.ifilter = header

        # Определение списка категорий товара
        names = []
        row = sh.row(1)
        old_pdata = None
        gvar.k = 0
        for cx in range(sh.ncols):
            value = row[cx].value.lower()
            value = self.parsenames(cx, value)
            names.append(value)
            mo = re.search(r'^k(\d)$', value)
            if mo:
                gvar.k = max(toint(mo.group(1)), gvar.k)

        # Сканирование таблицы
        start = 0
        self.idata = {}

        # Попытка извлечь категорию товара из метаописания
        cat = parsecat(header)

        # Сканирование по строкам
        for rx in range(start, sh.nrows):
            pdata = {}
            row = sh.row(rx)

            # Сканирование по столбцам
            for cx in range(sh.ncols):

                # Разбор текста ячейки
                key = names[cx]
                value = unicode(row[cx].value)
                cat = parsecat(value) or cat
                if not cat:
                    continue

                if value[-2:] == '.0':
                    value = value[:-2]
                if old_pdata and value == '-':
                    value = old_pdata[key]
                pdata[key] = value

            # Если категория не определена - пропуск
            if not cat:
                continue

            # Добавление информации о наличии товара в хэш
            if cat not in self.idata:
                self.idata[cat] = []

            self.idata[cat].append(pdata)

            old_pdata = pdata

    def getcats(self)     : return self.idata.keys()
    def getfilter(self)   : return self.ifilter
    def getdata(self, cat): return self.idata[cat]
    def getrows(self, cat): return len(self.idata[cat])

class ISDunlop(ISAbstractExcel):
    """Загрузка товара от поставщика моторезины Dunlop"""

    def parseheader(self, header):
        """Добавление метаописания, т.к. оно отсутствует в оригинальном файле"""
        return "default=whdunlop, clear=whdunlop, cat=rezina"

    def parsenames(self, cx, name):
        """Перенос колонок в ожидаемые согласно шаблону Excel-файла"""

        val = real_translit(name)
        if cx == 0:
            return "partno1"
        elif cx == 8:
            return "quantity"
        return name

    def getsource(self):
        """Обработка Excel-файла из почты"""

        # Удалить файл-источник по завершении работы
        self.clearsource = True

        # Имя временного файла для excel-таблицы
        fname = tempfile.mktemp(suffix = '.xls')

        # искать в почте письма от <отправитель> или от меня за последние
        # <N> дней с именем xls-вложения, начинающимся на ostatki или sklad
        res = readmail(<N>, "OR (FROM <отправитель>) (FROM <me>)",
            "(?i)(ostatki|sklad)(.*?)\.xls$")
        if res:
            writefile(fname, res)
            return fname
        return None

class ISMain(ISAbstractExcel):
    """Загрузка наличия товара из таблицы Google Docs"""
    def getsource(self):

        # Импорт модулей для работы с Google Docs
        import gdata.docs
        import gdata.docs.service
        import gdata.spreadsheet.service

        # Идентификатор документа в Google Docs
        EXCELID = "spreadsheet:<googleid>"

        # Удалить файл-источник по завершении работы
        self.clearsource = True

        # Имя временного файла для excel-таблицы
        fname = tempfile.mktemp(suffix = '.xls')
    
        # Подключение к Google Docs, получение Excel-документа
        gd_client = gdata.docs.service.DocsService()
        gd_client.ssl = True

        spreadsheets_client = gdata.spreadsheet.service.SpreadsheetsService()
        spreadsheets_client.ClientLogin(GUSER, GPASS)

        docs_auth_token = gd_client.GetClientLoginToken()
        gd_client.SetClientLoginToken(spreadsheets_client.GetClientLoginToken())

        # Экспорт таблицы во временный Excel-файл
        gd_client.Export(EXCELID, fname)
        # Reset DocList auth token
        gd_client.SetClientLoginToken(docs_auth_token) 
        return fname
 
class ISVlad(IStore):
    """Загрузка товара от поставщика <компания Владислав>

    Поставщик предоставляет данные о наличии товаров на нескольких своих
    складах в виде zip-архива dbf-таблицы. Интерфейс загружает эти данные,
    находя соответствия между кодами складов поставщика и объектами-складами,
    определенным в базе данных магазина
    """

    def getsource(self):
        """Скачивание архива с данными, извлечение dbf-структуры
        в переменную в памяти"""

        SITE = 'http://www.vladislav.ua/'
        URL1 = SITE + 'downloads.php'
        URL1r = '<iframe src="(.*?)"'
        URL2r = '<a\s+target=_blank\s+href="(.*?)"'

        # Чтение корневой HTML-страницы в переменную
        data = readurl(URL1)

        # Поиск ссылки на фрейм с ссылкой на файл.
        # Далеко запрятали ссылку на скачивание, змеи :)
        mo = re.search(URL1r, data)
        if mo:
            log(SITE + mo.group(1))

            # Чтение HTML-фрейма в переменную
            data = readurl(SITE + mo.group(1))

            # Поиск ссылки на zip-файл
            mo = re.search(URL2r, data)
            if mo:
                log(mo.group(1))

                # Скачивание zip-файла
                data = readurl(mo.group(1))

                # Распаковка в памяти
                z = zipfile.ZipFile(StringIO(data))
                data = z.read('base.dbf')

                # Возврат dbf-таблицы
                return StringIO(data)

        return None

    def loadsource(self):
        """Разбор dbf-файла с информацией о наличии товаров. 
        Также в базе данных магазина обновляются входящие цены товаров"""

        # Коды товарных групп (код = категория, комментарий, наценка)
        self.groups = {
            27462 : ['masla', 'Motul', 97.5],
            8757  : ['masla', 'NGK Spark plugs', 105],
            96498 : ['zvezdi', 'JT Sprockets', 107],
            99027 : ['zvezdi', 'Sunstar', 107],
            97364 : ['tsep', 'DID Chains', 100]
        }
        # Коды складов
        self.whmap = dict(
            KOL1 = 'whvlad-don',
            KOL2 = 'whvlad-dne',
            KOL3 = 'whvlad-kha',
            KOL4 = 'whvlad-kie',
            KOL5 = 'whvlad-lvi',
            KOL6 = 'whvlad-zap',
            KOL7 = 'whvlad-main')

        # Загрузка dbf-таблицы
        db = dbf.Dbf(self.source)
        groups = self.groups.keys()
        self.idata = {}

        # Проход по dbf-таблице
        for rec in db:
            if rec['KODGR'] in groups:

                # Определение категории товара, установка калибровочной наценки
                # входной цены для этой категории
                (cat, comment, kprice) = self.groups[rec['KODGR']]
                if cat not in self.idata:
                    self.idata[cat] = []

                # Создание словаря для объекта <товар>
                pdata = Storage(dict(id = rec['KOD'], keyfield = 'partno2'))

                # Загрузка объекта <товар>. Соответствующий объект в БД находится
                # классом Product автоматически
                prod = Product(None, pdata)

                # Обновление входной цены товара с учетом калибровочной наценки
                if prod.mode == classes.MOD_UPD:
                    price = '%.2f' % (rec['CENA'] * kprice / 100.0)
                    #print prod.id, prod.name, prod.price_out, price, prod.mode
                    prod.price_out  = price
                    prod.save(['price_out'])

                for (key, store) in self.whmap.iteritems():
                    val = rec[key]
                    if val:
                        if val == '*':
                            val = 10

                        # Загрузка объекта <единица хранения товара>
                        # для заполнения словаря pdata
                        pdata = Storage()
                        pdata.partno2  = rec['KOD']
                        pdata.quantity = toint(val)
                        pdata.store    = store
                        self.idata[cat].append(pdata)

    def getcats(self)     : return self.idata.keys()
    def getfilter(self)   : return 'clear=%s' % ';'.join(self.whmap.values())
    def getdata(self, cat): return self.idata[cat]
    def getrows(self, cat): return len(self.idata[cat])

# ----------------------------
# Список интерфейсов данных
# ----------------------------
interfaces = {
    'dunlop': ISDunlop,
    'vlad'  : ISVlad,
    'main'  : ISMain
}

# Запуск загрузчика - обновление данных о наличии товаров у поставщиков
StoreLoader()