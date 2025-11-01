"""
Core ID Factory - Deterministic ID and Code Generation
Generates all system identifiers automatically and consistently
"""

import re
import hashlib
from functools import lru_cache
from typing import Dict, List, Optional
from django.core.cache import cache


class IDFactory:
    """
    Central factory for generating all system identifiers.
    All IDs are deterministic - same input always produces same output.
    """

    # Separator constants
    PERMISSION_SEP = "_"
    API_SEP = "-"
    MENU_SEP = "-"

    # Module prefix mapping (for table names)
    MODULE_PREFIXES = {
        'finance': 'fin',
        'procurement': 'pro',
        'inventory': 'inv',
        'sales': 'sal',
        'production': 'prd',
        'hr': 'hr',
        'assets': 'ast',
        'projects': 'prj',
        'budgeting': 'bdg',
        'ai_companion': 'aic',
        'workflows': 'wfl',
        'metadata': 'meta',
        'permissions': 'perm',
        'users': 'usr',
        'companies': 'cmp',
        'audit': 'aud',
        'notifications': 'ntf',
        'dashboard': 'dsh',
        'report_builder': 'rpt',
        'form_builder': 'frm',
        'tasks': 'tsk',
        'security': 'sec',
    }

    # ================================================================
    # PERMISSION CODES
    # ================================================================

    @staticmethod
    @lru_cache(maxsize=1000)
    def make_permission_codes(app_label: str, model_name: str) -> Dict[str, str]:
        """
        Generate standard CRUD permission codes.

        Args:
            app_label: Django app label (e.g., 'finance')
            model_name: Model class name (e.g., 'JournalVoucher')

        Returns:
            dict with keys: view, create, update, delete

        Example:
            >>> IDFactory.make_permission_codes('finance', 'JournalVoucher')
            {
                'view': 'finance_view_journal_voucher',
                'create': 'finance_create_journal_voucher',
                'update': 'finance_update_journal_voucher',
                'delete': 'finance_delete_journal_voucher'
            }
        """
        base = IDFactory._normalize_for_permission(model_name)
        sep = IDFactory.PERMISSION_SEP

        return {
            'view': f"{app_label}{sep}view{sep}{base}",
            'create': f"{app_label}{sep}create{sep}{base}",
            'update': f"{app_label}{sep}update{sep}{base}",
            'delete': f"{app_label}{sep}delete{sep}{base}",
        }

    @staticmethod
    @lru_cache(maxsize=500)
    def make_extra_permission(app_label: str, model_name: str, action: str) -> str:
        """
        Generate custom permission code for special actions.

        Args:
            app_label: Django app label
            model_name: Model class name
            action: Custom action (e.g., 'approve', 'post', 'export')

        Returns:
            Permission code string

        Example:
            >>> IDFactory.make_extra_permission('procurement', 'PurchaseOrder', 'approve')
            'procurement_approve_purchase_order'
        """
        base = IDFactory._normalize_for_permission(model_name)
        action = IDFactory._normalize_for_permission(action)
        sep = IDFactory.PERMISSION_SEP

        return f"{app_label}{sep}{action}{sep}{base}"

    @staticmethod
    def _normalize_for_permission(name: str) -> str:
        """Convert model/action name to permission format (snake_case lowercase)"""
        # CamelCase to snake_case
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
        return s2.lower().replace(' ', '_').replace('-', '_')

    # ================================================================
    # API PATHS
    # ================================================================

    @staticmethod
    @lru_cache(maxsize=500)
    def make_api_path(app_label: str, model_name: str, version: str = 'v1', pluralize: bool = True) -> str:
        """
        Generate REST API path.

        Args:
            app_label: Django app label
            model_name: Model class name
            version: API version (default: 'v1')
            pluralize: Add 's' to make plural (default: True)

        Returns:
            API path string

        Example:
            >>> IDFactory.make_api_path('finance', 'JournalVoucher')
            '/api/v1/finance/journal-vouchers/'
        """
        base = IDFactory._normalize_for_url(model_name)

        if pluralize:
            base = IDFactory._pluralize(base)

        return f"/api/{version}/{app_label}/{base}/"

    @staticmethod
    def _normalize_for_url(name: str) -> str:
        """Convert model name to URL format (kebab-case lowercase)"""
        # CamelCase to kebab-case
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1)
        return s2.lower().replace('_', '-')

    @staticmethod
    def _pluralize(word: str) -> str:
        """Simple English pluralization"""
        # Already plural
        if word.endswith('s') or word.endswith('data'):
            return word

        # Special cases
        special_plurals = {
            'person': 'people',
            'child': 'children',
            'man': 'men',
            'woman': 'women',
            'tooth': 'teeth',
            'foot': 'feet',
            'analysis': 'analyses',
            'invoice': 'invoices',  # Not invoicees
        }

        if word in special_plurals:
            return special_plurals[word]

        # Standard rules
        if word.endswith('y') and len(word) > 1 and word[-2] not in 'aeiou':
            return word[:-1] + 'ies'  # company -> companies
        elif word.endswith(('s', 'x', 'z', 'ch', 'sh')):
            return word + 'es'  # box -> boxes
        else:
            return word + 's'

    # ================================================================
    # UI MENU KEYS
    # ================================================================

    @staticmethod
    @lru_cache(maxsize=500)
    def make_menu_key(app_label: str, model_name: str, pluralize: bool = True) -> str:
        """
        Generate UI menu/route key.

        Args:
            app_label: Django app label
            model_name: Model class name
            pluralize: Make plural (default: True)

        Returns:
            Menu key string

        Example:
            >>> IDFactory.make_menu_key('finance', 'JournalVoucher')
            'finance-journal-vouchers'
        """
        base = IDFactory._normalize_for_url(model_name)

        if pluralize:
            base = IDFactory._pluralize(base)

        return f"{app_label}{IDFactory.MENU_SEP}{base}"

    # ================================================================
    # METADATA TABLE/COLUMN NAMES
    # ================================================================

    @staticmethod
    @lru_cache(maxsize=500)
    def make_table_name(app_label: str, model_name: str) -> str:
        """
        Generate metadata table name (for visual data model and BI).

        Args:
            app_label: Django app label
            model_name: Model class name

        Returns:
            Table name string

        Example:
            >>> IDFactory.make_table_name('finance', 'JournalVoucher')
            'fin_journal_voucher'
        """
        # Get module prefix (3 chars)
        prefix = IDFactory.MODULE_PREFIXES.get(app_label, app_label[:3])

        # Normalize model name to snake_case
        base = IDFactory._normalize_for_permission(model_name)

        return f"{prefix}_{base}"

    @staticmethod
    @lru_cache(maxsize=1000)
    def make_column_name(table_name: str, field_name: str, is_custom: bool = False) -> str:
        """
        Generate metadata column name.

        Args:
            table_name: Table name (from make_table_name)
            field_name: Field name
            is_custom: Whether this is a user-added custom field

        Returns:
            Column name string

        Example:
            >>> IDFactory.make_column_name('fin_journal_voucher', 'entry_date', False)
            'entry_date'
            >>> IDFactory.make_column_name('fin_journal_voucher', 'custom_color', True)
            'fld_fin_journal_voucher_custom_color'
        """
        normalized_field = IDFactory._normalize_for_permission(field_name)

        if is_custom:
            return f"fld_{table_name}_{normalized_field}"
        else:
            return normalized_field

    # ================================================================
    # DOCUMENT NUMBER TYPES
    # ================================================================

    @staticmethod
    @lru_cache(maxsize=100)
    def make_doc_type(app_label: str, model_name: str) -> str:
        """
        Generate document type code for numbering.

        Args:
            app_label: Django app label
            model_name: Model class name

        Returns:
            Document type code (2-4 uppercase letters)

        Example:
            >>> IDFactory.make_doc_type('finance', 'JournalVoucher')
            'JV'
            >>> IDFactory.make_doc_type('procurement', 'PurchaseOrder')
            'PO'
        """
        # Common abbreviations
        abbreviations = {
            'JournalVoucher': 'JV',
            'PurchaseOrder': 'PO',
            'SalesOrder': 'SO',
            'GoodsReceiptNote': 'GRN',
            'GoodsReturnNote': 'GRN',
            'APBill': 'BILL',
            'ARInvoice': 'INV',
            'Payment': 'PAY',
            'Receipt': 'RCP',
            'AssetRegistration': 'AR',
            'WorkOrder': 'WO',
            'StockAdjustment': 'SA',
            'StockTransfer': 'ST',
            'LoanDisbursement': 'LD',
            'LoanRepayment': 'LR',
        }

        if model_name in abbreviations:
            return abbreviations[model_name]

        # Auto-generate from initials
        # JournalVoucher -> JV, PurchaseRequisition -> PR
        words = re.findall('[A-Z][a-z]*', model_name)
        if len(words) >= 2:
            return ''.join(word[0] for word in words).upper()
        elif len(words) == 1:
            return words[0][:3].upper()
        else:
            return model_name[:3].upper()

    # ================================================================
    # COLLISION DETECTION
    # ================================================================

    @staticmethod
    def check_permission_collision(codes: Dict[str, str]) -> tuple[bool, List[str]]:
        """
        Check if generated permission codes collide with existing ones.

        Args:
            codes: Dict of permission codes to check

        Returns:
            Tuple of (has_collision, list_of_colliding_codes)
        """
        try:
            from apps.permissions.models import Permission

            existing_codes = set(
                Permission.objects.filter(
                    code__in=codes.values()
                ).values_list('code', flat=True)
            )

            collisions = [code for code in codes.values() if code in existing_codes]
            return len(collisions) > 0, collisions

        except Exception:
            # Table doesn't exist yet (during initial migration)
            return False, []

    @staticmethod
    def resolve_collision(code: str, strategy: str = 'suffix') -> str:
        """
        Resolve code collision.

        Args:
            code: Original code that collided
            strategy: 'suffix' (add _2), 'hash' (add short hash), 'fail' (raise error)

        Returns:
            Resolved code

        Raises:
            ValueError: If strategy is 'fail'
        """
        if strategy == 'fail':
            raise ValueError(f"Permission code collision: {code}")

        elif strategy == 'hash':
            # Add short hash based on timestamp
            import time
            hash_val = hashlib.md5(f"{code}{time.time()}".encode()).hexdigest()[:6]
            return f"{code}_{hash_val}"

        else:  # suffix
            # Try _2, _3, etc.
            try:
                from apps.permissions.models import Permission
                counter = 2
                while Permission.objects.filter(code=f"{code}_{counter}").exists():
                    counter += 1
                return f"{code}_{counter}"
            except:
                return f"{code}_2"

    # ================================================================
    # CACHING UTILITIES
    # ================================================================

    @staticmethod
    def get_cached_permission_codes(app_label: str, model_name: str, ttl: int = 3600) -> Dict[str, str]:
        """
        Get permission codes with Redis caching.

        Args:
            app_label: Django app label
            model_name: Model class name
            ttl: Cache time-to-live in seconds (default: 1 hour)

        Returns:
            Dict of permission codes
        """
        cache_key = f"id_factory:perms:{app_label}:{model_name}"
        codes = cache.get(cache_key)

        if codes is None:
            codes = IDFactory.make_permission_codes(app_label, model_name)
            cache.set(cache_key, codes, timeout=ttl)

        return codes

    @staticmethod
    def invalidate_cache(app_label: str = None, model_name: str = None):
        """
        Invalidate cached IDs.

        Args:
            app_label: If provided, invalidate only this app (or all if None)
            model_name: If provided, invalidate only this model
        """
        if app_label and model_name:
            # Specific model
            cache_key = f"id_factory:perms:{app_label}:{model_name}"
            cache.delete(cache_key)
        elif app_label:
            # All models in app (pattern delete - Redis only)
            try:
                cache.delete_pattern(f"id_factory:perms:{app_label}:*")
            except AttributeError:
                # Fallback for non-Redis cache backends
                pass
        else:
            # Clear all ID factory cache
            try:
                cache.delete_pattern("id_factory:*")
            except AttributeError:
                pass

        # Clear LRU caches
        IDFactory.make_permission_codes.cache_clear()
        IDFactory.make_extra_permission.cache_clear()
        IDFactory.make_api_path.cache_clear()
        IDFactory.make_menu_key.cache_clear()
        IDFactory.make_table_name.cache_clear()
        IDFactory.make_column_name.cache_clear()
        IDFactory.make_doc_type.cache_clear()

    # ================================================================
    # VALIDATION
    # ================================================================

    @staticmethod
    def validate_id(id_value: str, id_type: str) -> tuple[bool, Optional[str]]:
        """
        Validate that an ID follows naming conventions.

        Args:
            id_value: The ID to validate
            id_type: Type of ID ('permission', 'api_path', 'menu_key', 'table_name')

        Returns:
            Tuple of (is_valid, error_message)
        """
        if id_type == 'permission':
            # Must be lowercase, underscores only, app_action_model format
            pattern = r'^[a-z_]+_[a-z_]+_[a-z_]+$'
            if not re.match(pattern, id_value):
                return False, "Permission must be lowercase with underscores in app_action_model format"

        elif id_type == 'api_path':
            # Must be /api/version/app/resource/ format
            pattern = r'^/api/v\d+/[a-z-]+/[a-z-]+/$'
            if not re.match(pattern, id_value):
                return False, "API path must be /api/v1/app/resource/ format"

        elif id_type == 'menu_key':
            # Must be app-resource format
            pattern = r'^[a-z]+-[a-z-]+$'
            if not re.match(pattern, id_value):
                return False, "Menu key must be lowercase with hyphens in app-resource format"

        elif id_type == 'table_name':
            # Must be prefix_model format
            pattern = r'^[a-z]+_[a-z_]+$'
            if not re.match(pattern, id_value):
                return False, "Table name must be lowercase with underscores in prefix_model format"

        return True, None


# Convenience functions (module-level)
def make_permission_codes(app_label: str, model_name: str) -> Dict[str, str]:
    """Shortcut to IDFactory.make_permission_codes"""
    return IDFactory.make_permission_codes(app_label, model_name)


def make_api_path(app_label: str, model_name: str) -> str:
    """Shortcut to IDFactory.make_api_path"""
    return IDFactory.make_api_path(app_label, model_name)


def make_menu_key(app_label: str, model_name: str) -> str:
    """Shortcut to IDFactory.make_menu_key"""
    return IDFactory.make_menu_key(app_label, model_name)


def make_table_name(app_label: str, model_name: str) -> str:
    """Shortcut to IDFactory.make_table_name"""
    return IDFactory.make_table_name(app_label, model_name)


def make_doc_type(app_label: str, model_name: str) -> str:
    """Shortcut to IDFactory.make_doc_type"""
    return IDFactory.make_doc_type(app_label, model_name)
