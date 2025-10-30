from django.core.management.base import BaseCommand
from apps.analytics.tasks import populate_data_warehouse

class Command(BaseCommand):
    help = "Runs the analytics ETL process to populate the data warehouse."

    def add_arguments(self, parser):
        parser.add_argument(
            "--period",
            type=str,
            default="30d",
            help="The period to run the analysis for (e.g., 7d, 30d, 90d, month, quarter).",
        )

    def handle(self, *args, **options):
        period = options["period"]
        self.stdout.write(f"Starting analytics ETL process for period: {period}...")
        # Using .delay() will queue the task to be executed by a Celery worker.
        # For simplicity in the local setup, we can call the function directly.
        # result = populate_data_warehouse.delay(period=period)
        # self.stdout.write(self.style.SUCCESS(f"Successfully queued ETL task. Task ID: {result.id}"))
        result = populate_data_warehouse(period=period)
        self.stdout.write(self.style.SUCCESS("Analytics ETL process completed."))
        self.stdout.write(str(result))
