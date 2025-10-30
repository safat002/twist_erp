import json
import os
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from langchain_core.documents import Document
from apps.ai_companion.services.ai_service_v2 import ai_service_v2


class Command(BaseCommand):
    help = "Index initial AI knowledge base into the vector store"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixtures",
            default=None,
            help="Optional path to a JSON fixtures file to index",
        )
        parser.add_argument(
            "--company-id",
            default=None,
            help="Optional company ID to index into a tenant-specific vector store",
        )

    def handle(self, *args, **options):
        fixtures_path = options.get("fixtures")
        default_fixture = (
            Path(__file__).resolve().parents[3]
            / "ai_companion"
            / "fixtures"
            / "ai_knowledge_base.json"
        )

        src = None
        if fixtures_path and Path(fixtures_path).exists():
            src = Path(fixtures_path)
        elif default_fixture.exists():
            src = default_fixture

        if not src:
            self.stderr.write(self.style.ERROR("No knowledge base fixture found."))
            return

        try:
            with open(src, "r", encoding="utf-8") as f:
                data = json.load(f)

            documents = [
                Document(page_content=item["content"], metadata={"source": item["title"]})
                for item in data
            ]

            index_name = str(options.get("company_id") or "global")
            ai_service_v2.index_documents_from_list(documents, index_name=index_name)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully indexed {len(documents)} documents into '{index_name}' from {src}."
                )
            )
        except Exception as exc:
            self.stderr.write(
                self.style.ERROR(f"Failed to index knowledge base: {exc}")
            )
            raise
