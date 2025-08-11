from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
import json

from ..models import JournalEntry, Tag


class EditJournalView(LoginRequiredMixin, View):
    """
    View for editing an existing journal entry with EditorJS support.
    """
    template_name = "journal/entry_edit.html"
    
    def get(self, request, entry_id):
        entry = get_object_or_404(JournalEntry, id=entry_id, user=request.user)
        tags = Tag.objects.filter(user=request.user).order_by('name')
        
        # Debug log for entry content
        print(f"DEBUG: Retrieved content for entry {entry_id}: {entry.content}")

        # Ensure content is valid JSON for EditorJS
        try:
            content_data = entry.content if entry.content else {"blocks": []}
        except (TypeError, ValueError):
            content_data = {"blocks": []}

        context = {
            'entry': entry,
            'available_tags': tags,
            'content_data': json.dumps(content_data),
        }
        return render(request, self.template_name, context)

    def post(self, request, entry_id):
        """Handle journal entry update"""
        entry = get_object_or_404(JournalEntry, id=entry_id, user=request.user)
        
        try:
            title = request.POST.get('title', '').strip()
            content = request.POST.get('content', '')
            is_public = request.POST.get('is_public') == 'on'
            tag_names = request.POST.getlist('tags')

            # Validation
            if not title:
                messages.error(request, "Title is required.")
                return redirect('journal:edit_entry', entry_id=entry_id)

            if not content:
                messages.error(request, "Content is required.")
                return redirect('journal:edit_entry', entry_id=entry_id)

            # Validate JSON content
            try:
                content_data = json.loads(content)
                if not isinstance(content_data, dict):
                    raise json.JSONDecodeError('Invalid content format', content, 0)
            except json.JSONDecodeError:
                messages.error(request, "Invalid content format.")
                return redirect('journal:edit_entry', entry_id=entry_id)

            # Update entry
            entry.title = title
            entry.content = content_data
            entry.is_public = is_public
            entry.save()

            # Handle tags
            entry.tags.clear()  # Remove existing tags
            
            for tag_name in tag_names:
                tag_name = tag_name.strip()
                if tag_name:
                    tag, created = Tag.objects.get_or_create(
                        user=request.user,
                        name=tag_name
                    )
                    entry.tags.add(tag)

            messages.success(request, f"'{title}' has been updated successfully!")
            return redirect('journal:entry_detail', entry_id=entry_id)

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('journal:edit_entry', entry_id=entry_id)
