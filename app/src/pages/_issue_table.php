<?php /** @var array $issues rows from issues JOIN users (display_name) */ ?>
<?php if (!$issues): ?><p class="muted">لا مراجعات.</p><?php return; endif ?>
<table class="grid">
  <thead><tr><th>#</th><th>الحالة</th><th>الهدف</th><th>الحقل</th><th>المقترح</th><th>المُبلِّغ</th><th>التاريخ</th></tr></thead>
  <?php foreach ($issues as $i): ?>
    <tr>
      <td><a href="<?= h(url(['p' => 'issue', 'id' => $i['id']])) ?>"><?= $i['id'] ?></a></td>
      <td><span class="st st-<?= h($i['status']) ?>"><?= ISSUE_STATUS[$i['status']] ?></span></td>
      <td class="small"><?= h(TARGET_TYPES[$i['target_type']]) ?> <code><?= h($i['target_key']) ?></code></td>
      <td><?= h(TARGET_FIELDS[$i['target_type']][$i['field']] ?? $i['field']) ?></td>
      <td class="small"><?= h(mb_strimwidth((string)($i['proposed_value'] ?: $i['comment']), 0, 90, '…')) ?></td>
      <td><?= h($i['display_name']) ?></td>
      <td class="nowrap small"><?= h(substr($i['created_at'], 0, 10)) ?></td>
    </tr>
  <?php endforeach ?>
</table>
