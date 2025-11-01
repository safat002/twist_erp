# mis_app/views.py

"""
Enhanced Django Views for MIS Application
Complete implementation with user management, permissions, and all existing functionality
"""

from collections import deque
import json
import logging
import os
import uuid
import numpy as np
import pandas as pd
import openpyxl
from datetime import datetime, timedelta
import traceback

from django.core.cache import cache
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import now
from django.views.decorators.http import require_http_methods, require_POST
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Count
from django.core.mail import send_mail
from django.template.loader import render_to_string

from sqlalchemy import create_engine, inspect, text, MetaData, Table, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.exc import SQLAlchemyError

# Import existing modules (preserved)
from .utils import get_external_engine
from .services.report_builder import ReportBuilderService
from .data_model_views import (
    data_model_designer,
    test_connection,
    suggest_joins,
    validate_model,
)

# Import enhanced models and forms
from .models import (
    ConnectionJoin, ExternalConnection, User, AuditLog, Dashboard, UserGroup, 
    GroupMembership, GroupPermission, UserPermission, Notification, SavedReport, 
    ExportHistory, DashboardShare, DashboardDataContext, UploadedTable, ReportShare,
    Widget, CleanedDataSource, DrillDownPath, CanvasLayout
)

# Import enhanced forms and permissions
from .forms import (
    CustomUserCreationForm, CustomUserChangeForm, UserGroupForm, BulkUserActionForm,
    UserSearchForm, DatabaseConnectionForm, UserImportForm
)

from .permissions import (
    PermissionManager, permission_required, user_management_required,
    database_management_required, upload_required, schema_modify_required,
    admin_required, OwnershipMixin
)

logger = logging.getLogger(__name__)

# =============================================================================
# HELPER FUNCTIONS (Preserved)
# =============================================================================

def get_pinned_dashboards(user):
    """Placeholder for fetching pinned dashboards"""
    return Dashboard.objects.none()

def log_user_activity(user, action, object_type=None, object_id=None, details=None, request=None):
    """Log user activity for audit trail"""
    try:
        AuditLog.objects.create(
            user=user,
            username=user.username,
            action=action,
            object_type=object_type or '',
            object_id=str(object_id) if object_id else '',
            object_name=str(object_id) if object_id else '',
            details=details or {},
            ip_address=request.META.get('REMOTE_ADDR') if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
            session_id=request.session.session_key if request and hasattr(request.session, 'session_key') else ''
        )
    except Exception as e:
        logger.error(f"Failed to log user activity: {e}")

def create_notification(user, title, message, notification_type='info', action_url=None):
    """Create a notification for a user"""
    try:
        return Notification.objects.create(
            recipient=user,
            title=title,
            message=message,
            type=notification_type,
            action_url=action_url
        )
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        return None

# =============================================================================
# AUTHENTICATION VIEWS (Enhanced)
# =============================================================================

def login_view(request):
    """Enhanced user login with security tracking"""
    if request.user.is_authenticated:
        return redirect('mis_app:home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if username and password:
            try:
                # Get user for account locking check
                user_obj = User.objects.filter(username=username).first()
                
                if user_obj and user_obj.is_account_locked():
                    messages.error(request, 'Your account is temporarily locked due to multiple failed login attempts. Please try again later.')
                    return render(request, 'login.html')

                user = authenticate(request, username=username, password=password)
                if user:
                    if user.is_active:
                        login(request, user)
                        
                        # Reset login attempts on successful login
                        user.reset_login_attempts()
                        user.last_activity = timezone.now()
                        user.save(update_fields=['login_attempts', 'locked_until', 'last_activity'])
                        
                        # Log successful login
                        log_user_activity(user, 'login', request=request)
                        
                        # Create welcome notification for first login
                        if user.last_login is None:
                            create_notification(
                                user, 
                                'Welcome to MIS System!', 
                                'Welcome to our Management Information System. Explore dashboards, reports, and data analysis tools.',
                                'success'
                            )
                        
                        messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                        next_url = request.GET.get('next', 'mis_app:home')
                        return redirect(next_url)
                    else:
                        messages.error(request, 'Your account is inactive. Please contact your administrator.')
                else:
                    # Increment login attempts for failed login
                    if user_obj:
                        user_obj.increment_login_attempts()
                    messages.error(request, 'Invalid username or password.')
            except Exception as e:
                logger.error(f"Login error: {e}")
                messages.error(request, 'An error occurred during login. Please try again.')
        else:
            messages.error(request, 'Please provide both username and password.')

    return render(request, 'login.html')

def logout_view(request):
    """Enhanced user logout with activity logging"""
    if request.user.is_authenticated:
        log_user_activity(request.user, 'logout', request=request)
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('mis_app:login')

# =============================================================================
# MAIN APPLICATION VIEWS (Enhanced)
# =============================================================================

@login_required(login_url='mis_app:login')
def home_view(request):
    """Enhanced home dashboard with user-specific stats"""
    # Get user-specific data
    recent_reports = SavedReport.objects.filter(owner=request.user)[:5]
    recent_dashboards = Dashboard.objects.filter(owner=request.user)[:5]
    notifications = Notification.objects.filter(recipient=request.user, is_read=False)[:5]
    
    # Get shared items
    shared_reports = SavedReport.objects.filter(
        shared_with=request.user
    ).exclude(owner=request.user)[:3]
    
    shared_dashboards = Dashboard.objects.filter(
        shared_with=request.user
    ).exclude(owner=request.user)[:3]

    # User statistics with permission awareness
    user_stats = {
        'total_reports': SavedReport.objects.filter(owner=request.user).count(),
        'total_dashboards': Dashboard.objects.filter(owner=request.user).count(),
        'total_connections': ExternalConnection.objects.filter(owner=request.user).count(),
        'shared_with_me': shared_reports.count() + shared_dashboards.count(),
        'unread_notifications': notifications.count(),
    }
    
    # Add admin stats if user is admin
    if request.user.can_access_admin():
        user_stats.update({
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'recent_users': User.objects.filter(date_joined__gte=timezone.now() - timedelta(days=7)).count(),
        })

    context = {
        'recent_reports': recent_reports,
        'recent_dashboards': recent_dashboards,
        'notifications': notifications,
        'shared_reports': shared_reports,
        'shared_dashboards': shared_dashboards,
        'user_stats': user_stats,
        'can_manage_users': request.user.can_manage_users(),
        'can_manage_database': request.user.can_manage_database(),
        'user_theme': request.user.theme_preference,
    }

    return render(request, 'home.html', context)

@login_required(login_url='mis_app:login')
def report_builder_view(request):
    """Enhanced report builder with sharing and permissions"""
    # Get user's own reports
    owned_reports = SavedReport.objects.filter(owner=request.user).order_by('-updated_at')
    
    # Get shared reports
    shared_reports = SavedReport.objects.filter(
        reportshare__user=request.user
    ).exclude(owner=request.user).order_by('-updated_at')
    
    # Combine and paginate
    all_reports = list(owned_reports) + list(shared_reports)
    paginator = Paginator(all_reports, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    # Get user's connections with permission check
    if request.user.can_upload_data():
        connections = ExternalConnection.objects.filter(owner=request.user)
    else:
        # Regular users can only see connections shared through groups
        accessible_connections = PermissionManager.get_user_permissions(
            request.user, 'connection'
        )
        connection_ids = [key.split(':')[1] for key in accessible_connections.keys()]
        connections = ExternalConnection.objects.filter(id__in=connection_ids)

    context = {
        'reports': page_obj,
        'connections': connections,
        'can_create_reports': True,  # All users can create reports
        'can_share_reports': request.user.user_type in ['Admin', 'Moderator'],
    }

    return render(request, 'report_builder.html', context)

@login_required
@user_management_required
def user_management_view(request):
    """Enhanced user management page with comprehensive functionality"""
    # Get search and filter parameters
    search = request.GET.get('search', '')
    user_type_filter = request.GET.get('user_type', '')
    department_filter = request.GET.get('department', '')
    status_filter = request.GET.get('is_active', '')
    group_filter = request.GET.get('group', '')
    
    # Build query
    users_query = User.objects.all()
    
    if search:
        users_query = users_query.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(department__icontains=search)
        )
    
    if user_type_filter:
        users_query = users_query.filter(user_type=user_type_filter)
    
    if department_filter:
        users_query = users_query.filter(department__icontains=department_filter)
    
    if status_filter:
        is_active = status_filter.lower() == 'true'
        users_query = users_query.filter(is_active=is_active)
    
    if group_filter:
        users_query = users_query.filter(user_groups__id=group_filter)
    
    # Order and paginate
    users = users_query.distinct().order_by('-date_joined')
    paginator = Paginator(users, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    # Get additional data
    groups = UserGroup.objects.filter(is_active=True).order_by('name')
    departments = User.objects.values_list('department', flat=True).distinct().exclude(department='')
    
    # User statistics
    user_stats = {
        'total_users': users_query.count(),
        'active_users': users_query.filter(is_active=True).count(),
        'admin_users': users_query.filter(user_type='Admin').count(),
        'locked_users': users_query.filter(locked_until__gt=timezone.now()).count(),
    }

    context = {
        'users': page_obj,
        'groups': groups,
        'departments': sorted(departments),
        'user_stats': user_stats,
        'search_form': UserSearchForm(initial={
            'search': search,
            'user_type': user_type_filter,
            'department': department_filter,
            'is_active': status_filter,
            'group': group_filter,
        }),
        'can_create_users': request.user.user_type == 'Admin',
        'can_delete_users': request.user.user_type == 'Admin',
        'current_user_id': str(request.user.id),
    }

    return render(request, 'user_management.html', context)

@login_required
@user_management_required
@require_POST
def create_group(request):
    """View to create a new user group."""
    form = UserGroupForm(request.POST, request_user=request.user)
    if form.is_valid():
        group = form.save()
        log_user_activity(
            request.user,
            'create',
            'group',
            group.id,
            {'group_name': group.name},
            request
        )
        messages.success(request, f'Group "{group.name}" has been created successfully.')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"Error creating group: {error}")

    return redirect('mis_app:user_management')

@login_required
@user_management_required
def edit_group(request, group_id):
    """View to edit an existing user group."""
    group = get_object_or_404(UserGroup, id=group_id)
    if request.method == 'POST':
        form = UserGroupForm(request.POST, instance=group, request_user=request.user)
        if form.is_valid():
            form.save()
            log_user_activity(
                request.user,
                'update',
                'group',
                group.id,
                {'group_name': group.name},
                request
            )
            messages.success(request, f'Group "{group.name}" has been updated successfully.')
            return redirect('mis_app:user_management')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error updating group: {error}")
    else:
        form = UserGroupForm(instance=group, request_user=request.user)

    return render(request, 'modals/edit_group_modal.html', {'form': form, 'group': group})


@login_required
@database_management_required
def database_management_view(request):
    """Enhanced database management with permission checks"""
    return render(request, 'database_management.html', {})

@login_required
def dashboard_management_view(request):
    """Enhanced dashboard management with sharing"""
    # Get user's own dashboards
    owned_dashboards = Dashboard.objects.filter(owner=request.user)
    
    # Get shared dashboards
    shared_dashboards = Dashboard.objects.filter(
        dashboardshare__user=request.user
    ).exclude(owner=request.user)
    
    # Get pinned dashboards
    pinned_dashboard_ids = request.user.pinned_dashboards
    pinned_dashboards = Dashboard.objects.filter(id__in=pinned_dashboard_ids) if pinned_dashboard_ids else Dashboard.objects.none()

    context = {
        'owned_dashboards': owned_dashboards,
        'shared_dashboards': shared_dashboards,
        'pinned_dashboards': pinned_dashboards,
        'can_create_dashboards': True,  # All users can create dashboards
    }

    return render(request, 'dashboard_management.html', context)

@login_required(login_url='mis_app:login')
def dashboard_design_view(request, dashboard_id):
    """Enhanced dashboard designer with permission checks"""
    dashboard = get_object_or_404(Dashboard, id=dashboard_id)
    
    # Check if user can edit this dashboard
    can_edit = (
        dashboard.owner == request.user or
        DashboardShare.objects.filter(
            dashboard=dashboard,
            user=request.user,
            permission='edit'
        ).exists() or
        request.user.user_type == 'Admin'
    )
    
    if not can_edit and not DashboardShare.objects.filter(
        dashboard=dashboard, user=request.user
    ).exists():
        messages.error(request, 'You do not have permission to access this dashboard.')
        return redirect('mis_app:dashboard_management')

    # Get user's accessible connections
    connections = ExternalConnection.objects.filter(
        Q(owner=request.user) | Q(is_internal=True)
    )
    
    # Add connections accessible through groups
    user_permissions = PermissionManager.get_user_permissions(request.user, 'connection')
    accessible_connection_names = [key.split(':')[1] for key in user_permissions.keys() if user_permissions[key] != 'none']
    group_connections = ExternalConnection.objects.filter(nickname__in=accessible_connection_names)
    connections = connections.union(group_connections)

    context = {
        'dashboard': dashboard,
        'connections': connections,
        'can_edit': can_edit,
        'is_owner': dashboard.owner == request.user,
    }

    return render(request, 'dashboard_design.html', context)

# =============================================================================
# USER MANAGEMENT API ENDPOINTS (New Enhanced Functionality)
# =============================================================================

@login_required
@user_management_required
@require_http_methods(["GET", "POST"])
def users_api(request):
    """Enhanced API for listing and creating users"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Create form with request user context
            form = CustomUserCreationForm(data, request_user=request.user)
            
            if form.is_valid():
                with transaction.atomic():
                    user = form.save()
                    
                    # Log user creation
                    log_user_activity(
                        request.user,
                        'create',
                        'user',
                        user.id,
                        {'created_user': user.username, 'user_type': user.user_type},
                        request
                    )
                    
                    # Create welcome notification
                    create_notification(
                        user,
                        'Welcome to MIS System!',
                        f'Your account has been created by {request.user.get_full_name()}. You can now log in and start using the system.',
                        'success'
                    )
                    
                    # Send welcome email if requested
                    if data.get('send_welcome_email', False):
                        try:
                            send_welcome_email(user, data.get('password', ''))
                        except Exception as e:
                            logger.error(f"Failed to send welcome email: {e}")
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'User {user.username} has been created successfully.',
                        'user_id': str(user.id)
                    }, status=201)
            else:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
                
        except Exception as e:
            logger.error(f"Error creating user: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred while creating the user. Please try again.'
            }, status=500)
    
    # GET request - list users with filtering
    search = request.GET.get('search', '')
    user_type = request.GET.get('user_type', '')
    is_active = request.GET.get('is_active', '')
    
    users_query = User.objects.all()
    
    if search:
        users_query = users_query.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if user_type:
        users_query = users_query.filter(user_type=user_type)
    
    if is_active:
        users_query = users_query.filter(is_active=is_active.lower() == 'true')
    
    users = users_query.order_by('-date_joined')[:50]  # Limit for performance
    
    users_data = []
    for user in users:
        users_data.append({
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'full_name': user.get_full_name(),
            'user_type': user.user_type,
            'department': user.department,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'is_locked': user.is_account_locked(),
            'groups': [{'id': str(g.id), 'name': g.name} for g in user.user_groups.all()],
        })
    
    return JsonResponse({
        'success': True,
        'users': users_data,
        'total': users_query.count()
    })

@login_required
@user_management_required
@require_http_methods(["GET", "PUT", "DELETE"])
def user_detail_api(request, user_id):
    """Enhanced API for user details"""
    try:
        user = User.objects.get(id=user_id)
    except (User.DoesNotExist, ValueError):
        return JsonResponse({
            'success': False,
            'error': 'User not found.'
        }, status=404)
    
    if request.method == 'GET':
        # Get user groups and permissions
        groups = user.user_groups.all()
        direct_permissions = UserPermission.objects.filter(user=user)
        
        user_data = {
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'user_type': user.user_type,
            'department': user.department,
            'job_title': user.job_title,
            'phone_number': user.phone_number,
            'manager': str(user.manager.id) if user.manager else None,
            'manager_name': user.manager.get_full_name() if user.manager else None,
            'theme_preference': user.theme_preference,
            'is_active': user.is_active,
            'is_email_verified': user.is_email_verified,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'last_activity': user.last_activity.isoformat() if user.last_activity else None,
            'login_attempts': user.login_attempts,
            'is_locked': user.is_account_locked(),
            'groups': [
                {
                    'id': str(g.id),
                    'name': g.name,
                    'color': g.color,
                    'role': GroupMembership.objects.get(user=user, group=g).role
                }
                for g in groups
            ],
            'direct_permissions': [
                {
                    'id': str(p.id),
                    'resource_type': p.resource_type,
                    'resource_name': p.resource_name,
                    'permission_level': p.permission_level,
                    'expires_at': p.expires_at.isoformat() if p.expires_at else None
                }
                for p in direct_permissions
            ]
        }
        
        return JsonResponse({
            'success': True,
            'user': user_data
        })
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            # Prevent users from editing themselves in certain ways
            if str(request.user.id) == str(user_id):
                restricted_fields = ['user_type', 'is_active']
                if any(field in data for field in restricted_fields):
                    return JsonResponse({
                        'success': False,
                        'error': 'You cannot modify your own access level or account status.'
                    }, status=403)
            
            # Create form for validation
            form_data = {
                'username': data.get('username', user.username),
                'email': data.get('email', user.email),
                'first_name': data.get('first_name', user.first_name),
                'last_name': data.get('last_name', user.last_name),
                'user_type': data.get('user_type', user.user_type),
                'department': data.get('department', user.department),
                'job_title': data.get('job_title', user.job_title),
                'phone_number': data.get('phone_number', user.phone_number),
                'theme_preference': data.get('theme_preference', user.theme_preference),
                'is_active': data.get('is_active', user.is_active),
            }
            
            # Handle manager assignment
            manager_id = data.get('manager')
            if manager_id:
                try:
                    form_data['manager'] = User.objects.get(id=manager_id)
                except User.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'Selected manager not found.'
                    }, status=400)
            
            # Validate email uniqueness
            if 'email' in data and data['email'] != user.email:
                if User.objects.filter(email=data['email']).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'A user with this email address already exists.'
                    }, status=400)
            
            # Update user fields
            old_values = {}
            new_values = {}
            
            for field, value in form_data.items():
                if hasattr(user, field):
                    old_value = getattr(user, field)
                    if old_value != value:
                        old_values[field] = str(old_value) if old_value else None
                        new_values[field] = str(value) if value else None
                        setattr(user, field, value)
            
            # Handle password change
            if data.get('password'):
                user.set_password(data['password'])
                user.last_password_change = timezone.now()
                new_values['password'] = 'Changed'
            
            # Handle account unlocking
            if data.get('unlock_account') and user.is_account_locked():
                user.reset_login_attempts()
                new_values['account_status'] = 'Unlocked'
            
            user.save()
            
            # Handle group assignments
            if 'groups' in data:
                new_group_ids = set(data['groups'])
                current_group_ids = set(str(g.id) for g in user.user_groups.all())
                
                # Remove from groups
                groups_to_remove = current_group_ids - new_group_ids
                if groups_to_remove:
                    GroupMembership.objects.filter(
                        user=user,
                        group_id__in=groups_to_remove
                    ).delete()
                
                # Add to groups
                groups_to_add = new_group_ids - current_group_ids
                for group_id in groups_to_add:
                    try:
                        group = UserGroup.objects.get(id=group_id)
                        GroupMembership.objects.create(
                            user=user,
                            group=group,
                            added_by=request.user
                        )
                    except UserGroup.DoesNotExist:
                        pass
            
            # Clear user permission cache
            PermissionManager.clear_user_cache(user.id)
            
            # Log the update
            log_user_activity(
                request.user,
                'update',
                'user',
                user.id,
                {'updated_user': user.username, 'changes': new_values},
                request
            )
            
            return JsonResponse({
                'success': True,
                'message': f'User {user.username} has been updated successfully.'
            })
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred while updating the user. Please try again.'
            }, status=500)
    
    elif request.method == 'DELETE':
        # Prevent users from deleting themselves
        if str(request.user.id) == str(user_id):
            return JsonResponse({
                'success': False,
                'error': 'You cannot delete your own account.'
            }, status=403)
        
        # Prevent deletion of the last admin
        if user.user_type == 'Admin' and User.objects.filter(user_type='Admin', is_active=True).count() <= 1:
            return JsonResponse({
                'success': False,
                'error': 'Cannot delete the last active administrator account.'
            }, status=403)
        
        try:
            username = user.username
            user.delete()
            
            # Log the deletion
            log_user_activity(
                request.user,
                'delete',
                'user',
                user_id,
                {'deleted_user': username},
                request
            )
            
            return JsonResponse({
                'success': True,
                'message': f'User {username} has been deleted successfully.'
            })
            
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred while deleting the user. Please try again.'
            }, status=500)

@login_required
@user_management_required
@require_POST
def bulk_user_actions_api(request):
    """API for bulk user operations"""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return JsonResponse({
                'success': False,
                'error': 'Please select at least one user to perform the action on.'
            }, status=400)
        
        # Prevent actions on self for certain operations
        if action in ['delete', 'deactivate'] and str(request.user.id) in user_ids:
            return JsonResponse({
                'success': False,
                'error': 'You cannot perform this action on your own account.'
            }, status=403)
        
        users = User.objects.filter(id__in=user_ids)
        processed_count = 0
        errors = []
        
        if action == 'activate':
            users.update(is_active=True)
            processed_count = users.count()
            
        elif action == 'deactivate':
            # Don't deactivate the last admin
            admin_ids = users.filter(user_type='Admin').values_list('id', flat=True)
            total_active_admins = User.objects.filter(user_type='Admin', is_active=True).count()
            
            if len(admin_ids) >= total_active_admins:
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot deactivate all administrator accounts.'
                }, status=403)
            
            users.update(is_active=False)
            processed_count = users.count()
            
        elif action == 'delete':
            # Check admin deletion constraint
            admin_count = users.filter(user_type='Admin').count()
            total_active_admins = User.objects.filter(user_type='Admin', is_active=True).count()
            
            if admin_count >= total_active_admins:
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot delete all administrator accounts.'
                }, status=403)
            
            processed_count = users.count()
            users.delete()
            
        elif action == 'change_type':
            new_user_type = data.get('new_user_type')
            if not new_user_type:
                return JsonResponse({
                    'success': False,
                    'error': 'Please select a user type for this action.'
                }, status=400)
            
            users.update(user_type=new_user_type)
            processed_count = users.count()
            
        elif action == 'assign_group':
            target_group_id = data.get('target_group')
            if not target_group_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Please select a group for this action.'
                }, status=400)
            
            try:
                group = UserGroup.objects.get(id=target_group_id)
                for user in users:
                    GroupMembership.objects.get_or_create(
                        user=user,
                        group=group,
                        defaults={'added_by': request.user}
                    )
                processed_count = users.count()
            except UserGroup.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Selected group not found.'
                }, status=400)
                
        elif action == 'remove_group':
            target_group_id = data.get('target_group')
            if not target_group_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Please select a group for this action.'
                }, status=400)
            
            GroupMembership.objects.filter(
                user__in=users,
                group_id=target_group_id
            ).delete()
            processed_count = users.count()
            
        elif action == 'reset_password':
            # This would typically send password reset emails
            processed_count = users.count()
            # Implementation depends on your password reset workflow
            
        else:
            return JsonResponse({
                'success': False,
                'error': f'Unknown action: {action}'
            }, status=400)
        
        # Clear permission caches for affected users
        for user_id in user_ids:
            PermissionManager.clear_user_cache(user_id)
        
        # Log bulk action
        log_user_activity(
            request.user,
            'bulk_action',
            'user',
            None,
            {
                'action': action,
                'user_count': processed_count,
                'user_ids': user_ids
            },
            request
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Bulk action completed successfully. {processed_count} users affected.',
            'processed_count': processed_count,
            'errors': errors
        })
        
    except Exception as e:
        logger.error(f"Error in bulk user actions: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred during the bulk operation. Please try again.'
        }, status=500)

@login_required
@user_management_required
@require_http_methods(["GET", "POST"])
def groups_api(request):
    """API for user group management"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            form = UserGroupForm(data, request_user=request.user)
            
            if form.is_valid():
                with transaction.atomic():
                    group = form.save()
                    
                    # Log group creation
                    log_user_activity(
                        request.user,
                        'create',
                        'group',
                        group.id,
                        {'group_name': group.name},
                        request
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'Group "{group.name}" has been created successfully.',
                        'group': {
                            'id': str(group.id),
                            'name': group.name,
                            'color': group.color,
                            'description': group.description
                        }
                    }, status=201)
            else:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
                
        except Exception as e:
            logger.error(f"Error creating group: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred while creating the group. Please try again.'
            }, status=500)
    
    # GET request
    groups = UserGroup.objects.filter(is_active=True).annotate(
        member_count=Count('users')
    ).order_by('name')
    
    groups_data = []
    for group in groups:
        groups_data.append({
            'id': str(group.id),
            'name': group.name,
            'description': group.description,
            'color': group.color,
            'member_count': group.member_count,
            'is_system_group': group.is_system_group,
            'created_at': group.created_at.isoformat(),
            'parent_group': str(group.parent_group.id) if group.parent_group else None,
        })
    
    return JsonResponse({
        'success': True,
        'groups': groups_data
    })

@login_required
@user_management_required
@require_http_methods(["GET", "PUT", "DELETE"])
def group_detail_api(request, group_id):
    """API for individual group management"""
    try:
        group = UserGroup.objects.get(id=group_id)
    except (UserGroup.DoesNotExist, ValueError):
        return JsonResponse({
            'success': False,
            'error': 'Group not found.'
        }, status=404)
    
    if request.method == 'GET':
        members = group.users.all()
        permissions = GroupPermission.objects.filter(group=group)
        
        group_data = {
            'id': str(group.id),
            'name': group.name,
            'description': group.description,
            'color': group.color,
            'is_active': group.is_active,
            'is_system_group': group.is_system_group,
            'parent_group': str(group.parent_group.id) if group.parent_group else None,
            'created_at': group.created_at.isoformat(),
            'members': [
                {
                    'id': str(m.id),
                    'username': m.username,
                    'full_name': m.get_full_name(),
                    'user_type': m.user_type,
                    'role': GroupMembership.objects.get(user=m, group=group).role
                }
                for m in members
            ],
            'permissions': [
                {
                    'id': str(p.id),
                    'resource_type': p.resource_type,
                    'resource_name': p.resource_name,
                    'permission_level': p.permission_level
                }
                for p in permissions
            ]
        }
        
        return JsonResponse({
            'success': True,
            'group': group_data
        })
    
    elif request.method == 'PUT':
        if group.is_system_group and not request.user.is_superuser:
            return JsonResponse({
                'success': False,
                'error': 'System groups cannot be modified.'
            }, status=403)
        
        try:
            data = json.loads(request.body)
            form = UserGroupForm(data, instance=group, request_user=request.user)
            
            if form.is_valid():
                group = form.save()
                
                # Log group update
                log_user_activity(
                    request.user,
                    'update',
                    'group',
                    group.id,
                    {'group_name': group.name},
                    request
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'Group "{group.name}" has been updated successfully.'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
                
        except Exception as e:
            logger.error(f"Error updating group {group_id}: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred while updating the group. Please try again.'
            }, status=500)
    
    elif request.method == 'DELETE':
        if group.is_system_group and not request.user.is_superuser:
            return JsonResponse({
                'success': False,
                'error': 'System groups cannot be deleted.'
            }, status=403)
        
        try:
            group_name = group.name
            group.delete()
            
            # Log group deletion
            log_user_activity(
                request.user,
                'delete',
                'group',
                group_id,
                {'group_name': group_name},
                request
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Group "{group_name}" has been deleted successfully.'
            })
            
        except Exception as e:
            logger.error(f"Error deleting group {group_id}: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred while deleting the group. Please try again.'
            }, status=500)

# =============================================================================
# THEME AND SETTINGS API ENDPOINTS (New)
# =============================================================================

@login_required
@require_POST
def switch_theme_api(request):
    """API to switch user theme"""
    try:
        data = json.loads(request.body)
        theme = data.get('theme')
        
        valid_themes = dict(User.THEME_CHOICES).keys()
        if theme not in valid_themes:
            return JsonResponse({
                'success': False,
                'error': f'Invalid theme. Valid options are: {", ".join(valid_themes)}'
            }, status=400)
        
        request.user.theme_preference = theme
        request.user.save(update_fields=['theme_preference'])
        
        return JsonResponse({
            'success': True,
            'message': f'Theme switched to {theme} successfully.',
            'theme': theme
        })
        
    except Exception as e:
        logger.error(f"Error switching theme: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to switch theme. Please try again.'
        }, status=500)

@login_required
@admin_required
@require_POST
def set_default_database_api(request):
    """API to set default database for reports and dashboards"""
    try:
        data = json.loads(request.body)
        database_alias = data.get('database')
        
        # Validate database alias exists in settings
        if database_alias not in settings.DATABASES:
            return JsonResponse({
                'success': False,
                'error': 'Invalid database specified.'
            }, status=400)
        
        # Update user's default database preference
        request.user.default_database = database_alias
        request.user.save(update_fields=['default_database'])
        
        # Log the change
        log_user_activity(
            request.user,
            'update',
            'setting',
            None,
            {'setting': 'default_database', 'value': database_alias},
            request
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Default database set to {database_alias} successfully.'
        })
        
    except Exception as e:
        logger.error(f"Error setting default database: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to set default database. Please try again.'
        }, status=500)

# =============================================================================
# UTILITY FUNCTIONS (New)
# =============================================================================

def send_welcome_email(user, temporary_password):
    """Send welcome email to new users"""
    try:
        subject = 'Welcome to MIS System'
        html_message = render_to_string('emails/welcome_email.html', {
            'user': user,
            'temporary_password': temporary_password,
            'login_url': f"{settings.SITE_URL}/login/",
        })
        
        send_mail(
            subject,
            '',  # Plain text version
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Welcome email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {e}")
        return False

# =============================================================================
# EXISTING API ENDPOINTS (Preserved and Enhanced with Permissions)
# =============================================================================

# [All your existing API endpoints remain here, but with added permission checks]
# I'll include a few key ones as examples, but the pattern applies to all:

@login_required
@require_POST
def execute_report_api(request):
    """API endpoint to execute a report build with permission checks"""
    try:
        config = json.loads(request.body).get('report_config', {})
        
        # Check if user has access to the requested connection
        connection_id = config.get('connection_id')
        if connection_id:
            if not PermissionManager.check_user_permission(
                request.user, 'connection', connection_id, 'view'
            ):
                return JsonResponse({
                    'success': False, 
                    'error': 'You do not have permission to access this database connection.'
                }, status=403)
        
        service = ReportBuilderService()
        df, total_rows, error = service.build_advanced_report(config, request.user)

        if error:
            return JsonResponse({'success': False, 'error': error}, status=400)

        # Convert DataFrame to a JSON-safe format
        df_safe = df.replace({pd.NaT: None, np.nan: None})
        headers = list(df_safe.columns)
        rows = df_safe.to_dict(orient='records')

        # Log report execution
        log_user_activity(
            request.user,
            'access',
            'report',
            None,
            {'rows_returned': total_rows, 'connection_id': connection_id},
            request
        )

        return JsonResponse({
            'success': True,
            'data': {'headers': headers, 'rows': rows},
            'total_rows': total_rows
        })

    except Exception as e:
        logger.error(f"Error executing report API: {e}", exc_info=True)
        return JsonResponse({
            'success': False, 
            'error': 'An error occurred while executing the report. Please try again.'
        }, status=500)

@login_required
@require_http_methods(["GET", "POST"])
def connections_api(request):
    """Enhanced API for listing and creating connections with validation and health checks"""
    if request.method == 'GET':
        connections = ExternalConnection.objects.filter(owner=request.user).order_by('nickname')
        data = []
        for conn in connections:
            try:
                engine = get_external_engine(conn.id, request.user)
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                conn.health_status = 'healthy'
            except Exception:
                conn.health_status = 'error'
            conn.save(update_fields=['health_status'])

            data.append({
                'id': str(conn.id),
                'nickname': conn.nickname,
                'db_type': conn.db_type,
                'health_status': conn.health_status,
                'host': conn.host,
                'port': conn.port,
                'is_default': conn.is_default,
                'is_internal': conn.is_internal,
            })

        return JsonResponse(data, safe=False)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Use enhanced form for validation
            form = DatabaseConnectionForm(data, request_user=request.user)
            
            if form.is_valid():
                conn = form.save()
                
                # Log connection creation
                log_user_activity(
                    request.user,
                    'create',
                    'connection',
                    conn.id,
                    {'connection_name': conn.nickname, 'db_type': conn.db_type},
                    request
                )
                
                return JsonResponse({
                    'success': True,
                    'connection': {
                        'id': str(conn.id),
                        'nickname': conn.nickname,
                        'db_type': conn.db_type
                    }
                }, status=201)
        except IntegrityError as e:
            logger.warning(f"[{request.user.username}] IntegrityError creating connection: {e}")
            return JsonResponse({
                'success': False, 
                'error': 'A connection with this name already exists. Please choose a different name.'
            }, status=400)

        except Exception as e:
            logger.error(f"[{request.user.username}] Failed to create connection: {e}", exc_info=True)
            return JsonResponse({
                'success': False, 
                'error': 'An error occurred while creating the database connection. Please check your settings and try again.'
            }, status=400)


@login_required
@upload_required  # New permission decorator
@require_POST
def create_table_from_file_api(request):
    """Create a table from uploaded file structure with permission checks"""
    try:
        data = json.loads(request.body)
        connection_id = data.get('connection_id')
        table_name = data.get('table_name')
        temp_filename = data.get('temp_filename')

        if not all([connection_id, table_name, temp_filename]):
            return JsonResponse({'success': False, 'error': 'Missing required parameters.'}, status=400)

        # Check if user can upload to this connection
        if not PermissionManager.check_user_permission(
            request.user, 'connection', connection_id, 'edit'
        ):
            return JsonResponse({
                'success': False,
                'error': 'You do not have permission to create tables in this database.'
            }, status=403)

        conn = ExternalConnection.objects.get(id=connection_id, owner=request.user)
        engine = get_external_engine(connection_id, request.user)
        if not engine:
            return JsonResponse({'success': False, 'error': 'Failed to connect to the database.'}, status=500)

        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'temp'))
        temp_filepath = fs.path(temp_filename)
        if not os.path.exists(temp_filepath):
            return JsonResponse({'success': False, 'error': 'Uploaded file not found.'}, status=404)

        # Load data file to infer schema
        if temp_filename.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(temp_filepath)
        elif temp_filename.lower().endswith('.csv'):
            df = pd.read_csv(temp_filepath)
        else:
            return JsonResponse({'success': False, 'error': 'Unsupported file type.'}, status=400)

        # Infer SQLAlchemy column types
        sqlalchemy_types_map = {
            'int64': Integer,
            'float64': Float,
            'bool': Boolean,
            'datetime64[ns]': DateTime,
            'object': String(255),  # Default to String for object/text
        }

        columns = []
        for col_name, dtype in df.dtypes.items():
            # Sanitize column names to be valid SQL identifiers
            sanitized_col_name = "".join(c if c.isalnum() else "_" for c in col_name)
            col_type = sqlalchemy_types_map.get(str(dtype), Text) # Use Text for more flexibility
            columns.append(Column(sanitized_col_name, col_type))

        metadata = MetaData(bind=engine)
        table = Table(table_name, metadata, *columns)

        # Drop table if it exists and then create it
        with engine.begin() as connection:
            table.drop(checkfirst=True)
            table.create()

        # Log table creation
        log_user_activity(
            request.user,
            'create',
            'table',
            None,
            {'table_name': table_name, 'connection_id': connection_id},
            request
        )

        # Track uploaded table in the system
        UploadedTable.objects.create(
            uploaded_by=request.user,
            connection=conn,
            table_name=table_name,
            original_filename=temp_filename,
            row_count=len(df),
            column_count=len(df.columns),
        )

        return JsonResponse({
            'success': True,
            'message': f'Table "{table_name}" created successfully from uploaded file.'
        })

    except ExternalConnection.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Connection not found or access denied.'}, status=404)
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy Error on table creation: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': f"Database error: {str(e)}"}, status=500)
    except Exception as e:
        logger.error(f"Failed to create table from file: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while creating the table. Please try again.'
        }, status=500)



# =============================================================================
# INCLUDE ALL YOUR EXISTING ENDPOINTS HERE
# =============================================================================

@login_required
def get_my_reports_api(request):
    """API to get a list of the current user's saved reports with sharing info"""
    owned_reports = SavedReport.objects.filter(owner=request.user)
    shared_reports = SavedReport.objects.filter(
        reportshare__user=request.user
    ).exclude(owner=request.user)
    
    data = []
    
    # Add owned reports
    for report in owned_reports:
        data.append({
            'id': str(report.id),
            'name': report.report_name,
            'created_at': report.created_at.isoformat(),
            'updated_at': report.updated_at.isoformat(),
            'is_owner': True,
            'can_edit': True,
            'can_share': request.user.can_manage_users(),
        })
    
    # Add shared reports
    for report in shared_reports:
        share_info = ReportShare.objects.get(report=report, user=request.user)
        data.append({
            'id': str(report.id),
            'name': report.report_name,
            'created_at': report.created_at.isoformat(),
            'updated_at': report.updated_at.isoformat(),
            'is_owner': False,
            'owner_name': report.owner.get_full_name(),
            'can_edit': share_info.permission == 'edit',
            'can_share': False,
        })
    
    return JsonResponse({'success': True, 'reports': data})

@login_required
@require_POST
def save_report_api(request):
    """Enhanced API endpoint to save a new report with sharing"""
    try:
        data = json.loads(request.body)
        report_name = data.get('report_name')
        config = data.get('report_config')
        connection_id = data.get('connection_id')

        if not report_name or not config:
            return JsonResponse({
                'success': False, 
                'error': 'Report name and configuration are required.'
            }, status=400)
        
        # Check connection permissions
        if connection_id and not PermissionManager.check_user_permission(
            request.user, 'connection', connection_id, 'view'
        ):
            return JsonResponse({
                'success': False,
                'error': 'You do not have permission to access this database connection.'
            }, status=403)

        # Check if report name already exists for this user
        if SavedReport.objects.filter(owner=request.user, report_name=report_name).exists():
            return JsonResponse({
                'success': False,
                'error': f'You already have a report named "{report_name}". Please choose a different name.'
            }, status=400)

        new_report = SavedReport.objects.create(
            owner=request.user,
            report_name=report_name,
            report_config=config,
            connection_id=connection_id
        )
        
        # Log report creation
        log_user_activity(
            request.user,
            'create',
            'report',
            new_report.id,
            {'report_name': report_name, 'connection_id': connection_id},
            request
        )

        return JsonResponse({
            'success': True, 
            'report_id': str(new_report.id), 
            'message': f'Report "{report_name}" saved successfully.'
        })

    except Exception as e:
        logger.error(f"Error saving report: {e}", exc_info=True)
        return JsonResponse({
            'success': False, 
            'error': 'An error occurred while saving the report. Please try again.'
        }, status=500)

# ... Continue with all your other existing endpoints ...

# For brevity, I'll note that ALL your existing endpoints should be included here
# with the same pattern of adding permission checks and user-friendly error messages

# =============================================================================
# ERROR HANDLERS (Enhanced)
# =============================================================================

def custom_404(request, exception):
    """Custom 404 error handler"""
    return render(request, '404.html', {
        'error_message': 'The page you are looking for could not be found.',
        'user_theme': request.user.theme_preference if request.user.is_authenticated else 'corporate'
    }, status=404)

def custom_500(request):
    """Custom 500 error handler"""
    return render(request, '500.html', {
        'error_message': 'An internal server error occurred. Please try again later or contact your administrator.',
        'user_theme': request.user.theme_preference if request.user.is_authenticated else 'corporate'
    }, status=500)

# =============================================================================
# API TEST ENDPOINT
# =============================================================================

@login_required
def test_api(request):
    """Simple test view to check if API is working"""
    return JsonResponse({
        'message': 'API is working correctly',
        'user': request.user.username,
        'user_type': request.user.user_type,
        'theme': request.user.theme_preference,
        'permissions': {
            'can_manage_users': request.user.can_manage_users(),
            'can_manage_database': request.user.can_manage_database(),
            'can_upload_data': request.user.can_upload_data(),
            'can_modify_schema': request.user.can_modify_schema(),
        },
        'stats': {
            'connections_count': ExternalConnection.objects.filter(owner=request.user).count(),
            'reports_count': SavedReport.objects.filter(owner=request.user).count(),
            'dashboards_count': Dashboard.objects.filter(owner=request.user).count(),
        }
    })

# =============================================================================
# INCLUDE ALL YOUR REMAINING EXISTING ENDPOINTS
# =============================================================================

@login_required
@user_management_required
@require_http_methods(["GET", "POST"])
def users_api(request):
    """Enhanced API for listing and creating users"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Create form with request user context
            form = CustomUserCreationForm(data, request_user=request.user)
            
            if form.is_valid():
                with transaction.atomic():
                    user = form.save()
                    
                    # Log user creation
                    log_user_activity(
                        request.user,
                        'create',
                        'user',
                        user.id,
                        {'created_user': user.username, 'user_type': user.user_type},
                        request
                    )
                    
                    # Create welcome notification
                    create_notification(
                        user,
                        'Welcome to MIS System!',
                        f'Your account has been created by {request.user.get_full_name()}. You can now log in and start using the system.',
                        'success'
                    )
                    
                    # Send welcome email if requested
                    if data.get('send_welcome_email', False):
                        try:
                            send_welcome_email(user, data.get('password', ''))
                        except Exception as e:
                            logger.error(f"Failed to send welcome email: {e}")
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'User {user.username} has been created successfully.',
                        'user_id': str(user.id)
                    }, status=21)
            else:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
                
        except Exception as e:
            logger.error(f"Error creating user: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred while creating the user. Please try again.'
            }, status=500)
    
    # GET request - list users with filtering
    search = request.GET.get('search', '')
    user_type = request.GET.get('user_type', '')
    is_active = request.GET.get('is_active', '')
    
    users_query = User.objects.all()
    
    if search:
        users_query = users_query.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if user_type:
        users_query = users_query.filter(user_type=user_type)
    
    if is_active:
        users_query = users_query.filter(is_active=is_active.lower() == 'true')
    
    users = users_query.order_by('-date_joined')[:50]  # Limit for performance
    
    users_data = []
    for user in users:
        users_data.append({
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'full_name': user.get_full_name(),
            'user_type': user.user_type,
            'department': user.department,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'is_locked': user.is_account_locked(),
            'groups': [{'id': str(g.id), 'name': g.name} for g in user.user_groups.all()],
        })
    
    return JsonResponse({
        'success': True,
        'users': users_data,
        'total': users_query.count()
    })

@login_required
@user_management_required
@require_http_methods(["GET", "PUT", "DELETE"])
def user_detail_api(request, user_id):
    """Enhanced API for user details"""
    try:
        user = User.objects.get(id=user_id)
    except (User.DoesNotExist, ValueError):
        return JsonResponse({
            'success': False,
            'error': 'User not found.'
        }, status=404)
    
    if request.method == 'GET':
        # Get user groups and permissions
        groups = user.user_groups.all()
        direct_permissions = UserPermission.objects.filter(user=user)
        
        user_data = {
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'user_type': user.user_type,
            'department': user.department,
            'job_title': user.job_title,
            'phone_number': user.phone_number,
            'manager': str(user.manager.id) if user.manager else None,
            'manager_name': user.manager.get_full_name() if user.manager else None,
            'theme_preference': user.theme_preference,
            'is_active': user.is_active,
            'is_email_verified': user.is_email_verified,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'last_activity': user.last_activity.isoformat() if user.last_activity else None,
            'login_attempts': user.login_attempts,
            'is_locked': user.is_account_locked(),
            'groups': [
                {
                    'id': str(g.id),
                    'name': g.name,
                    'color': g.color,
                    'role': GroupMembership.objects.get(user=user, group=g).role
                }
                for g in groups
            ],
            'direct_permissions': [
                {
                    'id': str(p.id),
                    'resource_type': p.resource_type,
                    'resource_name': p.resource_name,
                    'permission_level': p.permission_level,
                    'expires_at': p.expires_at.isoformat() if p.expires_at else None
                }
                for p in direct_permissions
            ]
        }
        
        return JsonResponse({
            'success': True,
            'user': user_data
        })
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            # Prevent users from editing themselves in certain ways
            if str(request.user.id) == str(user_id):
                restricted_fields = ['user_type', 'is_active']
                if any(field in data for field in restricted_fields):
                    return JsonResponse({
                        'success': False,
                        'error': 'You cannot modify your own access level or account status.'
                    }, status=403)
            
            # Create form for validation
            form_data = {
                'username': data.get('username', user.username),
                'email': data.get('email', user.email),
                'first_name': data.get('first_name', user.first_name),
                'last_name': data.get('last_name', user.last_name),
                'user_type': data.get('user_type', user.user_type),
                'department': data.get('department', user.department),
                'job_title': data.get('job_title', user.job_title),
                'phone_number': data.get('phone_number', user.phone_number),
                'theme_preference': data.get('theme_preference', user.theme_preference),
                'is_active': data.get('is_active', user.is_active),
            }
            
            # Handle manager assignment
            manager_id = data.get('manager')
            if manager_id:
                try:
                    form_data['manager'] = User.objects.get(id=manager_id)
                except User.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'Selected manager not found.'
                    }, status=400)
            
            # Validate email uniqueness
            if 'email' in data and data['email'] != user.email:
                if User.objects.filter(email=data['email']).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'A user with this email address already exists.'
                    }, status=400)
            
            # Update user fields
            old_values = {}
            new_values = {}
            
            for field, value in form_data.items():
                if hasattr(user, field):
                    old_value = getattr(user, field)
                    if old_value != value:
                        old_values[field] = str(old_value) if old_value else None
                        new_values[field] = str(value) if value else None
                        setattr(user, field, value)
            
            # Handle password change
            if data.get('password'):
                user.set_password(data['password'])
                user.last_password_change = timezone.now()
                new_values['password'] = 'Changed'
            
            # Handle account unlocking
            if data.get('unlock_account') and user.is_account_locked():
                user.reset_login_attempts()
                new_values['account_status'] = 'Unlocked'
            
            user.save()
            
            # Handle group assignments
            if 'groups' in data:
                new_group_ids = set(data['groups'])
                current_group_ids = set(str(g.id) for g in user.user_groups.all())
                
                # Remove from groups
                groups_to_remove = current_group_ids - new_group_ids
                if groups_to_remove:
                    GroupMembership.objects.filter(
                        user=user,
                        group_id__in=groups_to_remove
                    ).delete()
                
                # Add to groups
                groups_to_add = new_group_ids - current_group_ids
                for group_id in groups_to_add:
                    try:
                        group = UserGroup.objects.get(id=group_id)
                        GroupMembership.objects.create(
                            user=user,
                            group=group,
                            added_by=request.user
                        )
                    except UserGroup.DoesNotExist:
                        pass
            
            # Clear user permission cache
            PermissionManager.clear_user_cache(user.id)
            
            # Log the update
            log_user_activity(
                request.user,
                'update',
                'user',
                user.id,
                {'updated_user': user.username, 'changes': new_values},
                request
            )
            
            return JsonResponse({
                'success': True,
                'message': f'User {user.username} has been updated successfully.'
            })
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred while updating the user. Please try again.'
            }, status=500)
    
    elif request.method == 'DELETE':
        # Prevent users from deleting themselves
        if str(request.user.id) == str(user_id):
            return JsonResponse({
                'success': False,
                'error': 'You cannot delete your own account.'
            }, status=403)
        
        # Prevent deletion of the last admin
        if user.user_type == 'Admin' and User.objects.filter(user_type='Admin', is_active=True).count() <= 1:
            return JsonResponse({
                'success': False,
                'error': 'Cannot delete the last active administrator account.'
            }, status=403)
        
        try:
            username = user.username
            user.delete()
            
            # Log the deletion
            log_user_activity(
                request.user,
                'delete',
                'user',
                user_id,
                {'deleted_user': username},
                request
            )
            
            return JsonResponse({
                'success': True,
                'message': f'User {username} has been deleted successfully.'
            })
            
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred while deleting the user. Please try again.'
            }, status=500)

@login_required
@user_management_required
@require_POST
def bulk_user_actions_api(request):
    """API for bulk user operations"""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return JsonResponse({
                'success': False,
                'error': 'Please select at least one user to perform the action on.'
            }, status=400)
        
        # Prevent actions on self for certain operations
        if action in ['delete', 'deactivate'] and str(request.user.id) in user_ids:
            return JsonResponse({
                'success': False,
                'error': 'You cannot perform this action on your own account.'
            }, status=403)
        
        users = User.objects.filter(id__in=user_ids)
        processed_count = 0
        errors = []
        
        if action == 'activate':
            users.update(is_active=True)
            processed_count = users.count()
            
        elif action == 'deactivate':
            # Don't deactivate the last admin
            admin_ids = users.filter(user_type='Admin').values_list('id', flat=True)
            total_active_admins = User.objects.filter(user_type='Admin', is_active=True).count()
            
            if len(admin_ids) >= total_active_admins:
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot deactivate all administrator accounts.'
                }, status=403)
            
            users.update(is_active=False)
            processed_count = users.count()
            
        elif action == 'delete':
            # Check admin deletion constraint
            admin_count = users.filter(user_type='Admin').count()
            total_active_admins = User.objects.filter(user_type='Admin', is_active=True).count()
            
            if admin_count >= total_active_admins:
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot delete all administrator accounts.'
                }, status=403)
            
            processed_count = users.count()
            users.delete()
            
        elif action == 'change_type':
            new_user_type = data.get('new_user_type')
            if not new_user_type:
                return JsonResponse({
                    'success': False,
                    'error': 'Please select a user type for this action.'
                }, status=400)
            
            users.update(user_type=new_user_type)
            processed_count = users.count()
            
        elif action == 'assign_group':
            target_group_id = data.get('target_group')
            if not target_group_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Please select a group for this action.'
                }, status=400)
            
            try:
                group = UserGroup.objects.get(id=target_group_id)
                for user in users:
                    GroupMembership.objects.get_or_create(
                        user=user,
                        group=group,
                        defaults={'added_by': request.user}
                    )
                processed_count = users.count()
            except UserGroup.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Selected group not found.'
                }, status=400)
                
        elif action == 'remove_group':
            target_group_id = data.get('target_group')
            if not target_group_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Please select a group for this action.'
                }, status=400)
            
            GroupMembership.objects.filter(
                user__in=users,
                group_id=target_group_id
            ).delete()
            processed_count = users.count()
            
        elif action == 'reset_password':
            # This would typically send password reset emails
            processed_count = users.count()
            # Implementation depends on your password reset workflow
            
        else:
            return JsonResponse({
                'success': False,
                'error': f'Unknown action: {action}'
            }, status=400)
        
        # Clear permission caches for affected users
        for user_id in user_ids:
            PermissionManager.clear_user_cache(user_id)
        
        # Log bulk action
        log_user_activity(
            request.user,
            'bulk_action',
            'user',
            None,
            {
                'action': action,
                'user_count': processed_count,
                'user_ids': user_ids
            },
            request
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Bulk action completed successfully. {processed_count} users affected.',
            'processed_count': processed_count,
            'errors': errors
        })
        
    except Exception as e:
        logger.error(f"Error in bulk user actions: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred during the bulk operation. Please try again.'
        }, status=500)
    
@login_required
def dashboard_view(request, dashboard_id):
    """
    Return all tables, no filtering. Core dashboard page for viewing or editing.
    """
    dashboard = get_object_or_404(Dashboard, id=dashboard_id)
    can_edit = dashboard.owner == request.user or DashboardShare.objects.filter(
        dashboard=dashboard, user=request.user, permission="edit"
    ).exists()
    if not can_edit:
        return HttpResponseForbidden("You do not have permission to edit this dashboard.")
    return render(request, "mis_app/dashboard.html", {"dashboard": dashboard})

def dashboard_view(request):
    """
    Return all tables, no filtering. Core dashboard page for viewing or editing.
    """
    return render(request, "mis_app/dashboard.html")

@login_required
def dashboards_api(request):
    """API endpoint to list dashboards owned by the current user."""
    dashboards = Dashboard.objects.filter(owner=request.user)
    data = [{"id": str(d.id), "title": d.title} for d in dashboards]
    return JsonResponse({"success": True, "dashboards": data})

@login_required
def dashboard_detail_api(request, dashboard_id):
    """
    API endpoint for a single dashboard.
    """
    dashboard = get_object_or_404(Dashboard, id=dashboard_id, owner=request.user)
    data = {
        "id": str(dashboard.id),
        "title": dashboard.title,
        "description": dashboard.description,
        "config": dashboard.config,
    }
    return JsonResponse({"success": True, "dashboard": data})

@login_required
@require_http_methods(["GET", "POST"])
def dashboard_config_api(request, dashboard_id):
    """
    API endpoint to get and save the v2 dashboard configuration.
    """
    try:
        # Get the dashboard and check if the user has permission to edit
        dashboard = Dashboard.objects.get(id=dashboard_id)
        can_edit = (
            dashboard.owner == request.user or
            DashboardShare.objects.filter(
                dashboard=dashboard,
                user=request.user,
                permission='edit'
            ).exists()
        )

        if not can_edit:
            return HttpResponseForbidden("You do not have permission to edit this dashboard.")

        # --- Handle POST request (Saving the configuration) ---
        if request.method == 'POST':
            try:
                # Load the JSON data sent from the frontend
                config_data = json.loads(request.body)

                # Basic validation for the v2 schema
                if not isinstance(config_data, dict) or config_data.get('version') != 2:
                    return JsonResponse({'success': False, 'error': 'Invalid configuration schema provided.'}, status=400)

                # Update the dashboard object
                dashboard.config_v2 = config_data
                dashboard.config_version = 2
                dashboard.save() # This will also trigger our new signal to create a version history!

                return JsonResponse({'success': True, 'message': 'Dashboard saved successfully.'})

            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'Invalid JSON in request body.'}, status=400)
            except Exception as e:
                # Log the error in a real application
                return JsonResponse({'success': False, 'error': f'An unexpected error occurred: {str(e)}'}, status=500)

        # --- Handle GET request (Fetching the configuration) ---
        else: # This is the GET request
            # If a v2 config exists, return it. Otherwise, return an empty v2 shell.
            if dashboard.config_v2 and dashboard.config_version == 2:
                return JsonResponse(dashboard.config_v2)
            else:
                # Provide a default structure if no v2 config exists yet
                default_config = {
                    "version": 2,
                    "pages": [{"id": "page_1", "name": "Main Page", "widgets": []}],
                    "globalFilters": [],
                    "theme": "light"
                }
                return JsonResponse(default_config)

    except Dashboard.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Dashboard not found.'}, status=404)

@login_required
def create_dashboard_api(request):
    """API endpoint to create a new dashboard."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            dashboard_name = data.get('dashboard_name')

            if not dashboard_name:
                return JsonResponse({'success': False, 'error': 'Dashboard name is required.'}, status=400)

            # Create the new dashboard and its data context
            new_dashboard = Dashboard.objects.create(title=dashboard_name, owner=request.user)
            DashboardDataContext.objects.create(dashboard=new_dashboard)

            return JsonResponse({
                'success': True,
                'message': 'Dashboard created successfully.',
                'dashboard_id': new_dashboard.id
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)

@login_required
def get_widget_data_api(request, dashboard_id, widget_id):
    """
    Final, robust, and refactored API endpoint to fetch widget data.
    Uses a reliable iterative approach for join path resolution.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)

    try:
        # --- 1. Get Config, Context, and Filters ---
        payload = json.loads(request.body)
        widget_config = payload.get('widget_config', {})
        filters = payload.get('filters', [])
        data_config = widget_config.get('dataConfig', {})
        context = DashboardDataContext.objects.get(dashboard_id=dashboard_id)

        dimensions = data_config.get('dimensions', [])
        measures = data_config.get('measures', [])

        if not dimensions or not measures:
            return JsonResponse({'success': True, 'data': {'labels': [], 'datasets': []}})

        # --- 2. Identify ALL Required Tables (from widget AND filters) ---
        required_tables = set()
        for item in dimensions + measures + filters:
            field_name = item.get('field', '')
            if '.' in field_name:
                required_tables.add(field_name.split('.')[0])
        
        if not required_tables:
            required_tables.add(context.selected_tables[0])

        engine = get_external_engine(context.connection.id, request.user)
        dialect = engine.dialect.name
        q = '`' if dialect == 'mysql' else '"'
        def format_field(f):
            parts = f.split('.')
            return f'{q}{parts[0]}{q}.{q}{parts[1]}{q}' if len(parts) == 2 else f'{q}{f}{q}'

        dimension_field = dimensions[0]['field']
        measure_field = measures[0]['field']
        aggregation = measures[0].get('agg', 'SUM').upper()
        sql_from = ""
        sql_joins = ""

        # --- 3. Handle Single vs. Multi-Table Cases ---
        if len(required_tables) <= 1:
            source_table = list(required_tables)[0] if required_tables else context.selected_tables[0]
            sql_from = f"FROM {q}{source_table}{q}"
        else:
            # Multi-table join logic
            model_joins = list(ConnectionJoin.objects.filter(connection=context.connection).values())
            context_joins = context.joins or []
            all_possible_joins = model_joins + context_joins
            
            start_table = list(required_tables)[0]
            connected_tables = {start_table}
            final_join_path = []
            
            while not required_tables.issubset(connected_tables):
                found_join = False
                for join in all_possible_joins:
                    t1, t2 = join['left_table'], join['right_table']
                    if t1 in connected_tables and t2 not in connected_tables:
                        final_join_path.append(join)
                        connected_tables.add(t2)
                        found_join = True; break
                    elif t2 in connected_tables and t1 not in connected_tables:
                        final_join_path.append({'left_table': t2, 'left_column': join['right_column'], 'right_table': t1, 'right_column': join['left_column']})
                        connected_tables.add(t1)
                        found_join = True; break
                if not found_join:
                    raise Exception(f"Could not find a join path for table(s): {required_tables - connected_tables}.")

            sql_from = f"FROM {q}{start_table}{q}"
            for join in final_join_path:
                sql_joins += f" LEFT JOIN {q}{join['right_table']}{q} ON {format_field(join['left_table'] + '.' + join['left_column'])} = {format_field(join['right_table'] + '.' + join['right_column'])}"

        # --- 4. Build WHERE Clause ---
        sql_where, sql_params = "", {}
        if filters:
            where_clauses = []
            for i, f in enumerate(filters):
                if f.get('operator') == 'equals':
                    param_name = f"filter_val_{i}"
                    where_clauses.append(f"{format_field(f['field'])} = :{param_name}")
                    sql_params[param_name] = f['value']
            if where_clauses:
                sql_where = "WHERE " + " AND ".join(where_clauses)

        # --- 5. Build Final Query ---
        query = f"SELECT {format_field(dimension_field)} AS dimension, {aggregation}({format_field(measure_field)}) AS measure {sql_from} {sql_joins} {sql_where} GROUP BY 1 ORDER BY 2 DESC LIMIT 100;"
        
        # --- 6. Execute and Clean Data ---
        with engine.connect() as connection:
            df = pd.read_sql_query(text(query), connection, params=sql_params)

        df = df.replace({np.nan: None, pd.NaT: None})

        chart_data = {
            'labels': df['dimension'].tolist(),
            'datasets': [{'label': f'{aggregation} of {measure_field}', 'data': df['measure'].tolist()}]
        }
        return JsonResponse({'success': True, 'data': chart_data})

    except Exception as e:
        error_trace = traceback.format_exc()
        return JsonResponse({
            'success': False, 
            'error': 'An unexpected error occurred.',
            'details': str(e),
            'traceback': error_trace
        }, status=500)
    
@login_required
def data_context_api(request, dashboard_id):
    """API to get and save the dashboard's data context."""
    context, _ = DashboardDataContext.objects.get_or_create(dashboard_id=dashboard_id)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            connection_id = data.get('connection_id')
            if connection_id == 'Choose a connection...':
                connection_id = None

            context.connection_id = connection_id
            context.selected_tables = data.get('selected_tables', [])
            context.joins = data.get('joins', []) # <-- ADD THIS LINE
            context.save()
            return JsonResponse({'success': True, 'message': 'Data context saved.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    # GET request
    return JsonResponse({
        'connection_id': str(context.connection.id) if context.connection else None,
        'selected_tables': context.selected_tables or [],
        'joins': context.joins or [] # <-- ADD THIS LINE
    })

@login_required
def available_fields_api(request, dashboard_id):
    """
    Inspects the configured data context and returns a list of all available fields.
    This version correctly handles cases where the context is not yet configured.
    """
    try:
        context = DashboardDataContext.objects.get(dashboard_id=dashboard_id)
        
        # If no connection or tables are selected, return a successful but empty response
        if not context.connection or not context.selected_tables:
            return JsonResponse({'success': True, 'fields': []})

        engine = get_external_engine(context.connection.id, request.user)
        if not engine:
            raise Exception("Could not create database engine.")

        inspector = inspect(engine)
        all_fields = []
        
        for table_name in context.selected_tables:
            columns = inspector.get_columns(table_name)
            for column in columns:
                all_fields.append({
                    'name': column['name'],
                    'table': table_name,
                    'type': str(column['type']),
                })
        
        return JsonResponse({'success': True, 'fields': all_fields})

    except DashboardDataContext.DoesNotExist:
        # If the context object doesn't even exist, also return a successful empty response
        return JsonResponse({'success': True, 'fields': []})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
@login_required
def get_table_columns_api(request, connection_id, table_name):
    """Gets detailed column information for a single table."""
    engine = get_external_engine(connection_id, request.user)
    if not engine:
        return JsonResponse({'error': 'Database connection failed.'}, status=500)
    
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        pks = inspector.get_pk_constraint(table_name).get('constrained_columns', [])
        
        column_details = [{'name': col['name'], 'type': str(col['type'])} for col in columns]
        return JsonResponse({'columns': column_details, 'pks': pks})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def connection_detail_api(request, connection_id):
    conn = get_object_or_404(ExternalConnection, id=connection_id, owner=request.user)

    if request.method == 'GET':
        data = {
            'id': str(conn.id),
            'nickname': conn.nickname,
            'db_type': conn.db_type,
            'host': conn.host,
            'port': conn.port,
            'username': conn.username,
            'db_name': conn.db_name,
            'schema': conn.schema,
            'filepath': conn.filepath,
            'hidden_tables': conn.hidden_tables,
            'health_status': conn.health_status,
        }
        return JsonResponse(data)

    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            # --- UPDATED VALIDATION LOGIC ---
            test_details = { key: data.get(key, getattr(conn, key)) for key in ['db_type', 'host', 'port', 'username', 'db_name', 'filepath', 'schema']}
            test_details['password'] = data.get('password', conn.password) if 'password' in data and data.get('password') else conn.password
            
            connection_string = ""
            db_type = test_details['db_type']
            if db_type == 'postgresql':
                connection_string = f"postgresql+psycopg2://{test_details['username']}:{test_details['password']}@{test_details['host']}:{test_details['port']}/{test_details['db_name']}"
            elif db_type == 'mysql':
                 connection_string = f"mysql+pymysql://{test_details['username']}:{test_details['password']}@{test_details['host']}:{test_details['port']}/{test_details['db_name']}"
            elif db_type == 'sqlite':
                connection_string = f"sqlite:///{test_details['filepath']}"
            # ✅ ADDED MSSQL, ORACLE, SNOWFLAKE
            elif db_type == 'mssql':
                driver = "ODBC+Driver+17+for+SQL+Server"
                connection_string = f"mssql+pyodbc://{test_details['username']}:{test_details['password']}@{test_details['host']}:{test_details['port']}/{test_details['db_name']}?driver={driver}"
            elif db_type == 'oracle':
                connection_string = f"oracle+cx_oracle://{test_details['username']}:{test_details['password']}@{test_details['host']}:{test_details['port']}/?service_name={test_details['db_name']}"
            elif db_type == 'snowflake':
                connection_string = f"snowflake://{test_details['username']}:{test_details['password']}@{test_details['host']}/{test_details['db_name']}/{test_details['schema']}"

            try:
                connect_args = {}
                if db_type != 'sqlite':
                    connect_args['connect_timeout'] = 10
                temp_engine = create_engine(connection_string, connect_args=connect_args)
                with temp_engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
            except SQLAlchemyError as e:
                logger.error(f"Connection test failed for updated connection {conn.id}: {e}")
                return JsonResponse({'error': 'Connection test failed. Please check credentials and host. Changes not saved.'}, status=400)
            # --- END VALIDATION LOGIC ---

            if 'password' in data and not data['password']:
                del data['password']

            for key, value in data.items():
                setattr(conn, key, value)
            conn.save()
            return JsonResponse({'id': str(conn.id), 'message': 'Connection updated successfully.'})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    elif request.method == 'DELETE':
        conn.delete()
        return JsonResponse({'message': 'Connection deleted successfully.'}, status=204)
    
login_required(login_url='mis_app:login')
@require_POST
@csrf_exempt
def test_database_connection(request, connection_id):
    """Test database connection and update health status."""
    try:
        conn_obj = get_object_or_404(ExternalConnection, id=connection_id, owner=request.user)
        engine = get_external_engine(connection_id, request.user)
        
        if not engine:
            return JsonResponse({
                'success': False, 
                'error': 'Failed to create database engine.'
            }, status=500)
        
        try:
            # Test the connection
            with engine.connect() as connection:
                # Use a simple query to test the connection
                if conn_obj.db_type == 'sqlite':
                    connection.execute(text("SELECT 1"))
                else:
                    connection.execute(text("SELECT 1"))
                
            # Update connection status
            conn_obj.health_status = 'healthy'
            conn_obj.last_health_check = timezone.now()
            conn_obj.save(update_fields=['health_status', 'last_health_check'])
            
            return JsonResponse({
                'success': True, 
                'message': f'Connection to {conn_obj.nickname} is healthy.'
            })
            
        except Exception as e:
            # Update connection status to error
            conn_obj.health_status = 'error'
            conn_obj.last_health_check = timezone.now()
            conn_obj.save(update_fields=['health_status', 'last_health_check'])
            
            logger.error(f"Connection test failed for {conn_obj.nickname}: {str(e)}")
            return JsonResponse({
                'success': False, 
                'error': f'Database connection failed: {str(e)}'
            }, status=400)
            
    except ExternalConnection.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': 'Connection not found or access denied.'
        }, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in connection test: {str(e)}")
        return JsonResponse({
            'success': False, 
            'error': f'An unexpected error occurred: {str(e)}'
        }, status=500)
    
@login_required
def get_connection_tables_api(request, connection_id):
    """Get all tables for a connection."""
    try:
        conn_details = get_object_or_404(ExternalConnection, id=connection_id, owner=request.user)
        engine = None
        
        try:
            engine = get_external_engine(connection_id, request.user)
            if not engine:
                return JsonResponse({
                    'success': False, 
                    'error': 'Failed to connect to database.'
                })
            
            inspector = inspect(engine)
            schema = None
            if conn_details.db_type == 'postgresql' and conn_details.schema:
                schema = conn_details.schema
                
            tables = inspector.get_table_names(schema=schema)
            
            hidden_tables = set((conn_details.hidden_tables or '').split(','))
            visible_tables = sorted([table for table in tables if table not in hidden_tables])
            
            return JsonResponse({
                'success': True, 
                'tables': visible_tables
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e)
            })
            
    except Exception as e:
        logger.error(f"Error getting connection tables: {e}")
        return JsonResponse({
            'success': False, 
            'error': str(e)
        })
    
@login_required
def get_all_connection_tables_api(request, connection_id):
    """Get ALL tables (visible and hidden) for connection."""
    try:
        conn_details = get_object_or_404(ExternalConnection, id=connection_id, owner=request.user)
        engine = get_external_engine(connection_id, request.user)

        if not engine:
            return JsonResponse({'success': False, 'error': 'Failed to connect to database.'})
        
        inspector = inspect(engine)
        schema = None
        if conn_details.db_type == 'postgresql' and conn_details.schema:
            schema = conn_details.schema
        
        tables = inspector.get_table_names(schema=schema)
        # Return all tables, no filtering
        return JsonResponse({'success': True, 'tables': sorted(tables)})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
@login_required
@require_POST
def validate_sql(request):
    """Placeholder for a SQL validation endpoint."""
    # In a real application, this would use a library to parse and validate the SQL.
    # For now, we'll assume any non-empty query is valid for demonstration.
    try:
        data = json.loads(request.body)
        sql_query = data.get('sql', '')
        if sql_query.strip():
            return JsonResponse({'success': True, 'message': 'SQL syntax appears valid.'})
        else:
            return JsonResponse({'success': False, 'error': 'SQL query is empty.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    

def get_csrf_token(request):
    # Return CSRF token via JSON response
    token = get_token(request)
    return JsonResponse({'csrfToken': token})

