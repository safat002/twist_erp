# backend/core/admin.py
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _

class TwistERPAdminSite(AdminSite):
    site_header = _('TWIST ERP Administration')
    site_title = _('TWIST ERP Admin')
    index_title = _('Dashboard')

    def each_context(self, request):
        context = super().each_context(request)
        context['show_company_selector'] = True
        return context

admin_site = TwistERPAdminSite(name='twist_admin')
