# backend/core/management/commands/index_knowledge_base.py

from django.core.management.base import BaseCommand
from apps.ai_companion.models import AIKnowledgeBase
from apps.ai_companion.services.vector_store import VectorStoreService

class Command(BaseCommand):
    help = 'Index knowledge base for AI search'

    def handle(self, *args, **options):
        vector_store = VectorStoreService()

        companies = Company.objects.filter(is_active=True)

        for company in companies:
            self.stdout.write(f'Indexing knowledge base for {company.name}...')
            vector_store.index_erp_data(company.id)

        self.stdout.write(self.style.SUCCESS('✅ Indexing complete!'))
