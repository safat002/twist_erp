from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Q

from .models import Company, CompanyGroup, Branch, Department, DepartmentMembership
from .serializers import (
    CompanyGroupSerializer,
    CompanyGroupListSerializer,
    CompanyGroupMinimalSerializer,
    CompanyProvisionSerializer,
    CompanySerializer,
    CompanyListSerializer,
    CompanyMinimalSerializer,
    BranchSerializer,
    BranchListSerializer,
    BranchMinimalSerializer,
    DepartmentSerializer,
    DepartmentListSerializer,
    DepartmentMinimalSerializer,
    DepartmentMembershipSerializer,
)
from .services.provisioning import CompanyGroupProvisioner, ProvisioningError


# ============================================================================
# CompanyGroup ViewSet
# ============================================================================

class CompanyGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing CompanyGroups.
    Supports full CRUD operations with organizational scoping.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return CompanyGroupListSerializer
        elif self.action == 'minimal':
            return CompanyGroupMinimalSerializer
        return CompanyGroupSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = CompanyGroup.objects.all()

        # System admins see all
        if getattr(user, 'is_system_admin', False) or getattr(user, 'is_staff', False):
            pass
        else:
            # Regular users see only their accessible groups
            try:
                org_access = user.org_access
                accessible_group_ids = org_access.access_groups.values_list('id', flat=True)
                queryset = queryset.filter(id__in=accessible_group_ids)
            except:
                queryset = user.company_groups.all()

        # Apply filters
        if self.action == 'list':
            queryset = queryset.annotate(companies_count=Count('companies'))
            is_active = self.request.query_params.get('is_active')
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset.order_by('name')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        if not self._can_manage_groups(request.user):
            return Response({'detail': 'Not allowed to create company groups.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def _can_edit_group(self, user, group) -> bool:
        if not user or not user.is_authenticated:
            return False
        # Superuser or system admin always allowed
        if getattr(user, 'is_superuser', False) or getattr(user, 'is_system_admin', False):
            return True
        # Group owner may edit
        if group.owner_user_id and group.owner_user_id == user.id:
            return True
        # Users with access to the group may edit basic fields
        try:
            org_access = user.org_access
            if org_access and org_access.access_groups.filter(id=group.id).exists():
                return True
        except Exception:
            pass
        return False

    def _can_manage_groups(self, user) -> bool:
        """Restrictive check for create/delete operations: allow superuser or system admin."""
        return bool(user and user.is_authenticated and (getattr(user, 'is_superuser', False) or getattr(user, 'is_system_admin', False)))

    def update(self, request, *args, **kwargs):
        group = self.get_object()
        if not self._can_edit_group(request.user, group):
            return Response({'detail': 'Not allowed to edit this group.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        group = self.get_object()
        if not self._can_edit_group(request.user, group):
            return Response({'detail': 'Not allowed to edit this group.'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        group = self.get_object()
        if not self._can_manage_groups(request.user):
            return Response({'detail': 'Not allowed to delete company groups.'}, status=status.HTTP_403_FORBIDDEN)
        companies = list(group.companies.values('id', 'code', 'name'))
        if companies:
            return Response(
                {
                    'error': 'Cannot delete company group while companies exist. Delete companies first.',
                    'companies': companies,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['patch'], url_path='edit')
    def edit(self, request, pk=None):
        """Convenience endpoint for editing a group. Accepts partial updates."""
        group = self.get_object()
        if not self._can_edit_group(request.user, group):
            return Response({'detail': 'Not allowed to edit this group.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = CompanyGroupSerializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='minimal')
    def minimal(self, request):
        """Get minimal list for dropdowns."""
        queryset = self.get_queryset()
        serializer = CompanyGroupMinimalSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='companies')
    def companies(self, request, pk=None):
        """Get all companies in this group."""
        group = self.get_object()
        companies = group.companies.filter(is_active=True)
        serializer = CompanyListSerializer(companies, many=True)
        return Response(serializer.data)


# ============================================================================
# Company ViewSet
# ============================================================================

class CompanyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Companies with enhanced hierarchy support.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return CompanyListSerializer
        elif self.action == 'minimal':
            return CompanyMinimalSerializer
        return CompanySerializer

    def get_queryset(self):
        user = self.request.user

        # System admins see all
        if getattr(user, "is_system_admin", False) or getattr(user, "is_staff", False):
            queryset = Company.objects.all()
        else:
            # Regular users see only their accessible companies
            try:
                org_access = user.org_access
                accessible_company_ids = org_access.access_companies.values_list('id', flat=True)
                queryset = Company.objects.filter(id__in=accessible_company_ids)
            except:
                queryset = user.companies.all()

        # Apply filters
        if self.action == 'list':
            queryset = queryset.annotate(branches_count=Count('branches'))

            is_active = self.request.query_params.get('is_active')
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')

            company_group_id = self.request.query_params.get('company_group')
            if company_group_id:
                queryset = queryset.filter(company_group_id=company_group_id)

        return queryset.select_related('company_group', 'parent_company').order_by('code')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"], url_path="active")
    def active(self, request):
        """Get the currently active company from session."""
        company_id = request.session.get("active_company_id")
        queryset = self.get_queryset()
        company = queryset.filter(id=company_id).first() if company_id else None

        if not company:
            company = queryset.first()
            if company:
                request.session["active_company_id"] = str(company.id)

        if not company:
            return Response(
                {"detail": "No companies available for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CompanySerializer(company)
        return Response(serializer.data)

    @action(detail=False, methods=["post", "get"], url_path="activate")
    def activate(self, request):
        """Set active company in session (accepts POST or GET with id)."""
        company_id = request.data.get("id") or request.query_params.get("id") or request.data.get("company_id")
        if not company_id:
            return Response({"detail": "id is required"}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset()
        company = queryset.filter(id=company_id).first()
        if not company:
            return Response({"detail": "Company not found or not accessible"}, status=status.HTTP_404_NOT_FOUND)
        request.session["active_company_id"] = str(company.id)
        return Response({"status": "ok", "company": CompanySerializer(company).data})


class CurrencyChoicesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Source from CompanyGroup currency choices
        from .models import CompanyGroup
        choices = getattr(CompanyGroup, 'CURRENCY_CHOICES', [])
        data = [{"code": code, "name": name} for code, name in choices]
        return Response({"results": data})

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        """Set a company as active in the session."""
        company = self.get_queryset().filter(id=pk).first()
        if not company:
            return Response(
                {"detail": "Company not found or not assigned to this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        request.session["active_company_id"] = str(company.id)
        request.session["active_company_group_id"] = str(company.company_group_id)
        serializer = CompanySerializer(company)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='minimal')
    def minimal(self, request):
        """Get minimal list for dropdowns."""
        queryset = self.get_queryset().filter(is_active=True)
        company_group_id = request.query_params.get('company_group')
        if company_group_id:
            queryset = queryset.filter(company_group_id=company_group_id)
        serializer = CompanyMinimalSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='branches')
    def branches(self, request, pk=None):
        """Get all branches for this company."""
        company = self.get_object()
        branches = company.branches.filter(is_active=True)
        serializer = BranchListSerializer(branches, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='departments')
    def departments(self, request, pk=None):
        """Get all departments for this company."""
        company = self.get_object()
        departments = company.get_all_departments()
        serializer = DepartmentListSerializer(departments, many=True)
        return Response(serializer.data)


# ============================================================================
# Branch ViewSet
# ============================================================================

class BranchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Branches.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return BranchListSerializer
        elif self.action == 'minimal':
            return BranchMinimalSerializer
        return BranchSerializer

    def get_queryset(self):
        user = self.request.user

        # System admins see all
        if getattr(user, "is_system_admin", False) or getattr(user, "is_staff", False):
            queryset = Branch.objects.all()
        else:
            # Regular users see branches from their accessible companies
            try:
                org_access = user.org_access

                # If user has specific branch access, use that
                if org_access.access_branches.exists():
                    queryset = org_access.access_branches.all()
                else:
                    # Otherwise, get branches from accessible companies
                    accessible_company_ids = org_access.access_companies.values_list('id', flat=True)
                    queryset = Branch.objects.filter(company_id__in=accessible_company_ids)
            except:
                accessible_company_ids = user.companies.values_list('id', flat=True)
                queryset = Branch.objects.filter(company_id__in=accessible_company_ids)

        # Apply filters
        if self.action == 'list':
            queryset = queryset.annotate(departments_count=Count('departments'))

            is_active = self.request.query_params.get('is_active')
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')

            company_id = self.request.query_params.get('company')
            if company_id:
                queryset = queryset.filter(company_id=company_id)

            branch_type = self.request.query_params.get('branch_type')
            if branch_type:
                queryset = queryset.filter(branch_type=branch_type)

        return queryset.select_related('company', 'parent_branch').order_by('company__code', 'code')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'], url_path='minimal')
    def minimal(self, request):
        """Get minimal list for dropdowns."""
        queryset = self.get_queryset().filter(is_active=True)
        company_id = request.query_params.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        serializer = BranchMinimalSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='departments')
    def departments(self, request, pk=None):
        """Get all departments in this branch."""
        branch = self.get_object()
        departments = branch.departments.filter(is_active=True)
        serializer = DepartmentListSerializer(departments, many=True)
        return Response(serializer.data)


# ============================================================================
# Department ViewSet
# ============================================================================

class DepartmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Departments with flexible attachment.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return DepartmentListSerializer
        elif self.action == 'minimal':
            return DepartmentMinimalSerializer
        return DepartmentSerializer

    def get_queryset(self):
        user = self.request.user

        # System admins see all
        if getattr(user, "is_system_admin", False) or getattr(user, "is_staff", False):
            queryset = Department.objects.all()
        else:
            # Regular users see departments from their accessible scope
            try:
                org_access = user.org_access

                # If user has specific department access, use that
                if org_access.access_departments.exists():
                    queryset = org_access.access_departments.all()
                else:
                    # Otherwise, get departments from accessible companies
                    accessible_company_ids = org_access.access_companies.values_list('id', flat=True)
                    queryset = Department.objects.filter(company_id__in=accessible_company_ids)
            except:
                accessible_company_ids = user.companies.values_list('id', flat=True)
                queryset = Department.objects.filter(company_id__in=accessible_company_ids)

        # Apply filters
        if self.action == 'list':
            queryset = queryset.annotate(
                employees_count=Count('employees', filter=Q(departmentmembership__is_active=True))
            )

            is_active = self.request.query_params.get('is_active')
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')

            company_id = self.request.query_params.get('company')
            if company_id:
                queryset = queryset.filter(company_id=company_id)

            branch_id = self.request.query_params.get('branch')
            if branch_id:
                queryset = queryset.filter(branch_id=branch_id)

            department_type = self.request.query_params.get('department_type')
            if department_type:
                queryset = queryset.filter(department_type=department_type)

        return queryset.select_related('company', 'branch', 'department_head').order_by('company__code', 'code')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'], url_path='minimal')
    def minimal(self, request):
        """Get minimal list for dropdowns."""
        queryset = self.get_queryset().filter(is_active=True)

        company_id = request.query_params.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        branch_id = request.query_params.get('branch')
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        serializer = DepartmentMinimalSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='members')
    def members(self, request, pk=None):
        """Get all members of this department."""
        department = self.get_object()
        memberships = DepartmentMembership.objects.filter(
            department=department,
            is_active=True
        ).select_related('user')
        serializer = DepartmentMembershipSerializer(memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='add-member')
    def add_member(self, request, pk=None):
        """Add a member to this department."""
        department = self.get_object()
        data = request.data.copy()
        data['department'] = department.id

        serializer = DepartmentMembershipSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='remove-member/(?P<user_id>[^/.]+)')
    def remove_member(self, request, pk=None, user_id=None):
        """Remove a member from this department."""
        department = self.get_object()

        try:
            membership = DepartmentMembership.objects.get(
                department=department,
                user_id=user_id,
                is_active=True
            )
            membership.is_active = False
            membership.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except DepartmentMembership.DoesNotExist:
            return Response(
                {"detail": "Membership not found."},
                status=status.HTTP_404_NOT_FOUND
            )


# ============================================================================
# DepartmentMembership ViewSet
# ============================================================================

class DepartmentMembershipViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Department Memberships.
    """
    serializer_class = DepartmentMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # System admins see all
        if getattr(user, "is_system_admin", False) or getattr(user, "is_staff", False):
            queryset = DepartmentMembership.objects.all()
        else:
            # Regular users see memberships from their accessible departments
            try:
                org_access = user.org_access
                accessible_dept_ids = org_access.access_departments.values_list('id', flat=True)
                queryset = DepartmentMembership.objects.filter(department_id__in=accessible_dept_ids)
            except:
                # Fallback: see memberships in departments from their companies
                accessible_company_ids = user.companies.values_list('id', flat=True)
                queryset = DepartmentMembership.objects.filter(
                    department__company_id__in=accessible_company_ids
                )

        # Apply filters
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        department_id = self.request.query_params.get('department')
        if department_id:
            queryset = queryset.filter(department_id=department_id)

        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset.select_related('user', 'department').order_by('-assigned_date')


# ============================================================================
# Organizational Context API
# ============================================================================

class OrganizationalContextView(APIView):
    """
    Get and set the user's current organizational context.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get current organizational context."""
        user = request.user

        try:
            org_access = user.org_access
            context = {
                'primary_group_id': org_access.primary_group_id,
                'primary_company_id': org_access.primary_company_id,
                'primary_branch_id': org_access.primary_branch_id,
                'primary_department_id': org_access.primary_department_id,
                'current_company_id': request.session.get('active_company_id'),
                'current_branch_id': request.session.get('active_branch_id'),
                'current_department_id': request.session.get('active_department_id'),
            }
        except:
            context = {
                'primary_group_id': None,
                'primary_company_id': None,
                'primary_branch_id': None,
                'primary_department_id': None,
                'current_company_id': request.session.get('active_company_id'),
                'current_branch_id': None,
                'current_department_id': None,
            }

        return Response(context)

    def put(self, request):
        """Set current organizational context in session."""
        company_id = request.data.get('company_id')
        branch_id = request.data.get('branch_id')
        department_id = request.data.get('department_id')

        if company_id:
            request.session['active_company_id'] = str(company_id)
        if branch_id:
            request.session['active_branch_id'] = str(branch_id)
        if department_id:
            request.session['active_department_id'] = str(department_id)

        return Response({'status': 'Context updated successfully'})


# ============================================================================
# Legacy Views
# ============================================================================


class CompanyGroupProvisionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CompanyProvisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provisioner = CompanyGroupProvisioner()
        payload = serializer.validated_data
        try:
            result = provisioner.provision(
                group_name=payload["group_name"],
                industry_pack=payload.get("industry_pack_type", ""),
                supports_intercompany=payload.get("supports_intercompany", False),
                default_company_payload=payload.get("company"),
                admin_user=request.user,
            )
        except ProvisioningError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_payload = {
            "company_group": CompanyGroupSerializer(result.company_group).data,
            "company": CompanySerializer(result.company).data,
        }
        return Response(response_payload, status=status.HTTP_201_CREATED)
