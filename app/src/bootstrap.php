<?php
declare(strict_types=1);

const APP_ROOT = __DIR__ . '/..';

$GLOBALS['config'] = require (is_file(APP_ROOT . '/config.php') ? APP_ROOT . '/config.php' : APP_ROOT . '/config.example.php');

function cfg(string $key): mixed { return $GLOBALS['config'][$key] ?? null; }

if (PHP_SAPI !== 'cli' && session_status() === PHP_SESSION_NONE) {
    session_set_cookie_params(['httponly' => true, 'samesite' => 'Lax', 'secure' => !empty($_SERVER['HTTPS'])]);
    session_name('qiraat');
    session_start();
}

// ───────── databases ─────────
function content(): PDO
{
    static $pdo;
    if (!$pdo) {
        $path = cfg('content_db');
        if (!is_file($path)) throw new RuntimeException("قاعدة المحتوى غير موجودة: $path — شغّل python scripts/build_masail.py");
        $pdo = new PDO('sqlite:' . $path, null, null, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::SQLITE_ATTR_OPEN_FLAGS => PDO::SQLITE_OPEN_READONLY,
        ]);
    }
    return $pdo;
}

function reviews(): PDO
{
    static $pdo;
    if (!$pdo) {
        $path = cfg('reviews_db');
        if (!is_dir(dirname($path))) mkdir(dirname($path), 0775, true);
        $pdo = new PDO('sqlite:' . $path, null, null, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);
        $pdo->exec('PRAGMA foreign_keys = ON; PRAGMA journal_mode = WAL;');
        $pdo->exec(file_get_contents(APP_ROOT . '/sql/reviews.sql'));
        $cols = array_column($pdo->query('PRAGMA table_info(issues)')->fetchAll(), 'name');   // upgrade older DBs
        if (!in_array('resolution_source', $cols, true)) $pdo->exec('ALTER TABLE issues ADD COLUMN resolution_source TEXT');
    }
    return $pdo;
}

function q(PDO $db, string $sql, array $params = []): PDOStatement
{
    $st = $db->prepare($sql);
    $st->execute($params);
    return $st;
}

function meta(string $key): string
{
    static $meta;
    $meta ??= q(content(), 'SELECT key, value FROM meta')->fetchAll(PDO::FETCH_KEY_PAIR);
    return $meta[$key] ?? '';
}

/** @return array<string,array{qari:string,ord:int}> rawi => info, in canonical order */
function rawis(): array
{
    static $r;
    if ($r === null) {
        $r = [];
        foreach (q(content(), 'SELECT name, qari, ord FROM rawis ORDER BY ord') as $row) $r[$row['name']] = $row;
    }
    return $r;
}

/** @return array<string,string[]> qari => [rawi, rawi] */
function qurra(): array
{
    $out = [];
    foreach (rawis() as $name => $row) $out[$row['qari']][] = $name;
    return $out;
}

// ───────── helpers ─────────
function h(?string $s): string { return htmlspecialchars((string)$s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }

/** Strip tashkeel and unify letter forms (mirror of plain() in build_masail.py). */
function plain_ar(string $t): string
{
    $t = str_replace(['ٱ', "\u{0670}"], 'ا', $t);
    $t = preg_replace('/[\x{0610}-\x{061A}\x{064B}-\x{065F}\x{06D6}-\x{06ED}\x{0640}\x{FEFF}]/u', '', $t);
    $t = preg_replace('/[إأآ]/u', 'ا', $t);
    return str_replace('ى', 'ي', $t);
}

/** Name whole qurra when both rawis are present (mirror of names_for in build_masail.py). */
function names_for(array $rs): string
{
    if (count($rs) === count(rawis())) return 'الجميع';
    $names = [];
    $left = $rs;
    foreach (qurra() as $qari => $pair) {
        if (!array_diff($pair, $left)) {
            $names[] = $qari;
            $left = array_values(array_diff($left, $pair));
        }
    }
    return implode('، ', array_merge($names, $left));
}

function url(array $params = [], bool $keep = false): string
{
    $p = $keep ? array_merge($_GET, $params) : $params;
    $p = array_filter($p, fn($v) => $v !== null && $v !== '' && $v !== []);
    return 'index.php' . ($p ? '?' . http_build_query($p) : '');
}

function redirect(string $to): never { header('Location: ' . $to); exit; }

function flash(?string $msg = null, string $kind = 'ok'): array
{
    if ($msg !== null) { $_SESSION['flash'][] = [$kind, $msg]; return []; }
    $f = $_SESSION['flash'] ?? [];
    unset($_SESSION['flash']);
    return $f;
}

// ───────── auth & CSRF ─────────
function user(): ?array
{
    static $u = false;
    if ($u === false) {
        $u = null;
        if (!empty($_SESSION['uid'])) {
            $u = q(reviews(), 'SELECT * FROM users WHERE id = ? AND active = 1', [$_SESSION['uid']])->fetch() ?: null;
        }
    }
    return $u;
}

function is_admin(): bool { return (user()['role'] ?? '') === 'admin'; }

function require_login(): void
{
    if (!user()) { flash('يلزم تسجيل الدخول.', 'err'); redirect(url(['p' => 'login', 'next' => $_SERVER['REQUEST_URI'] ?? ''])); }
}

function require_admin(): void
{
    require_login();
    if (!is_admin()) { http_response_code(403); exit('غير مسموح.'); }
}

function csrf_token(): string { return $_SESSION['csrf'] ??= bin2hex(random_bytes(16)); }
function csrf_field(): string { return '<input type="hidden" name="csrf" value="' . csrf_token() . '">'; }
function csrf_check(): void
{
    if (!hash_equals($_SESSION['csrf'] ?? '', (string)($_POST['csrf'] ?? ''))) { http_response_code(400); exit('رمز الحماية غير صالح، أعد تحميل الصفحة.'); }
}

// ───────── review targets ─────────
const ISSUE_STATUS = ['open' => 'مفتوحة', 'accepted' => 'مقبولة', 'rejected' => 'مرفوضة', 'applied' => 'طُبِّقت'];
const TARGET_TYPES = ['masala' => 'مسألة', 'reading' => 'قراءة', 'mawdi' => 'موضع', 'qiraa' => 'قراءة راوٍ في موضع', 'bayt' => 'بيت من المتن', 'general' => 'ملاحظة عامة'];
const TARGET_FIELDS = [
    'masala'  => ['kalima' => 'الكلمة', 'qawl' => 'قول الشاطبي', 'rumuz' => 'فك الرموز', 'natija' => 'النتيجة', 'nitaq' => 'النطاق', 'abyat' => 'أرقام الأبيات', 'note' => 'الملاحظة', 'missing_mawdi' => 'موضع ناقص', 'other' => 'أخرى'],
    'reading' => ['by_text' => 'أصحاب القراءة', 'lafz' => 'اللفظ', 'wasf' => 'الأداء', 'hal' => 'الحال', 'dalil' => 'الدليل', 'ramz' => 'الرمز', 'other' => 'أخرى'],
    'mawdi'   => ['not_included' => 'الموضع ليس من المسألة', 'mawdi' => 'الكلمة', 'other' => 'أخرى'],
    'qiraa'   => ['lafz' => 'لفظ الراوي', 'wasf' => 'الأداء', 'hal' => 'الحال', 'wajh' => 'الوجه', 'other' => 'أخرى'],
    'bayt'    => ['sadr' => 'صدر البيت', 'ajz' => 'عجز البيت', 'bab' => 'الباب', 'other' => 'أخرى'],
    'general' => ['missing_masala' => 'مسألة ناقصة', 'other' => 'أخرى'],
];

/**
 * Resolve a target to [label, masala_id, current values by field, link]. Returns null if the key is unknown.
 */
function target_info(string $type, string $key): ?array
{
    $db = content();
    switch ($type) {
        case 'masala':
            $m = q($db, 'SELECT * FROM masail WHERE id = ?', [$key])->fetch();
            return $m ? ['label' => "المسألة {$m['id']}: {$m['kalima']}", 'masala_id' => $m['id'], 'values' => $m,
                         'link' => url(['p' => 'masala', 'id' => $m['id']])] : null;
        case 'reading':
            $r = q($db, 'SELECT * FROM readings WHERE rid = ?', [$key])->fetch();
            return $r ? ['label' => "القراءة {$r['rid']} ({$r['by_text']})", 'masala_id' => $r['masala_id'], 'values' => $r,
                         'link' => url(['p' => 'masala', 'id' => $r['masala_id']]) . '#r-' . $r['ord']] : null;
        case 'mawdi':
            $w = q($db, 'SELECT * FROM mawadi WHERE mid = ?', [$key])->fetch();
            return $w ? ['label' => "{$w['sura']} {$w['aya_no']}: {$w['mawdi']} (المسألة {$w['masala_id']})", 'masala_id' => $w['masala_id'],
                         'values' => $w, 'link' => url(['p' => 'qiraat', 'masala' => $w['masala_id'], 'sura' => $w['sura_no'], 'from' => $w['aya_no'], 'to' => $w['aya_no']])] : null;
        case 'qiraa':
            $parts = explode('|', $key);
            if (count($parts) !== 3) return null;
            [$mid, $rawi, $rid] = $parts;
            $x = q($db, 'SELECT * FROM qiraat_v WHERE mid = ? AND rawi = ? AND rid = ?', [$mid, $rawi, $rid])->fetch();
            return $x ? ['label' => "{$x['rawi']} في {$x['sura']} {$x['aya_no']}: {$x['mawdi']}", 'masala_id' => $x['id'], 'values' => $x,
                         'link' => url(['p' => 'qiraat', 'masala' => $x['id'], 'sura' => $x['sura_no'], 'from' => $x['aya_no'], 'to' => $x['aya_no']])] : null;
        case 'bayt':
            $b = q($db, 'SELECT * FROM matn WHERE n = ?', [(int)$key])->fetch();
            return $b ? ['label' => "البيت {$b['n']}", 'masala_id' => null, 'values' => $b, 'link' => url(['p' => 'matn', 'n' => $b['n']]) . '#b' . $b['n']] : null;
        case 'general':
            return ['label' => 'ملاحظة عامة', 'masala_id' => null, 'values' => [], 'link' => url(['p' => 'issues'])];
    }
    return null;
}

/** Open-issue counts for a list of [type, key] targets → "type|key" => n */
function open_issue_counts(string $type, array $keys): array
{
    if (!$keys) return [];
    $in = implode(',', array_fill(0, count($keys), '?'));
    $rows = q(reviews(), "SELECT target_key, COUNT(*) n FROM issues WHERE status = 'open' AND target_type = ? AND target_key IN ($in) GROUP BY target_key",
              array_merge([$type], array_values($keys)))->fetchAll(PDO::FETCH_KEY_PAIR);
    return $rows;
}

function report_link(string $type, string $key, string $label = '⚑'): string
{
    if (!user()) return '';
    return '<a class="flag" title="إبلاغ عن خطأ" href="' . h(url(['p' => 'report', 'type' => $type, 'key' => $key])) . '">' . h($label) . '</a>';
}
