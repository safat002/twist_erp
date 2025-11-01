# mis_app/data_views.py

"""
Django Views for Data Management
Complete implementation with all Flask functionality converted to Django
"""

import json
import logging
import os
import uuid
import pandas as pd
import numpy as np
import openpyxl
import re
import traceback
from datetime import datetime, date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from werkzeug.utils import secure_filename

from sqlalchemy import text, inspect, table, column, delete, MetaData, Integer, BigInteger, SmallInteger, Float, Numeric, DECIMAL, REAL
from sqlalchemy.types import VARCHAR, TEXT, BOOLEAN, DATE, TIMESTAMP

from .models import ExternalConnection, User
from .utils import get_external_engine

logger = logging.getLogger(__name__)

# Helper functions
def normalize_header(header):
    """Cleans a header string to be a normalized identifier."""
    return re.sub(r'[^a-z0-9_]', '_', str(header).lower())

def sanitize_column_name(col_name):
    """Cleans up a column name to be SQL-friendly."""
    col_name = str(col_name).strip()
    col_name = re.sub(r'\s+', '_', col_name)  # Replace spaces with underscores
    col_name = re.sub(r'[^a-zA-Z0-9_]', '', col_name)  # Remove special characters
    return col_name.lower()

def is_numeric_type(col_type):
    """Checks if a SQLAlchemy column type is numeric."""
    return isinstance(col_type, (Integer, BigInteger, SmallInteger, Float, Numeric, DECIMAL, REAL))

def get_visible_tables(connection_id=None, user=None): # Add user to the function signature
    """Gets a list of visible tables for a user."""
    try:
        if connection_id and user: # Check that we have a user
            # Ensure the connection belongs to the user requesting it
            connection = get_object_or_404(ExternalConnection, id=connection_id, owner=user)
            engine = get_external_engine(connection_id, user) # Pass the user to the engine helper
            
            if not engine:
                return []
            
            try:
                inspector = inspect(engine)
                
                # Handle different database types
                if connection.db_type == 'postgresql' and connection.schema:
                    all_db_tables = inspector.get_table_names(schema=connection.schema)
                else:
                    all_db_tables = inspector.get_table_names()
                
                # Filter hidden tables
                hidden_tables = set((connection.hidden_tables or '').split(',') if connection.hidden_tables else [])
                return sorted([table for table in all_db_tables if table not in hidden_tables])
            
            except Exception as e:
                logger.error(f"Error inspecting database: {str(e)}")
                return []
                
        return []
    except Exception as e:
        logger.error(f"Error in get_visible_tables: {str(e)}")
        return []

@login_required
@require_POST
def upload_data_api(request):
    """Handles direct file uploads and inserts data into a table."""
    try:
        connection_id = request.POST.get('connection_id')
        table_name = request.POST.get('table_name')
        has_headers = request.POST.get('has_headers') == 'true'
        replace_table = request.POST.get('replace_table') == 'true'
        file = request.FILES.get('file')

        if not all([connection_id, table_name, file]):
            return JsonResponse({'success': False, 'error': 'Missing connection, table name, or file.'}, status=400)

        engine = get_external_engine(connection_id, request.user) # Add request.user
        if not engine:
            return JsonResponse({'success': False, 'error': 'Database connection failed.'}, status=500)

        # Sanitize filename and determine file type
        filename = secure_filename(file.name)
        file_ext = os.path.splitext(filename)[1].lower()

        # Read the file into a pandas DataFrame
        if file_ext == '.csv':
            df = pd.read_csv(file, header=0 if has_headers else None)
        elif file_ext in ['.xls', '.xlsx']:
            df = pd.read_excel(file, header=0 if has_headers else None)
        else:
            return JsonResponse({'success': False, 'error': 'Unsupported file type. Please use CSV or Excel.'}, status=400)
            
        # If the file has no headers, assign generic column names like 'column_1', 'column_2', etc.
        if not has_headers:
            df.columns = [f'column_{i+1}' for i in range(len(df.columns))]

        # Normalize column headers to be database-friendly
        df.columns = [normalize_header(col) for col in df.columns]

        # Determine the upload method
        upload_method = 'replace' if replace_table else 'append'

        # Upload the DataFrame to the database
        df.to_sql(table_name, engine, if_exists=upload_method, index=False)

        return JsonResponse({
            'success': True,
            'message': f'Successfully uploaded {len(df)} rows to table "{table_name}".'
        })

    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}")
        # Provide a more specific error if possible
        if "does not exist" in str(e):
             return JsonResponse({'success': False, 'error': f'Upload failed. Table "{table_name}" does not exist in the database.'}, status=500)
        return JsonResponse({'success': False, 'error': f'An error occurred during upload: {str(e)}'}, status=500)

# API Views
@login_required
@require_POST
def check_password(request):
    """Verifies the current user's password."""
    try:
        data = json.loads(request.body)
        password = data.get('password')
        
        if not request.user.check_password(password):
            return JsonResponse({'success': False, 'message': 'Incorrect password.'}, status=403)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
@require_POST
def inspect_file(request):
    """Inspects an uploaded file for sheet names if Excel."""
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'message': 'No file provided.'}, status=400)
        
        file = request.FILES['file']
        filename = secure_filename(file.name)
        
        if not (filename.endswith('.csv') or filename.endswith(('.xls', '.xlsx'))):
            return JsonResponse({'success': False, 'message': 'Unsupported file type.'}, status=400)
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        temp_filename = f"{uuid.uuid4().hex}_{filename}"
        temp_file_path = os.path.join(upload_dir, temp_filename)
        
        # Save file temporarily
        with open(temp_file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        sheets = []
        if filename.endswith(('.xls', '.xlsx')):
            try:
                workbook = openpyxl.load_workbook(temp_file_path, read_only=True, data_only=True)
                sheets = workbook.sheetnames
            except Exception as e:
                os.remove(temp_file_path)
                return JsonResponse({'success': False, 'message': f'Could not read Excel file: {e}'}, status=500)
        
        return JsonResponse({
            'success': True, 
            'temp_filename': temp_filename, 
            'sheets': sheets
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
def get_columns_for_table(request, connection_id, table_name):
    """Gets detailed column information for a single table."""
    try:
        if request.user.user_type not in ['Admin', 'Moderator']:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        engine = get_external_engine(connection_id)
        if not engine:
            return JsonResponse({'success': False, 'error': 'Database connection failed.'}, status=500)
        
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        
        column_details = [
            {'name': col['name'], 'type': str(col['type'])}
            for col in columns
        ]
        
        # Get primary keys
        try:
            pk_constraint = inspector.get_pk_constraint(table_name)
            pks = pk_constraint.get('constrained_columns', []) if pk_constraint else []
        except:
            pks = []
        
        return JsonResponse({
            'success': True, 
            'columns': column_details,
            'pks': pks
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_POST
def rename_table(request):
    """Rename a table."""
    try:
        if request.user.user_type not in ['Admin', 'Moderator']:
            return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
        
        data = json.loads(request.body)
        connection_id = data.get('connection_id')
        old_name = data.get('old_name')
        new_name = data.get('new_name')
        
        engine = get_external_engine(connection_id)
        if not engine:
            return JsonResponse({'success': False, 'message': 'Database connection failed.'}, status=500)
        
        with engine.begin() as connection:
            if engine.dialect.name in ['postgresql', 'sqlite']:
                query = text(f"ALTER TABLE {old_name} RENAME TO {new_name}")
            elif engine.dialect.name == 'mysql':
                query = text(f"RENAME TABLE {old_name} TO {new_name}")
            else:
                return JsonResponse({'success': False, 'message': f'Unsupported database type: {engine.dialect.name}'}, status=400)
            
            connection.execute(query)
        
        return JsonResponse({'success': True, 'message': f'Table {old_name} renamed to {new_name}.'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@require_POST
def rename_column(request):
    """Rename a column."""
    try:
        if request.user.user_type not in ['Admin', 'Moderator']:
            return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
        
        data = json.loads(request.body)
        connection_id = data.get('connection_id')
        table_name = data.get('table_name')
        old_name = data.get('old_name')
        new_name = data.get('new_name')
        
        engine = get_external_engine(connection_id)
        if not engine:
            return JsonResponse({'success': False, 'message': 'Database connection failed.'}, status=500)
        
        with engine.begin() as connection:
            if engine.dialect.name in ['postgresql', 'sqlite']:
                query = text(f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {new_name}")
            elif engine.dialect.name == 'mysql':
                # For MySQL, we need to preserve the column type
                inspector = inspect(engine)
                cols = inspector.get_columns(table_name)
                col_info = next((c for c in cols if c['name'] == old_name), None)
                
                if not col_info:
                    return JsonResponse({'success': False, 'message': f'Column {old_name} not found.'}, status=404)
                
                col_type = str(col_info['type'])
                query = text(f"ALTER TABLE {table_name} CHANGE COLUMN {old_name} {new_name} {col_type}")
            else:
                return JsonResponse({'success': False, 'message': f'Unsupported database type: {engine.dialect.name}'}, status=400)
            
            connection.execute(query)
        
        return JsonResponse({'success': True, 'message': f'Column {old_name} renamed to {new_name}.'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@require_POST
def truncate_table(request):
    """Truncate a table (delete all data)."""
    try:
        if request.user.user_type not in ['Admin', 'Moderator']:
            return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
        
        data = json.loads(request.body)
        connection_id = data.get('connection_id')
        table_name = data.get('table_name')
        password = data.get('password')
        
        if not request.user.check_password(password):
            return JsonResponse({'success': False, 'message': 'Incorrect password.'}, status=403)
        
        engine = get_external_engine(connection_id)
        if not engine:
            return JsonResponse({'success': False, 'message': 'Database connection failed.'}, status=500)
        
        with engine.begin() as connection:
            if engine.dialect.name == 'mysql':
                query = text(f"TRUNCATE TABLE {table_name}")
            else:
                query = text(f"DELETE FROM {table_name}")
            
            connection.execute(query)
        
        return JsonResponse({'success': True, 'message': f'All data from {table_name} has been deleted.'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@require_POST
def drop_table(request):
    """Drop a table permanently."""
    try:
        if request.user.user_type not in ['Admin', 'Moderator']:
            return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
        
        data = json.loads(request.body)
        connection_id = data.get('connection_id')
        table_name = data.get('table_name')
        password = data.get('password')
        
        if not request.user.check_password(password):
            return JsonResponse({'success': False, 'message': 'Incorrect password.'}, status=403)
        
        engine = get_external_engine(connection_id)
        if not engine:
            return JsonResponse({'success': False, 'message': 'Database connection failed.'}, status=500)
        
        with engine.begin() as connection:
            query = text(f"DROP TABLE {table_name}")
            connection.execute(query)
        
        return JsonResponse({'success': True, 'message': f'Table {table_name} has been permanently deleted.'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@require_POST
def delete_rows(request):
    """Delete specific rows from a table."""
    try:
        if request.user.user_type not in ['Admin', 'Moderator']:
            return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
        
        data = json.loads(request.body)
        connection_id = data.get('connection_id')
        table_name = data.get('table_name')
        pks_to_delete = data.get('pks')
        pk_column = data.get('pk_column')
        
        engine = get_external_engine(connection_id)
        if not engine:
            return JsonResponse({'success': False, 'message': 'Database connection failed.'}, status=500)
        
        with engine.begin() as connection:
            # Use parameterized query for safety
            placeholders = ','.join(['%s'] * len(pks_to_delete))
            query = text(f"DELETE FROM {table_name} WHERE {pk_column} IN ({placeholders})")
            result = connection.execute(query, pks_to_delete)
        
        return JsonResponse({'success': True, 'message': f'Successfully deleted {result.rowcount} rows.'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
def get_table_data(request, connection_id, table_name):
    """Get table data with pagination and proper error handling."""
    try:
        # Validate table name
        if not table_name.replace('_', '').replace('-', '').isalnum():
            return JsonResponse({'data': [], 'error': 'Invalid table name format'}, status=400)

        # Get connection and ensure user owns it
        connection_details = get_object_or_404(ExternalConnection, id=connection_id, owner=request.user)
        
        # Get database engine
        engine = get_external_engine(connection_id, request.user)
        if not engine:
            return JsonResponse({'data': [], 'error': 'External database not connected.'}, status=400)

        with engine.connect() as connection:
            # Use parameterized query for safety
            from sqlalchemy import text
            query = text(f"SELECT * FROM {table_name} LIMIT 1000")
            result = connection.execute(query)
            
            # Convert to list of dictionaries
            rows = []
            for row in result.fetchall():
                row_dict = {}
                for key, value in row._mapping.items():
                    # Handle different data types
                    if value is None:
                        row_dict[key] = None
                    # CHANGE THIS LINE:
                    elif isinstance(value, (datetime, date)):
                        row_dict[key] = str(value)
                    elif isinstance(value, Decimal):
                        row_dict[key] = float(value)
                    else:
                        row_dict[key] = value
                rows.append(row_dict)
            
            # Get table statistics
            stats_query = text(f"SELECT COUNT(*) as row_count FROM {table_name}")
            stats_result = connection.execute(stats_query)
            row_count = stats_result.fetchone()[0]
            
            # Get column information
            from sqlalchemy import inspect
            inspector = inspect(engine)
            columns = inspector.get_columns(table_name)
            
            stats = {
                'total_rows': row_count,
                'total_columns': len(columns),
                'table_size': f"{row_count} rows",
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return JsonResponse({
                'success': True,
                'data': rows,
                'stats': stats,
                'columns': [col['name'] for col in columns]
            })
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Error in get_table_data: {str(e)}")
        return JsonResponse({
            'success': False,
            'data': [], 
            'error': f'Server-side error: {str(e)}'
        }, status=500)

@login_required
@require_POST
def preview_data(request):
    """Preview data from uploaded file."""
    try:
        data = json.loads(request.body)
        temp_filename = data.get('temp_filename')
        table_name = data.get('table_name')
        connection_id = data.get('connection_id')
        sheet_name = data.get('sheet_name')
        
        if not all([temp_filename, table_name, connection_id]):
            return JsonResponse({'success': False, 'message': 'Missing required data.'}, status=400)
        
        engine = get_external_engine(connection_id)
        if not engine:
            return JsonResponse({'success': False, 'message': 'External database not connected.'})
        
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        temp_file_path = os.path.join(upload_dir, temp_filename)
        
        if not os.path.exists(temp_file_path):
            return JsonResponse({'success': False, 'message': 'Temporary file not found. Please try again.'})
        
        # Read file
        if temp_filename.lower().endswith('.csv'):
            df = pd.read_csv(temp_file_path, low_memory=False)
        else:  # Excel
            df = pd.read_excel(temp_file_path, sheet_name=sheet_name)
        
        # Get existing table columns
        inspector = inspect(engine)
        db_columns = [col['name'] for col in inspector.get_columns(table_name)]
        
        file_columns = list(df.columns)
        normalized_file_cols = {normalize_header(c): c for c in file_columns}
        
        initial_mapping = []
        for db_col in db_columns:
            normalized_db_col = normalize_header(db_col)
            best_match = normalized_file_cols.get(normalized_db_col, '')
            initial_mapping.append({
                'db_column': db_col,
                'file_column': best_match
            })
        
        preview_json = df.head(5).to_json(orient='split')
        
        return JsonResponse({
            'success': True,
            'db_columns': db_columns,
            'file_columns': file_columns,
            'initial_mapping': initial_mapping,
            'preview_data': preview_json,
            'temp_filename': temp_filename
        })
    
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'})

@login_required
@require_POST
def confirm_upload(request):
    """Confirm and execute data upload."""
    try:
        data = json.loads(request.body)
        connection_id = data.get('connection_id')
        
        if not connection_id:
            return JsonResponse({'success': False, 'message': 'Connection ID is required.'}, status=400)
        
        engine = get_external_engine(connection_id)
        if not engine:
            return JsonResponse({'success': False, 'message': 'External database not connected.'})
        
        table_name = data.get('table_name')
        temp_filename = data.get('temp_filename')
        user_mapping = data.get('mapping', [])
        upload_method = data.get('upload_method', 'append')  # Get the upload method
        
        if not all([table_name, temp_filename, user_mapping]):
            return JsonResponse({'success': False, 'message': 'Missing table name, file, or column mapping.'})
        
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        temp_file_path = os.path.join(upload_dir, temp_filename)
        
        if not os.path.exists(temp_file_path):
            return JsonResponse({'success': False, 'message': 'Temporary file not found. Please try again.'})
        
        # Read file
        df = pd.read_csv(temp_file_path, low_memory=False)
        
        # Create rename map
        rename_map = {
            item['file_column']: item['db_column'] 
            for item in user_mapping 
            if item['file_column'] and item['db_column']
        }
        
        if not rename_map:
            os.remove(temp_file_path)
            return JsonResponse({'success': False, 'message': 'No columns were mapped from the file. Upload cancelled.'})
        
        # Select and rename columns
        df_to_upload = df[list(rename_map.keys())].copy()
        df_to_upload.rename(columns=rename_map, inplace=True)
        
        # Handle serial number column and data type conversion
        inspector = inspect(engine)
        db_columns_info = inspector.get_columns(table_name)
        db_col_names = [c['name'] for c in db_columns_info]
        
        # Add serial number column if it exists and not in uploaded data
        if 'slno_pk' in db_col_names and 'slno_pk' not in df_to_upload.columns:
            start_index = 0
            if upload_method == 'append':
                with engine.connect() as connection:
                    result = connection.execute(text(f"SELECT MAX(slno_pk) FROM {table_name}"))
                    start_index = result.scalar_one_or_none() or 0
            
            df_to_upload.insert(0, 'slno_pk', np.arange(start_index + 1, start_index + 1 + len(df_to_upload)))
        
        # Data type conversions
        for col_info in db_columns_info:
            col_name = col_info['name']
            sql_type = str(col_info['type']).upper()
            
            if col_name in df_to_upload.columns:
                if 'INT' in sql_type:
                    df_to_upload[col_name] = pd.to_numeric(df_to_upload[col_name], errors='coerce').fillna(0).astype(np.int64)
                elif any(t in sql_type for t in ['FLOAT', 'DECIMAL', 'NUMERIC']):
                    df_to_upload[col_name] = pd.to_numeric(df_to_upload[col_name], errors='coerce').fillna(0.0).astype(float)
        
        # Upload to database
        df_to_upload.to_sql(table_name, engine, if_exists=upload_method, index=False)
        
        # Clean up temp file
        os.remove(temp_file_path)
        
        return JsonResponse({
            'success': True, 
            'message': f'Successfully uploaded {len(df_to_upload)} rows to {table_name}.'
        })
    
    except Exception as e:
        # Clean up temp file on error
        try:
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            temp_file_path = os.path.join(upload_dir, data.get('temp_filename', ''))
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except:
            pass
        
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': f'An error occurred during final upload: {str(e)}'})

@login_required
@require_POST
def create_table(request):
    """Create a new table manually."""
    try:
        if request.user.user_type not in ['Admin', 'Moderator']:
            return JsonResponse({'success': False, 'message': 'Permission Denied'}, status=403)
        
        data = json.loads(request.body)
        connection_id = data.get('connection_id')
        
        if not connection_id:
            return JsonResponse({'success': False, 'message': 'Connection ID is required.'}, status=400)
        
        engine = get_external_engine(connection_id)
        if not engine:
            return JsonResponse({'success': False, 'message': 'External database not connected.'}, status=400)
        
        table_name = data.get('table_name')
        columns = data.get('columns')
        
        if not table_name or not columns:
            return JsonResponse({'success': False, 'message': 'Table name and columns are required.'})
        
        if not table_name.isidentifier():
            return JsonResponse({'success': False, 'message': f'Invalid table name: {table_name}'})
        
        sql_parts = []
        primary_keys = []
        
        for col in columns:
            col_name = col.get('name')
            if not col_name or not col_name.isidentifier():
                return JsonResponse({'success': False, 'message': f'Invalid column name: {col_name}'})
            
            part = f"{col_name} {col.get('type')}"
            sql_parts.append(part)
            
            if col.get('pk'):
                primary_keys.append(f"{col_name}")
        
        if primary_keys:
            sql_parts.append(f"PRIMARY KEY ({', '.join(primary_keys)})")
        
        sql_query = text(f"CREATE TABLE {table_name} ({', '.join(sql_parts)})")
        
        with engine.begin() as connection:
            connection.execute(sql_query)
        
        return JsonResponse({'success': True, 'message': f'Table {table_name} created successfully.'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Database error: {e}'})

@login_required
@require_POST
def add_column(request):
    """Add a new column to an existing table."""
    try:
        if request.user.user_type not in ['Admin', 'Moderator']:
            return JsonResponse({'success': False, 'message': 'Permission Denied'}, status=403)
        
        data = json.loads(request.body)
        connection_id = data.get('connection_id')
        
        if not connection_id:
            return JsonResponse({'success': False, 'message': 'Connection ID is required.'}, status=400)
        
        engine = get_external_engine(connection_id)
        if not engine:
            return JsonResponse({'success': False, 'message': 'External database not connected.'}, status=400)
        
        table_name = data.get('table_name')
        column_name = data.get('column_name')
        column_type = data.get('column_type')
        
        if not all([table_name, column_name, column_type]):
            return JsonResponse({'success': False, 'message': 'Missing required data.'}, status=400)
        
        if not table_name.isidentifier() or not column_name.isidentifier():
            return JsonResponse({'success': False, 'message': 'Invalid table or column name.'}, status=400)
        
        sql_query = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        
        with engine.begin() as connection:
            connection.execute(sql_query)
        
        return JsonResponse({'success': True, 'message': f'Column {column_name} added to table {table_name}.'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Database error: {e}'})

@login_required
@require_POST
def drop_column(request):
    """Drop a column from a table."""
    try:
        if request.user.user_type not in ['Admin', 'Moderator']:
            return JsonResponse({'success': False, 'message': 'Permission Denied'}, status=403)
        
        data = json.loads(request.body)
        connection_id = data.get('connection_id')
        
        engine = get_external_engine(connection_id)
        if not engine:
            return JsonResponse({'success': False, 'message': 'Database not connected.'}, status=400)
        
        table_name = data.get('table_name')
        column_name = data.get('column_name')
        
        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE {table_name} DROP COLUMN {column_name}"))
        
        return JsonResponse({'success': True, 'message': f'Column {column_name} deleted successfully.'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@require_POST
def modify_column_type(request):
    """Modify the data type of a column."""
    try:
        if request.user.user_type not in ['Admin', 'Moderator']:
            return JsonResponse({'success': False, 'message': 'Permission Denied'}, status=403)
        
        data = json.loads(request.body)
        connection_id = data.get('connection_id')
        
        engine = get_external_engine(connection_id)
        if not engine:
            return JsonResponse({'success': False, 'message': 'Database not connected.'}, status=400)
        
        table_name = data.get('table_name')
        column_name = data.get('column_name')
        new_type = data.get('new_type')
        
        with engine.begin() as connection:
            if engine.dialect.name == 'postgresql':
                query = text(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE {new_type} USING {column_name}::{new_type}")
            elif engine.dialect.name == 'mysql':
                query = text(f"ALTER TABLE {table_name} MODIFY COLUMN {column_name} {new_type}")
            elif engine.dialect.name == 'sqlite':
                return handle_sqlite_column_type_change(connection, table_name, column_name, new_type)
            else:
                return JsonResponse({'success': False, 'message': f'Unsupported database type: {engine.dialect.name}'}, status=400)
            
            connection.execute(query)
        
        return JsonResponse({'success': True, 'message': f'Data type for {column_name} changed to {new_type}.'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

def handle_sqlite_column_type_change(connection, table_name, column_name, new_type):
    """Handle SQLite column type changes by creating a new table and copying data."""
    try:
        inspector = inspect(connection.engine)
        columns = inspector.get_columns(table_name)
        pks = inspector.get_pk_constraint(table_name)['constrained_columns']
        
        new_table_name = f"{table_name}_new"
        
        # Create new table with modified column type
        column_defs = []
        for col in columns:
            col_type = new_type if col['name'] == column_name else str(col['type'])
            col_def = f"{col['name']} {col_type}"
            if col['name'] in pks:
                col_def += " PRIMARY KEY"
            column_defs.append(col_def)
        
        create_sql = text(f"CREATE TABLE {new_table_name} ({', '.join(column_defs)})")
        connection.execute(create_sql)
        
        # Copy data
        column_names = [f"{col['name']}" for col in columns]
        insert_sql = text(f"INSERT INTO {new_table_name} ({', '.join(column_names)}) SELECT {', '.join(column_names)} FROM {table_name}")
        connection.execute(insert_sql)
        
        # Replace old table
        connection.execute(text(f"DROP TABLE {table_name}"))
        connection.execute(text(f"ALTER TABLE {new_table_name} RENAME TO {table_name}"))
        
        return JsonResponse({'success': True, 'message': f'Data type for {column_name} changed to {new_type}.'})
    
    except Exception as e:
        # Clean up on error
        try:
            connection.execute(text(f"DROP TABLE IF EXISTS {new_table_name}"))
        except:
            pass
        raise e

@login_required
@require_POST
def set_primary_key(request):
    """Set primary key for a table."""
    try:
        if request.user.user_type not in ['Admin', 'Moderator']:
            return JsonResponse({'success': False, 'message': 'Permission Denied'}, status=403)
        
        data = json.loads(request.body)
        connection_id = data.get('connection_id')
        
        engine = get_external_engine(connection_id)
        if not engine:
            return JsonResponse({'success': False, 'message': 'Database not connected.'}, status=400)
        
        table_name = data.get('table_name')
        columns = data.get('columns')
        
        with engine.begin() as connection:
            # Drop existing primary key first
            try:
                connection.execute(text(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {table_name}_pkey"))
            except:
                pass  # Ignore if constraint doesn't exist
            
            # Add new primary key if any columns are provided
            if columns:
                pk_columns = ', '.join(columns)
                connection.execute(text(f"ALTER TABLE {table_name} ADD PRIMARY KEY ({pk_columns})"))
        
        return JsonResponse({'success': True, 'message': 'Primary key updated successfully.'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
def get_visible_tables_for_connection(request, connection_id):
    """API endpoint to get a list of visible tables for a specific connection."""
    try:
        # Pass the request.user object to the helper function
        visible_tables = get_visible_tables(connection_id, request.user) 
        return JsonResponse(visible_tables, safe=False)
    except Exception as e:
        logger.error(f"Error getting visible tables: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
    
@login_required
def get_table_schema_api(request, table_name):
    """Get table schema information."""
    try:
        connection_id = request.GET.get('connection_id')
        if not connection_id:
            return JsonResponse({'error': 'Connection ID is required'}, status=400)
        
        engine = get_external_engine(connection_id, request.user)
        if not engine:
            return JsonResponse({'error': 'Database connection failed'}, status=500)
        
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        
        return JsonResponse({
            'success': True,
            'columns': [{'name': col['name'], 'type': str(col['type'])} for col in columns]
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def get_detailed_columns(request, connection_id):
    """Get detailed column information for multiple tables."""
    try:
        engine = get_external_engine(connection_id)
        if not engine:
            return JsonResponse({'columns': [], 'error': 'External database not connected.'})
        
        data = json.loads(request.body)
        tables_to_query = data.get('tables', [])
        
        inspector = inspect(engine)
        all_columns = []
        
        for table_name in tables_to_query:
            try:
                columns = inspector.get_columns(table_name)
                for col in columns:
                    all_columns.append({
                        'full_name': f"{table_name}.{col['name']}",
                        'source': table_name,
                        'name': col['name'],
                        'is_numeric': is_numeric_type(col['type'])
                    })
            except Exception as e:
                print(f"Could not get columns for table {table_name}: {e}")
        
        return JsonResponse({'columns': all_columns})
    
    except Exception as e:
        return JsonResponse({'columns': [], 'error': str(e)})

# Main view
@login_required
def data_management_view(request):
    """Main data management page."""
    try:
        # This can be simplified if Admins should see all connections
        if request.user.user_type in ['Admin', 'Moderator']:
            connections = ExternalConnection.objects.all().order_by('nickname')
        else:
            connections = ExternalConnection.objects.filter(owner=request.user).order_by('nickname')
        
        context = {
            'connections': connections,
            # THIS IS THE CRITICAL LOGIC THAT SHOWS THE TABS
            'user_can_upload': request.user.user_type in ['Admin', 'Moderator', 'Uploader'],
            'user_can_modify': request.user.user_type in ['Admin', 'Moderator'],
            'initial_connection_id': connections.first().id if connections.exists() else None
        }
        
        return render(request, 'data_management.html', context)
    
    except Exception as e:
        logger.error(f"Error in data_management_view: {str(e)}")
        return render(request, 'data_management.html', {'connections': [], 'error': str(e)})
    
def get_best_pandas_dtype(series):
    """Analyzes a pandas Series and suggests the best data type."""
    if series.empty:
        return 'VARCHAR(255)'
    
    series_str = series.astype(str).str.strip()
    
    # Check for numeric, handling accounting negatives like (1,234.56)
    numeric_count = 0
    cleaned_series_for_numeric = series_str.str.replace(r'[$,]', '', regex=True).str.replace(r'^\((.*)\)$', r'-\1', regex=True)
    numeric_vals = pd.to_numeric(cleaned_series_for_numeric, errors='coerce')
    
    if numeric_vals.notna().sum() / len(series) > 0.8: # If 80% are numeric
        if (numeric_vals.dropna() % 1 == 0).all(): # Check if all are integers
            return 'INTEGER'
        else:
            return 'FLOAT'
            
    # Check for date formats
    try:
        if pd.to_datetime(series_str, errors='coerce').notna().sum() / len(series) > 0.7: # If 70% are dates
            if series_str.str.contains(r':').any():
                return 'TIMESTAMP'
            return 'DATE'
    except Exception:
        pass

    # Check for boolean
    bool_keywords = {'true', 'false', 'yes', 'no', 't', 'f', '1', '0', 'y', 'n'}
    if series_str.str.lower().isin(bool_keywords).sum() / len(series) > 0.8: # If 80% are bool-like
        return 'BOOLEAN'

    return 'VARCHAR(255)'


@login_required
@require_POST
def analyze_upload(request):
    """Analyzes an uploaded file to suggest a table schema and show a preview."""
    if request.user.user_type not in ['Admin', 'Moderator']:
        return JsonResponse({'error': "Permission Denied"}, status=403)

    try:
        data = json.loads(request.body)
        temp_filename = data.get('temp_filename')
        sheet_name = data.get('sheet_name')

        if not temp_filename:
            return JsonResponse({'error': "Missing temporary file name."}, status=400)

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        temp_filepath = os.path.join(upload_dir, temp_filename)
        
        if not os.path.exists(temp_filepath):
            return JsonResponse({'error': "Temporary file not found."}, status=404)

        if temp_filename.endswith('.csv'):
            df = pd.read_csv(temp_filepath, low_memory=False, on_bad_lines='skip')
        else:
            df = pd.read_excel(temp_filepath, sheet_name=sheet_name, engine='openpyxl')

        original_columns = list(df.columns)
        df.columns = [sanitize_column_name(str(col)) for col in original_columns]
        column_name_map = dict(zip(df.columns, original_columns))

        df.dropna(how='all', inplace=True)
        
        schema = []
        for col in df.columns:
            original_name = column_name_map.get(col, col)
            sample_data = df[col].dropna().head(100)
            dtype = get_best_pandas_dtype(sample_data) if not sample_data.empty else 'VARCHAR(255)'
            is_pk_candidate = (col == 'id' or col.endswith('_id') or (not sample_data.empty and df[col].nunique() == len(df.dropna(subset=[col]))))
            schema.append({'original_name': original_name, 'sql_name': col, 'sql_type': dtype, 'is_pk': is_pk_candidate})

        table_name_suggestion = sanitize_column_name(os.path.splitext(temp_filename.split('_', 1)[1])[0])
        preview_data_raw = df.head(5).replace({np.nan: None}).to_dict(orient='records')
        
        # Remap preview keys back to original names for display
        preview_data = [{column_name_map.get(k, k): v for k, v in row.items()} for row in preview_data_raw]

        return JsonResponse({
            'success': True, 'table_name': table_name_suggestion, 'schema': schema,
            'preview_data': preview_data, 'temp_filename': temp_filename
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'error': f"Analysis failed: {str(e)}"}, status=500)


@login_required
@require_POST
def create_table_from_import(request):
    """Creates a table from a user-confirmed schema and imports data from the temp file."""
    if request.user.user_type not in ['Admin', 'Moderator']:
        return JsonResponse({'error': "Permission Denied"}, status=403)

    try:
        data = json.loads(request.body)
        table_name = data.get('table_name')
        schema = data.get('schema')
        temp_filename = data.get('temp_filename')
        connection_id = data.get('connection_id')

        if not all([connection_id, table_name, schema, temp_filename]):
            return JsonResponse({'error': "Missing required data."}, status=400)

        engine = get_external_engine(connection_id, request.user)
        if not engine:
            return JsonResponse({'error': "External database not connected."}, status=400)

        inspector = inspect(engine)
        if table_name in inspector.get_table_names():
            return JsonResponse({'error': f"Table '{table_name}' already exists."}, status=409)

        user_selected_pk_cols = [col['sql_name'] for col in schema if col.get('is_pk')]
        if not user_selected_pk_cols:
            schema.insert(0, {'sql_name': 'sl_no_pk', 'sql_type': 'BIGINT', 'is_pk': True})

        sql_parts = []
        primary_keys = [f"\"{col['sql_name']}\"" for col in schema if col.get('is_pk')]
        for col in schema:
            sql_parts.append(f"\"{col['sql_name']}\" {col['sql_type']}")
        
        if primary_keys:
            sql_parts.append(f"PRIMARY KEY ({', '.join(primary_keys)})")

        create_sql = text(f"CREATE TABLE \"{table_name}\" ({', '.join(sql_parts)});")
        
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        temp_filepath = os.path.join(upload_dir, temp_filename)
        if not os.path.exists(temp_filepath):
            return JsonResponse({'error': "Temporary file not found."}, status=404)

        with engine.begin() as connection:
            connection.execute(create_sql)
        
        df = pd.read_csv(temp_filepath, low_memory=False)
        df.columns = [sanitize_column_name(str(col)) for col in df.columns]
        
        if 'sl_no_pk' not in df.columns and 'sl_no_pk' in [c['sql_name'] for c in schema]:
             df.insert(0, 'sl_no_pk', np.arange(1, len(df) + 1))

        df.to_sql(table_name, engine, if_exists='append', index=False)
        
        os.remove(temp_filepath)
        return JsonResponse({'success': True, 'message': f"Successfully created table '{table_name}' and imported {len(df)} rows."})
    except Exception as e:
        # Rollback: try to drop the partially created table
        try:
            with engine.begin() as connection:
                connection.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        except: pass
        traceback.print_exc()
        return JsonResponse({'error': f"An error occurred: {str(e)}"}, status=500)
    
