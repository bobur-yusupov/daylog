from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from ..models import JournalEntry, Tag


class DashboardView(LoginRequiredMixin, View):
    """
    Dashboard view for authenticated users.
    """

    template_name = "journal/dashboard.html"

    def get(self, request):
        entries = JournalEntry.objects.filter(user=request.user).order_by(
            "-updated_at"
        )[:5]
        last_modified_entry = JournalEntry.objects.filter(user=request.user).order_by(
            "-updated_at"
        ).first()
        tags = Tag.objects.filter(user=request.user).order_by("-created_at")[:10]

        context = {
            "user": request.user,
            "recent_entries": entries,
            "last_modified_entry": last_modified_entry,
            "recent_tags": tags,
            "total_entries": JournalEntry.objects.filter(user=request.user).count(),
            "total_tags": Tag.objects.filter(user=request.user).count(),
        }
        return render(request, self.template_name, context)
