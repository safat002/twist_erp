"""
Product Model - For saleable items in Sales/CRM module
Products are what you sell to customers.
"""
from decimal import Decimal
from django.conf import settings
from django.db import models


class Product(models.Model):
    """
    Products are saleable items sold to customers.
    Can optionally link to an Item for inventory tracking.

    Different from Item (in inventory app) which represents operational items.
    """

    PRODUCT_TYPE_CHOICES = [
        ('GOODS', 'Goods'),
        ('SERVICE', 'Service'),
    ]

    # Base fields
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        help_text="Company this record belongs to"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Identification
    code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Classification
    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPE_CHOICES,
        default='GOODS',
        help_text="Type of product"
    )

    # Link to inventory (optional)
    linked_item = models.ForeignKey(
        'inventory.Item',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        help_text="Link to inventory item if this product needs stock tracking"
    )

    # Pricing
    selling_price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text="Standard selling price"
    )
    mrp = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text="Maximum Retail Price"
    )
    cost_price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text="Reference cost for margin calculation"
    )

    # Discounting
    allow_discount = models.BooleanField(default=True)
    max_discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Maximum discount percentage allowed"
    )

    # Taxation
    tax_category = models.ForeignKey(
        'TaxCategory',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Tax category for automatic tax calculation"
    )
    hsn_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="Harmonized System Nomenclature code for GST/VAT"
    )

    # Accounting
    sales_account = models.ForeignKey(
        'finance.Account',
        on_delete=models.PROTECT,
        related_name='sales_products',
        help_text="Sales revenue account"
    )
    revenue_account = models.ForeignKey(
        'finance.Account',
        on_delete=models.PROTECT,
        related_name='revenue_products',
        null=True,
        blank=True,
        help_text="Alternative revenue account (if different from sales)"
    )

    # Master data
    category = models.ForeignKey(
        'ProductCategory',
        on_delete=models.PROTECT,
        help_text="Product category for classification and reporting"
    )
    uom = models.ForeignKey(
        'inventory.UnitOfMeasure',
        on_delete=models.PROTECT,
        related_name='products',
        help_text="Unit of measure"
    )

    # E-commerce / Customer portal
    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(
        default=False,
        help_text="Visible in customer portal/e-commerce"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Sort order in listings"
    )

    # Images and media
    image_url = models.URLField(blank=True, max_length=500)
    thumbnail_url = models.URLField(blank=True, max_length=500)

    # Backward compatibility (link to old Product model during migration)
    legacy_product_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Link to original Product record (for migration tracking)"
    )

    class Meta:
        db_table = 'sales_product'
        unique_together = ('company', 'code')
        indexes = [
            models.Index(fields=['company', 'category']),
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['company', 'is_published']),
            models.Index(fields=['company', 'code']),
        ]
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def available_quantity(self):
        """Get available stock from linked item"""
        if self.linked_item:
            return self.linked_item.get_available_stock()
        return Decimal('0.00')

    def get_price_for_customer(self, customer=None, quantity=1):
        """
        Get price for specific customer considering:
        - Customer-specific pricing
        - Quantity discounts
        - Customer group pricing
        TODO: Implement customer pricing matrix
        """
        return self.selling_price

    def calculate_margin(self):
        """Calculate profit margin"""
        if self.selling_price > 0:
            margin = ((self.selling_price - self.cost_price) / self.selling_price) * 100
            return round(margin, 2)
        return 0.00


class ProductCategory(models.Model):
    """
    Categories for saleable products (hierarchical)
    Supports: Category → Sub-Category → Sub-Sub-Category → ...
    """
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        help_text="Company this record belongs to"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Hierarchical structure
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='sub_categories',
        help_text="Parent category (null for root categories)"
    )

    # Hierarchy path for efficient queries
    hierarchy_path = models.CharField(
        max_length=500,
        editable=False,
        blank=True,
        db_index=True,
        help_text='Path: 1/2/3/4 for efficient hierarchy queries'
    )

    # Level in hierarchy
    level = models.IntegerField(default=0, editable=False)

    # Sales-specific fields
    display_order = models.IntegerField(
        default=0,
        help_text="Sort order in listings"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Featured category (e-commerce)"
    )

    is_active = models.BooleanField(default=True)

    # NEW: Default template flag
    is_default_template = models.BooleanField(
        default=False,
        help_text="System default category that can be customized"
    )

    class Meta:
        db_table = 'sales_product_category'
        unique_together = ('company', 'code')
        verbose_name_plural = 'Product Categories'
        ordering = ['display_order', 'code']
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['company', 'parent_category']),
            models.Index(fields=['hierarchy_path']),
        ]

    def __str__(self):
        return self.get_full_path()

    def save(self, *args, **kwargs):
        # Calculate level and hierarchy path
        if self.parent_category:
            self.level = self.parent_category.level + 1
            parent_path = self.parent_category.hierarchy_path or str(self.parent_category.id)
            if not self.pk:
                self.hierarchy_path = f"{parent_path}/new"
            else:
                self.hierarchy_path = f"{parent_path}/{self.id}"
        else:
            self.level = 0
            if not self.pk:
                self.hierarchy_path = "new"
            else:
                self.hierarchy_path = str(self.id)

        super().save(*args, **kwargs)

        # Update hierarchy path if new record
        if 'new' in self.hierarchy_path:
            if self.parent_category:
                parent_path = self.parent_category.hierarchy_path or str(self.parent_category.id)
                new_path = f"{parent_path}/{self.id}"
            else:
                new_path = str(self.id)

            ProductCategory.objects.filter(pk=self.pk).update(hierarchy_path=new_path)
            self.hierarchy_path = new_path

    def get_ancestors(self):
        """Get all parent categories up to root"""
        ancestors = []
        current = self.parent_category
        while current:
            ancestors.insert(0, current)
            current = current.parent_category
        return ancestors

    def get_descendants(self):
        """Get all child categories (recursive)"""
        return ProductCategory.objects.filter(
            company=self.company,
            hierarchy_path__startswith=self.hierarchy_path + '/'
        )

    def get_full_path(self):
        """Get full category path: 'Electronics / Mobile Phones / Smartphones'"""
        ancestors = self.get_ancestors()
        path_parts = [a.name for a in ancestors] + [self.name]
        return ' / '.join(path_parts)


class TaxCategory(models.Model):
    """Tax categories for products"""
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        help_text="Company this record belongs to"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Tax rates
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Tax rate percentage"
    )

    # Tax configuration (JSON for flexibility)
    tax_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tax configuration: {type: 'GST', cgst: 9, sgst: 9} or {type: 'VAT', rate: 15}"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'sales_tax_category'
        unique_together = ('company', 'code')
        verbose_name_plural = 'Tax Categories'

    def __str__(self):
        return f"{self.code} - {self.name} ({self.tax_rate}%)"
