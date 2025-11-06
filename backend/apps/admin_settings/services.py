from typing import Dict, Optional, List, Set
from django.core.cache import cache
from django.db.models import Q
from apps.companies.models import Company, CompanyGroup
from .models import ModuleFeatureToggle


class FeatureService:
    """
    Service layer for feature toggle operations.

    Handles feature resolution, caching, and scope hierarchy.
    """

    CACHE_TTL = 300  # 5 minutes
    CACHE_PREFIX = 'features'

    @classmethod
    def get_cache_key(cls, scope_type: str, company_group_id: Optional[int] = None,
                     company_id: Optional[int] = None) -> str:
        """Generate cache key for feature toggles."""
        if scope_type == 'COMPANY' and company_id:
            return f"{cls.CACHE_PREFIX}:company:{company_id}"
        elif scope_type == 'GROUP' and company_group_id:
            return f"{cls.CACHE_PREFIX}:group:{company_group_id}"
        else:
            return f"{cls.CACHE_PREFIX}:global"

    @classmethod
    def invalidate_cache(cls, scope_type: str = None, company_group=None, company=None):
        """Invalidate feature cache for specific scope."""
        if scope_type == 'COMPANY' and company:
            cache.delete(cls.get_cache_key('COMPANY', company_id=company.id))
            # Also invalidate group and global caches as they may be used in resolution
            if company.company_group:
                cache.delete(cls.get_cache_key('GROUP', company_group_id=company.company_group.id))
        elif scope_type == 'GROUP' and company_group:
            cache.delete(cls.get_cache_key('GROUP', company_group_id=company_group.id))

        # Always invalidate global cache
        cache.delete(cls.get_cache_key('GLOBAL'))

    @classmethod
    def get_features_for_company(cls, company: Company) -> Dict[str, Dict]:
        """
        Get all resolved features for a company.

        Resolution order (later overrides earlier):
        1. Global features
        2. Company Group features
        3. Company-specific features

        Returns:
            Dict with feature keys as keys and feature data as values
            Example: {
                'finance.module': {'enabled': True, 'visible': True, 'status': 'enabled', ...},
                'finance.journal_vouchers': {'enabled': True, ...},
            }
        """
        cache_key = cls.get_cache_key('COMPANY', company_id=company.id)
        cached = cache.get(cache_key)

        if cached is not None:
            return cached

        # Build feature map with hierarchical resolution
        features = {}

        # 1. Global features
        global_features = ModuleFeatureToggle.objects.filter(
            scope_type='GLOBAL',
            is_enabled=True
        ).select_related('created_by', 'updated_by')

        for feature in global_features:
            features[feature.full_key] = cls._serialize_feature(feature)

        # 2. Company Group features (override global)
        if company.company_group:
            group_features = ModuleFeatureToggle.objects.filter(
                scope_type='GROUP',
                company_group=company.company_group,
            ).select_related('created_by', 'updated_by')

            for feature in group_features:
                # Group feature overrides global
                if feature.is_enabled:
                    features[feature.full_key] = cls._serialize_feature(feature)
                else:
                    # If explicitly disabled at group level, remove it
                    features.pop(feature.full_key, None)

        # 3. Company-specific features (override all)
        company_features = ModuleFeatureToggle.objects.filter(
            scope_type='COMPANY',
            company=company,
        ).select_related('created_by', 'updated_by')

        for feature in company_features:
            if feature.is_enabled:
                features[feature.full_key] = cls._serialize_feature(feature)
            else:
                # If explicitly disabled at company level, remove it
                features.pop(feature.full_key, None)

        # After building the feature map, calculate dependents
        cls._add_dependents_to_features(features)

        # Cache the result
        cache.set(cache_key, features, cls.CACHE_TTL)

        return features

    @classmethod
    def get_global_features(cls) -> Dict[str, Dict]:
        """Get all global features."""
        cache_key = cls.get_cache_key('GLOBAL')
        cached = cache.get(cache_key)

        if cached is not None:
            return cached

        features = {}
        global_features = ModuleFeatureToggle.objects.filter(
            scope_type='GLOBAL',
            is_enabled=True
        ).select_related('created_by', 'updated_by')

        for feature in global_features:
            features[feature.full_key] = cls._serialize_feature(feature)

        cache.set(cache_key, features, cls.CACHE_TTL)
        return features

    @classmethod
    def is_feature_enabled(cls, feature_key: str, company: Optional[Company] = None) -> bool:
        """
        Check if a specific feature is enabled.

        Args:
            feature_key: Full feature key (e.g., 'finance.journal_vouchers')
            company: Company context (optional)

        Returns:
            True if feature is enabled, False otherwise
        """
        if company:
            features = cls.get_features_for_company(company)
        else:
            features = cls.get_global_features()

        return feature_key in features and features[feature_key].get('enabled', False)

    @classmethod
    def is_feature_visible(cls, feature_key: str, company: Optional[Company] = None) -> bool:
        """Check if a feature is visible in menus."""
        if company:
            features = cls.get_features_for_company(company)
        else:
            features = cls.get_global_features()

        return feature_key in features and features[feature_key].get('visible', False)

    @classmethod
    def get_enabled_modules(cls, company: Optional[Company] = None) -> Set[str]:
        """Get set of enabled module names."""
        if company:
            features = cls.get_features_for_company(company)
        else:
            features = cls.get_global_features()

        modules = set()
        for key, data in features.items():
            if data.get('enabled') and '.module' in key:
                module_name = key.split('.')[0]
                modules.add(module_name)

        return modules

    @classmethod
    def check_dependencies(cls, feature_key: str, company: Optional[Company] = None) -> Dict[str, bool]:
        """
        Check if all dependencies for a feature are met.

        Returns:
            Dict with dependency keys as keys and their status as values
        """
        if company:
            features = cls.get_features_for_company(company)
        else:
            features = cls.get_global_features()

        feature_data = features.get(feature_key)
        if not feature_data:
            return {}

        dependencies = feature_data.get('depends_on', [])
        result = {}

        for dep_key in dependencies:
            result[dep_key] = cls.is_feature_enabled(dep_key, company)

        return result

    @classmethod
    def _serialize_feature(cls, feature: ModuleFeatureToggle) -> Dict:
        """Serialize feature toggle to dictionary."""
        return {
            'enabled': feature.is_enabled,
            'visible': feature.is_visible,
            'status': feature.status,
            'name': feature.feature_name,
            'description': feature.description,
            'help_text': feature.help_text,
            'icon': feature.icon,
            'config': feature.config,
            'depends_on': feature.depends_on,
            'priority': feature.priority,
            'scope_type': feature.scope_type,
            # 'dependents' will be added later in the view layer via compute_dependents
        }

    @classmethod
    def compute_dependents(cls, features: Dict[str, Dict]) -> Dict[str, Dict[str, list]]:
        """
        Given a feature map (key -> data with 'depends_on'), compute reverse dependencies.

        Returns a mapping of feature_key -> {
            'dependent_keys': [list of feature keys that depend on this feature],
            'dependents': [list of display names of those features]
        }
        """
        dependents_map: Dict[str, Dict[str, list]] = {}

        # Initialize
        for key in features.keys():
            dependents_map[key] = {'dependent_keys': [], 'dependents': []}

        for key, data in features.items():
            deps = data.get('depends_on') or []
            # Normalize dependency keys to full keys if module-only specified
            for dep_key in deps:
                # Accept both 'module.feature' and 'module' forms; expand 'module' to 'module.module'
                normalized = dep_key if '.' in dep_key else f"{dep_key}.module"
                if normalized not in dependents_map:
                    # If dependency key not present in features map (e.g., disabled or missing), still record key
                    dependents_map.setdefault(normalized, {'dependent_keys': [], 'dependents': []})
                dependents_map[normalized]['dependent_keys'].append(key)

        # Populate human-readable names
        for dep_key, info in dependents_map.items():
            names = []
            for dkey in info['dependent_keys']:
                dname = features.get(dkey, {}).get('name') or dkey
                names.append(dname)
            info['dependents'] = names

        return dependents_map

    @classmethod
    def _add_dependents_to_features(cls, features: Dict[str, Dict]):
        """
        Calculate and add a 'dependents' list to each feature.
        This is the reverse of 'depends_on'.
        """
        # Initialize dependents list for all features
        for key in features:
            features[key]['dependents'] = []

        # Build the reverse dependency map
        for key, data in features.items():
            dependencies = data.get('depends_on', [])
            if not dependencies:
                continue

            for dep_key in dependencies:
                if dep_key in features:
                    # Add the current feature's name as a dependent
                    dependent_name = data.get('name', key)
                    if dependent_name not in features[dep_key]['dependents']:
                        features[dep_key]['dependents'].append(dependent_name)
