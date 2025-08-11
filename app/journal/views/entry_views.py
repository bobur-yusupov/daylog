from django.shortcuts import render, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from ..models import JournalEntry, Tag


class JournalListView(LoginRequiredMixin, View):
    """
    View for listing all journal entries with filtering options.
    """
    template_name = "journal/entry_list.html"
    
    def get(self, request):
        entries = JournalEntry.objects.filter(user=request.user).order_by('-created_at')
        tags = Tag.objects.filter(user=request.user).order_by('name')
        
        # Filter by tag if specified
        tag_filter = request.GET.get('tag')
        if tag_filter:
            entries = entries.filter(tags__name=tag_filter)
        
        # Search functionality
        search_query = request.GET.get('search')
        if search_query:
            entries = entries.filter(title__icontains=search_query)
        
        context = {
            'entries': entries,
            'tags': tags,
            'current_tag': tag_filter,
            'search_query': search_query,
        }
        return render(request, self.template_name, context)


class JournalDetailView(LoginRequiredMixin, View):
    """
    View for displaying a single journal entry.
    """
    template_name = "journal/entry_detail.html"
    
    def get(self, request, entry_id):
        entry = get_object_or_404(JournalEntry, id=entry_id, user=request.user)
        
        context = {
            'entry': entry,
        }
        return render(request, self.template_name, context)
