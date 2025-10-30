from __future__ import annotations

from django.apps import apps
from django.core.management import BaseCommand, CommandError
from django.db import connections, transaction
from django.db.models import JSONField


class Command(BaseCommand):
    help = "Promote a JSONB attribute into a dedicated database column."

    def add_arguments(self, parser):
        parser.add_argument('--model', required=True, help='Target model in the form app_label.ModelName')
        parser.add_argument('--json-field', required=True, help='Name of the JSONField storing custom data')
        parser.add_argument('--attribute', required=True, help='Key within the JSON object to promote')
        parser.add_argument('--column-type', default='TEXT', help='SQL column type for the new field (default: TEXT)')
        parser.add_argument('--database', default='default', help='Database alias to run against')
        parser.add_argument('--drop-json', action='store_true', help='Remove the promoted key from the JSON document')

    def handle(self, *args, **options):
        model = self._resolve_model(options['model'])
        json_field_name = options['json_field']
        attribute = options['attribute']
        column_type = options['column_type']
        database = options['database']
        drop_json = options['drop_json']

        try:
            json_field = model._meta.get_field(json_field_name)
        except Exception as exc:
            raise CommandError(
                f"Model '{model.__name__}' has no field named '{json_field_name}'."
            ) from exc

        if not isinstance(json_field, JSONField):
            raise CommandError(f"Field '{json_field_name}' on {model.__name__} is not a JSONField.")

        connection = connections[database]
        table = model._meta.db_table
        column_name = attribute

        with connection.cursor() as cursor, transaction.atomic(using=database):
            self.stdout.write(self.style.NOTICE(f"Adding column '{column_name}' to {table}"))
            cursor.execute(f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS "{column_name}" {column_type};')

            self.stdout.write(self.style.NOTICE(f"Populating column '{column_name}' from JSON attribute '{attribute}'"))
            extract_expression = self._extract_expression(json_field_name, column_type)
            cursor.execute(
                f'UPDATE "{table}" SET "{column_name}" = {extract_expression}',
                [attribute],
            )

            if drop_json:
                cursor.execute(
                    f'UPDATE "{table}" SET "{json_field_name}" = "{json_field_name}" - %s', [attribute]
                )

        self.stdout.write(self.style.SUCCESS('Field promotion completed.'))

    def _resolve_model(self, label: str):
        try:
            app_label, model_name = label.split('.')
        except ValueError as exc:
            raise CommandError("Model must be specified as 'app_label.ModelName'.") from exc
        model = apps.get_model(app_label, model_name)
        if model is None:
            raise CommandError(f"Unable to locate model '{label}'.")
        return model

    def _extract_expression(self, json_field: str, column_type: str) -> str:
        upper_type = column_type.upper()
        if upper_type in {"INTEGER", "INT", "BIGINT", "SMALLINT"}:
            return f"(({json_field} ->> %s)::INTEGER)"
        if upper_type in {"NUMERIC", "DECIMAL", "FLOAT", "DOUBLE PRECISION"}:
            return f"(({json_field} ->> %s)::NUMERIC)"
        return f"{json_field} ->> %s"
