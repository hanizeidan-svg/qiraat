<?php
declare(strict_types=1);

require __DIR__ . '/../src/bootstrap.php';
require __DIR__ . '/../src/filters.php';

const PAGES = ['home', 'qiraat', 'jadwal', 'masail', 'masala', 'matn', 'qita', 'report', 'issues', 'issue', 'login', 'logout', 'users', 'export'];
const PUBLIC_PAGES = ['login'];

$page = $_GET['p'] ?? 'home';
if (!in_array($page, PAGES, true)) { http_response_code(404); $page = 'home'; }
if (!cfg('public_read') && !in_array($page, PUBLIC_PAGES, true)) require_login();

try {
    ob_start();
    $title = '';
    require __DIR__ . "/../src/pages/$page.php";   // may exit early (redirect / download)
    $body = ob_get_clean();
} catch (Throwable $e) {
    ob_end_clean();
    http_response_code(500);
    error_log((string)$e);
    $title = 'خطأ';
    $body = '<div class="flash err">' . h($e->getMessage()) . '</div>';
}
require __DIR__ . '/../src/layout.php';
