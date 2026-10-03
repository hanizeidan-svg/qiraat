<?php
$title = 'الدخول';
$next = (string)($_GET['next'] ?? $_POST['next'] ?? '');
if (!preg_match('~^/[^/\\\\]~', $next) && !str_starts_with($next, 'index.php')) $next = 'index.php';   // local redirects only

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_check();
    $_SESSION['login_fail'] ??= 0;
    if ($_SESSION['login_fail'] >= 5) sleep(2);
    $u = q(reviews(), 'SELECT * FROM users WHERE username = ? AND active = 1', [trim((string)($_POST['username'] ?? ''))])->fetch();
    if ($u && password_verify((string)($_POST['password'] ?? ''), $u['password_hash'])) {
        session_regenerate_id(true);
        $_SESSION['uid'] = $u['id'];
        $_SESSION['login_fail'] = 0;
        redirect($next);
    }
    $_SESSION['login_fail']++;
    flash('اسم المستخدم أو كلمة المرور غير صحيحة.', 'err');
    redirect(url(['p' => 'login', 'next' => $next]));
}
?>
<h1>دخول المراجعين</h1>
<form method="post" class="form narrow">
  <?= csrf_field() ?>
  <input type="hidden" name="next" value="<?= h($next) ?>">
  <label>اسم المستخدم <input name="username" autocomplete="username" required></label>
  <label>كلمة المرور <input type="password" name="password" autocomplete="current-password" required></label>
  <button>دخول</button>
</form>
<p class="muted">الحسابات يُنشئها المشرف.</p>
