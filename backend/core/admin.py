from django.contrib import admin
from django.contrib.admin import AdminSite


class TwistAdminSite(AdminSite):
    site_header = "Twist Administration"
    site_title = "Twist Administration"
    index_title = "Control Centre"
    enable_nav_sidebar = True


# Export a module-level admin_site that urls.py expects
admin_site = TwistAdminSite()

# Also configure the default site for third-party registrations that use admin.site
admin.site.site_header = TwistAdminSite.site_header
admin.site.site_title = TwistAdminSite.site_title
admin.site.index_title = TwistAdminSite.index_title
