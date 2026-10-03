<?php
require_admin();
$status = in_array($_GET['status'] ?? 'accepted', array_keys(ISSUE_STATUS), true) ? ($_GET['status'] ?? 'accepted') : 'accepted';
$rows = q(reviews(), 'SELECT i.*, u.display_name AS reporter FROM issues i JOIN users u ON u.id = i.created_by WHERE i.status = ? ORDER BY i.masala_id, i.id', [$status])->fetchAll();
$out = [];
foreach ($rows as $i) {
    $info = target_info($i['target_type'], $i['target_key']);
    $comments = q(reviews(), 'SELECT u.display_name AS who, c.body, c.created_at FROM issue_comments c JOIN users u ON u.id = c.user_id WHERE c.issue_id = ? ORDER BY c.id', [$i['id']])->fetchAll();
    $src = $i['masala_id'] ? q(content(), 'SELECT src_file FROM masail WHERE id = ?', [$i['masala_id']])->fetchColumn() : null;
    $out[] = $i + ['target_label' => $info['label'] ?? null, 'value_now' => $info ? ($info['values'][$i['field']] ?? null) : null,
                   'src_file' => $src ?: null, 'comments' => $comments];
}
header('Content-Type: application/json; charset=utf-8');
header('Content-Disposition: attachment; filename="reviews-' . $status . '-' . date('Ymd') . '.json"');
echo json_encode(['exported_at' => date('c'), 'content_commit' => meta('git_commit'), 'status' => $status, 'issues' => $out],
                 JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
exit;
