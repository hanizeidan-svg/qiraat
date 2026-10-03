<?php
// انسخ هذا الملف إلى config.php وعدّل القيم.
return [
    'site_title'  => 'مسائل الشاطبية',
    // قاعدة المحتوى (تُولَّد من data/masail/*.yaml بالأمر: python scripts/build_masail.py) — للقراءة فقط
    'content_db'  => __DIR__ . '/../data/out/qiraat.db',
    // قاعدة المراجعات والمستخدمين — يكتب فيها التطبيق، ولا يمسها إعادة البناء
    'reviews_db'  => __DIR__ . '/data/reviews.db',
    // true: التصفح متاح للجميع، والإبلاغ للمراجعين. false: كل شيء بعد الدخول.
    'public_read' => true,
    'page_size'   => 40,
];
