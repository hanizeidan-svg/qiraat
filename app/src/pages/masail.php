<?php
$title = 'المسائل';
$bab = trim((string)($_GET['bab'] ?? ''));
$naw = in_array($_GET['naw'] ?? '', ['فرش', 'أصول'], true) ? $_GET['naw'] : '';
$kw = trim((string)($_GET['kw'] ?? ''));
$params = [];
$w = ['1=1'];
if ($bab) { $w[] = 'bab = ?'; $params[] = $bab; }
if ($naw) { $w[] = 'naw = ?'; $params[] = $naw; }
if ($kw !== '') { $w[] = '(kalima_plain LIKE ? OR id LIKE ? OR abyat LIKE ?)'; array_push($params, '%' . plain_ar($kw) . '%', "%$kw%", "%$kw%"); }
$rows = q(content(), 'SELECT * FROM masail WHERE ' . implode(' AND ', $w) . ' ORDER BY CAST(abyat AS INTEGER), id', $params)->fetchAll();
$issues = q(reviews(), "SELECT masala_id, COUNT(*) FROM issues WHERE status = 'open' AND masala_id IS NOT NULL GROUP BY masala_id")->fetchAll(PDO::FETCH_KEY_PAIR);
$babs = q(content(), 'SELECT bab, MIN(CAST(abyat AS INTEGER)) a FROM masail GROUP BY bab ORDER BY a')->fetchAll(PDO::FETCH_COLUMN);
?>
<h1>المسائل <small><?= count($rows) ?></small></h1>
<form class="filters" method="get">
  <input type="hidden" name="p" value="masail">
  <div class="row">
    <label>الباب <select name="bab"><option value="">الكل</option>
      <?php foreach ($babs as $b): ?><option <?= $bab === $b ? 'selected' : '' ?>><?= h($b) ?></option><?php endforeach ?></select></label>
    <label>النوع <select name="naw"><option value="">الكل</option>
      <?php foreach (['فرش', 'أصول'] as $n): ?><option <?= $naw === $n ? 'selected' : '' ?>><?= $n ?></option><?php endforeach ?></select></label>
    <label class="grow">بحث (الكلمة أو رقم المسألة أو البيت) <input type="search" name="kw" value="<?= h($kw) ?>"></label>
    <button>عرض</button>
  </div>
</form>
<table class="grid">
  <thead><tr><th>المسألة</th><th>البيت</th><th>الباب</th><th>الكلمة</th><th>النطاق</th><th>المواضع</th><th>النتيجة</th><th></th></tr></thead>
  <tbody>
  <?php foreach ($rows as $m): ?>
    <tr>
      <td class="nowrap"><a href="<?= h(url(['p' => 'masala', 'id' => $m['id']])) ?>"><?= h($m['id']) ?></a></td>
      <td><?= h($m['abyat']) ?></td>
      <td><?= h($m['bab']) ?></td>
      <td class="quran"><?= h($m['kalima']) ?></td>
      <td class="muted"><?= h($m['nitaq']) ?></td>
      <td><?= $m['adad'] ?></td>
      <td class="small"><?= h($m['natija']) ?></td>
      <td><?php if (!empty($issues[$m['id']])): ?><span class="badge warn"><?= $issues[$m['id']] ?> ⚑</span><?php endif ?>
          <?php if ($m['review']): ?><span class="badge warn" title="<?= h($m['review']) ?>">للمراجعة</span><?php endif ?></td>
    </tr>
  <?php endforeach ?>
  </tbody>
</table>
