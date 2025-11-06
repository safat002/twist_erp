from django.contrib import admin
from .models import Donor, Program, ComplianceRequirement, ComplianceSubmission


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "email", "phone", "company")
    search_fields = ("code", "name", "email", "phone")
    list_filter = ("company",)


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "donor", "status", "start_date", "end_date", "company")
    list_filter = ("company", "status", "donor")
    search_fields = ("code", "title")


@admin.register(ComplianceRequirement)
class ComplianceRequirementAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "program", "frequency", "next_due_date", "status")
    list_filter = ("status", "frequency", "program")
    search_fields = ("code", "name")


@admin.register(ComplianceSubmission)
class ComplianceSubmissionAdmin(admin.ModelAdmin):
    list_display = ("requirement", "period_start", "period_end", "submitted_at", "status")
    list_filter = ("status", "requirement")
    search_fields = ("notes",)

