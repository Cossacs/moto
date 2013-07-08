<?
$tidy = new tidy;
$config = array(
'indent' => true,
'output-html' => true,
'wrap' => 200);
$tidy->parseString($html, $config, 'utf8');
$tidy->cleanRepair();
$html = $tidy;
if (preg_match('/<body>\s*(.*)\s*<\/body>/msU', $html, $matches)) {
    $html = $matches[1];
}
print $html;
?>