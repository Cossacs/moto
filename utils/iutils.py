# coding:  utf-8
# --------------------------------------------
# HEADER: Load Utils Configuration
# Created by: Cossacs, 2011
# --------------------------------------------
#
# Вспомогательная библиотека для скриптов импорта:
#  - Загрузчика наличия товаров на складах
#  - Загрузчика новых товаров

# Путь к модулям движка сайта
KERNEL    = '/home/motofortuna/www/cgi-py/app-lib'

GUSER = "<google_user>@gmail.com"
GPASS = "<google_pass>"
GSERVER_IMAP = "imap.gmail.com"
GSERVER_SMTP = "smtp.gmail.com"

#__all__ = ["gvar", "db", "FakeDoc", "DBObject", "sendmail"]

import sys
sys.path.append(KERNEL)
from utils import *
from optparse import OptionParser
import os, web, kernel, database, classes, tidy, re, utils
import email, smtplib, imaplib

re_body = re.compile(r'<body>(.*?)</body>', re.M + re.S)
log.quiet = False

class FakeDoc(object):
    """Документ-пустышка, необходим из-за особенностей архитектуры"""
    def __init__(self):
        self.site = gvar.site
        self.db   = gvar.site.db

class DBObject(classes.DBObject):
    """Родительский класс для объекта базы данных
    (товара, категории, свойства товара и т.п.)"""
    def __init__(self, pdata, data = None):
        self.pdata = pdata
        if not data:
            data = Storage()
        classes.DBObject.__init__(self, gvar.doc, data)

    def NotCreated(self):
        pass

    def save(self, afields = None):
        classes.DBObject.save(self, afields)

    def error(self, message):
        raise Exception(message)

class GVar(Storage):
    """Класс, содержащий в себе движок, некоторые настройки
    и вспомогательные функции"""
    def __init__(self):
        self.basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
          'import')

        # Движок сайта
        self.site    = kernel.site

        # Парсер опций командной строки
        self.parser = OptionParser()

    def htmlrepair(self, text):
        """Восстановление поврежденного/некорректного HTML"""

        options = dict(output_html = True, indent = True, wrap = 200,
            char_encoding = "utf8")
        text = text.encode("utf8")
        res = tidy.parseString(text, **options)
        res = unicode(str(res), "utf8")
        mo = re_body.search(res)
        if mo:
            lines = []
            for line in mo.group(1).splitlines():
                if line.strip():
                    lines.append(line[4:])
            res = "\n".join(lines)
        return res

    def singledb(self):
        """Подмена пула подключений к БД на единственное соединение с БД"""
        def shlock(): return db
        def shunlock(): pass

        self.db      = db
        self.site.db = db
        db.shlock    = shlock
        db.shunlock  = shunlock

def readmail(days, criteria, fpattern):
    """Извлечение аттачмената из первого подходящего письма 
    в папке INBOX почтового ящика Google Mail

    Поиск происходит в письмах, отсортированных по дате в реверсном порядке.
    Выбирается первое письмо, подходящее под вхоящие параметры. Опции:
      days - максимальный возраст письма, в днях
      criteria - фильтр, согласно протоколу IMAP
      fpattern - регулярное выражение, шаблон имени файла во вложении"""
        
    def getheader(header_text, default = "ascii"):
        if not isstr(header_text):
            return header_text

        headers = email.Header.decode_header(header_text)
        header_sections = [unicode(text, charset or default)
                       for text, charset in headers]
        return u"".join(header_sections)

    res = []

    m = imaplib.IMAP4_SSL(GSERVER_IMAP, 993)
    m.login(GUSER, GPASS)

    since = datetime.datetime.now() - datetime.timedelta(days = days)
    since = since.strftime("%d-%b-%Y")
    searchString = "(SINCE %s) " % since + criteria

    m.select("INBOX")
    resp, items = m.search(None, searchString)
    items = items[0].split()
    for emailid in items:
        resp, data = m.fetch(emailid, "(RFC822)")
        email_body = data[0][1]
        mail = email.message_from_string(email_body)
        if mail.get_content_maintype() != 'multipart':
            continue


        date = time.mktime(email.Utils.parsedate(mail["Date"]))

        for part in mail.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            filename = getheader(part.get_filename())
            counter = 1
            if not filename:
                filename = 'part-%03d%s' % (counter, 'bin')
                counter += 1

            filename = real_translit(filename)
            if re.search(fpattern, filename):
                data = part.get_payload(decode = True)
                res.append((date, filename, data))

    if res:
        data = sorted(res, key = lambda x: x[0], reverse = True)[0]
        return data[2]

    return None

def sendmail(subject, text, files = [], send_from = GUSER,
    send_to = [config.EMAIL]):
    """Отправка письма на почтовый ящик"""

    assert type(send_to) == list
    assert type(files)   == list

    msg = email.MIMEMultipart.MIMEMultipart()
    msg['From']    = send_from
    msg['To']      = email.Utils.COMMASPACE.join(send_to)
    msg['Date']    = email.Utils.formatdate(localtime = True)
    msg['Subject'] = subject

    msg.attach(email.MIMEText.MIMEText(text, _charset = "utf-8"))

    for f in files:
        part = email.MIMEBase.MIMEBase('application', "octet-stream")
        part.set_payload(open(file,"rb").read())
        email.Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' %
            os.path.basename(f))
        msg.attach(part)

    server = smtplib.SMTP_SSL(GSERVER_SMTP, 465)
    server.login(GUSER, GPASS)
    server.sendmail(send_from, send_to, msg.as_string())
    server.close()

gvar = GVar()
db = gvar.site.db