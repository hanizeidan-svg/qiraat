<?php
$id = (int)($_GET['id'] ?? 0);
$i = q(reviews(), 'SELECT i.*, u.display_name, r.display_name AS resolver FROM issues i JOIN users u ON u.id = i.created_by
                   LEFT JOIN users r ON r.id = i.resolved_by WHERE i.id = ?', [$id])->fetch();
if (!$i) { http_response_code(404); echo '<p>غير موجودة.</p>'; return; }
$title = "المراجعة #$id";

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    require_login();
    csrf_check();
    $action = (string)($_POST['action'] ?? '');
    $body = trim((string)($_POST['body'] ?? ''));
    if ($action === 'comment' && $body !== '') {
        q(reviews(), 'INSERT INTO issue_comments (issue_id, user_id, body) VALUES (?,?,?)', [$id, user()['id'], $body]);
        flash('أُضيف التعليق.');
    } elseif (in_array($action, ['accepted', 'rejected', 'open', 'applied'], true)) {
        require_admin();
        $source = trim((string)($_POST['source'] ?? ''));
        if (in_array($action, ['accepted', 'rejected'], true) && $source === '' && !$i['resolution_source']) {
            flash('اذكر مصدر القرار (مثل: الوافي ص 236، أو إقرار المراجع).', 'err');
            redirect(url(['p' => 'issue', 'id' => $id]));
        }
        q(reviews(), 'UPDATE issues SET status = ?, resolved_by = ?, resolved_at = datetime(\'now\'), resolution_note = ?, resolution_source = ? WHERE id = ?',
          [$action, user()['id'], $body !== '' ? $body : $i['resolution_note'], $source !== '' ? $source : $i['resolution_source'], $id]);
        if ($body !== '') q(reviews(), 'INSERT INTO issue_comments (issue_id, user_id, body) VALUES (?,?,?)', [$id, user()['id'], '[' . ISSUE_STATUS[$action] . '] ' . $body]);
        flash('حُدِّثت الحالة: ' . ISSUE_STATUS[$action]);
    }
    redirect(url(['p' => 'issue', 'id' => $id]));
}

$info = target_info($i['target_type'], $i['target_key']);
$now = $info ? (string)($info['values'][$i['field']] ?? '') : null;
$comments = q(reviews(), 'SELECT c.*, u.display_name FROM issue_comments c JOIN users u ON u.id = c.user_id WHERE c.issue_id = ? ORDER BY c.id', [$id])->fetchAll();
$fieldLabel = TARGET_FIELDS[$i['target_type']][$i['field']] ?? $i['field'];
?>
<h1>المراجعة #<?= $id ?> <span class="st st-<?= h($i['status']) ?>"><?= ISSUE_STATUS[$i['status']] ?></span></h1>
<dl class="kv">
  <dt>الهدف</dt><dd><?= h(TARGET_TYPES[$i['target_type']]) ?>:
    <?php if ($info): ?><a href="<?= h($info['link']) ?>"><?= h($info['label']) ?></a><?php else: ?><span class="warn">لم يعد موجودًا في المحتوى الحالي</span><?php endif ?>
    <code><?= h($i['target_key']) ?></code></dd>
  <dt>الحقل</dt><dd><?= h($fieldLabel) ?></dd>
  <dt>القيمة وقت البلاغ</dt><dd class="quran"><?= h($i['current_value']) ?: '—' ?></dd>
  <?php if ($now !== null && $now !== (string)$i['current_value']): ?><dt>القيمة الآن</dt><dd class="quran ok"><?= h($now) ?></dd><?php endif ?>
  <dt>المقترح</dt><dd class="quran"><?= nl2br(h($i['proposed_value'])) ?: '—' ?></dd>
  <dt>التعليل</dt><dd><?= nl2br(h($i['comment'])) ?: '—' ?></dd>
  <dt>المُبلِّغ</dt><dd><?= h($i['display_name']) ?> · <?= h($i['created_at']) ?> · نسخة المحتوى <?= h($i['content_commit']) ?></dd>
  <?php if ($i['resolver']): ?><dt>الفصل</dt><dd><?= h($i['resolver']) ?> · <?= h($i['resolved_at']) ?><?= $i['resolution_note'] ? ' — ' . h($i['resolution_note']) : '' ?></dd><?php endif ?>
  <?php if ($i['resolution_source']): ?><dt>مصدر القرار</dt><dd><?= h($i['resolution_source']) ?></dd><?php endif ?>
</dl>

<h2>النقاش</h2>
<?php foreach ($comments as $c): ?>
  <div class="comment"><b><?= h($c['display_name']) ?></b> <small class="muted"><?= h($c['created_at']) ?></small><p><?= nl2br(h($c['body'])) ?></p></div>
<?php endforeach ?>
<?php if (!$comments): ?><p class="muted">لا تعليقات.</p><?php endif ?>

<?php if (user()): ?>
<form method="post" class="form">
  <?= csrf_field() ?>
  <label>تعليق<?= is_admin() ? ' / ملاحظة الفصل' : '' ?> <textarea name="body" rows="3"></textarea></label>
  <?php if (is_admin()): ?>
  <label>مصدر القرار (مطلوب عند القبول أو الرفض)
    <input name="source" list="sources" value="<?= h($i['resolution_source']) ?>" placeholder="الوافي ص 236 — أو: إقرار المراجع"></label>
  <datalist id="sources"><option value="الوافي ص "><option value="الإضاءة ص "><option value="إقرار المراجع"></datalist>
  <?php endif ?>
  <div class="row">
    <button name="action" value="comment">إضافة تعليق</button>
    <?php if (is_admin()): ?>
      <button name="action" value="accepted" class="ok">قبول</button>
      <button name="action" value="rejected" class="danger">رفض</button>
      <button name="action" value="applied" class="ghost">طُبِّقت في المصدر</button>
      <button name="action" value="open" class="ghost">إعادة فتح</button>
    <?php endif ?>
  </div>
</form>
<?php endif ?>
