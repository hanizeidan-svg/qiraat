// قارئ ⇄ راوياه في نموذج التصفية
document.querySelectorAll('.filters .qari').forEach(box => {
  const q = box.querySelector('[data-qari]');
  const rs = [...box.querySelectorAll('input[name="r[]"]')];
  const sync = () => { const n = rs.filter(r => r.checked).length; q.checked = n === rs.length; q.indeterminate = n > 0 && n < rs.length; };
  q.addEventListener('change', () => { rs.forEach(r => r.checked = q.checked); sync(); });
  rs.forEach(r => r.addEventListener('change', sync));
  sync();
});
document.querySelectorAll('[data-all],[data-none]').forEach(b => b.addEventListener('click', () => {
  const on = b.hasAttribute('data-all');
  b.closest('form').querySelectorAll('input[name="r[]"], [data-qari]').forEach(c => { c.checked = on; c.indeterminate = false; });
}));

// على الشاشات الصغيرة تبدأ التصفية مطويّة
if (matchMedia('(max-width: 700px)').matches) document.querySelectorAll('details.fbox').forEach(d => d.open = false);
