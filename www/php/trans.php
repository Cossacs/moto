<?php

function throw_ex($message) {
    throw new Exception($message);
}

function query($sql, $params = null) {
    $q = $sql;
    if ($params) {
        foreach ($params as $param) {
            $p[] = '"'.mysql_real_escape_string($param).'"';
        }
        $q = vsprintf($sql, $p);
    }
    $res = mysql_query($q) or throw_ex(mysql_error());
    return $res;
}

function getnewid($table) {
    $res = query('SELECT getnewid(%s)', array($table));
    $row = mysql_fetch_row($res);
    return $row[0];
}

# Подключение к базе данных
mysql_connect(localhost,"USER","PASS");
mysql_select_db("motofortuna");
mysql_set_charset("utf8");

# Создаем для примера таблицу table1 (parent) и table2 (child)
query("CREATE TEMPORARY TABLE table1 (id INT UNSIGNED, name CHAR(60))");
query("CREATE TEMPORARY TABLE table2 (id INT UNSIGNED, id_parent INT UNSIGNED)");

# Собственно, пример
query('START TRANSACTION');
try {
    $id_parent = getnewid('table1');
    $params = array($id_parent, 'Водка "козлячая"');
    query("INSERT INTO table1(id, name) VALUES(%s, %s)", $params);

    $id = getnewid('table2');
    $params = array($id, $id_parent);
    query("INSERT INTO table2(id, id_parent) VALUES(%s, %s)", $params);

#   Пример ошибки: неверный SQL запрос. В таблицы table1 и table2 ничего не добавится
#
#   $params = array($id, $id_parent);
#   query("INSERT INTOO table2(id_parent, id) VALUES(%s, %s)", $params);

    query('COMMIT');
} catch (Exception $e) {
    query('ROLLBACK');
    $error = $e->getMessage();
    # Делаем что-то с текстом ошибки $error
    echo "В процессе пакетного добавления случилась неприятность:<p><i>".$error."</i>";
}

echo "<br>Table 1 data: ";
$res = query("SELECT * FROM table1");
print_r(mysql_fetch_assoc($res));

echo "<br>Table 2 data: ";
$res = query("SELECT * FROM table2");
print_r(mysql_fetch_assoc($res));

?>