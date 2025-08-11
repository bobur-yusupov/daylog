from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
import json

from ..models import JournalEntry, Tag


class NewJournalView(LoginRequiredMixin, View):
    """
    View for creating a new journal entry with EditorJS support.
    """
    template_name = "journal/entry_create.html"
    
    def get(self, request):
        tags = Tag.objects.filter(user=request.user).order_by('name')
        context = {
            'available_tags': tags,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        """Handle journal entry creation"""
        try:
            title = request.POST.get('title', '').strip()
            content = request.POST.get('content', '')
            is_public_raw = request.POST.get('is_public', '')
            is_public = str(is_public_raw).lower() in ['on', 'true', '1', 'yes']
            tag_names = request.POST.getlist('tags')
            
            if not title:
                messages.error(request, 'Title is required.')
                return self.get(request)
            
            if not content:
                messages.error(request, 'Content is required.')
                return self.get(request)
            
            # Parse and validate EditorJS content
            try:
                content_data = json.loads(content)
            except json.JSONDecodeError:
                messages.error(request, 'Invalid content format.')
                return self.get(request)
            
            # Create the journal entry
            entry = JournalEntry.objects.create(
                user=request.user,
                title=title,
                content=content_data,
                is_public=is_public
            )
            
            # Handle tags
            for tag_name in tag_names:
                if tag_name.strip():
                    tag, created = Tag.objects.get_or_create(
                        user=request.user,
                        name=tag_name.strip()
                    )
                    entry.tags.add(tag)
            
            messages.success(request, f'Journal entry "{title}" created successfully!')
            return redirect("journal:dashboard")
            
        except Exception as e:
            messages.error(request, f'Error creating journal entry: {str(e)}')
            return self.get(request)
