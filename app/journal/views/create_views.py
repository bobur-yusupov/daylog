from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
import json

from ..models import JournalEntry, Tag


class NewJournalView(LoginRequiredMixin, View):
    """
    View for creating a new journal entry.
    Creates an actual entry immediately and redirects to it.
    """

    def get(self, request):
        """Create a new blank journal entry and redirect to it"""
        try:
            # Create a new blank journal entry
            now = timezone.now()
            title = f"New Entry - {now.strftime('%B %d, %Y at %I:%M %p')}"
            
            # Create minimal EditorJS content structure
            default_content = {
                "time": int(now.timestamp() * 1000),
                "blocks": [],
                "version": "2.28.2"
            }
            
            entry = JournalEntry.objects.create(
                user=request.user,
                title=title,
                content=default_content,
                is_public=False,
            )
            
            # Redirect to dashboard with the new entry selected
            return redirect('journal:dashboard_with_entry', entry_id=entry.id)
            
        except Exception as e:
            messages.error(request, f"Error creating new journal entry: {str(e)}")
            return redirect('journal:dashboard')

    def post(self, request):
        """Handle journal entry creation from the legacy form (fallback)"""
        try:
            title = request.POST.get("title", "").strip()
            content = request.POST.get("content", "")
            is_public_raw = request.POST.get("is_public", "")
            is_public = str(is_public_raw).lower() in ["on", "true", "1", "yes"]
            tag_names = request.POST.getlist("tags")

            if not title:
                messages.error(request, "Title is required.")
                return self.get(request)

            if not content:
                messages.error(request, "Content is required.")
                return self.get(request)

            # Parse and validate EditorJS content
            try:
                content_data = json.loads(content)
            except json.JSONDecodeError:
                messages.error(request, "Invalid content format.")
                return self.get(request)

            # Create the journal entry
            entry = JournalEntry.objects.create(
                user=request.user,
                title=title,
                content=content_data,
                is_public=is_public,
            )

            # Handle tags
            for tag_name in tag_names:
                if tag_name.strip():
                    tag, created = Tag.objects.get_or_create(
                        user=request.user, name=tag_name.strip()
                    )
                    entry.tags.add(tag)

            messages.success(request, f'Journal entry "{title}" created successfully!')
            return redirect('journal:dashboard_with_entry', entry_id=entry.id)

        except Exception as e:
            messages.error(request, f"Error creating journal entry: {str(e)}")
            return redirect('journal:dashboard')
