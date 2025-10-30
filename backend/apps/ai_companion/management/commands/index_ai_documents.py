
from django.core.management.base import BaseCommand
from apps.ai_companion.services.ai_service_v2 import ai_service_v2

class Command(BaseCommand):
    help = "Indexes documents for the AI companion."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=str,
            default="docs",
            help="The source directory of the documents to index.",
        )
        parser.add_argument(
            "--company-id",
            type=str,
            default="global",
            help="Optional company ID to target a tenant-specific vector index.",
        )

    def handle(self, *args, **options):
        source_directory = options["source"]
        index_name = options["company_id"] or "global"
        self.stdout.write(f"Indexing documents from '{source_directory}' into '{index_name}'...")
        ai_service_v2.index_documents(source_directory, index_name=index_name)
        self.stdout.write(self.style.SUCCESS("Successfully indexed documents."))
