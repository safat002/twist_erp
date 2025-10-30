from __future__ import annotations

import datetime
import os
import shlex
import subprocess
from pathlib import Path
from typing import Dict

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connections


class Command(BaseCommand):
    help = "Create a timestamped backup of the Twist ERP databases."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            dest="output_dir",
            default=str(Path(settings.BASE_DIR).parent / "backups"),
            help="Directory where the backup files will be placed. Defaults to <project_root>/backups.",
        )
        parser.add_argument(
            "--format",
            dest="format",
            choices=["auto", "json"],
            default="auto",
            help="Backup format: auto (pg_dump if available, otherwise JSON dumpdata) or json.",
        )
        parser.add_argument(
            "--database",
            dest="database",
            action="append",
            default=None,
            help="Explicit database alias(es) to backup. Defaults to every configured database.",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"]).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        format_choice = options["format"]
        requested_dbs = options["database"]

        self.stdout.write(self.style.NOTICE(f"Starting ERP backup at {timestamp}"))
        databases = self._selected_databases(requested_dbs)
        for alias, config in databases.items():
            self.stdout.write(f"• Backing up database '{alias}'")
            filename_prefix = f"{alias}_{timestamp}"

            if format_choice == "json":
                self._dump_json(alias, output_dir / f"{filename_prefix}.json")
                continue

            if self._can_use_pg_dump(config):
                try:
                    self._dump_pg(config, output_dir / f"{filename_prefix}.sql")
                    continue
                except subprocess.CalledProcessError as exc:
                    self.stderr.write(
                        self.style.WARNING(
                            f"pg_dump failed for '{alias}' ({exc}); falling back to JSON dumpdata."
                        )
                    )

            # fallback
            self._dump_json(alias, output_dir / f"{filename_prefix}.json")

        self.stdout.write(self.style.SUCCESS(f"Backup complete. Files stored in {output_dir}"))

    def _selected_databases(self, requested: list[str] | None) -> Dict[str, Dict]:
        databases = connections.databases.copy()
        if not requested:
            return databases
        selected = {}
        for alias in requested:
            if alias not in databases:
                raise CommandError(f"Database alias '{alias}' is not configured.")
            selected[alias] = databases[alias]
        return selected

    def _can_use_pg_dump(self, config: Dict) -> bool:
        import shutil

        engine = config.get("ENGINE", "")
        if "postgresql" not in engine:
            return False
        return bool(shutil.which("pg_dump"))

    def _dump_pg(self, config: Dict, destination: Path) -> None:
        import shutil

        pg_dump = shutil.which("pg_dump")
        if not pg_dump:
            raise subprocess.CalledProcessError(1, "pg_dump")

        env = os.environ.copy()
        if config.get("PASSWORD"):
            env["PGPASSWORD"] = config["PASSWORD"]

        args = [
            pg_dump,
            "--no-owner",
            "--no-privileges",
            "-f",
            str(destination),
        ]
        if config.get("HOST"):
            args.extend(["-h", config["HOST"]])
        if config.get("PORT"):
            args.extend(["-p", str(config["PORT"])])
        if config.get("USER"):
            args.extend(["-U", config["USER"]])

        db_name = config.get("NAME")
        if not db_name:
            raise CommandError("Database NAME is required for pg_dump backups.")
        args.append(db_name)

        self.stdout.write(f"  Running: {' '.join(shlex.quote(a) for a in args)}")
        subprocess.run(args, check=True, env=env)

    def _dump_json(self, alias: str, destination: Path) -> None:
        with destination.open("w", encoding="utf-8") as handle:
            call_command(
                "dumpdata",
                "--natural-foreign",
                "--natural-primary",
                database=alias,
                stdout=handle,
            )
