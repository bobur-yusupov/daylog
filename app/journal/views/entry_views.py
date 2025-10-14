from django.shortcuts import render, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
import json

from ..models import JournalEntry, Tag


class JournalListView(LoginRequiredMixin, View):
    """
    View for listing all journal entries with filtering options.
    """

    template_name = "journal/entry_list.html"

    def get(self, request):
        entries = JournalEntry.objects.filter(user=request.user).order_by("-created_at")
        tags = Tag.objects.filter(user=request.user).order_by("name")

        # Filter by tag if specified
        tag_filter = request.GET.get("tag")
        if tag_filter:
            entries = entries.filter(tags__name=tag_filter)

        # Search functionality
        search_query = request.GET.get("search")
        if search_query:
            entries = entries.filter(title__icontains=search_query)

        context = {
            "entries": entries,
            "tags": tags,
            "current_tag": tag_filter,
            "search_query": search_query,
        }
        return render(request, self.template_name, context)


class JournalDetailView(LoginRequiredMixin, View):
    """
    View for displaying a single journal entry.
    Supports both regular requests and AJAX requests.
    """

    template_name = "journal/entry_detail.html"

    def get(self, request, entry_id):
        entry = get_object_or_404(JournalEntry, id=entry_id, user=request.user)

        # If it's an AJAX request, return JSON data for the dashboard
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "id": str(entry.id),
                    "title": entry.title,
                    "content": entry.content if entry.content else {},
                    "content_json": json.dumps(entry.content if entry.content else {}),
                    "updated_at": entry.updated_at.strftime("%b %d, %Y %H:%M"),
                    "updated_at_iso": entry.updated_at.isoformat(),
                }
            )

        context = {
            "entry": entry,
        }
        return render(request, self.template_name, context)


class SharedJournalView(View):
    """
    View for displaying a shared journal entry (read-only).
    No authentication required.
    """

    template_name = "journal/shared_entry.html"

    def get(self, request, share_token):
        entry = get_object_or_404(JournalEntry, share_token=share_token)

        context = {
            "entry": entry,
            "is_shared": True,
        }
        return render(request, self.template_name, context)


class GenerateShareTokenView(LoginRequiredMixin, View):
    """
    API view to generate a share token for a journal entry.
    """

    def post(self, request, entry_id):
        entry = get_object_or_404(JournalEntry, id=entry_id, user=request.user)
        token = entry.generate_share_token()
        share_url = request.build_absolute_uri(f"/share/{token}/")

        return JsonResponse(
            {"success": True, "share_token": token, "share_url": share_url}
        )


class RevokeShareTokenView(LoginRequiredMixin, View):
    """
    API view to revoke a share token for a journal entry.
    """

    def post(self, request, entry_id):
        entry = get_object_or_404(JournalEntry, id=entry_id, user=request.user)
        entry.revoke_share_token()

        return JsonResponse({"success": True, "message": "Share link revoked"})
