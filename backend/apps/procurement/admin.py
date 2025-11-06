from django.contrib import admin

from .models import Supplier, PurchaseRequisition, PurchaseOrder, PurchaseOrderLine, PurchaseRequisitionDraft


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "email", "phone", "is_active", "company")
    search_fields = ("code", "name", "email", "phone")
    list_filter = ("is_active", "company")


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 0


@admin.register(PurchaseRequisition)
class PurchaseRequisitionAdmin(admin.ModelAdmin):
    list_display = ("requisition_number", "status", "priority", "cost_center", "requested_by", "company", "created_at")
    list_filter = ("status", "priority", "company")
    search_fields = ("requisition_number", "justification")
    date_hierarchy = "created_at"


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "supplier", "order_date", "status", "total_amount", "company")
    list_filter = ("status", "order_date", "company")
    search_fields = ("order_number", "external_reference", "notes")
    date_hierarchy = "order_date"
    inlines = [PurchaseOrderLineInline]


@admin.register(PurchaseRequisitionDraft)
class PurchaseRequisitionDraftAdmin(admin.ModelAdmin):
    list_display = ("requisition_number", "company", "request_date", "needed_by", "status")
    list_filter = ("company", "status")
    search_fields = ("requisition_number", "purpose")
    readonly_fields = ("requisition_number", "created_at", "updated_at", "created_by")
    date_hierarchy = 'request_date'
    actions = ["mark_submitted", "mark_cancelled", "export_csv"]

    def mark_submitted(self, request, queryset):
        updated = queryset.update(status='SUBMITTED')
        self.message_user(request, f"Marked {updated} drafts as SUBMITTED")
    mark_submitted.short_description = "Mark selected drafts as SUBMITTED"

    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status='CANCELLED')
        self.message_user(request, f"Marked {updated} drafts as CANCELLED")
    mark_cancelled.short_description = "Mark selected drafts as CANCELLED"

    def export_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename=purchase_requisition_drafts.csv'
        writer = csv.writer(resp)
        writer.writerow(['Number', 'Company', 'Request Date', 'Needed By', 'Status', 'Items', 'Purpose'])
        for obj in queryset:
            writer.writerow([
                obj.requisition_number,
                getattr(obj.company, 'code', obj.company_id),
                obj.request_date,
                obj.needed_by,
                obj.status,
                len(obj.lines or []),
                (obj.purpose or '').replace('\n', ' '),
            ])
        return resp
    export_csv.short_description = "Export selected to CSV"

from .models import PurchaseRequisitionDraft
