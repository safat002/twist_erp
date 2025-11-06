from __future__ import annotations

from typing import Any


def _get_finance_settings(company) -> dict[str, Any]:
    # Prefer a dedicated 'finance' section inside company.settings if present; fallback to top-level keys.
    settings = getattr(company, "settings", {}) or {}
    finance = settings.get("finance") or {}
    # Merge flat keys with nested finance keys (nested keys take precedence)
    merged = {**settings, **finance}
    return merged


def require_journal_review(company) -> bool:
    settings = _get_finance_settings(company)
    return bool(settings.get("require_journal_review", False))


def require_invoice_approval(company) -> bool:
    settings = _get_finance_settings(company)
    # External-facing docs default to approval required
    return bool(settings.get("require_invoice_approval", True))


def require_payment_approval(company) -> bool:
    settings = _get_finance_settings(company)
    return bool(settings.get("require_payment_approval", True))


def enforce_segregation_of_duties(company) -> bool:
    settings = _get_finance_settings(company)
    return bool(settings.get("enforce_finance_sod", True))


def enforce_period_posting(company) -> bool:
    settings = _get_finance_settings(company)
    return bool(settings.get("enforce_period_posting", True))


# Phase 6: Enhanced Configuration Functions

def should_auto_post_inventory_je(company) -> bool:
    """Check if inventory journal entries should be auto-posted"""
    settings = _get_finance_settings(company)
    return bool(settings.get("auto_post_inventory_je", False))


def should_auto_post_landed_cost(company) -> bool:
    """Check if landed cost adjustments should be auto-posted"""
    settings = _get_finance_settings(company)
    return bool(settings.get("auto_post_landed_cost", False))


def get_inventory_gl_sync_mode(company) -> str:
    """
    Get inventory-GL sync mode.
    Options: 'realtime', 'batch', 'manual'
    """
    settings = _get_finance_settings(company)
    return settings.get("inventory_gl_sync_mode", "realtime")


def get_reconciliation_tolerance_amount(company) -> str:
    """Get reconciliation tolerance amount (e.g., '0.01' for 1 cent)"""
    settings = _get_finance_settings(company)
    return str(settings.get("reconciliation_tolerance_amount", "0.01"))


def get_reconciliation_tolerance_percent(company) -> str:
    """Get reconciliation tolerance percentage (e.g., '1.0' for 1%)"""
    settings = _get_finance_settings(company)
    return str(settings.get("reconciliation_tolerance_percent", "1.0"))


def is_auto_reconciliation_enabled(company) -> bool:
    """Check if automatic reconciliation checks are enabled"""
    settings = _get_finance_settings(company)
    return bool(settings.get("enable_auto_reconciliation", False))

