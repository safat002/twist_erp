// Persist collapse/expand state for Django Admin fieldsets and groups across navigations
// Works with Jazzmin as well as stock Django admin
(function () {
  function storageKeyFor(el, idx) {
    try {
      var path = window.location.pathname || 'path';
      var id = el.getAttribute('id') || el.dataset.collapseId || String(idx);
      var model = document.body ? (document.body.getAttribute('data-app') + '.' + document.body.getAttribute('data-model')) : '';
      return ['twist-admin', 'collapse', model || '', path, id].filter(Boolean).join(':');
    } catch (e) {
      return 'twist-admin:collapse:' + (idx || '0');
    }
  }

  function applySavedState(el, key) {
    try {
      var saved = localStorage.getItem(key);
      if (saved === 'open') {
        el.classList.remove('collapsed');
        // Some themes wrap content; ensure content is visible
        var content = el.querySelector('.collapse, .card-body, .module, .fieldset-content');
        if (content && content.style && content.style.display === 'none') {
          content.style.display = '';
        }
      }
    } catch (_) {}
  }

  function bindToggle(el, key) {
    // Stock Django: h2 is the toggle; Jazzmin often uses .card-header
    var header = el.querySelector('h2, legend, .card-header, .grp-collapse-handler');
    if (!header) return;
    header.addEventListener('click', function () {
      // Delay until theme's JS toggles classes
      setTimeout(function () {
        var isCollapsed = el.classList.contains('collapsed');
        try {
          localStorage.setItem(key, isCollapsed ? 'closed' : 'open');
        } catch (_) {}
      }, 0);
    }, true);
  }

  function init() {
    var targets = Array.prototype.slice.call(document.querySelectorAll('fieldset.collapse, .inline-group.collapse, .card.collapse, .module.collapse'));
    targets.forEach(function (el, idx) {
      var key = storageKeyFor(el, idx);
      applySavedState(el, key);
      bindToggle(el, key);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

