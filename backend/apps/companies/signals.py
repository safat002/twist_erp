"""
Signal handlers for companies app.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Company
from .services import DefaultDataService
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Company)
def load_default_data_on_company_creation(sender, instance, created, **kwargs):
    """
    Automatically load industry-specific default data when a new company is created.

    This signal loads:
    - Currencies (BDT, USD, EUR)
    - Chart of Accounts (industry-specific)
    - Item Categories
    - Product Categories
    - Tax Categories
    - Cost Centers
    - Units of Measure
    """
    if created and not instance.default_data_loaded:
        try:
            logger.info(f"Loading default data for new company: {instance.name} ({instance.industry_category})")

            service = DefaultDataService(instance, created_by=instance.created_by)
            results = service.load_all_defaults()

            logger.info(f"Default data loaded successfully for {instance.name}: {results}")

        except Exception as e:
            logger.error(f"Failed to load default data for {instance.name}: {str(e)}", exc_info=True)
            # Don't raise - allow company creation to succeed even if default data loading fails
