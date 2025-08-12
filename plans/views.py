from rest_framework import viewsets, permissions
from .models import Plan
from .serializers import PlanSerializer


class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.prefetch_related("benefits__service").all()
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        is_popular = self.request.query_params.get("popular")
        if is_popular:
            queryset = queryset.filter(is_popular=True)
        return queryset
