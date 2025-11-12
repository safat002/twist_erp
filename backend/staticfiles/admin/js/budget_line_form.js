// Dynamic show/hide and required rules for Budget Line form in Django Admin
(function () {
  function q(sel) { return document.querySelector(sel); }
  function qa(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  function getFieldEl(name) {
    var el = q('[name="' + name + '"]');
    if (!el) return null;
    // Jazzmin/AdminLTE wraps inputs in .form-group or .row .col-*
    var container = el.closest('.form-group') || el.closest('.row') || el.closest('div');
    return { input: el, container: container };
  }

  function setVisible(name, visible) {
    var fe = getFieldEl(name);
    if (!fe || !fe.container) return;
    fe.container.style.display = visible ? '' : 'none';
  }

  function setRequired(name, required) {
    var fe = getFieldEl(name);
    if (!fe || !fe.input) return;
    try {
      fe.input.required = !!required;
      if (required) {
        fe.input.setAttribute('aria-required', 'true');
      } else {
        fe.input.removeAttribute('aria-required');
      }
    } catch (_) {}
  }

  function ensureHintContainer() {
    var budgetSel = q('select[name="budget"]');
    if (!budgetSel) return null;
    var parent = budgetSel.closest('.form-group') || budgetSel.closest('.row') || budgetSel.parentElement;
    if (!parent) return null;
    var hint = q('#budget-type-hint');
    if (!hint) {
      hint = document.createElement('div');
      hint.id = 'budget-type-hint';
      hint.style.fontSize = '12px';
      hint.style.color = '#6c757d';
      hint.style.marginTop = '6px';
      parent.appendChild(hint);
    }
    return hint;
  }

  function setHint(bt) {
    var hint = ensureHintContainer();
    if (!hint) return;
    var t = String(bt || '').toLowerCase();
    if (t === 'operational') {
      hint.textContent = 'Operational/Production budget: Product and Item are required. Item Name auto-fills from Item; Sub-Category optional.';
    } else if (t === 'revenue') {
      hint.textContent = 'Revenue budget: Product is required; Item fields are hidden here.';
    } else if (t) {
      hint.textContent = 'This budget type hides Product, Item and Sub-Category in this form.';
    } else {
      hint.textContent = '';
    }
  }

  function applyForType(bt) {
    var t = String(bt || '').toLowerCase();
    if (t === 'operational') {
      setVisible('product', true);
      setVisible('item', true);
      setVisible('sub_category', true);
      setRequired('product', true);
      setRequired('item', true);
    } else if (t === 'revenue') {
      setVisible('product', true);
      setVisible('item', false);
      setVisible('sub_category', false);
      setRequired('product', true);
      setRequired('item', false);
    } else {
      // OPEX/CAPEX or others
      setVisible('product', false);
      setVisible('item', false);
      setVisible('sub_category', false);
      setRequired('product', false);
      setRequired('item', false);
    }
    setHint(bt);
  }

  async function fetchBudgetType(id) {
    if (!id) return null;
    // Prefer inline map on the widget if present
    try {
      var sel = q('select[name="budget"]');
      if (sel) {
        var mapRaw = sel.getAttribute('data-budget-types');
        if (mapRaw) {
          var map = JSON.parse(mapRaw);
          var bt = map && map[String(id)];
          if (bt) return bt;
        }
        var init = sel.getAttribute('data-initial-type');
        if (init && String(sel.value) === String(id)) return init;
      }
    } catch (_) {}
    try {
      var res = await fetch('/api/v1/budgets/periods/' + id + '/');
      if (!res.ok) return null;
      var data = await res.json();
      return data && data.budget_type ? data.budget_type : null;
    } catch (_) { return null; }
  }

  async function onBudgetChange() {
    var budgetSel = q('select[name="budget"]');
    if (!budgetSel) return;
    var id = budgetSel.value || '';
    var bt = await fetchBudgetType(id);
    applyForType(bt);
  }

  function init() {
    // presence check: only run on BudgetLine admin forms
    var budgetSel = q('select[name="budget"]');
    if (!budgetSel) return;
    // initial
    onBudgetChange();
    // change listener
    budgetSel.addEventListener('change', onBudgetChange);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
