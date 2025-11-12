from __future__ import annotations

from typing import Optional, Tuple

from apps.finance.models import InventoryPostingRule, Account


def resolve_inventory_accounts(
    *,
    company,
    product=None,
    warehouse=None,
    transaction_type: str = ''
) -> Tuple[Optional[Account], Optional[Account]]:
    """
    Resolve inventory and COGS accounts using a multi-level fallback matrix.

    Preference order (most specific → least):
        1. Budget-item or item specific rule (optionally scoped to warehouse/txn).
        2. Category/sub-category + warehouse/transaction combinations.
        3. Warehouse-type scoped rules.
        4. Transaction-only rules.
        5. Company default rule.
        6. Product's own inventory/expense accounts.
    """
    if not company:
        return None, None

    rules = InventoryPostingRule.objects.filter(company=company, is_active=True).order_by('priority', '-updated_at')
    budget_item = getattr(product, 'budget_item', None)
    item_obj = product
    sub_category = getattr(product, 'category', None)
    top_category = sub_category
    while top_category and top_category.parent_category:
        top_category = top_category.parent_category
    wh_type = getattr(warehouse, 'warehouse_type', '') if warehouse else ''
    txn = (transaction_type or '').upper()

    def pick_rule(qs):
        if txn:
            match = qs.filter(transaction_type=txn).first()
            if match:
                return match
        return qs.filter(transaction_type='').first() or qs.first()

    def match_item_rule(qs):
        if warehouse:
            rule = pick_rule(qs.filter(warehouse=warehouse))
            if rule:
                return rule
        return pick_rule(qs)

    if budget_item:
        rule = match_item_rule(rules.filter(budget_item=budget_item))
        if rule:
            return rule.inventory_account, rule.cogs_account

    if item_obj:
        rule = match_item_rule(rules.filter(item=item_obj))
        if rule:
            return rule.inventory_account, rule.cogs_account

    def match_by_matrix(category, sub_cat, wh):
        qs = rules
        if category is None:
            qs = qs.filter(category__isnull=True)
        else:
            qs = qs.filter(category=category)
        if sub_cat is None:
            qs = qs.filter(sub_category__isnull=True)
        else:
            qs = qs.filter(sub_category=sub_cat)
        if wh is None:
            qs = qs.filter(warehouse__isnull=True)
        else:
            qs = qs.filter(warehouse=wh)
        return pick_rule(qs)

    matrix_attempts = []
    if sub_category and warehouse:
        matrix_attempts.append((top_category or sub_category, sub_category, warehouse))
    if sub_category:
        matrix_attempts.append((top_category or sub_category, sub_category, None))
    if warehouse:
        matrix_attempts.append((top_category or sub_category, None, warehouse))
    matrix_attempts.append((top_category or sub_category, None, None))
    matrix_attempts.append((None, None, warehouse))
    matrix_attempts.append((None, None, None))

    for category, sub_cat, wh in matrix_attempts:
        rule = match_by_matrix(category, sub_cat, wh)
        if rule:
            return rule.inventory_account, rule.cogs_account

    patterns = [
        (top_category or sub_category, wh_type),
        (top_category or sub_category, ''),
        (None, wh_type),
        (None, ''),
    ]

    for category, warehouse_type in patterns:
        qs = rules
        if category:
            qs = qs.filter(category=category, sub_category__isnull=True, warehouse__isnull=True)
        else:
            qs = qs.filter(category__isnull=True, sub_category__isnull=True, warehouse__isnull=True)
        qs = qs.filter(warehouse_type=warehouse_type)
        rule = pick_rule(qs)
        if rule:
            return rule.inventory_account, rule.cogs_account

    txn_rule = pick_rule(rules.filter(category__isnull=True, sub_category__isnull=True, warehouse__isnull=True, warehouse_type=''))
    if txn_rule:
        return txn_rule.inventory_account, txn_rule.cogs_account

    inv_acct = getattr(product, 'inventory_account', None) if product else None
    cogs_acct = getattr(product, 'expense_account', None) if product else None
    return inv_acct, cogs_acct
