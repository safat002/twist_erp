from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework import status
from django.core.cache import cache
from .services import FeatureService
from .serializers import (
    FeatureMapSerializer,
    ModuleFeatureToggleSerializer,
    FeatureAuditLogSerializer,
    FeatureToggleUpdateSerializer
)
from .models import ModuleFeatureToggle, FeatureAuditLog


class FeatureFlagsView(APIView):
    """
    API endpoint for fetching feature flags.

    GET /api/v1/admin-settings/features/
    Returns all enabled features for the current user's company.
    """

    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        """Get feature flags for current company."""
        company = getattr(request, 'company', None)

        if not company:
            # No company context - return global features only
            features = FeatureService.get_global_features()
            scope = 'GLOBAL'
        else:
            # Get resolved features for company
            features = FeatureService.get_features_for_company(company)
            scope = f'COMPANY:{company.code}'

        # Get enabled modules
        modules = list(FeatureService.get_enabled_modules(company))

        # Check if from cache
        cache_key = FeatureService.get_cache_key(
            'COMPANY' if company else 'GLOBAL',
            company_id=company.id if company else None
        )
        cached = cache.get(cache_key) is not None

        # Enrich with dependents map
        try:
            dependents_map = FeatureService.compute_dependents(features)
            # Merge into features objects
            for key, info in dependents_map.items():
                if key in features:
                    features[key]['dependent_keys'] = info.get('dependent_keys', [])
                    features[key]['dependents'] = info.get('dependents', [])
        except Exception:
            # Non-fatal enrichment
            pass

        data = {
            'features': features,
            'modules': modules,
            'scope': scope,
            'cached': cached,
        }

        serializer = FeatureMapSerializer(data)
        return Response(serializer.data)


class FeatureCheckView(APIView):
    """
    Check if a specific feature is enabled.

    GET /api/v1/admin-settings/features/check/?key=finance.journal_vouchers
    """

    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        """Check feature status."""
        feature_key = request.query_params.get('key')

        if not feature_key:
            return Response(
                {'error': 'Feature key is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        company = getattr(request, 'company', None)

        enabled = FeatureService.is_feature_enabled(feature_key, company)
        visible = FeatureService.is_feature_visible(feature_key, company)
        dependencies = FeatureService.check_dependencies(feature_key, company)

        return Response({
            'feature_key': feature_key,
            'enabled': enabled,
            'visible': visible,
            'dependencies': dependencies,
            'dependencies_met': all(dependencies.values()) if dependencies else True,
        })


class FeatureToggleUpdateView(APIView):
    """
    Toggle a feature on/off (admin only, for dashboard toggles).

    POST /api/v1/admin-settings/features/<module>/<feature>/toggle/
    Body: {"is_enabled": true}
    """

    permission_classes = [IsAdminUser]

    def post(self, request, module_name, feature_key):
        """Toggle feature."""
        serializer = FeatureToggleUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        company = getattr(request, 'company', None)

        # Determine scope
        if company:
            scope_type = 'COMPANY'
            filters = {
                'module_name': module_name,
                'feature_key': feature_key,
                'scope_type': 'COMPANY',
                'company': company,
            }
        else:
            scope_type = 'GLOBAL'
            filters = {
                'module_name': module_name,
                'feature_key': feature_key,
                'scope_type': 'GLOBAL',
                'company__isnull': True,
                'company_group__isnull': True,
            }

        try:
            toggle = ModuleFeatureToggle.objects.get(**filters)
            old_value = toggle.is_enabled
            toggle.is_enabled = serializer.validated_data['is_enabled']
            toggle.updated_by = request.user
            toggle.save()

            # Log the change
            FeatureAuditLog.objects.create(
                feature_toggle=toggle,
                action='enabled' if toggle.is_enabled else 'disabled',
                old_value={'is_enabled': old_value},
                new_value={'is_enabled': toggle.is_enabled},
                user=request.user,
                ip_address=self._get_client_ip(request),
            )

            return Response({
                'success': True,
                'feature_key': toggle.full_key,
                'is_enabled': toggle.is_enabled,
                'message': f'Feature {toggle.feature_name} {"enabled" if toggle.is_enabled else "disabled"} successfully.'
            })

        except ModuleFeatureToggle.DoesNotExist:
            return Response(
                {'error': 'Feature toggle not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @staticmethod
    def _get_client_ip(request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class FeatureListView(APIView):
    """
    List all feature toggles (admin only).

    GET /api/v1/admin-settings/features/list/
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        """List all feature toggles."""
        queryset = ModuleFeatureToggle.objects.all().order_by('-priority', 'module_name', 'feature_key')

        # Apply filters
        module = request.query_params.get('module')
        if module:
            queryset = queryset.filter(module_name=module)

        scope_type = request.query_params.get('scope')
        if scope_type:
            queryset = queryset.filter(scope_type=scope_type)

        enabled = request.query_params.get('enabled')
        if enabled is not None:
            queryset = queryset.filter(is_enabled=enabled.lower() == 'true')

        serializer = ModuleFeatureToggleSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'features': serializer.data
        })


class FeatureAuditLogView(APIView):
    """
    View feature audit logs.

    GET /api/v1/admin-settings/features/audit/
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get audit logs."""
        queryset = FeatureAuditLog.objects.select_related(
            'feature_toggle', 'user'
        ).order_by('-timestamp')[:100]  # Last 100 entries

        serializer = FeatureAuditLogSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'logs': serializer.data
        })


class CacheInvalidationView(APIView):
    """
    Invalidate feature cache (admin only).

    POST /api/v1/admin-settings/features/invalidate-cache/
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        """Invalidate cache."""
        # Invalidate all caches by clearing all feature-related keys
        try:
            # Clear global cache
            cache.delete(f"{FeatureService.CACHE_PREFIX}:global")

            # Note: For production, you might want to use cache.delete_pattern if available
            # For now, we'll just clear known patterns

            return Response({
                'success': True,
                'message': 'Feature cache invalidated successfully'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
