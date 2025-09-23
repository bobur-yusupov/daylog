from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
import json

from ..models import JournalEntry, Tag


class DashboardView(LoginRequiredMixin, View):
    """
    Dashboard view for authenticated users with search functionality.
    Handles both root dashboard and entry-specific dashboard URLs.
    """

    template_name = "journal/dashboard.html"

    def get(self, request, entry_id=None):
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

        # Get recent entries (limit to 5 for dashboard)
        entries = entries_queryset.order_by("-updated_at")[:5]

        # Handle entry_id parameter
        if entry_id:
            # Verify the entry exists and belongs to the user
            current_entry = get_object_or_404(
                JournalEntry.objects.prefetch_related('tags'), 
                id=entry_id, 
                user=request.user
            )
            active_entry = current_entry
        else:
            # If no entry_id, redirect to the most recent entry
            if entries:
                most_recent = entries.first()
                return redirect('journal:dashboard_with_entry', entry_id=most_recent.id)
            else:
                # No entries exist
                active_entry = None

        # Get recent tags
        tags = Tag.objects.filter(user=request.user).order_by("-created_at")[:10]

        # If it's an AJAX request for search, return JSON
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "entries": [
                        {
                            "id": str(entry.id),
                            "title": entry.title,
                            "updated_at": entry.updated_at.strftime("%b %d, %Y %H:%M"),
                            "is_active": entry == active_entry,
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
            "active_entry": active_entry,
            "recent_tags": tags,
            "search_query": search_query,
            "total_entries": JournalEntry.objects.filter(user=request.user).count(),
            "total_tags": Tag.objects.filter(user=request.user).count(),
        }
        return render(request, self.template_name, context)
