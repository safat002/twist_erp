from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.apps import apps # Import apps
from .models import User, UserCompanyRole


class UserCompanyRoleInline(admin.TabularInline):
    # Use get_model to ensure models are fully loaded
    model = apps.get_model('users', 'UserCompanyRole') # Explicitly get the model
    extra = 0


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "phone", "avatar")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                    "is_system_admin",
                )
            },
        ),
        ("Companies", {"fields": ("default_company",)}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "default_company")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups", "default_company")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("username",)
    inlines = [UserCompanyRoleInline]


@admin.register(UserCompanyRole)
class UserCompanyRoleAdmin(admin.ModelAdmin):
    list_display = ["user", "company", "role", "is_active", "assigned_at"]
    list_filter = ["company", "role", "is_active"]
    search_fields = ["user__username", "user__email", "company__code", "role__name"]

