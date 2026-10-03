<?php
$id = (string)($_GET['id'] ?? '');
$m = q(content(), 'SELECT * FROM masail WHERE id = ?', [$id])->fetch();
if (!$m) { http_response_code(404); echo '<p>المسألة غير موجودة.</p>'; return; }
$title = "المسألة {$m['id']}";
$abyat = q(content(), 'SELECT t.* FROM masala_abyat a JOIN matn t ON t.n = a.bayt WHERE a.masala_id = ? ORDER BY t.n', [$id])->fetchAll();
$readings = q(content(), 'SELECT * FROM readings WHERE masala_id = ? ORDER BY ord', [$id])->fetchAll();
$rr = [];
foreach (q(content(), 'SELECT rr.rid, rr.rawi FROM reading_rawis rr JOIN readings d ON d.rid = rr.rid JOIN rawis r ON r.name = rr.rawi WHERE d.masala_id = ? ORDER BY r.ord', [$id]) as $x) $rr[$x['rid']][] = $x['rawi'];
$mawadi = q(content(), 'SELECT * FROM mawadi WHERE masala_id = ? ORDER BY sura_no, aya_no, word_no', [$id])->fetchAll();
$issues = q(reviews(), 'SELECT i.*, u.display_name FROM issues i JOIN users u ON u.id = i.created_by WHERE i.masala_id = ? ORDER BY i.id DESC', [$id])->fetchAll();
$fields = TARGET_FIELDS['masala'];
?>
<h1>المسألة <?= h($m['id']) ?>: <span class="quran"><?= h($m['kalima']) ?></span> <?= report_link('masala', $m['id'], '⚑ إبلاغ') ?></h1>
<p class="muted"><?= h($m['bab']) ?> · <?= h($m['nitaq']) ?> · <?= $m['adad'] ?> موضع · المصدر: <code><?= h($m['src_file']) ?></code></p>

<section class="matn-box">
  <?php foreach ($abyat as $b): ?>
    <div class="bayt quran"><span class="n"><a href="<?= h(url(['p' => 'matn', 'n' => $b['n']])) ?>#b<?= $b['n'] ?>"><?= $b['n'] ?></a></span>
      <span class="sadr"><?= h($b['sadr']) ?></span><span class="ajz"><?= h($b['ajz']) ?></span></div>
  <?php endforeach ?>
</section>

<dl class="kv">
  <dt>قول الشاطبي</dt><dd class="quran"><?= h($m['qawl']) ?></dd>
  <?php if ($m['rumuz']): ?><dt>الرموز</dt><dd><?= h($m['rumuz']) ?></dd><?php endif ?>
  <dt>النتيجة المعمول بها</dt><dd><?= h($m['natija']) ?></dd>
  <?php if ($m['note']): ?><dt>ملاحظة</dt><dd><?= h($m['note']) ?></dd><?php endif ?>
  <?php if ($m['review']): ?><dt>للمراجعة</dt><dd class="warn"><?= h($m['review']) ?></dd><?php endif ?>
</dl>

<h2>القراءات</h2>
<table class="grid">
  <thead><tr><th>#</th><th>أصحابها</th><th>اللفظ</th><th>الأداء</th><th>الحال</th><th>الدليل</th><th>الرمز</th><th></th></tr></thead>
  <?php foreach ($readings as $r): ?>
    <tr id="r-<?= $r['ord'] ?>">
      <td><?= $r['ord'] ?></td>
      <td><?= h(names_for($rr[$r['rid']] ?? [])) ?><?= $r['by_text'] === 'الباقون' ? ' <small class="muted">(الباقون)</small>' : '' ?></td>
      <td class="quran"><?= $r['lafz'] !== '' ? h($r['lafz']) : '<span class="ui">' . ($r['tahwil'] ? 'يُولَّد في كل موضع' : 'كلفظ حفص') . '</span>' ?></td>
      <td><?= h($r['wasf']) ?></td>
      <td class="muted"><?= h($r['hal']) ?></td>
      <td class="quran small"><?= h($r['dalil']) ?></td>
      <td class="small"><?= h($r['ramz']) ?></td>
      <td><?= report_link('reading', $r['rid']) ?></td>
    </tr>
  <?php endforeach ?>
</table>

<h2>المواضع <small><?= count($mawadi) ?></small></h2>
<p><a class="btn" href="<?= h(url(['p' => 'qiraat', 'masala' => $m['id']])) ?>">عرض قراءات كل الرواة في المواضع</a>
   <a class="btn ghost" href="<?= h(url(['p' => 'jadwal', 'masala' => $m['id']])) ?>">جدولًا</a></p>
<ol class="mawadi-list">
  <?php foreach ($mawadi as $w): ?>
    <li><?= h($w['sura']) ?> <?= $w['aya_no'] ?>: <span class="quran"><?= h($w['mawdi']) ?></span> <?= report_link('mawdi', $w['mid']) ?></li>
  <?php endforeach ?>
</ol>

<h2>المراجعات <small><?= count($issues) ?></small></h2>
<?php if (user()): ?><p><a class="btn" href="<?= h(url(['p' => 'report', 'type' => 'masala', 'key' => $m['id']])) ?>">إبلاغ عن خطأ في المسألة</a></p><?php endif ?>
<?php include __DIR__ . '/_issue_table.php'; ?>
