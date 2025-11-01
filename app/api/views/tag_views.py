from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
)
from drf_spectacular.types import OpenApiTypes

from journal.models import Tag, JournalEntry
from api.serializers.journal_serailizers import TagSerializer, JournalEntrySerializer
from .pagination import StandardResultsSetPagination


@extend_schema_view(
    list=extend_schema(
        summary="List user tags",
        description="Retrieve a paginated list of tags belonging to the authenticated user.",
        tags=["Tags"],
    ),
    create=extend_schema(
        summary="Create a new tag",
        description="Create a new tag for the authenticated user. Tag names must be unique per user.",
        tags=["Tags"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a tag",
        description="Get details of a specific tag.",
        tags=["Tags"],
    ),
    update=extend_schema(
        summary="Update a tag",
        description="Update a tag's name. The new name must be unique per user.",
        tags=["Tags"],
    ),
    partial_update=extend_schema(
        summary="Partially update a tag",
        description="Partially update a tag's properties.",
        tags=["Tags"],
    ),
    destroy=extend_schema(
        summary="Delete a tag",
        description="Delete a tag. This will remove the tag from all associated journal entries.",
        tags=["Tags"],
    ),
)
class TagViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Tags with full CRUD operations
    """

    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Filter tags by the current user"""
        return Tag.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        """Automatically assign the current user when creating a tag"""
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Create a new tag with duplicate checking"""
        name = request.data.get("name", "").strip()

        if not name:
            return Response(
                {"error": "Tag name is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Normalize tag name to match model's clean() method
        normalized_name = name.lower()
        
        # Check if tag already exists for this user (using normalized name)
        if Tag.objects.filter(user=request.user, name=normalized_name).exists():
            return Response(
                {"error": f'Tag "{name}" already exists'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Update tag with duplicate checking"""
        instance = self.get_object()
        name = request.data.get("name", "").strip()

        if not name:
            return Response(
                {"error": "Tag name is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Normalize tag name to match model's clean() method
        normalized_name = name.lower()
        
        # Check if another tag with this name exists for this user (using normalized name)
        existing_tag = (
            Tag.objects.filter(user=request.user, name=normalized_name)
            .exclude(id=instance.id)
            .first()
        )

        if existing_tag:
            return Response(
                {"error": f'Tag "{name}" already exists'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Search tags",
        description="Search for tags by name with pagination support.",
        parameters=[
            OpenApiParameter(
                name="q",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search query for tag names",
                required=True,
            ),
        ],
        tags=["Tags"],
    )
    @action(detail=False, methods=["get"])
    def search(self, request):
        """Search tags by name with pagination"""
        query = request.query_params.get("q", "").strip()

        if not query:
            return Response(
                {"count": 0, "results": [], "links": {"next": None, "previous": None}}
            )

        queryset = self.get_queryset().filter(name__icontains=query)

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Fallback if pagination is not configured
        serializer = self.get_serializer(queryset[:10], many=True)
        return Response({"results": serializer.data})

    @extend_schema(
        summary="Get entries for tag",
        description="Retrieve all journal entries associated with a specific tag, with pagination.",
        tags=["Tags"],
    )
    @action(detail=True, methods=["get"])
    def entries(self, request, pk=None):
        """Get all journal entries for a specific tag with pagination"""
        tag = self.get_object()
        queryset = JournalEntry.objects.filter(tags=tag, user=request.user).order_by(
            "-created_at"
        )

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = JournalEntrySerializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data).data
            # Add tag info to the response
            response_data["tag"] = self.get_serializer(tag).data
            return Response(response_data)

        # Fallback if pagination is not configured
        serializer = JournalEntrySerializer(queryset, many=True)
        return Response(
            {
                "tag": self.get_serializer(tag).data,
                "entries": serializer.data,
                "count": queryset.count(),
            }
        )
