from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from .services.provisioning import CompanyGroupProvisioner, ProvisioningError


class CompanyGroupProvisionForm(forms.Form):
    group_name = forms.CharField(label="Group name", max_length=255)
    industry_pack_type = forms.CharField(label="Industry pack", max_length=50, required=False)
    supports_intercompany = forms.BooleanField(label="Supports inter-company", required=False)

    company_name = forms.CharField(label="Default company name", max_length=255, required=False)
    company_code = forms.CharField(label="Default company code", max_length=20, required=False)
    currency_code = forms.CharField(label="Currency code", max_length=10, required=False, initial="USD")
    fiscal_year_start = forms.DateField(label="Fiscal year start", required=False)


@method_decorator(staff_member_required, name="dispatch")
class AdminCompanyGroupProvisionView(View):
    template_name = "admin/companies/provision_company_group.html"

    def get(self, request):
        form = CompanyGroupProvisionForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = CompanyGroupProvisionForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        cd = form.cleaned_data
        payload = {
            "name": cd.get("company_name") or cd["group_name"],
            "code": cd.get("company_code") or (cd["group_name"][:10].upper().replace(" ", "")),
        }
        if cd.get("currency_code"):
            payload["currency_code"] = cd["currency_code"]
        if cd.get("fiscal_year_start"):
            payload["fiscal_year_start"] = cd["fiscal_year_start"]

        provisioner = CompanyGroupProvisioner()
        try:
            result = provisioner.provision(
                group_name=cd["group_name"],
                industry_pack=cd.get("industry_pack_type") or "",
                supports_intercompany=bool(cd.get("supports_intercompany")),
                default_company_payload=payload,
                admin_user=request.user,
            )
        except ProvisioningError as exc:
            messages.error(request, f"Provisioning failed: {exc}")
            return render(request, self.template_name, {"form": form})
        except Exception as exc:  # Fallback to surface any unexpected errors
            messages.error(request, f"Unexpected error: {exc}")
            return render(request, self.template_name, {"form": form})

        messages.success(
            request,
            f"Provisioned group '{result.company_group.name}' and company '{result.company.name}'.",
        )

        try:
            url = reverse("admin:companies_companygroup_change", args=[result.company_group.id])
        except Exception:
            url = reverse("admin:index")
        return redirect(url)

