<?php
// إنشاء حساب من سطر الأوامر (للمشرف الأول):
//   php app/bin/create_user.php <username> "<الاسم الظاهر>" [admin|reviewer]
// تُطلب كلمة المرور تفاعليًّا، أو تُمرَّر عبر متغير البيئة QIRAAT_PASSWORD.
declare(strict_types=1);
require __DIR__ . '/../src/bootstrap.php';

[$_, $username, $name, $role] = $argv + [null, null, null, 'reviewer'];
if (!$username || !$name || !in_array($role, ['admin', 'reviewer'], true)) {
    fwrite(STDERR, "usage: php app/bin/create_user.php <username> \"<display name>\" [admin|reviewer]\n");
    exit(1);
}
$pass = getenv('QIRAAT_PASSWORD') ?: null;
if (!$pass) {
    fwrite(STDOUT, 'Password (8+ chars): ');
    $pass = trim((string)fgets(STDIN));
}
if (mb_strlen($pass) < 8) { fwrite(STDERR, "password too short\n"); exit(1); }
q(reviews(), 'INSERT INTO users (username, display_name, password_hash, role) VALUES (?,?,?,?)',
  [$username, $name, password_hash($pass, PASSWORD_DEFAULT), $role]);
echo "created $role: $username\n";
