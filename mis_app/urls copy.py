# mis_app/urls.py (Updated with data management URLs)

"""
URL Configuration for MIS Application
Updated to include all data management endpoints
"""

from django.urls import path
from . import views, data_views

app_name = 'mis_app'

urlpatterns = [
    # Authentication URLs
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    
    # Main application URLs
    path('home/', views.home_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Data Management URLs
    path('data-management/', data_views.data_management_view, name='data_management'),
    
    # Data Management API URLs
    path('api/data/check-password/', data_views.check_password, name='api_check_password'),
    path('api/data/inspect-file/', data_views.inspect_file, name='api_inspect_file'),
    path('api/data/upload-data/', data_views.upload_data_api, name='api_upload_data'),

     path('api/analyze_upload', data_views.analyze_upload, name='api_analyze_upload'),
    path('api/create_table_from_import', data_views.create_table_from_import, name='api_create_table_from_import'),

    path('api/data/get-columns-for-table/<uuid:connection_id>/<str:table_name>/', 
         data_views.get_columns_for_table, name='api_get_columns_for_table'),
    path('api/data/rename-table/', data_views.rename_table, name='api_rename_table'),
    path('api/data/rename-column/', data_views.rename_column, name='api_rename_column'),
    path('api/data/truncate-table/', data_views.truncate_table, name='api_truncate_table'),
    path('api/data/drop-table/', data_views.drop_table, name='api_drop_table'),
    path('api/data/delete-rows/', data_views.delete_rows, name='api_delete_rows'),
    path('api/data/get-table-data/<uuid:connection_id>/<str:table_name>/', data_views.get_table_data, name='api_get_table_data'),
    path('api/data/preview-data/', data_views.preview_data, name='api_preview_data'),
    path('api/data/confirm-upload/', data_views.confirm_upload, name='api_confirm_upload'),
    path('api/data/create-table/', data_views.create_table, name='api_create_table'),
    path('api/data/add-column/', data_views.add_column, name='api_add_column'),
    path('api/data/drop-column/', data_views.drop_column, name='api_drop_column'),
    path('api/data/modify-column-type/', data_views.modify_column_type, name='api_modify_column_type'),
    path('api/data/set-primary-key/', data_views.set_primary_key, name='api_set_primary_key'),
    path('api/data/visible-tables/<uuid:connection_id>/', 
         data_views.get_visible_tables_for_connection, name='api_get_visible_tables'),
    path('api/data/get-detailed-columns/<uuid:connection_id>/', 
         data_views.get_detailed_columns, name='api_get_detailed_columns'),
    path('api/data/get-table-schema/<str:table_name>/', data_views.get_table_schema_api, name='api_get_table_schema'),


    # Report Builder URLs
    path('report-builder/', views.report_builder_view, name='report_builder'),
    path('api/reports/', views.reports_api, name='api_reports'),
    path('api/reports/<uuid:report_id>/', views.report_detail_api, name='api_report_detail'),
    path('api/reports/<uuid:report_id>/execute/', views.execute_report, name='api_execute_report'),
    
    # Dashboard URLs
    path('dashboard-design/', views.dashboard_design_view, name='dashboard_design'),
    path('dashboard-management/', views.dashboard_management_view, name='dashboard_management'),
    path('api/dashboards/', views.dashboards_api, name='api_dashboards'),
    path('api/dashboards/<uuid:dashboard_id>/', views.dashboard_detail_api, name='api_dashboard_detail'),
    
    # Database Connection URLs
    path('database-management/', views.database_management_view, name='database_management'),
    path('api/connections/', views.connections_api, name='api_connections'),
    path('api/connections/<uuid:connection_id>/', views.connection_detail_api, name='api_connection_detail'),
    path('api/connections/<uuid:connection_id>/test/', views.test_database_connection, name='api_test_connection'),
    path('api/connections/<uuid:connection_id>/tables/', views.get_connection_tables_api, name='api_get_connection_tables'),
    path('api/connections/<uuid:connection_id>/tables/all/', views.get_all_connection_tables_api, name='api_get_all_connection_tables'),
    
    # User Management URLs (Admin only)
    path('user-management/', views.user_management_view, name='user_management'),
    path('api/users/', views.users_api, name='api_users'),
    path('api/users/<int:user_id>/', views.user_detail_api, name='api_user_detail'),
    
    # Utility URLs
    path('api/validate-sql/', views.validate_sql, name='api_validate_sql'),
    path('api/get-csrf-token/', views.get_csrf_token, name='api_get_csrf_token'),

]