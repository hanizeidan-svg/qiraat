<?php
$title = 'المتن';
$kw = trim((string)($_GET['kw'] ?? ''));
$n = (int)($_GET['n'] ?? 0);
$bab = trim((string)($_GET['bab'] ?? ''));
$babs = q(content(), 'SELECT bab, MIN(n) a, MAX(n) b FROM matn GROUP BY bab ORDER BY a')->fetchAll();
if ($n && !$bab) $bab = (string)q(content(), 'SELECT bab FROM matn WHERE n = ?', [$n])->fetchColumn();
if ($bab === '' && $kw === '') $bab = $babs[0]['bab'];

$params = [];
if ($kw !== '') { $where = 'plain LIKE ?'; $params[] = '%' . plain_ar($kw) . '%'; }
else { $where = 'bab = ?'; $params[] = $bab; }
$abyat = q(content(), "SELECT * FROM matn WHERE $where ORDER BY n", $params)->fetchAll();
$links = [];
foreach (q(content(), 'SELECT a.bayt, m.id, m.kalima FROM masala_abyat a JOIN masail m ON m.id = a.masala_id') as $x) $links[$x['bayt']][] = $x;
$issues = open_issue_counts('bayt', array_map('strval', array_column($abyat, 'n')));
?>
<h1>متن الشاطبية</h1>
<form class="filters" method="get">
  <input type="hidden" name="p" value="matn">
  <div class="row">
    <label>الباب <select name="bab" onchange="this.form.submit()">
      <?php foreach ($babs as $b): ?><option value="<?= h($b['bab']) ?>" <?= $bab === $b['bab'] ? 'selected' : '' ?>><?= h($b['bab']) ?> (<?= $b['a'] ?>–<?= $b['b'] ?>)</option><?php endforeach ?>
    </select></label>
    <label class="grow">بحث في المتن (بلا تشكيل) <input type="search" name="kw" value="<?= h($kw) ?>"></label>
    <button>بحث</button>
  </div>
</form>
<p class="muted"><?= count($abyat) ?> بيتًا</p>
<section class="matn-box">
  <?php foreach ($abyat as $b): ?>
    <div class="bayt quran <?= $b['n'] === $n ? 'hl' : '' ?>" id="b<?= $b['n'] ?>">
      <span class="n"><?= $b['n'] ?></span>
      <span class="sadr"><?= h($b['sadr']) ?></span><span class="ajz"><?= h($b['ajz']) ?></span>
      <span class="meta">
        <?php foreach ($links[$b['n']] ?? [] as $l): ?><a class="chip" href="<?= h(url(['p' => 'masala', 'id' => $l['id']])) ?>"><?= h($l['id']) ?></a><?php endforeach ?>
        <?php if (!empty($issues[(string)$b['n']])): ?><span class="badge warn"><?= $issues[(string)$b['n']] ?> ⚑</span><?php endif ?>
        <?= report_link('bayt', (string)$b['n']) ?>
      </span>
    </div>
  <?php endforeach ?>
</section>
