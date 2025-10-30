from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Project
from .serializers import ProjectSerializer, TaskSerializer


class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        company = getattr(self.request, "company", None)
        qs = Project.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs


class ProjectGanttView(APIView):
    def get(self, request, pk):
        try:
            project = Project.objects.get(pk=pk)
        except Project.DoesNotExist:
            return Response({"detail": "Project not found"}, status=404)
        tasks = project.tasks.all()
        return Response(TaskSerializer(tasks, many=True).data)
