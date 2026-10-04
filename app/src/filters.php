<?php
declare(strict_types=1);

const HAL_BOTH = 'وصلًا ووقفًا';

/** Read and sanitize filters from the query string. */
function filters(): array
{
    $all = array_keys(rawis());
    $sel = array_values(array_intersect($all, (array)($_GET['r'] ?? [])));
    foreach ((array)($_GET['qari'] ?? []) as $qari) $sel = array_merge($sel, qurra()[$qari] ?? []);
    $sel = $sel ? array_values(array_intersect($all, array_unique($sel))) : $all;   // keep canonical order
    $int = fn($k) => isset($_GET[$k]) && $_GET[$k] !== '' ? max(0, (int)$_GET[$k]) : null;
    return [
        'rawis'  => $sel,
        'sura'   => $int('sura'),
        'from'   => $int('from'),
        'to'     => $int('to'),
        'naw'    => in_array($_GET['naw'] ?? '', ['فرش', 'أصول'], true) ? $_GET['naw'] : '',
        'bab'    => trim((string)($_GET['bab'] ?? '')),
        'masala' => trim((string)($_GET['masala'] ?? '')),
        'kw'     => trim((string)($_GET['kw'] ?? '')),
        'khilaf' => !empty($_GET['khilaf']),
        'hal'    => in_array($_GET['hal'] ?? '', ['وصلًا', 'وقفًا'], true) ? $_GET['hal'] : '',
        'review' => !empty($_GET['review']),
        'tahrir' => array_key_exists($_GET['tahrir'] ?? '', TAHRIR_KINDS) || ($_GET['tahrir'] ?? '') === '*' ? $_GET['tahrir'] : '',
        'page'   => max(1, (int)($_GET['page'] ?? 1)),
    ];
}

/** Halls of a reading that match the selected hal filter. */
function hal_values(array $f): array { return $f['hal'] ? [$f['hal'], HAL_BOTH] : ['وصلًا', 'وقفًا', HAL_BOTH]; }

function in_list(array $vals, array &$params): string
{
    foreach ($vals as $v) $params[] = $v;
    return implode(',', array_fill(0, count($vals), '?')) ?: 'NULL';
}

/** WHERE clause over `mawadi w JOIN masail m`. */
function where_mawadi(array $f, array &$params): string
{
    $w = ['1=1'];
    if ($f['sura'])   { $w[] = 'w.sura_no = ?'; $params[] = $f['sura']; }
    if ($f['from'])   { $w[] = 'w.aya_no >= ?'; $params[] = $f['from']; }
    if ($f['to'])     { $w[] = 'w.aya_no <= ?'; $params[] = $f['to']; }
    if ($f['naw'])    { $w[] = 'm.naw = ?'; $params[] = $f['naw']; }
    if ($f['bab'])    { $w[] = 'm.bab = ?'; $params[] = $f['bab']; }
    if ($f['masala']) { $w[] = 'm.id = ?'; $params[] = $f['masala']; }
    if ($f['kw'] !== '') {
        $kw = '%' . plain_ar($f['kw']) . '%';
        $w[] = '(w.mawdi_plain LIKE ? OR m.kalima_plain LIKE ? OR EXISTS (SELECT 1 FROM qiraat qk WHERE qk.mid = w.mid AND qk.lafz_plain LIKE ?))';
        array_push($params, $kw, $kw, $kw);
    }
    if ($f['tahrir'] === '*') $w[] = "m.tahrir <> ''";
    elseif ($f['tahrir'] !== '') { $w[] = 'm.id IN (SELECT masala_id FROM tahrir WHERE naw = ?)'; $params[] = $f['tahrir']; }
    if ($f['review']) {
        $ids = q(reviews(), "SELECT DISTINCT masala_id FROM issues WHERE status = 'open' AND masala_id IS NOT NULL")->fetchAll(PDO::FETCH_COLUMN);
        $w[] = "(m.review <> '' OR m.id IN (" . in_list($ids, $params) . '))';
    }
    // at least one selected rawi has a reading here matching hal/khilaf
    $sub = 'SELECT 1 FROM qiraat qq JOIN readings dd ON dd.rid = qq.rid WHERE qq.mid = w.mid AND qq.rawi IN (' . in_list($f['rawis'], $params) . ')'
         . ' AND dd.hal IN (' . in_list(hal_values($f), $params) . ')';
    if ($f['khilaf']) $sub .= ' AND qq.hafs = 0';
    $w[] = "EXISTS ($sub)";
    return implode(' AND ', $w);
}

/** Paged list of mawadi for the filters. → [rows, total] */
function find_mawadi(array $f, ?int $limit = null): array
{
    $params = [];
    $where = where_mawadi($f, $params);
    $total = (int)q(content(), "SELECT COUNT(*) FROM mawadi w JOIN masail m ON m.id = w.masala_id WHERE $where", $params)->fetchColumn();
    $limit ??= (int)cfg('page_size');
    $sql = "SELECT w.*, m.bab, m.naw, m.abyat, m.kalima, m.review, m.natija, m.marji, m.tahrir FROM mawadi w JOIN masail m ON m.id = w.masala_id
            WHERE $where ORDER BY w.sura_no, w.aya_no, w.word_no, m.id LIMIT $limit OFFSET " . (($f['page'] - 1) * $limit);
    return [q(content(), $sql, $params)->fetchAll(), $total];
}

/** Readings of the selected rawis at the given mawadi → mid => rawi => rows */
function readings_at(array $mids, array $f): array
{
    if (!$mids) return [];
    $params = [];
    $sql = 'SELECT q.mid, q.rid, q.rawi, q.lafz, q.wajh, q.hafs, d.wasf, d.hal, d.dalil, d.ramz, d.ord, d.ziyada
            FROM qiraat q JOIN readings d ON d.rid = q.rid JOIN rawis r ON r.name = q.rawi
            WHERE q.mid IN (' . in_list($mids, $params) . ') AND q.rawi IN (' . in_list($f['rawis'], $params) . ')
              AND d.hal IN (' . in_list(hal_values($f), $params) . ')
            ORDER BY r.ord, d.ord';
    $out = [];
    foreach (q(content(), $sql, $params) as $row) $out[$row['mid']][$row['rawi']][] = $row;
    return $out;
}

/**
 * Group rawis whose readings at a موضع are identical → [[rawis[], rows[]], ...] in canonical order.
 */
function group_by_reading(array $byRawi): array
{
    $groups = [];
    foreach ($byRawi as $rawi => $rows) {
        $sig = implode('¦', array_map(fn($r) => $r['rid'] . '/' . $r['lafz'] . '/' . $r['wajh'], $rows));
        $groups[$sig][0][] = $rawi;
        $groups[$sig][1] = $rows;
    }
    return array_values($groups);
}

function pager(int $total, int $page, int $size): string
{
    $pages = (int)ceil($total / max(1, $size));
    if ($pages <= 1) return '';
    $html = '<nav class="pager">';
    $win = array_unique(array_filter([1, $page - 2, $page - 1, $page, $page + 1, $page + 2, $pages], fn($p) => $p >= 1 && $p <= $pages));
    sort($win);
    $prev = 0;
    foreach ($win as $p) {
        if ($p - $prev > 1) $html .= '<span>…</span>';
        $html .= $p === $page ? "<b>$p</b>" : '<a href="' . h(url(['page' => $p], true)) . "\">$p</a>";
        $prev = $p;
    }
    return $html . '</nav>';
}

/** The shared filter form. */
function filter_form(array $f, string $page): string
{
    $suras = q(content(), 'SELECT DISTINCT sura_no, sura FROM mawadi ORDER BY sura_no')->fetchAll();
    $babs = q(content(), 'SELECT bab, MIN(abyat) a FROM masail GROUP BY bab ORDER BY CAST(a AS INTEGER)')->fetchAll(PDO::FETCH_COLUMN);
    $sel = array_flip($f['rawis']);
    ob_start(); ?>
<details class="fbox" open><summary>التصفية: <?= h(names_for($f['rawis'])) ?></summary>
<form class="filters" method="get" action="index.php">
  <input type="hidden" name="p" value="<?= h($page) ?>">
  <fieldset class="rawis">
    <legend>القراء والرواة <button type="button" class="link" data-all>الكل</button> · <button type="button" class="link" data-none>لا شيء</button></legend>
    <?php foreach (qurra() as $qari => $pair): ?>
      <div class="qari">
        <label class="qn"><input type="checkbox" data-qari> <?= h($qari) ?></label>
        <?php foreach ($pair as $r): ?>
          <label><input type="checkbox" name="r[]" value="<?= h($r) ?>" <?= isset($sel[$r]) ? 'checked' : '' ?>> <?= h($r) ?></label>
        <?php endforeach ?>
      </div>
    <?php endforeach ?>
  </fieldset>
  <div class="row">
    <label>السورة
      <select name="sura"><option value="">الكل</option>
        <?php foreach ($suras as $s): ?><option value="<?= $s['sura_no'] ?>" <?= $f['sura'] === (int)$s['sura_no'] ? 'selected' : '' ?>><?= $s['sura_no'] . '. ' . h($s['sura']) ?></option><?php endforeach ?>
      </select></label>
    <label>من آية <input type="number" name="from" min="1" value="<?= h((string)$f['from']) ?>" class="num"></label>
    <label>إلى <input type="number" name="to" min="1" value="<?= h((string)$f['to']) ?>" class="num"></label>
    <label>النوع
      <select name="naw"><option value="">الكل</option>
        <?php foreach (['فرش', 'أصول'] as $n): ?><option <?= $f['naw'] === $n ? 'selected' : '' ?>><?= $n ?></option><?php endforeach ?>
      </select></label>
    <label>الباب
      <select name="bab"><option value="">الكل</option>
        <?php foreach ($babs as $b): ?><option <?= $f['bab'] === $b ? 'selected' : '' ?>><?= h($b) ?></option><?php endforeach ?>
      </select></label>
    <label>الحال
      <select name="hal"><option value="">الوصل والوقف</option>
        <?php foreach (['وصلًا', 'وقفًا'] as $hv): ?><option <?= $f['hal'] === $hv ? 'selected' : '' ?>><?= $hv ?></option><?php endforeach ?>
      </select></label>
  </div>
  <div class="row">
    <label class="grow">بحث (الكلمة أو لفظ الراوي، بلا تشكيل) <input type="search" name="kw" value="<?= h($f['kw']) ?>"></label>
    <label>المسألة <input type="text" name="masala" value="<?= h($f['masala']) ?>" class="num" placeholder="2-021"></label>
    <label class="chk"><input type="checkbox" name="khilaf" value="1" <?= $f['khilaf'] ? 'checked' : '' ?>> ما خالف حفصًا فقط</label>
    <label class="chk"><input type="checkbox" name="review" value="1" <?= $f['review'] ? 'checked' : '' ?>> ما عليه مراجعة</label>
    <label>التحرير <select name="tahrir"><option value="">الكل</option><option value="*" <?= $f['tahrir'] === '*' ? 'selected' : '' ?>>كل ما فيه تحرير أو تنبيه</option>
      <?php foreach (TAHRIR_KINDS as $k => $_): ?><option <?= $f['tahrir'] === $k ? 'selected' : '' ?>><?= h($k) ?></option><?php endforeach ?></select></label>
    <button type="submit">عرض</button>
    <a class="btn ghost" href="<?= h(url(['p' => $page])) ?>">مسح</a>
  </div>
</form>
</details>
<?php
    return ob_get_clean();
}
