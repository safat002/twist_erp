from __future__ import annotations

from typing import Optional, Tuple

from apps.finance.models import InventoryPostingRule, Account


def resolve_inventory_accounts(*, company, product=None, warehouse=None, transaction_type: str = '') -> Tuple[Optional[Account], Optional[Account]]:
    """
    Resolve inventory and COGS accounts using posting rules with a fallback cascade.

    Cascade order (most specific → least):
    - category + warehouse_type + txn
    - category + warehouse_type
    - category + txn
    - category only
    - warehouse_type + txn
    - warehouse_type only
    - txn only
    If none found, fall back to product-level accounts (if provided), else None.
    """
    if not company:
        return None, None

    rules = InventoryPostingRule.objects.filter(company=company, is_active=True)
    cat = getattr(product, 'category', None)
    wh_type = getattr(warehouse, 'warehouse_type', '') if warehouse else ''
    txn = (transaction_type or '').upper()

    patterns = [
        (cat, wh_type, txn),
        (cat, wh_type, ''),
        (cat, '', txn),
        (cat, '', ''),
        (None, wh_type, txn),
        (None, wh_type, ''),
        (None, '', txn),
    ]

    for c, w, t in patterns:
        qs = rules
        if c is not None:
            qs = qs.filter(category=c)
        else:
            qs = qs.filter(category__isnull=True)
        if w:
            qs = qs.filter(warehouse_type=w)
        else:
            qs = qs.filter(warehouse_type='')
        if t:
            qs = qs.filter(transaction_type=t)
        else:
            qs = qs.filter(transaction_type='')

        match = qs.first()
        if match:
            return match.inventory_account, match.cogs_account

    inv_acct = getattr(product, 'inventory_account', None) if product else None
    cogs_acct = getattr(product, 'expense_account', None) if product else None
    return inv_acct, cogs_acct

