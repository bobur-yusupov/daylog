from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse

from ..models import JournalEntry, Tag


class SearchView(LoginRequiredMixin, View):
    """
    Dedicated search view for journal entries with advanced search capabilities.
    """

    template_name = "journal/search.html"

    def get(self, request):
        search_query = request.GET.get("q", "").strip()
        tag_filter = request.GET.get("tag", "").strip()
        page = request.GET.get("page", 1)

        # Base queryset
        entries_queryset = JournalEntry.objects.filter(user=request.user)

        # Apply search filters
        if search_query:
            entries_queryset = entries_queryset.filter(
                Q(title__icontains=search_query)
                | Q(content__icontains=search_query)
            ).distinct()

        if tag_filter:
            entries_queryset = entries_queryset.filter(
                tags__name__icontains=tag_filter
            ).distinct()

        # Order by relevance (most recent first for now)
        entries_queryset = entries_queryset.order_by("-updated_at")

        # Pagination
        paginator = Paginator(entries_queryset, 10)  # 10 entries per page
        page_obj = paginator.get_page(page)

        # Add content preview to each entry
        entries_with_preview = []
        for entry in page_obj:
            entry.content_preview = self._get_content_preview(entry.content)
            entries_with_preview.append(entry)

        # Get all tags for filter suggestions
        user_tags = Tag.objects.filter(user=request.user).order_by("name")

        # If it's an AJAX request, return JSON for autocomplete
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "entries": [
                    {
                        "id": str(entry.id),
                        "title": entry.title,
                        "updated_at": entry.updated_at.strftime("%b %d, %Y %H:%M"),
                        "tags": [tag.name for tag in entry.tags.all()],
                        "preview": self._get_content_preview(entry.content),
                    }
                    for entry in page_obj
                ],
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
                "total_count": paginator.count,
            })

        context = {
            "search_query": search_query,
            "tag_filter": tag_filter,
            "entries": page_obj,  # This will have the content_preview attribute
            "user_tags": user_tags,
            "total_count": paginator.count,
            "has_results": paginator.count > 0,
        }

        return render(request, self.template_name, context)

    def _get_content_preview(self, content, max_length=200):
        """Extract text preview from EditorJS content."""
        if not content or not isinstance(content, dict):
            return ""

        blocks = content.get("blocks", [])
        text_parts = []

        for block in blocks[:3]:  # Only check first 3 blocks
            if block.get("type") == "paragraph":
                text = block.get("data", {}).get("text", "")
                if text:
                    # Remove HTML tags for preview
                    import re
                    clean_text = re.sub(r'<[^>]+>', '', text)
                    text_parts.append(clean_text)

        preview = " ".join(text_parts)
        if len(preview) > max_length:
            preview = preview[:max_length] + "..."

        return preview