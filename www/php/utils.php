<?php

function real_translit($str) {

    $transtable = array(
        'А' => 'A',  'Б' => 'B',  'В' => 'V',    'Г' => 'G',  'Д' => 'D',  'Е' => 'E',
        'Ё' => 'Yo', 'Ж' => 'Zh', 'З' => 'Z',    'И' => 'I',  'Й' => 'Y',  'К' => 'K',
        'Л' => 'L',  'М' => 'M',  'Н' => 'N',    'О' => 'O',  'П' => 'P',  'Р' => 'R',
        'С' => 'S',  'Т' => 'T',  'У' => 'U',    'Ф' => 'F',  'Х' => 'H',  'Ц' => 'Ts',
        'Ч' => 'Ch', 'Ш' => 'Sh', 'Щ' => 'Shch', 'Ъ' => '',   'Ы' => 'I',  'Ь' => '',
        'Э' => 'E',  'Ю' => 'Yu', 'Я' => 'Ya',   'а' => 'a',  'б' => 'b',  'в' => 'v',
        'г' => 'g',  'д' => 'd',  'е' => 'e',    'ё' => 'yo', 'ж' => 'zh', 'з' => 'z',
        'и' => 'i',  'й' => 'y',  'к' => 'k',    'л' => 'l',  'м' => 'm',  'н' => 'n',
        'о' => 'o',  'п' => 'p',  'р' => 'r',    'с' => 's',  'т' => 't',  'у' => 'u',
        'ф' => 'f',  'х' => 'h',  'ц' => 'ts',   'ч' => 'ch', 'ш' => 'sh', 'щ' => 'shch',
        'ъ' => '',   'ы' => 'i',  'ь' => '',     'э' => 'e',  'ю' => 'yu', 'я' => 'ya');

    return strtr($str, $transtable);
}

# Функция возвращает отформатированную строку, готовую для записи
# в поле translit
function translit($str) {
    $str = strtolower(real_translit($str));
    if (preg_match_all("/[a-z0-9]+/", $str, $matches)) {
        $str = implode("-", $matches[0]);
        return $str;
    }
    return NULL;
}

# Функция разбивает текст свойства на массив из двух элементов:
#  1 - имя свойства
#  2 - полное имя свойства (NULL если нет)
function prop_split($text) {
    $text = trim($text);
    $res = preg_split('/\s*\|\s*/', $text, 2);
    if (count($res) == 1) $res[2] = NULL;
    return $res;
}

# Функция возвращает значение crc для картинки. На входе:
#   props - массив всех текстовых значений свойств товара
#   index - номер картинки по порядку, не указывается для малого изображения товара
function image_crc($props, $index = NULL) {
    $s = '';
    foreach ($props as $prop) $s .= translit($prop);
    if (!$s) return NULL;
    if ($index) $s .= $index;
    return ($s) ? crc32($s) : NULL;
}

# Функция расшифровывает текст и возвращает массив из двух элементов:
#  1 - сумма
#  2 - код валюты
function product_price($text) {
    $text = strtolower(real_translit($text));
    $text = str_replace(' ', '', $text);
    if (preg_match('/^(\d+)[\.,]?(\d+)?(.*)/', $text, $matches)) {
        $val = $matches[1];
        if ($matches[2]) $val .= ".".$matches[2];
        $res[0] = floatval($val);

        if (preg_match('/grn|uah|hrn|griv/', $matches[3])) {
            $cur = 'UAH';
        } elseif (preg_match('/e/', $matches[3])) {
            $cur = 'EUR'; 
        } elseif (preg_match('/usd|dol|baks|zel|\$/', $matches[3])) {
            $cur = 'USD';
        }
        if (($cur) && ($val)) return array($val, $cur);
    }
    return NULL;
}

# Функция разбивает текст описания товара на массив из двух элементов:
#  1 - заголовок
#  2 - описание товара
function product_note($text) {
    $text = trim($text);
    $res = preg_split('/\s*[\|\n]\s*/', $text, 2);
    return (count($res) == 2) ? $res : NULL;
}

# Функция разбивает текст с ссылками и возвращает массив ссылок
function product_images($text) {
    $text = trim($text);
    $res = preg_split('/[\s\|\n]+/', $text);
    return $res;
}

# Пример 1. Обработка в translit
#echo translit("Оригинальные запчасти Honda");

# Пример 2. Обработка в translit
#print_r(prop_split("1л|1 литр"));

# Пример 3. Подсчет CRC для image
#$props = array("Масла", "Ipone", "Full Power Katana", "10w50", "4T", "1л");
#echo image_crc($props, 1);

# Пример 4. Определение суммы и валюты
#print_r(product_price('50 998,4 евро'));

# Пример 5. Описание товара
#$text = 'Здесь у нас заголовок
#   а тут собственно текст';
#print_r(product_note($text));

# Пример 6. Список ссылок на изображение
#$text =  'http://www.bikebandit.com/motul.gif  |  c:\temp\ipone.jpg';
#print_r(product_images($text));

?>