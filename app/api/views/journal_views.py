from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
import json

from journal.models import Tag, JournalEntry
from api.serializers.journal_serailizers import TagSerializer, JournalEntrySerializer


class StandardResultsSetPagination(PageNumberPagination):
    """Custom pagination class for API responses"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'has_next': self.page.has_next(),
            'has_previous': self.page.has_previous(),
            'results': data
        })


class LargePagination(PageNumberPagination):
    """Pagination class for potentially large datasets like search results"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'has_next': self.page.has_next(),
            'has_previous': self.page.has_previous(),
            'results': data
        })


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
        return Tag.objects.filter(user=self.request.user).order_by('-created_at')
    
    def perform_create(self, serializer):
        """Automatically assign the current user when creating a tag"""
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Create a new tag with duplicate checking"""
        name = request.data.get('name', '').strip()
        
        if not name:
            return Response(
                {'error': 'Tag name is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if tag already exists for this user
        if Tag.objects.filter(user=request.user, name=name).exists():
            return Response(
                {'error': f'Tag "{name}" already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Update tag with duplicate checking"""
        instance = self.get_object()
        name = request.data.get('name', '').strip()
        
        if not name:
            return Response(
                {'error': 'Tag name is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if another tag with this name exists for this user
        existing_tag = Tag.objects.filter(
            user=request.user, 
            name=name
        ).exclude(id=instance.id).first()
        
        if existing_tag:
            return Response(
                {'error': f'Tag "{name}" already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
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
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search tags by name with pagination"""
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response({
                'count': 0,
                'results': [],
                'links': {'next': None, 'previous': None}
            })
        
        queryset = self.get_queryset().filter(name__icontains=query)
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # Fallback if pagination is not configured
        serializer = self.get_serializer(queryset[:10], many=True)
        return Response({'results': serializer.data})
    
    @extend_schema(
        summary="Get entries for tag",
        description="Retrieve all journal entries associated with a specific tag, with pagination.",
        tags=["Tags"],
    )
    @action(detail=True, methods=['get'])
    def entries(self, request, pk=None):
        """Get all journal entries for a specific tag with pagination"""
        tag = self.get_object()
        queryset = JournalEntry.objects.filter(
            tags=tag,
            user=request.user
        ).order_by('-created_at')
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = JournalEntrySerializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data).data
            # Add tag info to the response
            response_data['tag'] = self.get_serializer(tag).data
            return Response(response_data)
        
        # Fallback if pagination is not configured
        serializer = JournalEntrySerializer(queryset, many=True)
        return Response({
            'tag': self.get_serializer(tag).data,
            'entries': serializer.data,
            'count': queryset.count()
        })


@extend_schema_view(
    list=extend_schema(
        summary="List journal entries",
        description="Retrieve a paginated list of journal entries with optional filtering by tags, public status, and search terms.",
        parameters=[
            OpenApiParameter(
                name="tags",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by tag names (can be multiple)",
                many=True,
            ),
            OpenApiParameter(
                name="is_public",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter by public status",
            ),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search in title and content",
            ),
        ],
        tags=["Journal Entries"],
    ),
    create=extend_schema(
        summary="Create a journal entry",
        description="Create a new journal entry with EditorJS content and optional tags.",
        examples=[
            OpenApiExample(
                "EditorJS Content Example",
                value={
                    "title": "My Daily Thoughts",
                    "content": {
                        "time": 1643723964077,
                        "blocks": [
                            {
                                "id": "header-1",
                                "type": "header",
                                "data": {
                                    "text": "Today's Reflection",
                                    "level": 2
                                }
                            },
                            {
                                "id": "paragraph-1",
                                "type": "paragraph",
                                "data": {
                                    "text": "Today was a productive day..."
                                }
                            }
                        ],
                        "version": "2.28.2"
                    },
                    "is_public": False,
                    "tag_names": ["personal", "reflection"]
                },
                request_only=True,
            )
        ],
        tags=["Journal Entries"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a journal entry",
        description="Get details of a specific journal entry.",
        tags=["Journal Entries"],
    ),
    update=extend_schema(
        summary="Update a journal entry",
        description="Update a journal entry's content, title, tags, or public status.",
        tags=["Journal Entries"],
    ),
    partial_update=extend_schema(
        summary="Partially update a journal entry",
        description="Partially update a journal entry's properties.",
        tags=["Journal Entries"],
    ),
    destroy=extend_schema(
        summary="Delete a journal entry",
        description="Delete a journal entry permanently.",
        tags=["Journal Entries"],
    ),
)
class JournalEntryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Journal Entries with EditorJS support
    """
    serializer_class = JournalEntrySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_pagination_class(self):
        """
        Return different pagination classes based on the action
        """
        if self.action in ['search', 'public']:
            return LargePagination
        return self.pagination_class
    
    def paginate_queryset(self, queryset):
        """
        Override to use dynamic pagination class
        """
        # Temporarily set the pagination class
        original_pagination_class = self.pagination_class
        self.pagination_class = self.get_pagination_class()
        
        # Call the parent method
        result = super().paginate_queryset(queryset)
        
        # Restore original pagination class
        self.pagination_class = original_pagination_class
        
        return result
    
    def get_queryset(self):
        """Filter entries by the current user with optional filtering"""
        queryset = JournalEntry.objects.filter(
            user=self.request.user
        ).prefetch_related('tags').order_by('-created_at')
        
        # Filter by tags if provided
        tag_names = self.request.query_params.getlist('tags')
        if tag_names:
            queryset = queryset.filter(tags__name__in=tag_names).distinct()
        
        # Filter by public status
        is_public = self.request.query_params.get('is_public')
        if is_public is not None:
            is_public_bool = is_public.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_public=is_public_bool)
        
        # Search in title and content
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(content__icontains=search)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        """Automatically assign the current user when creating an entry"""
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Create a new journal entry with EditorJS content validation"""
        # Validate EditorJS content
        content = request.data.get('content')
        if content:
            validated_content = self._validate_editorjs_content(content)
            if 'error' in validated_content:
                return Response(validated_content, status=status.HTTP_400_BAD_REQUEST)
            request.data['content'] = validated_content['content']
        
        # Handle tags
        tag_names = request.data.get('tag_names', [])
        
        response = super().create(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_201_CREATED:
            # Add tags to the created entry
            entry = JournalEntry.objects.get(id=response.data['id'])
            self._handle_tags(entry, tag_names)
            
            # Return updated entry data with tags
            serializer = self.get_serializer(entry)
            response.data = serializer.data
        
        return response
    
    def update(self, request, *args, **kwargs):
        """Update journal entry with EditorJS content validation"""
        # Validate EditorJS content
        content = request.data.get('content')
        if content:
            validated_content = self._validate_editorjs_content(content)
            if 'error' in validated_content:
                return Response(validated_content, status=status.HTTP_400_BAD_REQUEST)
            request.data['content'] = validated_content['content']
        
        # Handle tags
        tag_names = request.data.get('tag_names', [])
        
        response = super().update(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_200_OK:
            # Update tags for the entry
            entry = self.get_object()
            self._handle_tags(entry, tag_names)
            
            # Return updated entry data with tags
            serializer = self.get_serializer(entry)
            response.data = serializer.data
        
        return response
    
    def _validate_editorjs_content(self, content):
        """Validate EditorJS content structure"""
        try:
            if isinstance(content, str):
                content_data = json.loads(content)
            else:
                content_data = content
            
            # Basic EditorJS structure validation
            if not isinstance(content_data, dict):
                return {'error': 'Content must be a valid EditorJS object'}
            
            if 'blocks' not in content_data:
                return {'error': 'Content must contain blocks array'}
            
            if not isinstance(content_data['blocks'], list):
                return {'error': 'Blocks must be an array'}
            
            # Validate each block
            for i, block in enumerate(content_data['blocks']):
                if not isinstance(block, dict):
                    return {'error': f'Block {i} must be an object'}
                
                required_fields = ['id', 'type', 'data']
                for field in required_fields:
                    if field not in block:
                        return {'error': f'Block {i} missing required field: {field}'}
            
            return {'content': content_data}
            
        except json.JSONDecodeError:
            return {'error': 'Invalid JSON content'}
        except Exception as e:
            return {'error': f'Content validation error: {str(e)}'}
    
    def _handle_tags(self, entry, tag_names):
        """Handle tag assignment for journal entry"""
        if not isinstance(tag_names, list):
            return
        
        # Clear existing tags
        entry.tags.clear()
        
        # Add new tags
        for tag_name in tag_names:
            if tag_name.strip():
                tag, created = Tag.objects.get_or_create(
                    user=self.request.user,
                    name=tag_name.strip()
                )
                entry.tags.add(tag)
    
    @extend_schema(
        summary="Search journal entries",
        description="Search journal entries by title, content, or tags with enhanced pagination.",
        parameters=[
            OpenApiParameter(
                name="q",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search query",
                required=True,
            ),
        ],
        tags=["Journal Entries"],
    )
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Enhanced search for journal entries with pagination"""
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response({
                'query': '',
                'count': 0,
                'results': [],
                'links': {'next': None, 'previous': None}
            })
        
        queryset = self.get_queryset().filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct()
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data).data
            response_data['query'] = query
            return Response(response_data)
        
        # Fallback if pagination is not configured
        serializer = self.get_serializer(queryset[:20], many=True)
        return Response({
            'query': query,
            'results': serializer.data,
            'count': queryset.count()
        })
    
    @extend_schema(
        summary="Duplicate journal entry",
        description="Create a copy of an existing journal entry. The copy will always be private.",
        tags=["Journal Entries"],
    )
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Create a duplicate of an existing journal entry"""
        original_entry = self.get_object()
        
        # Create new entry with same content
        new_entry = JournalEntry.objects.create(
            user=request.user,
            title=f"Copy of {original_entry.title}",
            content=original_entry.content,
            is_public=False  # Always create copies as private
        )
        
        # Copy tags
        new_entry.tags.set(original_entry.tags.all())
        
        serializer = self.get_serializer(new_entry)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        summary="Get content statistics",
        description="Get detailed statistics about the content of a journal entry including word count, character count, block count, and block types.",
        tags=["Journal Entries"],
    )
    @action(detail=True, methods=['get'])
    def content_stats(self, request, pk=None):
        """Get content statistics for a journal entry"""
        entry = self.get_object()
        
        stats = {
            'word_count': 0,
            'character_count': 0,
            'block_count': 0,
            'block_types': {}
        }
        
        try:
            content = entry.content
            if isinstance(content, dict) and 'blocks' in content:
                stats['block_count'] = len(content['blocks'])
                
                for block in content['blocks']:
                    block_type = block.get('type', 'unknown')
                    stats['block_types'][block_type] = stats['block_types'].get(block_type, 0) + 1
                    
                    # Count words and characters from text content
                    if 'data' in block and 'text' in block['data']:
                        text = block['data']['text']
                        stats['word_count'] += len(text.split())
                        stats['character_count'] += len(text)
                    
                    # Handle list items
                    elif 'data' in block and 'items' in block['data']:
                        for item in block['data']['items']:
                            if isinstance(item, str):
                                stats['word_count'] += len(item.split())
                                stats['character_count'] += len(item)
        
        except Exception as e:
            return Response(
                {'error': f'Error calculating stats: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(stats)
    
    @extend_schema(
        summary="Get filtered entries",
        description="Get journal entries with advanced filtering options including date ranges and tag presence.",
        parameters=[
            OpenApiParameter(
                name="date_from",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter entries from this date (YYYY-MM-DD)",
            ),
            OpenApiParameter(
                name="date_to",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter entries until this date (YYYY-MM-DD)",
            ),
            OpenApiParameter(
                name="has_tags",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by tag presence ('true' or 'false')",
                enum=["true", "false"],
            ),
        ],
        tags=["Journal Entries"],
    )
    @action(detail=False, methods=['get'])
    def filtered(self, request):
        """Get journal entries with advanced filtering and pagination"""
        queryset = self.get_queryset()
        
        # Advanced filtering options
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        has_tags = request.query_params.get('has_tags')  # 'true' or 'false'
        min_words = request.query_params.get('min_words')
        max_words = request.query_params.get('max_words')
        
        # Date range filtering
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=date_to_obj)
            except ValueError:
                pass
        
        # Filter by presence of tags
        if has_tags == 'true':
            queryset = queryset.filter(tags__isnull=False).distinct()
        elif has_tags == 'false':
            queryset = queryset.filter(tags__isnull=True)
        
        # Word count filtering would require a more complex approach
        # For now, we'll leave it as a placeholder for future enhancement
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # Fallback if pagination is not configured
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'count': queryset.count()
        })
    
    @extend_schema(
        summary="Get public entries",
        description="Retrieve public journal entries from all users with optional filtering by username.",
        parameters=[
            OpenApiParameter(
                name="user",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by username",
            ),
        ],
        tags=["Journal Entries"],
    )
    @action(detail=False, methods=['get'])
    def public(self, request):
        """Get public journal entries with pagination (for potential sharing feature)"""
        queryset = JournalEntry.objects.filter(
            is_public=True
        ).select_related('user').prefetch_related('tags').order_by('-created_at')
        
        # Optional filtering by user
        username = request.query_params.get('user')
        if username:
            queryset = queryset.filter(user__username=username)
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # Fallback if pagination is not configured
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'entries': serializer.data,
            'count': queryset.count()
        })
