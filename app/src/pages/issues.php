<?php
$title = 'المراجعات';
$status = array_key_exists($_GET['status'] ?? '', ISSUE_STATUS) ? $_GET['status'] : '';
$type = array_key_exists($_GET['type'] ?? '', TARGET_TYPES) ? $_GET['type'] : '';
$masala = trim((string)($_GET['masala'] ?? ''));
$mine = !empty($_GET['mine']) && user();
$params = [];
$w = ['1=1'];
if ($status) { $w[] = 'i.status = ?'; $params[] = $status; }
if ($type) { $w[] = 'i.target_type = ?'; $params[] = $type; }
if ($masala) { $w[] = 'i.masala_id = ?'; $params[] = $masala; }
if ($mine) { $w[] = 'i.created_by = ?'; $params[] = user()['id']; }
$issues = q(reviews(), 'SELECT i.*, u.display_name FROM issues i JOIN users u ON u.id = i.created_by WHERE ' . implode(' AND ', $w) . ' ORDER BY i.id DESC LIMIT 500', $params)->fetchAll();
?>
<h1>المراجعات</h1>
<form class="filters" method="get">
  <input type="hidden" name="p" value="issues">
  <div class="row">
    <label>الحالة <select name="status"><option value="">الكل</option>
      <?php foreach (ISSUE_STATUS as $k => $l): ?><option value="<?= $k ?>" <?= $status === $k ? 'selected' : '' ?>><?= $l ?></option><?php endforeach ?></select></label>
    <label>نوع الهدف <select name="type"><option value="">الكل</option>
      <?php foreach (TARGET_TYPES as $k => $l): ?><option value="<?= $k ?>" <?= $type === $k ? 'selected' : '' ?>><?= h($l) ?></option><?php endforeach ?></select></label>
    <label>المسألة <input name="masala" value="<?= h($masala) ?>" class="num"></label>
    <?php if (user()): ?><label class="chk"><input type="checkbox" name="mine" value="1" <?= $mine ? 'checked' : '' ?>> بلاغاتي</label><?php endif ?>
    <button>عرض</button>
  </div>
</form>
<div class="bar">
  <?php if (user()): ?><a class="btn" href="<?= h(url(['p' => 'report', 'type' => 'general'])) ?>">ملاحظة عامة / مسألة ناقصة</a><?php endif ?>
  <?php if (is_admin()): ?><a href="<?= h(url(['p' => 'export'])) ?>">تصدير المقبولة (JSON)</a><?php endif ?>
</div>
<?php include __DIR__ . '/_issue_table.php'; ?>
