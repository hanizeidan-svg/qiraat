<?php
$title = '';
$db = content();
$stats = q($db, "SELECT naw, COUNT(*) n, SUM(adad) w FROM masail GROUP BY naw")->fetchAll();
$babs = q($db, "SELECT bab, naw, COUNT(*) n, SUM(adad) w, MIN(CAST(abyat AS INTEGER)) a FROM masail GROUP BY bab ORDER BY a")->fetchAll();
$byStatus = q(reviews(), 'SELECT status, COUNT(*) FROM issues GROUP BY status')->fetchAll(PDO::FETCH_KEY_PAIR);
$byTahrir = q($db, 'SELECT naw, COUNT(DISTINCT masala_id) FROM tahrir GROUP BY naw')->fetchAll(PDO::FETCH_KEY_PAIR);
?>
<section class="hero">
  <h1>مسائل «حرز الأماني ووجه التهاني»</h1>
  <p>كل مسألة ذكرها الشاطبي، بمواضعها في القرآن، وقراءة كل راوٍ فيها بلفظه وأدائه ودليله من النظم.</p>
</section>

<section>
  <h2>اعرض رواية</h2>
  <div class="cards">
    <?php foreach (qurra() as $qari => $pair): ?>
      <div class="card">
        <a class="big" href="<?= h(url(['p' => 'qiraat', 'qari' => [$qari]])) ?>"><?= h($qari) ?></a>
        <div><?php foreach ($pair as $r): ?><a href="<?= h(url(['p' => 'qiraat', 'r' => [$r]])) ?>"><?= h($r) ?></a> <?php endforeach ?></div>
        <a class="small" href="<?= h(url(['p' => 'qiraat', 'qari' => [$qari], 'khilaf' => 1])) ?>">ما خالف فيه حفصًا</a>
      </div>
    <?php endforeach ?>
  </div>
</section>

<section class="two">
  <div>
    <h2>المحتوى</h2>
    <table class="grid">
      <tr><th>النوع</th><th>المسائل</th><th>المواضع</th></tr>
      <?php foreach ($stats as $s): ?><tr><td><?= h($s['naw']) ?></td><td><?= $s['n'] ?></td><td><?= $s['w'] ?></td></tr><?php endforeach ?>
    </table>
    <h3>الأبواب</h3>
    <table class="grid">
      <tr><th>الباب</th><th>المسائل</th><th>المواضع</th></tr>
      <?php foreach ($babs as $b): ?>
        <tr><td><a href="<?= h(url(['p' => 'masail', 'bab' => $b['bab']])) ?>"><?= h($b['bab']) ?></a></td><td><?= $b['n'] ?></td><td><?= $b['w'] ?></td></tr>
      <?php endforeach ?>
    </table>
  </div>
  <div>
    <h2>التحريرات والتنبيهات</h2>
    <table class="grid">
      <?php foreach (TAHRIR_KINDS as $k => $_): ?>
        <tr><td><a href="<?= h(url(['p' => 'masail', 'tahrir' => $k])) ?>"><?= tahrir_badges($k) ?></a></td><td><?= (int)($byTahrir[$k] ?? 0) ?></td></tr>
      <?php endforeach ?>
    </table>
    <h2>المراجعة</h2>
    <table class="grid">
      <?php foreach (ISSUE_STATUS as $k => $label): ?>
        <tr><td><a href="<?= h(url(['p' => 'issues', 'status' => $k])) ?>"><?= $label ?></a></td><td><?= (int)($byStatus[$k] ?? 0) ?></td></tr>
      <?php endforeach ?>
    </table>
    <p class="muted">يبلّغ المراجعون عن الأخطاء بعلامة ⚑ بجوار أي مسألة أو قراءة أو موضع أو بيت، ويفصل المشرف فيها، ثم تُطبَّق المقبولة على ملفات المصدر ويُعاد البناء.</p>
    <?php if (!user()): ?><p><a class="btn" href="<?= h(url(['p' => 'login'])) ?>">دخول المراجعين</a></p><?php endif ?>
  </div>
</section>
