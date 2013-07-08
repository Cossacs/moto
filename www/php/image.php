<?php

function img_name2typ($name) {
    $img_types = array(
      'gif'  => 'G',
      'jpg'  => 'J',
      'jpeg' => 'J',
      'png'  => 'P',
      'bmp'  => 'B'
    );
    $name = strtolower($name);
    if (preg_match("/\.([a-z0-9]+)$/", $name, $matches)) {
        $ext = $matches[1];
        return $img_types[$ext];
    }
    return NULL;
}

print img_name2typ('Vasya.jPG2');

?>