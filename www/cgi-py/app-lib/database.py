# coding: utf-8
# ------------------------------------
# Database module
# ------------------------------------

import MySQLdb, web
import config, sql

from utils import *

EDB_CONNECT = 'DB: Connection error, "%s"'
EDB_EMPTY   = 'DB: Empty data'
EDB_DICKEY  = 'DB: wrong keyfield'
ESQL_ERROR  = 'DB: %s | Params: %s | %s'

MSQL_EXEC     = 1
MSQL_FETCHONE = 2
MSQL_FETCHALL = 3

INIT_COMMAND = 'SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED'

class DBRequest(object):
    def __init__(self):
        self.data   = None
        self.result = None
        self.description = None

class Database(object):
    def __getcon(self):    return self.__con   
          
    con    = property(__getcon)
    
    def __init__(self):
        self.__con     = None      
        self.__clearbuf()
        self.connect()
        
    def __clearbuf(self):        
        self.__batchsql = {}
        self.__newid    = {}
       
    def connect(self):
        try:
            self.__con  = MySQLdb.connect(
                db      = config.DB,
                host    = config.DB_HOST,
                user    = config.DB_USER,
                passwd  = config.DB_PASS,
                charset = 'utf8',
                init_command = INIT_COMMAND
                )
            log('DB: Connected to "%s@%s"' % (config.DB, config.DB_HOST))
        except Exception, e:
            log(EDB_CONNECT % e, M_ERR)
            raise e
                                              
    def fetchall(self, sql, params = []):
        request = self.execute(sql, params, MSQL_FETCHALL)
        return request.data
                
    def fetchrow(self, sql, params = []):
        request = self.execute(sql, params, MSQL_FETCHONE)
        return request.data
          
    def fetchdic(self, sql, keyfield = 'id', params = []):
        data = self.fetchobj(sql, params)
        if not data:
            return None
        if keyfield not in data[0]:
            log(EDB_DICKEY, M_ERR)
            raise Exception(EDB_DICKEY)
        result = {}
        for row in data:
            result[row[keyfield]] = row
        return result

    def fetchobj(self, sql, params = []):
        request = self.execute(sql, params, MSQL_FETCHALL)
        if request.data == None: 
            return None
        names = [x[0].lower() for x in request.description]
        res = [Storage(dict(zip(names, x))) for x in request.data]
        return res
    
    def fetchval(self, sql, params = []):
        result = self.fetchrow(sql, params)
        if result == None:
            return None
        else:
            return result[0]
        
    def fetchvals(self, sql, params = []):
        return (map(lambda s: s[0], self.fetchall(sql, params)))

    def fetchrowdic(self, sql, params = []):
        request = self.execute(sql, params, MSQL_FETCHONE)
        if request.data == None:
            return None
        res = {}
        for i in xrange( 0, len( request.data ) ):
            res[request.description[i][0].lower()] = request.data[i]
        return res

    def fetchrowobj(self, sql, params = []):
        request = self.execute(sql, params, MSQL_FETCHONE)
        if request.data == None: 
            return None
        names = [x[0].lower() for x in request.description]
        res = Storage(dict(zip(names, request.data)))
        return res
    
    def fetchdicvals(self, sql, keyfield, 
                     uni    = False, 
                     params = []):
        result = self.fetchdic(sql, keyfield, uni, params)
        for key in result.keys():
            result[key] = result[key][0]
        return result

    def fetchobject(self, table, id, field = 'id'):
        if type(table) == list:
            t = table[0]
            f = map(lambda t2: '%s.%s = %s.%s' % (t, field, t2, field), table[1:])
            f.append('%s.%s = %s' % (t, field, '%s'))            
            q = sql.get_f(['*'], sql.joiner(table), f)
        else:
            q = sql.get_fval(['*'], table, field)
        return self.fetchrowobj(q, [id])
    
    def execute(self, sql, params = [], mode = MSQL_EXEC, commit = False):
        log.t_trace('start')
        if config.DEBUG:
            log('---------------------')
            log('%s | Params: %s' % (sql, params))
            log('---------------------')

        result = None
        def _execute():
#            try:
                if mode == MSQL_EXEC:
                    cursor.execute(query, params)
                    return None
                else:
                    return cursor.execute(query, params)
#            except MySQLdb.DatabaseError, e:
#                self.connect()
#                cursor.execute(query, params)

        cursor = self.__con.cursor()
        query = sql
        try:
            if islist(sql):
                for query in sql:
                    result = _execute()
            else:
                result = _execute()
        except MySQLdb.DatabaseError, e:
            p = str(params)[:1000]
            log(ESQL_ERROR % (query, p, e), M_ERR)
            raise e

        request = DBRequest()
        request.description = cursor.description
        request.result = result

        if mode == MSQL_EXEC:
            if commit:
                self.__con.commit()
        elif mode == MSQL_FETCHONE:
            request.data = cursor.fetchone()
        elif mode == MSQL_FETCHALL:
            request.data = cursor.fetchall()
        cursor.close()

        log.t_trace('end')
        return request

    def call(self, procname, params = [], commit = False):
        q = 'CALL %s(%s)' % (procname, sql.f(params))
        self.execute(q, params)
        if commit:
            self.commit()

    def commit(self):
        self.__con.commit()

    def rollback(self):
        self.__con.rollback()
       
    def get_fields(self, table):
        return map(
            lambda s: s.strip().lower(),
            self.fetchvals(sql.tabfields, [table]))

    def istable(self, table):
        q = 'SHOW FULL TABLES LIKE %s'
        if self.fetchval(q, [table]):
            return True
        return False

    def droptable(self, table):
        q = "DROP TABLE %s" % table
        self.execute(q)

    def pgbytr(self, translit):
        return self.fetchval(sql.get('getpgbytr(%s)'), [translit])

    def propbytr(self, translit):
        return self.fetchval(sql.get('getpropbytr(%s)'), [translit])