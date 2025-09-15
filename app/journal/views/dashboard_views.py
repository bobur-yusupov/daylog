from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
import json

from ..models import JournalEntry, Tag


class DashboardView(LoginRequiredMixin, View):
    """
    Dashboard view for authenticated users with search functionality.
    """

    template_name = "journal/dashboard.html"

    def get(self, request):
        search_query = request.GET.get("search", "").strip()

        # Base queryset
        entries_queryset = JournalEntry.objects.filter(user=request.user)

        # Apply search filter if provided
        if search_query:
            entries_queryset = entries_queryset.filter(
                Q(title__icontains=search_query)
                | Q(content__icontains=search_query)
                | Q(tags__name__icontains=search_query)
            ).distinct()

        # Get recent entries (limit to 10 for dashboard)
        entries = entries_queryset.order_by("-updated_at")[:10]

        # Get last modified entry (considering search if applied)
        last_modified_entry = entries.first() if entries else None

        # Get recent tags
        tags = Tag.objects.filter(user=request.user).order_by("-created_at")[:10]

        # Serialize entry content properly for JavaScript
        entries_with_content = []
        for entry in entries:
            entry_dict = {
                "id": str(entry.id),
                "title": entry.title,
                "content": entry.content if entry.content else {},
                "updated_at": entry.updated_at,
                "content_json": json.dumps(entry.content if entry.content else {}),
            }
            entries_with_content.append(entry_dict)

        # If it's an AJAX request for search, return JSON
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "entries": [
                        {
                            "id": str(entry.id),
                            "title": entry.title,
                            "updated_at": entry.updated_at.strftime("%b %d, %Y %H:%M"),
                            "is_active": entry == last_modified_entry,
                        }
                        for entry in entries
                    ],
                    "total_count": entries_queryset.count(),
                    "search_query": search_query,
                }
            )

        context = {
            "user": request.user,
            "recent_entries": entries,
            "entries_data": entries_with_content,
            "last_modified_entry": last_modified_entry,
            "recent_tags": tags,
            "search_query": search_query,
            "total_entries": JournalEntry.objects.filter(user=request.user).count(),
            "total_tags": Tag.objects.filter(user=request.user).count(),
        }
        return render(request, self.template_name, context)
