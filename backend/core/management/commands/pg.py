from django.core.management.base import BaseCommand, CommandError
from embedded_db.init_db import EmbeddedPostgres


class Command(BaseCommand):
    help = "Manage embedded PostgreSQL (init/start/stop/status)."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["init", "start", "stop", "status"], help="Action to perform")
        parser.add_argument("--port", dest="port", default=54322, type=int)
        parser.add_argument("--data-dir", dest="data_dir", default="./pgdata")
        parser.add_argument("--bin-dir", dest="bin_dir", default=None)

    def handle(self, *args, **options):
        action = options["action"]
        port = options["port"]
        data_dir = options["data_dir"]
        bin_dir = options["bin_dir"]

        db = EmbeddedPostgres(data_dir=data_dir, port=port, bin_dir=bin_dir)

        try:
            if action == "init":
                db.init_and_start()
                self.stdout.write(self.style.SUCCESS(f"Embedded Postgres started on port {port}"))
            elif action == "start":
                db.start()
                self.stdout.write(self.style.SUCCESS(f"Embedded Postgres started on port {port}"))
            elif action == "stop":
                db.stop()
                self.stdout.write(self.style.SUCCESS("Embedded Postgres stopped"))
            elif action == "status":
                running = db.status()
                self.stdout.write(self.style.SUCCESS("Running" if running else "Stopped"))
        except Exception as exc:
            raise CommandError(str(exc))

