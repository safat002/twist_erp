from io import BytesIO

import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.companies.models import CompanyGroup, Company
from apps.users.models import User
from apps.data_migration.models import MigrationJob
from apps.data_migration.services.pipeline import MigrationPipeline


class MigrationPipelineChunkingTests(TestCase):
    def setUp(self):
        self.group = CompanyGroup.objects.create(name="Demo Group", code="DEMO-G")
        self.company = Company.objects.create(name="Demo Co", code="DEMO", company_group=self.group)
        self.user = User.objects.create_user(username="u1", password="x")

    def _csv_file(self, rows=5):
        df = pd.DataFrame([
            {"name": f"Item {i}", "code": f"ITM-{i:03d}", "qty": i} for i in range(1, rows + 1)
        ])
        buf = BytesIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return SimpleUploadedFile("items.csv", buf.read(), content_type="text/csv")

    def test_stage_rows_in_chunks(self):
        job = MigrationJob.objects.create(company=self.company, company_group=self.group, created_by=self.user)
        pipe = MigrationPipeline(job)
        f = pipe.add_file(uploaded_by=self.user, file_name="items.csv", file_content=self._csv_file(rows=7))
        pipe.profile_files()
        staged = pipe.stage_rows(user=self.user, chunk_size=3)
        # Expect all rows staged
        self.assertEqual(staged, 7)
        # Validate returns a summary dict
        summary = pipe.validate(user=self.user)
        self.assertIsInstance(summary, dict)

