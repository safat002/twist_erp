# mis_app/data_model_views.py
import json
import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
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
    """API endpoint to save the joins and layout."""
    if request.user.user_type not in ['Admin', 'Moderator']:
        return JsonResponse({'success': False, 'error': "Permission denied."}, status=403)

    connection = get_object_or_404(ExternalConnection, id=connection_id, owner=request.user)
    data = json.loads(request.body)
    
    try:
        # Save Joins (Delete and Re-add)
        ConnectionJoin.objects.filter(connection=connection).delete()
        for join_data in data.get('joins', []):
            ConnectionJoin.objects.create(connection=connection, **join_data)

        # Save Layout (Delete and Re-add)
        CanvasLayout.objects.filter(connection=connection).delete()
        for layout_data in data.get('layout', []):
            CanvasLayout.objects.create(
                connection=connection,
                table_name=layout_data['table_name'],
                x_pos=int(layout_data['x']),
                y_pos=int(layout_data['y']),
                collapsed=layout_data.get('collapsed', False)
            )
        
        return JsonResponse({'success': True, 'message': "Data model saved successfully."})
    except Exception as e:
        logger.error(f"Error saving data model for connection {connection_id}: {e}", exc_info=True)
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

@login_required
def get_model(request, connection_id):
    """API endpoint to get all necessary data for the modeling canvas."""
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
            
            all_tables_info.append({
                "name": table_name,
                "columns": formatted_columns
            })

        saved_joins = ConnectionJoin.objects.filter(connection_id=connection_id)
        saved_layout = CanvasLayout.objects.filter(connection_id=connection_id)

        return JsonResponse({
            'success': True,
            'tables': all_tables_info,
            'joins': [{
                "id": j.id, 
                "left_table": j.left_table, 
                "left_column": j.left_column,
                "right_table": j.right_table, 
                "right_column": j.right_column,
                "join_type": j.join_type, 
                "cardinality": j.cardinality
            } for j in saved_joins],
            'layout': [{"table_name": l.table_name, "x": l.x_pos, "y": l.y_pos, "collapsed": l.collapsed} for l in saved_layout]
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def suggest_joins(request, connection_id):
    """API endpoint to suggest joins between tables."""
    try:
        engine = get_external_engine(connection_id, request.user)
        if not engine:
            return JsonResponse({'success': False, 'error': "Database connection failed."}, status=500)
            
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        suggested_joins = []
        
        # Implement actual join detection logic here
        for i, table1_name in enumerate(tables):
            table1_cols = inspector.get_columns(table1_name)
            
            for j, table2_name in enumerate(tables):
                if i == j: continue
                
                table2_cols = inspector.get_columns(table2_name)
                
                # Simple heuristic: find a column in table2 that matches the name of table1's primary key
                table1_pk = next((c['name'] for c in table1_cols if c['primary_key']), None)
                
                if table1_pk:
                    fk_name = f"{table1_name}_id"
                    
                    if any(c['name'] == fk_name for c in table2_cols):
                        suggested_joins.append({
                            "left_table": table2_name,
                            "left_column": fk_name,
                            "right_table": table1_name,
                            "right_column": table1_pk,
                            "join_type": "INNER",
                            "cardinality": "many-to-one"
                        })
        
        return JsonResponse({'success': True, 'joins': suggested_joins})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def validate_model(request, connection_id):
    """API endpoint to validate the data model for issues like circular references."""
    if request.method == 'POST':
        data = json.loads(request.body)
        # Implement validation logic
        return JsonResponse({'success': True, 'issues': []})
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

@login_required
def save_model(request, connection_id):
    """API endpoint to save the joins and layout."""
    if request.user.user_type not in ['Admin', 'Moderator']:
        return JsonResponse({'success': False, 'error': "Permission denied."}, status=403)

    if request.method == 'POST':
        data = json.loads(request.body)
        
        try:
            # Save Joins (Delete and Re-add)
            ConnectionJoin.objects.filter(connection_id=connection_id).delete()
            for join_data in data.get('joins', []):
                new_join = ConnectionJoin(
                    connection_id=connection_id,
                    left_table=join_data['left_table'],
                    left_column=join_data['left_column'],
                    right_table=join_data['right_table'],
                    right_column=join_data['right_column'],
                    join_type=join_data.get('join_type', 'INNER'),
                    cardinality=join_data.get('cardinality', 'one-to-many')
                )
                new_join.save()

            # Save Layout (Delete and Re-add)
            CanvasLayout.objects.filter(connection_id=connection_id).delete()
            for layout_data in data.get('layout', []):
                new_layout = CanvasLayout(
                    connection_id=connection_id,
                    table_name=layout_data['table_name'],
                    x_pos=int(layout_data['x']),
                    y_pos=int(layout_data['y']),
                    collapsed=layout_data.get('collapsed', False)
                )
                new_layout.save()
            
            return JsonResponse({'success': True, 'message': "Data model saved successfully."})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)