<?php
/** @var string $title  @var string $body  @var string $page */
$nav = ['home' => 'الرئيسية', 'qiraat' => 'القراءات', 'jadwal' => 'الجدول', 'masail' => 'المسائل', 'matn' => 'المتن', 'issues' => 'المراجعات'];
$u = user();
$openIssues = (int)q(reviews(), "SELECT COUNT(*) FROM issues WHERE status = 'open'")->fetchColumn();
?><!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= h(($title ? "$title — " : '') . cfg('site_title')) ?></title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=IBM+Plex+Sans+Arabic:wght@400;600&display=swap">
<link rel="stylesheet" href="assets/app.css?v=1">
</head>
<body>
<header class="top">
  <a class="brand" href="index.php"><?= h(cfg('site_title')) ?></a>
  <nav>
    <?php foreach ($nav as $p => $label): ?>
      <a href="<?= h(url(['p' => $p])) ?>" class="<?= $page === $p ? 'on' : '' ?>"><?= $label ?><?= $p === 'issues' && $openIssues ? " <span class=\"badge\">$openIssues</span>" : '' ?></a>
    <?php endforeach ?>
  </nav>
  <div class="who">
    <?php if ($u): ?>
      <?= h($u['display_name']) ?> <small>(<?= $u['role'] === 'admin' ? 'مشرف' : 'مراجع' ?>)</small>
      <?php if ($u['role'] === 'admin'): ?> · <a href="<?= h(url(['p' => 'users'])) ?>">المستخدمون</a><?php endif ?>
      · <form method="post" action="<?= h(url(['p' => 'logout'])) ?>" class="inline"><?= csrf_field() ?><button class="link">خروج</button></form>
    <?php else: ?>
      <a href="<?= h(url(['p' => 'login'])) ?>">دخول المراجعين</a>
    <?php endif ?>
  </div>
</header>
<main>
  <?php foreach (flash() as [$kind, $msg]): ?><div class="flash <?= h($kind) ?>"><?= h($msg) ?></div><?php endforeach ?>
  <?= $body ?>
</main>
<footer>
  بيانات المحتوى: <?= h(meta('masail')) ?> مسألة · <?= h(meta('mawadi')) ?> موضع · بُنيت <?= h(meta('built_at')) ?><?= meta('git_commit') ? ' · ' . h(meta('git_commit')) : '' ?>
</footer>
<script src="assets/app.js?v=1"></script>
</body>
</html>
