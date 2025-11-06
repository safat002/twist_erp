// Persist and improve sidebar menu behavior (AdminLTE/Jazzmin)
(function () {
  var STORAGE_KEY = 'twist-admin:sidebar:open-items';

  function getContainer() {
    return document.querySelector('.nav-sidebar[data-widget="treeview"]') || document.querySelector('.nav-sidebar');
  }

  function setAccordionDisabled(container) {
    if (!container) return;
    try {
      container.setAttribute('data-accordion', 'false');
    } catch (_) {}
  }

  function readOpenSet() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return new Set();
      var arr = JSON.parse(raw);
      if (!Array.isArray(arr)) return new Set();
      return new Set(arr);
    } catch (_) {
      return new Set();
    }
  }

  function writeOpenSet(set) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(set)));
    } catch (_) {}
  }

  function idForItem(li) {
    if (!li) return null;
    // Prefer an id/data-id; fallback to link text
    var id = li.getAttribute('id') || li.dataset.key || null;
    if (id) return id;
    var a = li.querySelector(':scope > a');
    if (a && a.textContent) return a.textContent.trim();
    return null;
  }

  function applySaved(container, openSet) {
    var items = container.querySelectorAll('.nav-item.has-treeview, .has-treeview');
    items.forEach(function (li) {
      var key = idForItem(li);
      if (key && openSet.has(key)) {
        li.classList.add('menu-open');
        var tree = li.querySelector(':scope > .nav-treeview');
        if (tree) tree.style.display = 'block';
      }
    });
  }

  function bind(container, openSet) {
    container.addEventListener('click', function (e) {
      var a = e.target.closest('a');
      if (!a) return;
      // Toggle handlers are anchors that have a sibling .nav-treeview
      var li = a.parentElement;
      if (!li) return;
      var sub = li.querySelector(':scope > .nav-treeview');
      if (!sub) return; // leaf node; ignore
      // Delay to allow AdminLTE to toggle classes, then persist
      setTimeout(function () {
        var key = idForItem(li);
        if (!key) return;
        if (li.classList.contains('menu-open')) {
          openSet.add(key);
        } else {
          openSet.delete(key);
        }
        writeOpenSet(openSet);
      }, 0);
    }, true);
  }

  function init() {
    var container = getContainer();
    if (!container) return;
    setAccordionDisabled(container); // allow multiple open; avoid auto-close
    var openSet = readOpenSet();
    applySaved(container, openSet);
    bind(container, openSet);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

