moto
====

Пример движка интернет-магазина на Python (демо - moto.gyrolab.net), который запущен
на одной виртуальной машине t1.micro в облаке Amazon EC2 (регион US West) под управлением
Linux Debian 6.0 "Squeeze".

Описание структуры сайта - http://moto.gyrolab.net/articles/ustroystvo-sayta.html


Код слабо документированы, для примера Python-кода я добавил комментарии в скрипт,
обновляющий наличие товаров. Скрипт использует движок сайта:

 - istore.py - основной скрипт
 - iutils.py - общий функционал для скриптов, исползующих движок сайта
 
Исходники движка на Python:

 - www/cgi-py/app.wsgi - главный файл приложения
 - www/cgi-py/app-lib/classes.py - простая ORM сайта
 - www/cgi-py/app-lib/config.py - базовые настройки сайта
 - www/cgi-py/app-lib/const.py - основные константы
 - www/cgi-py/app-lib/database.py - библиотека для работы с БД
 - www/cgi-py/app-lib/debugmonitor.py - для режима отладки (на production сервере выключен)
 - www/cgi-py/app-lib/interface.py - интерфейсы страниц
 - www/cgi-py/app-lib/kernel.py - ядро сайта: пулы обработчиков, очереди, базовые классы,
   AJAX-функционал, кэш, Cron и т.п.
 - www/cgi-py/app-lib/search.py - библиотека поиска
 - www/cgi-py/app-lib/sql.py - функции для создания SQL-запросов
 - www/cgi-py/app-lib/utils.py - вспомогательные функции, логгер
