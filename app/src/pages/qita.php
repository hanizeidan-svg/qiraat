<?php
$id = (int)($_GET['id'] ?? 0);
$x = q(content(), 'SELECT * FROM qita WHERE id = ?', [$id])->fetch();
if (!$x) { http_response_code(404); echo '<p>القطعة غير موجودة.</p>'; return; }
$title = "القطعة $id";
$abyat = q(content(), 'SELECT * FROM matn WHERE n BETWEEN ? AND ? ORDER BY n', [$x['bayt_from'], $x['bayt_to']])->fetchAll();
$parts = qita_parts(array_column($abyat, 'n'));
$masail = q(content(), 'SELECT m.*, mq.exact FROM masala_qita mq JOIN masail m ON m.id = mq.masala_id WHERE mq.qita_id = ? ORDER BY m.rowid', [$id])->fetchAll();
$prev = $id > 1 ? $id - 1 : null;
$next = q(content(), 'SELECT id FROM qita WHERE id = ?', [$id + 1])->fetchColumn();
?>
<h1>القطعة <?= $id ?> <small class="muted"><?= h($x['bab']) ?> · البيت <?= $x['bayt_from'] ?><?= $x['bayt_to'] != $x['bayt_from'] ? '–' . $x['bayt_to'] : '' ?></small></h1>
<p class="muted">
  <?php if ($prev): ?><a href="<?= h(url(['p' => 'qita', 'id' => $prev])) ?>">→ السابقة</a><?php endif ?>
  <?php if ($next): ?> · <a href="<?= h(url(['p' => 'qita', 'id' => $next])) ?>">التالية ←</a><?php endif ?>
  · <a href="<?= h(url(['p' => 'matn', 'n' => $x['bayt_from']])) ?>#b<?= $x['bayt_from'] ?>">في المتن</a>
</p>
<p class="quran" style="font-size:1.3rem"><?= h($x['nass']) ?></p>
<section class="matn-box">
  <?php foreach ($abyat as $b): ?>
    <div class="bayt quran"><span class="n"><?= $b['n'] ?></span>
      <span class="sadr"><?= hemistich_q($parts[$b['n']][0] ?? [], [$id]) ?></span><span class="ajz"><?= hemistich_q($parts[$b['n']][1] ?? [], [$id]) ?></span></div>
  <?php endforeach ?>
</section>
<h2>المسائل <small><?= count($masail) ?></small></h2>
<?php if (!$masail): ?><p class="muted">لا مسائل مرتبطة بهذه القطعة (خارج نطاق القاعدة، أو مقدمة/خاتمة).</p>
<?php else: ?>
<table class="grid">
  <tr><th>المسألة</th><th>الكلمة</th><th>الباب</th><th>النتيجة المعمول بها</th><th></th></tr>
  <?php foreach ($masail as $m): ?>
  <tr><td><a href="<?= h(url(['p' => 'masala', 'id' => $m['id']])) ?>"><?= h($m['id']) ?></a></td>
      <td class="quran"><?= h($m['kalima']) ?></td><td class="small"><?= h($m['bab']) ?></td>
      <td class="small"><?= h($m['natija']) ?> <?= tahrir_badges($m['tahrir']) ?></td>
      <td><?= $m['exact'] ? '' : '<span class="badge warn">تقريبي</span>' ?></td></tr>
  <?php endforeach ?>
</table>
<?php endif ?>
