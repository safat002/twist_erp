import csv
import shutil
import tempfile
from datetime import date
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.finance.models import Account, AccountType, Journal, JournalVoucher
from apps.data_migration.models import (
    MigrationJob,
    MigrationStagingRow,
    MigrationValidationError,
    migration_enums,
)
from apps.data_migration.services import MigrationPipeline
from apps.companies.models import Company, CompanyGroup


class MigrationPipelineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="migration.tester", password="changeme", email="tester@example.com"
        )
        cls.company_group = CompanyGroup.objects.create(
            name="Test Group",
            db_name="cg_test",
            industry_pack_type="trading",
            supports_intercompany=False,
        )
        cls.company = Company.objects.create(
            company_group=cls.company_group,
            code="TST",
            name="Test Company",
            legal_name="Test Company Ltd.",
            fiscal_year_start=date(2025, 1, 1),
            tax_id="TX123456789",
            registration_number="REG-001",
        )

        cls.ar_account = Account.objects.create(
            company=cls.company,
            created_by=cls.user,
            code="1100",
            name="Accounts Receivable",
            account_type=AccountType.ASSET,
        )
        cls.equity_account = Account.objects.create(
            company=cls.company,
            created_by=cls.user,
            code="3100",
            name="Opening Balance Equity",
            account_type=AccountType.EQUITY,
        )
        cls.ap_account = Account.objects.create(
            company=cls.company,
            created_by=cls.user,
            code="2100",
            name="Accounts Payable",
            account_type=AccountType.LIABILITY,
        )

        cls.general_journal = Journal.objects.create(
            company=cls.company,
            created_by=cls.user,
            code="GEN",
            name="General Journal",
            type="GENERAL",
        )

    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix="migration-media-")
        self.addCleanup(lambda: shutil.rmtree(self.media_root, ignore_errors=True))
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()

    def tearDown(self):
        self.override.disable()

    def _build_csv_file(self):
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "invoice_number",
                "invoice_type",
                "partner_type",
                "partner_id",
                "invoice_date",
                "due_date",
                "subtotal",
                "tax_amount",
                "discount_amount",
                "total_amount",
            ]
        )
        writer.writerow(
            [
                "OPEN-INV-001",
                "AR",
                "CUSTOMER",
                1,
                "2025-01-01",
                "2025-01-31",
                "1000.00",
                "0",
                "0",
                "1000.00",
            ]
        )
        writer.writerow(
            [
                "OPEN-INV-002",
                "AR",
                "CUSTOMER",
                2,
                "2025-01-05",
                "2025-02-04",
                "500.00",
                "0",
                "0",
                "500.00",
            ]
        )
        content = output.getvalue().encode("utf-8")
        return SimpleUploadedFile("opening_ar.csv", content, content_type="text/csv")

    def test_pipeline_full_flow_creates_gl_entries(self):
        job = MigrationPipeline.create_job(
            company=self.company,
            created_by=self.user,
            entity_name_guess="opening_ar",
            target_model="finance.Invoice",
        )
        pipeline = MigrationPipeline(job)
        migration_file = pipeline.add_file(
            uploaded_by=self.user,
            file_name="opening_ar.csv",
            file_content=self._build_csv_file(),
        )
        self.assertEqual(migration_file.status, migration_enums.MigrationFileStatus.UPLOADED)

        df = pipeline.profile_files()
        self.assertEqual(job.status, migration_enums.MigrationJobStatus.DETECTED)
        self.assertEqual(len(df.index), 2)

        pipeline.generate_field_mappings()
        job.refresh_from_db()
        self.assertEqual(job.status, migration_enums.MigrationJobStatus.MAPPED)
        self.assertGreater(job.field_mappings.count(), 0)

        pipeline.stage_rows(user=self.user)
        staged_rows = job.staging_rows.all()
        self.assertEqual(staged_rows.count(), 2)
        self.assertEqual(
            staged_rows.filter(status=migration_enums.StagingRowStatus.PENDING_VALIDATION).count(), 2
        )

        validation_summary = pipeline.validate(user=self.user)
        job.refresh_from_db()
        self.assertEqual(job.status, migration_enums.MigrationJobStatus.VALIDATED)
        errors = list(
            MigrationValidationError.objects.filter(migration_job=job).values_list("error_code", "error_message")
        )
        self.assertEqual(validation_summary.get("invalid", 0), 0, msg=f"Validation errors: {errors}")
        self.assertEqual(MigrationValidationError.objects.filter(migration_job=job).count(), 0)

        pipeline.submit_for_approval(user=self.user)
        job.refresh_from_db()
        self.assertEqual(job.status, migration_enums.MigrationJobStatus.AWAITING_APPROVAL)

        pipeline.approve(approver=self.user)
        job.refresh_from_db()
        self.assertEqual(job.status, migration_enums.MigrationJobStatus.APPROVED)

        commit_log = pipeline.commit(user=self.user)
        job.refresh_from_db()
        self.assertEqual(job.status, migration_enums.MigrationJobStatus.COMMITTED)
        self.assertEqual(commit_log.summary.get("created"), 2)
        self.assertEqual(len(commit_log.gl_entries), 2)

        vouchers = JournalVoucher.objects.filter(company=self.company)
        self.assertEqual(vouchers.count(), 2)
        self.assertTrue(all(voucher.status == "POSTED" for voucher in vouchers))

        invoices = job.company.invoice_set.order_by("invoice_number")
        self.assertEqual(invoices.count(), 2)
        for invoice in invoices:
            self.assertEqual(invoice.status, "POSTED")
            self.assertIsNotNone(invoice.journal_voucher)

        staging_statuses = {
            status: job.staging_rows.filter(status=status).count()
            for status in migration_enums.StagingRowStatus.values
        }
        self.assertEqual(staging_statuses[migration_enums.StagingRowStatus.VALID], 2)

    def test_rollback_removes_records(self):
        job = MigrationPipeline.create_job(
            company=self.company,
            created_by=self.user,
            entity_name_guess="opening_ar",
            target_model="finance.Invoice",
        )
        pipeline = MigrationPipeline(job)
        pipeline.add_file(
            uploaded_by=self.user,
            file_name="opening_ar.csv",
            file_content=self._build_csv_file(),
        )
        pipeline.profile_files()
        pipeline.generate_field_mappings()
        pipeline.stage_rows(user=self.user)
        pipeline.validate(user=self.user)
        pipeline.submit_for_approval(user=self.user)
        pipeline.approve(approver=self.user)
        pipeline.commit(user=self.user)
        self.assertEqual(job.company.invoice_set.count(), 2)

        deleted = pipeline.rollback(user=self.user)
        job.refresh_from_db()
        self.assertEqual(job.status, migration_enums.MigrationJobStatus.ROLLED_BACK)
        self.assertEqual(deleted, 2)
        self.assertEqual(job.company.invoice_set.count(), 0)
