from __future__ import annotations

import copy
import datetime
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import psycopg
from django.conf import settings
from django.core.management import call_command
from django.db import DEFAULT_DB_ALIAS, connections, transaction
from django.utils.text import slugify

from ..models import Company, CompanyGroup

logger = logging.getLogger(__name__)


class ProvisioningError(RuntimeError):
    """Raised when a tenant provisioning step fails."""


@dataclass
class ProvisioningResult:
    company_group: CompanyGroup
    company: Company


class CompanyGroupProvisioner:
    """
    Helper responsible for creating new CompanyGroup tenants together with their
    dedicated PostgreSQL database and baseline company record.
    """

    def __init__(self, template_alias: str = DEFAULT_DB_ALIAS):
        self.template_alias = template_alias

    def provision(
        self,
        *,
        group_name: str,
        industry_pack: str = "",
        supports_intercompany: bool = False,
        default_company_payload: Optional[Dict[str, Any]] = None,
        admin_user=None,
    ) -> ProvisioningResult:
        slug = slugify(group_name) or "tenant"
        db_alias = f"cg_{slug}"
        if CompanyGroup.objects.filter(db_name=db_alias).exists():
            raise ProvisioningError(f"A company group using database '{db_alias}' already exists.")

        base_config = self._base_database_config()
        tenant_config = self._build_database_config(base_config, db_alias)

        with transaction.atomic():
            company_group = CompanyGroup.objects.create(
                name=group_name,
                db_name=db_alias,
                industry_pack_type=industry_pack,
                supports_intercompany=supports_intercompany,
                status="creating",
            )

        try:
            self._ensure_database_exists(tenant_config, db_alias)
            self._register_database_alias(db_alias, tenant_config)
            self._run_migrations(db_alias)

            company_payload = default_company_payload or {}
            company = self._create_company(company_group, company_payload)

            if admin_user:
                self._assign_admin_user(admin_user, company)

            company_group.status = "active"
            company_group.save(update_fields=["status", "updated_at"])
        except Exception as exc:
            company_group.status = "failed"
            company_group.save(update_fields=["status", "updated_at"])
            logger.exception("Provisioning failed for %s: %s", group_name, exc)
            raise

        logger.info("Provisioned company group '%s' with database '%s'", group_name, db_alias)
        return ProvisioningResult(company_group=company_group, company=company)

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #
    def _base_database_config(self) -> Dict[str, Any]:
        try:
            template = connections.databases[self.template_alias]
        except KeyError as exc:
            raise ProvisioningError(
                f"Template database alias '{self.template_alias}' is not configured."
            ) from exc
        return copy.deepcopy(template)

    def _build_database_config(self, template: Dict[str, Any], db_alias: str) -> Dict[str, Any]:
        config = copy.deepcopy(template)
        config["NAME"] = db_alias
        config.setdefault("OPTIONS", {})
        return config

    def _ensure_database_exists(self, config: Dict[str, Any], db_alias: str) -> None:
        engine = config.get("ENGINE", "")
        if "postgresql" not in engine:
            raise ProvisioningError("Only PostgreSQL-backed tenants are supported.")

        maintenance_db = os.environ.get("PG_MAINTENANCE_DB", "postgres")
        conn_kwargs = {
            "host": config.get("HOST"),
            "port": config.get("PORT"),
            "user": config.get("USER"),
            "password": config.get("PASSWORD"),
            "dbname": maintenance_db,
        }
        conn_kwargs = {k: v for k, v in conn_kwargs.items() if v}

        create_sql = f'CREATE DATABASE "{config["NAME"]}"'
        with psycopg.connect(**conn_kwargs) as connection:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (config["NAME"],)
                )
                exists = cursor.fetchone()
                if exists:
                    logger.info("Database '%s' already exists; skipping create.", config["NAME"])
                    return
                cursor.execute(create_sql)
        logger.info("Created database '%s'.", config["NAME"])

    def _register_database_alias(self, alias: str, config: Dict[str, Any]) -> None:
        settings.DATABASES[alias] = config
        connections.databases[alias] = config

    def _run_migrations(self, alias: str) -> None:
        call_command("migrate", database=alias, interactive=False, verbosity=0)

    def _create_company(
        self, company_group: CompanyGroup, payload: Dict[str, Any]
    ) -> Company:
        defaults = {
            "code": payload.get("code") or company_group.name[:10].upper().replace(" ", ""),
            "name": payload.get("name") or company_group.name,
            "legal_name": payload.get("legal_name") or payload.get("name") or company_group.name,
            "currency_code": payload.get("currency_code", "USD"),
            "fiscal_year_start": payload.get("fiscal_year_start") or datetime.date.today(),
            "tax_id": payload.get("tax_id") or f"TEMP-{company_group.id}",
            "registration_number": payload.get("registration_number") or f"REG-{company_group.id}",
            "settings": payload.get("settings") or {},
            "is_active": True,
        }
        company = Company.objects.create(company_group=company_group, **defaults)
        return company

    def _assign_admin_user(self, user, company: Company) -> None:
        if hasattr(user, "companies"):
            user.companies.add(company)
