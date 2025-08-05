from django.shortcuts import render, redirect
from django.views import View


# Create your views here.
def dashboard(request):
    """
    Dashboard view for authenticated users.
    """
    if not request.user.is_authenticated:
        return redirect("authentication:login")

    return render(request, "journal/dashboard.html", {"user": request.user})


class NewJournalView(View):
    """
    View for creating a new journal entry.
    """
    def get(self, request):
        return render(request, "journal/new_journal.html")

    def post(self, request):
        # Logic to handle form submission and save the new journal entry
        # would go here.
        return redirect("journal:dashboard")