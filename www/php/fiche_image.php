<?php

$DB      = "<db>";
$DB_USER = "<dbuser>";
$DB_PASS = "<dbpass>";

function query($sql, $params = null) {
    $q = $sql;
    if ($params) {
        foreach ($params as $param) {
            $p[] = '"'.mysql_real_escape_string($param).'"';
        }
        $q = vsprintf($sql, $p);
    }
    $res = mysql_query($q) or die(mysql_error());
    return $res;
}

function getimage($DB, $DB_USER, $DB_PASS, $table) {
    mysql_connect(localhost, $DB_USER, $DB_PASS);
    mysql_select_db($DB);

    $query = "SELECT size, type, image FROM $table WHERE id = %s";

    $result = query($query, array($_REQUEST["id"]));
    if (mysql_numrows($result)) {
        $row = mysql_fetch_row($result);
        $size = $row[0];
        $type = $row[1];
        $data = $row[2];

        header("Content-Length: $size");
        header("Content-Type: image/gif");
        echo $data;
    }
    #mysql_close();
}



switch($_REQUEST["size"])
{
    case "full":
        getimage($DB, $DB_USER, $DB_PASS, "fiche_image");
        break;
    case "preview":
        getimage($DB, $DB_USER, $DB_PASS, "fiche_image480");
        break;
    case "thumb":
        getimage($DB, $DB_USER, $DB_PASS, "fiche_image100");
        break;
}


?>