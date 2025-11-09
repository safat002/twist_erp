"""
Management command to build the AI vector index using ai_service_v2.
Indexes a documentation directory into a FAISS store.
"""

from pathlib import Path
from django.core.management.base import BaseCommand, CommandParser
from django.conf import settings

from apps.ai_companion.services.ai_service_v2 import ai_service_v2


class Command(BaseCommand):
    help = "Index documentation into the AI vector store (ai_service_v2)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--path",
            type=str,
            help="Directory to index (defaults to ./docs at repo root)",
        )
        parser.add_argument(
            "--index",
            type=str,
            default="global",
            help="Index name (e.g., 'global' or company id)",
        )

    def handle(self, *args, **options):
        # Find a docs directory to index
        candidates = []
        if options.get("path"):
            candidates.append(Path(options["path"]))
        # Repo root docs (BASE_DIR is backend folder)
        candidates.append(Path(settings.BASE_DIR).parent / "docs")
        # Backend local docs fallback
        candidates.append(Path(settings.BASE_DIR) / "docs")

        docs_dir = None
        for p in candidates:
            if p.exists() and p.is_dir():
                docs_dir = p
                break

        if not docs_dir:
            self.stdout.write(self.style.WARNING("No docs directory found to index."))
            return

        index_name = str(options.get("index") or "global")
        self.stdout.write(f"Indexing documents from '{docs_dir}' into index '{index_name}'...")
        ai_service_v2.index_documents(str(docs_dir), index_name=index_name)
        self.stdout.write(self.style.SUCCESS("Indexing complete."))

