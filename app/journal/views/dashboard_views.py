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
            "-created_at"
        )[:5]
        tags = Tag.objects.filter(user=request.user).order_by("-created_at")[:10]

        context = {
            "user": request.user,
            "recent_entries": entries,
            "recent_tags": tags,
            "total_entries": JournalEntry.objects.filter(user=request.user).count(),
            "total_tags": Tag.objects.filter(user=request.user).count(),
        }
        return render(request, self.template_name, context)
