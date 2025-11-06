from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import ModuleFeatureToggle


@receiver(post_save, sender=ModuleFeatureToggle)
def invalidate_feature_cache_on_save(sender, instance, **kwargs):
    """Invalidate feature cache when a toggle is created or updated."""
    from .services import FeatureService
    FeatureService.invalidate_cache(
        instance.scope_type,
        instance.company_group,
        instance.company
    )


@receiver(post_delete, sender=ModuleFeatureToggle)
def invalidate_feature_cache_on_delete(sender, instance, **kwargs):
    """Invalidate feature cache when a toggle is deleted."""
    from .services import FeatureService
    FeatureService.invalidate_cache(
        instance.scope_type,
        instance.company_group,
        instance.company
    )
