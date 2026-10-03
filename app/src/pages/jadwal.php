<?php
$title = 'الجدول';
$f = filters();
[$rows, $total] = find_mawadi($f, 100);
$rd = readings_at(array_column($rows, 'mid'), $f);
?>
<h1>الجدول <small>صف لكل موضع، وعمود لكل راوٍ</small></h1>
<?= filter_form($f, 'jadwal') ?>
<div class="bar"><span><?= $total ?> موضع</span><a href="<?= h(url(['p' => 'qiraat', 'page' => null], true)) ?>">عرض مفصل</a></div>
<div class="scroll">
<table class="grid wide">
  <thead><tr><th>الموضع</th><th>الكلمة</th><th>المسألة</th>
    <?php foreach ($f['rawis'] as $r): ?><th><?= h($r) ?></th><?php endforeach ?></tr></thead>
  <tbody>
  <?php foreach ($rows as $w): ?>
    <tr>
      <td class="nowrap"><?= h($w['sura']) ?> <?= $w['aya_no'] ?></td>
      <td class="quran"><?= h($w['mawdi']) ?></td>
      <td><a href="<?= h(url(['p' => 'masala', 'id' => $w['masala_id']])) ?>"><?= h($w['masala_id']) ?></a></td>
      <?php foreach ($f['rawis'] as $r): ?>
        <td class="<?= array_filter($rd[$w['mid']][$r] ?? [], fn($x) => !$x['hafs']) ? 'khilaf' : '' ?>">
          <?php foreach ($rd[$w['mid']][$r] ?? [] as $x): ?>
            <div><span class="quran"><?= h($x['lafz']) ?></span> <small><?= h($x['wasf']) ?><?= $x['hal'] === HAL_BOTH ? '' : ' [' . h($x['hal']) . ']' ?></small></div>
          <?php endforeach ?>
        </td>
      <?php endforeach ?>
    </tr>
  <?php endforeach ?>
  </tbody>
</table>
</div>
<?= pager($total, $f['page'], 100) ?>
