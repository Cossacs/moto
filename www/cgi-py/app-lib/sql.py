# coding: utf-8
# ------------------------------------
# SQL Functions/Constants module
# ------------------------------------

import types

def joiner(data, sep = ',\n  ', fmt = '%s'):
    if isinstance(fmt, types.FunctionType):
        func = fmt
    else:
        func = lambda s: fmt % s

    if type(data) == list:
        return sep.join(map(func, data))
    else:
        return func(data)

def get(fields, tables = None):
    fields = joiner(fields)
    res = "SELECT\n  %s" % fields
    if tables:
        tables = joiner(tables)
        res = res + "\nFROM\n  %s" % tables
    return res
        
def get_f(fields, tables, filter):
    fields = joiner(fields)
    tables = joiner(tables)
    filter = fand(filter)
    res = 'SELECT\n  %s\nFROM\n  %s' % (fields, tables)
    if filter:
        res += '\nWHERE\n  %s' % filter
    return res
        
def get_fval(fields, tables, key):
    fields = joiner(fields)
    tables = joiner(tables)
    return "SELECT\n  %s\nFROM\n  %s\nWHERE\n  %s = %s" % (fields, tables, key, '%s')
      
def update(fields, table, key = None, filter = None):
    fields = joiner(fields, ', \n', lambda s: s + ' = %s')
    res = 'UPDATE %s SET %s' % (table, fields)
    if key != None:
        res += ' WHERE %s = %s' % (key, '%s')
    elif filter != None:
        res += ' WHERE %s' % fand(filter)
    return res

def insert(fields, table):
    values = f(fields)
    fields = joiner(fields)
    return 'INSERT INTO %s(\n  %s\n) VALUES (%s)' % (table, fields, values)

def delete(table, filter):
    res = 'DELETE FROM ' + table
    if filter:
        if type(filter) != str:
            filter = fand(filter)
        res += ' WHERE %s' % filter
    return res

def f(keys):
    return joiner(keys, ', ', lambda s: '%s')

def fand(filter):
    return joiner(filter, "\n  AND ", '(%s)')

def f_or(filter):
    return joiner(filter, "\n    OR ", '(%s)')

def fin(field, values, param = False):
    if param:
        values = ['%s'] * len(values)
    if len(values) == 1:
        return '%s = %s' % (field, values[0])
    return field + ' IN (%s)' % joiner(values, ', ')

def fvals(filter):
    return map(lambda s: '%s = %s' % s, filter.iteritems())

def order(query, order):
    if type(order) == list:
        order = joiner(order, fmt = '%s %s')
    return query + "\nORDER BY\n  " + order

def group(query, fields):
    return query + "\nGROUP BY\n  " + joiner(fields)

def limit(query, offset, count):
    return query + "\nLIMIT\n  %d, %d"  % (offset, count)

def index(fields, table, name = None):
    if not name:
        name = "i" + "".join(map(lambda s: s[:2] + s[-2:], fields))    
    return "CREATE INDEX %s ON %s (%s)" % (name, table, ", ".join(fields))

def drop(table):
    return "DROP TABLE IF EXISTS %s" % table

def exists(query):
    return 'EXISTS (%s)' % query

def tempname(table):
    return "tmp_" + table

def temp(src, table, dst = None, ifields = []):
    table = tempname(table)
    q = [drop(table)]
    q.append("CREATE TEMPORARY TABLE %s ENGINE = MEMORY\n%s" % (table, src))
    if ifields:
        q.append(index(ifields, table))
    if dst:
        q.append(dst % table)
    return q

def indexorder(fields):
    return map(lambda s: s[0], fields)

def union(qlist):
    return "\nUNION\n".join(qlist)