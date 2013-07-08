# coding: utf-8
# --------------------------------------------
# HEADER: Application constants
# --------------------------------------------

MOD_IMAGE   = 'image'
MOD_CATALOG = 'catalog'
MOD_MAIN    = 'main'
MOD_STATIC  = 'info'
MOD_LIB     = 'lib'
MOD_ARTICLE = 'articles'
MOD_PROP    = 'prop'

DEFAULT_EXT   = 'html'
DEFAULT_MODS = [MOD_MAIN, MOD_CATALOG]
ROOT_MODS    = [MOD_MAIN, MOD_ARTICLE]
DEFAULT_PVIEW = 'S'

PRODUCT_URL_LEN = 2
IMAGE_URL_LEN   = PRODUCT_URL_LEN + 2

LEX_MAIN     = u'Главная'
LEX_ALL      = u'Все'
LEX_ARTICLES = u'Статьи'
LEX_PARTNO   = u'Артикул'

MSG_DESC       = u'Магазин Мофортуна - расходники, экипировка, запчасти для мотоциклов'
MSG_EMPTY_PROD = u'Товары не найдены'

SYS_DOCOBJ_ID = 'i%d'

AJAX_LINK  = "gethax({%s})"
AJAX_REPLY = "<!-- :ax:%s:begin: //-->\n%s\n<!-- :ax:%s:end: //-->\n"
AJAX_BLOCK = "<div id='%s'>\n%s\n</div>\n"
AJAX_MODEL = """
  <script type="text/javascript">
    SRAX.Model2Blocks['ilist'] = {%s};
    var ajax_url    = '%s';
    var ajax_tree   = '%s';
    var ajax_lastid = '%s';
  </script>
"""

IMAGE_TYPES = [
  ('G', 'gif'),
  ('J', 'jpg'),
  ('J', 'jpeg'),
  ('P', 'png'),
  ('B', 'bmp')
]

SITE_MAP = {
    MOD_STATIC: {
        'about'  : u'Про нас',
        'buy'    : u'Как купить у нас товар',
        'zakaz'  : u'Товары под заказ из США или Англии',
        'contact': u'Контактная информация'
    },
    MOD_LIB: {
        'order'  : u'Мой заказ',
        'news'   : u'Новости',
        'ichain' : u'Подбор размера цепи'
    }
}

PRICE_FORMAT = "<div class='price%s'><div>%s %s</div><div class='price_hint'>%s%s</div></div>"

SYS_TRANSTABLE = {
     u'А':u'A',  u'Б':u'B',  u'В':u'V',    u'Г':u'G',  u'Д':u'D',  u'Е':u'E',
     u'Ё':u'Yo', u'Ж':u'Zh', u'З':u'Z',    u'И':u'I',  u'Й':u'Y',  u'К':u'K',
     u'Л':u'L',  u'М':u'M',  u'Н':u'N',    u'О':u'O',  u'П':u'P',  u'Р':u'R',
     u'С':u'S',  u'Т':u'T',  u'У':u'U',    u'Ф':u'F',  u'Х':u'H',  u'Ц':u'Ts',
     u'Ч':u'Ch', u'Ш':u'Sh', u'Щ':u'Shch', u'Ъ':u'',   u'Ы':u'I',  u'Ь':u'',
     u'Э':u'E',  u'Ю':u'Yu', u'Я':u'Ya',   u'а':u'a',  u'б':u'b',  u'в':u'v',
     u'г':u'g',  u'д':u'd',  u'е':u'e',    u'ё':u'e',  u'ж':u'zh', u'з':u'z',
     u'и':u'i',  u'й':u'y',  u'к':u'k',    u'л':u'l',  u'м':u'm',  u'н':u'n',
     u'о':u'o',  u'п':u'p',  u'р':u'r',    u'с':u's',  u'т':u't',  u'у':u'u',
     u'ф':u'f',  u'х':u'h',  u'ц':u'ts',   u'ч':u'ch', u'ш':u'sh', u'щ':u'shch',
     u'ъ':u'',   u'ы':u'i',  u'ь':u'',     u'э':u'e',  u'ю':u'yu', u'я':u'ya'}

MEM_SEARCH = 'mem_prop_set'
SQL_SEARCH = """
    TRUNCATE TABLE %s;
    ALTER TABLE %s ENGINE=MEMORY;
    INSERT INTO %s
    SELECT
      id_product, pview,
      id_prop1, id_prop2, id_prop3, id_prop4, id_prop5, id_prop6, id_prop7, id_prop8
    FROM prop_set""" % (MEM_SEARCH, MEM_SEARCH, MEM_SEARCH)