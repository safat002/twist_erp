# mis_app/data_model_views.py
import json
import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from sqlalchemy import inspect
from .models import ExternalConnection, ConnectionJoin, CanvasLayout
from .utils import get_external_engine

logger = logging.getLogger(__name__)

@login_required
def data_model_designer_view(request):
    """Renders the main data model designer page."""
    connections = ExternalConnection.objects.filter(owner=request.user).order_by('nickname')
    context = {
        'connections': connections,
    }
    return render(request, 'data_model.html', context)

@login_required
def get_data_model_api(request, connection_id):
    """API endpoint to get all necessary data for the modeling canvas."""
    connection = get_object_or_404(ExternalConnection, id=connection_id, owner=request.user)
    engine = get_external_engine(connection_id, request.user)
    if not engine:
        return JsonResponse({'success': False, 'error': "Database connection failed."}, status=500)

    try:
        inspector = inspect(engine)
        all_tables_info = []
        numeric_types = ['INT', 'INTEGER', 'SMALLINT', 'BIGINT', 'FLOAT', 'REAL', 'NUMERIC', 'DECIMAL', 'DOUBLE']

        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            pks = inspector.get_pk_constraint(table_name).get('constrained_columns', [])
            
            # --- NEW HEURISTIC LOGIC ---
            # If no formal primary key is found, check for a column named 'id' as a fallback.
            if not pks:
                for c in columns:
                    if c['name'].lower() == 'id':
                        pks.append(c['name'])
                        break  # Found it, no need to look further
            # --- END OF NEW LOGIC ---

            formatted_columns = []
            for c in columns:
                col_type_str = str(c['type']).upper()
                is_numeric = any(num_type in col_type_str for num_type in numeric_types)
                formatted_columns.append({
                    "name": c['name'], 
                    "type": str(c['type']), 
                    "is_pk": c['name'] in pks,
                    "is_numeric": is_numeric
                })
            
            all_tables_info.append({"name": table_name, "columns": formatted_columns})

        saved_joins = ConnectionJoin.objects.filter(connection=connection)
        saved_layout = CanvasLayout.objects.filter(connection=connection)

        return JsonResponse({
            'success': True,
            'tables': all_tables_info,
            'joins': list(saved_joins.values('left_table', 'left_column', 'right_table', 'right_column', 'join_type', 'cardinality')),
            'layout': list(saved_layout.values('table_name', 'x_pos', 'y_pos', 'collapsed'))
        })
    except Exception as e:
        logger.error(f"Error getting data model for connection {connection_id}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_POST
def save_data_model_api(request, connection_id):
    """API endpoint to save the joins and layout for a given connection."""
    if request.user.user_type not in ['Admin', 'Moderator']:
        return JsonResponse({'success': False, 'error': "Permission denied."}, status=403)

    connection = get_object_or_404(ExternalConnection, id=connection_id, owner=request.user)

    try:
        data = json.loads(request.body)

        # --- Save Joins ---
        ConnectionJoin.objects.filter(connection=connection).delete()

        join_objects_to_create = []
        for join_data in data.get('joins', []):
            join_objects_to_create.append(ConnectionJoin(
                connection=connection,
                left_table=join_data.get('leftTable') or join_data.get('left_table', ''),
                left_column=join_data.get('leftColumn') or join_data.get('left_column', ''),
                right_table=join_data.get('rightTable') or join_data.get('right_table', ''),
                right_column=join_data.get('rightColumn') or join_data.get('right_column', ''),
                join_type=join_data.get('joinType') or join_data.get('join_type', 'INNER'),
                cardinality=join_data.get('cardinality', 'one-to-many')
            ))
        if join_objects_to_create:
            ConnectionJoin.objects.bulk_create(join_objects_to_create)

        # --- Save Layout ---
        CanvasLayout.objects.filter(connection=connection).delete()

        layout_objects_to_create = []
        for layout_data in data.get('layout', []):
            layout_objects_to_create.append(CanvasLayout(
                connection=connection,
                table_name=layout_data.get('tableName', ''),
                x_pos=int(layout_data.get('x', 0)),
                y_pos=int(layout_data.get('y', 0)),
                collapsed=layout_data.get('collapsed', False)
            ))
        if layout_objects_to_create:
            CanvasLayout.objects.bulk_create(layout_objects_to_create)

        return JsonResponse({'success': True, 'message': "Data model saved successfully."})

    except Exception as e:
        logger.error(f"[{request.user.username}] Error saving data model for connection {connection_id}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
@login_required
def data_model_designer(request):
    """Renders the main data model designer page."""
    connections = ExternalConnection.objects.filter(owner=request.user).order_by('nickname')
    return render(request, 'data_model.html', {
        'connections': connections, 
        'full_width_page': True,
        'current_user': request.user
    })

@login_required
@require_GET
def test_connection(request, connection_id):
    """API endpoint to test a single database connection."""
    try:
        engine = get_external_engine(connection_id, request.user)
        if engine:
            engine.dispose()
            return JsonResponse({'success': True, 'message': "Connection successful!"})
        else:
            return JsonResponse({'success': False, 'error': "Connection failed. Check credentials and network."})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# @login_required
# def get_model(request, connection_id):
#     """API endpoint to get all necessary data for the modeling canvas."""
#     engine = get_external_engine(connection_id, request.user)
#     if not engine:
#         return JsonResponse({'success': False, 'error': "Database connection failed."}, status=500)

#     try:
#         inspector = inspect(engine)
#         all_tables_info = []
        
#         numeric_types = ['INT', 'INTEGER', 'SMALLINT', 'BIGINT', 'FLOAT', 'REAL', 'NUMERIC', 'DECIMAL', 'DOUBLE']

#         for table_name in inspector.get_table_names():
#             columns = inspector.get_columns(table_name)
#             pks = inspector.get_pk_constraint(table_name).get('constrained_columns', [])
            
#             formatted_columns = []
#             for c in columns:
#                 col_type_str = str(c['type']).upper()
#                 is_numeric = any(num_type in col_type_str for num_type in numeric_types)
#                 formatted_columns.append({
#                     "name": c['name'], 
#                     "type": str(c['type']), 
#                     "is_pk": c['name'] in pks,
#                     "is_numeric": is_numeric
#                 })
            
#             all_tables_info.append({
#                 "name": table_name,
#                 "columns": formatted_columns
#             })

#         saved_joins = ConnectionJoin.objects.filter(connection_id=connection_id)
#         saved_layout = CanvasLayout.objects.filter(connection_id=connection_id)

#         return JsonResponse({
#             'success': True,
#             'tables': all_tables_info,
#             'joins': [{
#                 "id": j.id, 
#                 "left_table": j.left_table, 
#                 "left_column": j.left_column,
#                 "right_table": j.right_table, 
#                 "right_column": j.right_column,
#                 "join_type": j.join_type, 
#                 "cardinality": j.cardinality
#             } for j in saved_joins],
#             # This layout section is now corrected
#             'layout': [{
#                 "table_name": l.table_name, 
#                 "x_pos": l.x_pos, # Corrected key
#                 "y_pos": l.y_pos, # Corrected key
#                 "collapsed": l.collapsed
#             } for l in saved_layout]
#         })
#     except Exception as e:
#         return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_GET
def suggest_joins(request, connection_id):
    """
    Suggests possible joins between tables in a given connection.
    Uses heuristics based on column names, primary keys, and foreign key patterns.
    """
    try:
        engine = get_external_engine(connection_id, request.user)
        if not engine:
            return JsonResponse({'success': False, 'error': "Database connection failed."}, status=500)

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        suggested_joins = []

        # Cache column metadata for efficiency
        table_columns = {
            table: inspector.get_columns(table)
            for table in tables
        }

        # Build a map of primary keys
        table_primary_keys = {
            table: next((col['name'] for col in cols if col.get('primary_key')), None)
            for table, cols in table_columns.items()
        }

        # Heuristic join detection
        for left_table in tables:
            left_cols = table_columns[left_table]

            for right_table in tables:
                if left_table == right_table:
                    continue

                right_cols = table_columns[right_table]
                right_pk = table_primary_keys.get(right_table)

                if not right_pk:
                    continue

                # Heuristic 1: foreign key naming convention
                fk_candidates = [f"{right_table}_id", f"{right_pk}", f"{right_table}_{right_pk}"]

                for left_col in left_cols:
                    left_col_name = left_col['name']
                    if left_col_name in fk_candidates:
                        suggested_joins.append({
                            "left_table": left_table,
                            "left_column": left_col_name,
                            "right_table": right_table,
                            "right_column": right_pk,
                            "join_type": "INNER",
                            "cardinality": "many-to-one",
                            "confidence": "high"
                        })

                # Heuristic 2: exact column name match
                for left_col in left_cols:
                    for right_col in right_cols:
                        if left_col['name'] == right_col['name'] and left_col['name'] != right_pk:
                            suggested_joins.append({
                                "left_table": left_table,
                                "left_column": left_col['name'],
                                "right_table": right_table,
                                "right_column": right_col['name'],
                                "join_type": "INNER",
                                "cardinality": "ambiguous",
                                "confidence": "medium"
                            })

        # Deduplicate suggestions
        seen = set()
        final_joins = []
        for join in suggested_joins:
            key = (
                join['left_table'], join['left_column'],
                join['right_table'], join['right_column']
            )
            if key not in seen:
                seen.add(key)
                final_joins.append(join)

        return JsonResponse({'success': True, 'joins': final_joins})

    except Exception as e:
        logger.error(f"[{request.user.username}] Failed to suggest joins for connection {connection_id}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': f"Join suggestion failed: {str(e)}"}, status=500)

@login_required
@require_POST
def validate_model(request, connection_id):
    """API endpoint to validate the data model for issues."""
    try:
        data = json.loads(request.body)
        # Implement validation logic here
        issues = []
        # Add validation logic as needed
        
        return JsonResponse({'success': True, 'issues': issues})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# @login_required
# def save_model(request, connection_id):
#     """API endpoint to save the joins and layout."""
#     if request.user.user_type not in ['Admin', 'Moderator']:
#         return JsonResponse({'success': False, 'error': "Permission denied."}, status=403)

#     if request.method == 'POST':
#         data = json.loads(request.body)
        
#         try:
#             # Save Joins (Delete and Re-add)
#             ConnectionJoin.objects.filter(connection_id=connection_id).delete()
#             for join_data in data.get('joins', []):
#                 new_join = ConnectionJoin(
#                     connection_id=connection_id,
#                     left_table=join_data.get('leftTable'),      # Corrected key
#                     left_column=join_data.get('leftColumn'),  # Corrected key
#                     right_table=join_data.get('rightTable'),    # Corrected key
#                     right_column=join_data.get('rightColumn'),# Corrected key
#                     join_type=join_data.get('joinType', 'INNER'),
#                     cardinality=join_data.get('cardinality', 'one-to-many')
#                 )
#                 new_join.save()

#             # Save Layout (Delete and Re-add)
#             CanvasLayout.objects.filter(connection_id=connection_id).delete()
#             for layout_data in data.get('layout', []):
#                 new_layout = CanvasLayout(
#                     connection_id=connection_id,
#                     table_name=layout_data.get('tableName'), # Corrected key
#                     x_pos=int(layout_data.get('x', 0)),
#                     y_pos=int(layout_data.get('y', 0)),
#                     collapsed=layout_data.get('collapsed', False)
#                 )
#                 new_layout.save()
            
#             return JsonResponse({'success': True, 'message': "Data model saved successfully."})
#         except Exception as e:
#             return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
#     return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)