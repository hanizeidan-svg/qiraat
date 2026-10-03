<?php
require_login();
$title = 'إبلاغ عن خطأ';
$type = (string)($_GET['type'] ?? $_POST['type'] ?? 'general');
$key = (string)($_GET['key'] ?? $_POST['key'] ?? '');
if (!isset(TARGET_FIELDS[$type])) { $type = 'general'; $key = ''; }
$info = target_info($type, $key);
if (!$info) { http_response_code(404); echo '<p>الهدف غير موجود.</p>'; return; }
$fields = TARGET_FIELDS[$type];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_check();
    $field = (string)($_POST['field'] ?? '');
    $proposed = trim((string)($_POST['proposed'] ?? ''));
    $comment = trim((string)($_POST['comment'] ?? ''));
    if (!isset($fields[$field])) { flash('اختر الحقل.', 'err'); }
    elseif ($proposed === '' && $comment === '') { flash('اكتب التصحيح المقترح أو التعليل.', 'err'); }
    else {
        q(reviews(), 'INSERT INTO issues (target_type, target_key, masala_id, field, current_value, proposed_value, comment, content_commit, created_by)
                      VALUES (?,?,?,?,?,?,?,?,?)',
          [$type, $key, $info['masala_id'], $field, (string)($info['values'][$field] ?? ''), $proposed, $comment, meta('git_commit'), user()['id']]);
        flash('سُجِّل البلاغ. شكرًا لك.');
        redirect(url(['p' => 'issue', 'id' => reviews()->lastInsertId()]));
    }
}
$cur = array_map(fn($f) => (string)($info['values'][$f] ?? ''), array_combine(array_keys($fields), array_keys($fields)));
?>
<h1>إبلاغ عن خطأ</h1>
<p><?= h(TARGET_TYPES[$type]) ?>: <a href="<?= h($info['link']) ?>"><?= h($info['label']) ?></a> <code><?= h($key) ?></code></p>
<form method="post" class="form" action="<?= h(url(['p' => 'report'])) ?>">
  <?= csrf_field() ?>
  <input type="hidden" name="type" value="<?= h($type) ?>"><input type="hidden" name="key" value="<?= h($key) ?>">
  <label>الحقل
    <select name="field" id="field">
      <?php foreach ($fields as $k => $label): ?><option value="<?= h($k) ?>" data-cur="<?= h($cur[$k]) ?>"><?= h($label) ?></option><?php endforeach ?>
    </select></label>
  <label>القيمة الحالية <textarea id="cur" readonly rows="2" class="quran"></textarea></label>
  <label>التصحيح المقترح <textarea name="proposed" rows="3" class="quran"></textarea></label>
  <label>التعليل / المصدر (مثل: الوافي ص…، إرشاد المريد…) <textarea name="comment" rows="3"></textarea></label>
  <button>إرسال</button>
</form>
<script>
  const sel = document.getElementById('field'), cur = document.getElementById('cur');
  const sync = () => cur.value = sel.selectedOptions[0].dataset.cur || '';
  sel.addEventListener('change', sync); sync();
</script>
