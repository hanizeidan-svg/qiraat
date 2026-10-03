<?php
require_admin();
$title = 'المستخدمون';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_check();
    $action = (string)($_POST['action'] ?? '');
    if ($action === 'create') {
        $username = trim((string)($_POST['username'] ?? ''));
        $name = trim((string)($_POST['display_name'] ?? ''));
        $pass = (string)($_POST['password'] ?? '');
        $role = ($_POST['role'] ?? '') === 'admin' ? 'admin' : 'reviewer';
        if (!preg_match('/^[\w.-]{3,40}$/u', $username) || $name === '' || mb_strlen($pass) < 8) {
            flash('اسم المستخدم (3 أحرف فأكثر بلا مسافات)، والاسم، وكلمة مرور من 8 أحرف فأكثر.', 'err');
        } else {
            try {
                q(reviews(), 'INSERT INTO users (username, display_name, password_hash, role) VALUES (?,?,?,?)',
                  [$username, $name, password_hash($pass, PASSWORD_DEFAULT), $role]);
                flash("أُنشئ الحساب: $username");
            } catch (PDOException) { flash('اسم المستخدم مستعمل.', 'err'); }
        }
    } elseif ($action === 'toggle') {
        $uid = (int)$_POST['id'];
        if ($uid === (int)user()['id']) flash('لا يمكنك تعطيل حسابك.', 'err');
        else q(reviews(), 'UPDATE users SET active = 1 - active WHERE id = ?', [$uid]);
    } elseif ($action === 'password') {
        $pass = (string)($_POST['password'] ?? '');
        if (mb_strlen($pass) < 8) flash('كلمة المرور 8 أحرف فأكثر.', 'err');
        else { q(reviews(), 'UPDATE users SET password_hash = ? WHERE id = ?', [password_hash($pass, PASSWORD_DEFAULT), (int)$_POST['id']]); flash('غُيِّرت كلمة المرور.'); }
    }
    redirect(url(['p' => 'users']));
}
$users = q(reviews(), 'SELECT u.*, (SELECT COUNT(*) FROM issues WHERE created_by = u.id) n FROM users u ORDER BY u.id')->fetchAll();
?>
<h1>المستخدمون</h1>
<table class="grid">
  <thead><tr><th>المستخدم</th><th>الاسم</th><th>الدور</th><th>البلاغات</th><th>الحالة</th><th></th></tr></thead>
  <?php foreach ($users as $u): ?>
    <tr class="<?= $u['active'] ? '' : 'muted' ?>">
      <td><?= h($u['username']) ?></td><td><?= h($u['display_name']) ?></td>
      <td><?= $u['role'] === 'admin' ? 'مشرف' : 'مراجع' ?></td><td><?= $u['n'] ?></td>
      <td><?= $u['active'] ? 'فعّال' : 'معطّل' ?></td>
      <td class="nowrap">
        <form method="post" class="inline"><?= csrf_field() ?><input type="hidden" name="id" value="<?= $u['id'] ?>">
          <button name="action" value="toggle" class="link"><?= $u['active'] ? 'تعطيل' : 'تفعيل' ?></button></form>
        <form method="post" class="inline"><?= csrf_field() ?><input type="hidden" name="id" value="<?= $u['id'] ?>">
          <input type="password" name="password" placeholder="كلمة مرور جديدة" autocomplete="new-password" class="num">
          <button name="action" value="password" class="link">تغيير</button></form>
      </td>
    </tr>
  <?php endforeach ?>
</table>

<h2>حساب جديد</h2>
<form method="post" class="form narrow">
  <?= csrf_field() ?>
  <label>اسم المستخدم <input name="username" required pattern="[\w.\-]{3,40}"></label>
  <label>الاسم الظاهر <input name="display_name" required></label>
  <label>كلمة المرور <input type="password" name="password" minlength="8" required autocomplete="new-password"></label>
  <label>الدور <select name="role"><option value="reviewer">مراجع</option><option value="admin">مشرف</option></select></label>
  <button name="action" value="create">إنشاء</button>
</form>
