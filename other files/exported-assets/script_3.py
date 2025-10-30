
# Create Celery tasks for data migration

celery_tasks = """from celery import shared_task
from django.apps import apps
from apps.data_migration.models import MigrationSession
from apps.data_migration.services.data_profiler import DataProfiler
from apps.data_migration.services.field_matcher import FieldMatcher
from apps.data_migration.services.validator import DataValidator
from apps.data_migration.services.transformer import DataTransformer
from apps.data_migration.services.importer import DataImporter
import pandas as pd

@shared_task(bind=True)
def process_data_upload(self, session_id):
    \"\"\"
    Process uploaded data file
    - Parse file
    - Profile data
    - Generate mapping suggestions
    \"\"\"
    try:
        session = MigrationSession.objects.get(id=session_id)
        session.status = 'PROFILING'
        session.save()
        
        # Read file
        if session.source_type == 'EXCEL':
            df = pd.read_excel(session.source_file.path)
        elif session.source_type == 'CSV':
            df = pd.read_csv(session.source_file.path)
        else:
            raise ValueError(f"Unsupported source type: {session.source_type}")
        
        # Profile data
        profiler = DataProfiler()
        profile = profiler.profile_data(df)
        
        # Save profile
        from apps.data_migration.models import DataProfile
        DataProfile.objects.create(
            session=session,
            columns=profile['columns'],
            column_types=profile.get('column_types', {}),
            column_stats=profile.get('column_stats', {}),
            null_counts=profile['data_quality'].get('total_nulls', 0),
            duplicate_rows=profile['data_quality'].get('duplicate_rows', 0),
            sample_rows=profile['sample_rows']
        )
        
        # Generate field mapping suggestions
        target_schema = _get_target_schema(
            session.target_module,
            session.target_model
        )
        
        matcher = FieldMatcher()
        mappings = matcher.match_fields(
            profile['columns'],
            target_schema
        )
        
        session.mapping_config = {'suggested_mappings': mappings}
        session.total_rows = len(df)
        session.status = 'PROFILED'
        session.save()
        
        return {
            'status': 'success',
            'row_count': len(df),
            'column_count': len(df.columns),
            'mappings': len(mappings)
        }
    
    except Exception as e:
        session.status = 'FAILED'
        session.save()
        raise

@shared_task(bind=True)
def validate_data(self, session_id):
    \"\"\"
    Validate data before import
    \"\"\"
    try:
        session = MigrationSession.objects.get(id=session_id)
        session.status = 'VALIDATING'
        session.save()
        
        # Read and transform data
        df = _read_source_data(session)
        mapped_data = _apply_mapping(df, session.mapping_config)
        
        # Transform
        transformer = DataTransformer()
        transformed_data = transformer.transform_batch(
            mapped_data,
            session.transformation_rules
        )
        
        # Validate
        validator = DataValidator(
            session.target_model,
            session.validation_rules
        )
        validation_results = validator.validate_batch(transformed_data)
        
        # Save validation results
        session.processed_rows = len(transformed_data)
        session.error_rows = validation_results['error_count']
        session.status = 'VALIDATED'
        session.save()
        
        return {
            'status': 'success',
            'valid_rows': validation_results['valid_count'],
            'error_rows': validation_results['error_count']
        }
    
    except Exception as e:
        session.status = 'FAILED'
        session.save()
        raise

@shared_task(bind=True)
def import_data(self, session_id):
    \"\"\"
    Import validated data
    \"\"\"
    try:
        session = MigrationSession.objects.get(id=session_id)
        session.status = 'IMPORTING'
        session.started_at = timezone.now()
        session.save()
        
        # Read, map, transform, validate
        df = _read_source_data(session)
        mapped_data = _apply_mapping(df, session.mapping_config)
        
        transformer = DataTransformer()
        transformed_data = transformer.transform_batch(
            mapped_data,
            session.transformation_rules
        )
        
        validator = DataValidator(
            session.target_model,
            session.validation_rules
        )
        validated_data = validator.validate_batch(transformed_data)
        
        # Import
        importer = DataImporter(session)
        results = importer.import_data(validated_data)
        
        session.success_rows = results['imported']
        session.error_rows = results['errors']
        session.status = 'COMPLETED'
        session.completed_at = timezone.now()
        session.save()
        
        # Save as template if requested
        if session.save_as_template:
            _create_template_from_session(session)
        
        return {
            'status': 'success',
            'imported': results['imported'],
            'errors': results['errors']
        }
    
    except Exception as e:
        session.status = 'FAILED'
        session.save()
        raise

@shared_task
def rollback_migration(session_id):
    \"\"\"
    Rollback imported data
    \"\"\"
    from apps.data_migration.services.rollback import RollbackService
    
    session = MigrationSession.objects.get(id=session_id)
    rollback_service = RollbackService()
    
    deleted_count = rollback_service.rollback_session(session)
    
    return {
        'status': 'success',
        'deleted_count': deleted_count
    }

def _get_target_schema(module_name, model_name):
    \"\"\"Get target model schema\"\"\"
    model = apps.get_model(module_name, model_name)
    
    schema = []
    for field in model._meta.fields:
        schema.append({
            'name': field.name,
            'type': field.get_internal_type().lower(),
            'required': not field.null,
            'aliases': [field.verbose_name.lower()]
        })
    
    return schema

def _read_source_data(session):
    \"\"\"Read source data file\"\"\"
    if session.source_type == 'EXCEL':
        return pd.read_excel(session.source_file.path)
    elif session.source_type == 'CSV':
        return pd.read_csv(session.source_file.path)
    else:
        raise ValueError(f"Unsupported source type")

def _apply_mapping(df, mapping_config):
    \"\"\"Apply field mapping to dataframe\"\"\"
    mappings = mapping_config.get('mappings', {})
    
    mapped_data = []
    for _, row in df.iterrows():
        mapped_row = {}
        for source_col, target_field in mappings.items():
            if source_col in row:
                mapped_row[target_field] = row[source_col]
        mapped_data.append(mapped_row)
    
    return mapped_data

def _create_template_from_session(session):
    \"\"\"Create reusable template from successful migration\"\"\"
    from apps.data_migration.models import MigrationTemplate
    
    MigrationTemplate.objects.create(
        company=session.company,
        name=f"{session.name} Template",
        target_module=session.target_module,
        target_model=session.target_model,
        field_mappings=session.mapping_config,
        validation_rules=session.validation_rules,
        transformation_rules=session.transformation_rules
    )
"""

with open('migration_tasks.py', 'w') as f:
    f.write(celery_tasks)

print("✓ Created migration_tasks.py (Celery async tasks)")
print(f"  Size: {len(celery_tasks)} characters")
