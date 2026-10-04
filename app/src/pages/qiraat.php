<?php
$title = 'القراءات';
$f = filters();

// CSV export of the whole filtered set (one row per موضع × راوٍ × وجه)
if (($_GET['format'] ?? '') === 'csv') {
    [$rows] = find_mawadi(['page' => 1] + $f, 1000000);
    $rd = readings_at(array_column($rows, 'mid'), $f);
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="qiraat.csv"');
    $out = fopen('php://output', 'w');
    fwrite($out, "\xEF\xBB\xBF");
    fputcsv($out, ['السورة', 'رقم السورة', 'الآية', 'الكلمة (حفص)', 'الراوي', 'القارئ', 'اللفظ', 'الأداء', 'الحال', 'الوجه', 'يوافق حفصًا', 'الباب', 'المسألة', 'البيت', 'الدليل', 'الرمز', 'مصدر الاعتماد', 'زيادة على النظم', 'تحرير / تنبيه']);
    foreach ($rows as $w) foreach ($rd[$w['mid']] ?? [] as $rawi => $list) foreach ($list as $x) {
        fputcsv($out, [$w['sura'], $w['sura_no'], $w['aya_no'], $w['mawdi'], $rawi, rawis()[$rawi]['qari'], $x['lafz'], $x['wasf'], $x['hal'],
                       $x['wajh'], $x['hafs'] ? 'نعم' : 'لا', $w['bab'], $w['masala_id'], $w['abyat'], $x['dalil'], $x['ramz'], $w['marji'], $x['ziyada'] ? 'نعم' : '', $w['tahrir']]);
    }
    exit;
}

[$rows, $total] = find_mawadi($f);
$rd = readings_at(array_column($rows, 'mid'), $f);
$issues = open_issue_counts('mawdi', array_column($rows, 'mid'));
$selLabel = names_for($f['rawis']);
?>
<h1>القراءات <small><?= h($selLabel) ?></small></h1>
<?= filter_form($f, 'qiraat') ?>
<div class="bar">
  <span><?= $total ?> موضع</span>
  <a href="<?= h(url(['format' => 'csv', 'page' => null], true)) ?>">تنزيل CSV</a>
  <a href="<?= h(url(['p' => 'jadwal', 'page' => null], true)) ?>">عرض جدولي</a>
</div>

<?php foreach ($rows as $w): $byRawi = $rd[$w['mid']] ?? []; ?>
<article class="mawdi">
  <header>
    <span class="ref"><?= h($w['sura']) ?> <?= $w['aya_no'] ?></span>
    <span class="word quran"><?= h($w['mawdi']) ?></span>
    <span class="tag <?= $w['naw'] === 'فرش' ? 'farsh' : 'usul' ?>"><?= h($w['bab']) ?></span>
    <a class="masala" href="<?= h(url(['p' => 'masala', 'id' => $w['masala_id']])) ?>">المسألة <?= h($w['masala_id']) ?> · البيت <?= h($w['abyat']) ?></a>
    <?php if (!empty($issues[$w['mid']])): ?><span class="badge warn" title="مراجعات مفتوحة"><?= $issues[$w['mid']] ?> ⚑</span><?php endif ?>
    <?php if ($w['review']): ?><span class="badge warn" title="<?= h($w['review']) ?>">للمراجعة</span><?php endif ?>
    <?= tahrir_badges($w['tahrir']) ?>
    <?= report_link('mawdi', $w['mid']) ?>
  </header>
  <details class="aya"><summary>الآية</summary><p class="quran"><?= h($w['aya']) ?></p></details>
  <table class="readings">
    <?php foreach (group_by_reading($byRawi) as [$rs, $list]): ?>
      <?php foreach ($list as $i => $x): ?>
      <tr class="<?= $x['hafs'] ? '' : 'khilaf' ?>">
        <?php if ($i === 0): ?><th rowspan="<?= count($list) ?>"><?= h(names_for($rs)) ?></th><?php endif ?>
        <td class="lafz quran"><?= h($x['lafz']) ?></td>
        <td><?= h($x['wasf']) ?><?= $x['ziyada'] ? ' <span class="tg tg-z" title="وجه زاده المحققون على النظم">زيادة</span>' : '' ?></td>
        <td class="muted"><?= $x['hal'] === HAL_BOTH ? '' : h($x['hal']) ?><?= $x['wajh'] ? ' · وجه ' . h($x['wajh']) : '' ?></td>
        <td class="dalil"><details><summary>الدليل</summary><span class="quran"><?= h($x['dalil']) ?></span><?php if ($x['ramz'] && $x['ramz'] !== '—'): ?><br><small><?= h($x['ramz']) ?></small><?php endif ?></details></td>
        <td><?= count($rs) === 1 ? report_link('qiraa', $w['mid'] . '|' . $rs[0] . '|' . $x['rid']) : report_link('reading', $x['rid']) ?></td>
      </tr>
      <?php endforeach ?>
    <?php endforeach ?>
  </table>
</article>
<?php endforeach ?>
<?php if (!$rows): ?><p class="muted">لا نتائج.</p><?php endif ?>
<?= pager($total, $f['page'], (int)cfg('page_size')) ?>
