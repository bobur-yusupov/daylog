from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

from .models import JournalEntry, Tag


# Create your views here.
class DashboardView(LoginRequiredMixin, View):
    """
    Dashboard view for authenticated users.
    """
    def get(self, request):
        entries = JournalEntry.objects.filter(user=request.user).order_by('-created_at')[:5]
        tags = Tag.objects.filter(user=request.user).order_by('-created_at')[:10]
        
        context = {
            'user': request.user,
            'recent_entries': entries,
            'recent_tags': tags,
            'total_entries': JournalEntry.objects.filter(user=request.user).count(),
            'total_tags': Tag.objects.filter(user=request.user).count(),
        }
        return render(request, "journal/dashboard.html", context)


class NewJournalView(LoginRequiredMixin, View):
    """
    View for creating a new journal entry with EditorJS support.
    """
    def get(self, request):
        tags = Tag.objects.filter(user=request.user).order_by('name')
        context = {
            'available_tags': tags,
        }
        return render(request, "journal/new_journal.html", context)

    def post(self, request):
        """Handle journal entry creation"""
        try:
            title = request.POST.get('title', '').strip()
            content = request.POST.get('content', '')
            is_public = request.POST.get('is_public') == 'on'
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


class EditJournalView(LoginRequiredMixin, View):
    """
    View for editing an existing journal entry.
    """
    def get(self, request, entry_id):
        entry = get_object_or_404(JournalEntry, id=entry_id, user=request.user)
        tags = Tag.objects.filter(user=request.user).order_by('name')
        
        context = {
            'entry': entry,
            'available_tags': tags,
            'entry_tags': list(entry.tags.values_list('name', flat=True)),
        }
        return render(request, "journal/edit_journal.html", context)
    
    def post(self, request, entry_id):
        """Handle journal entry updates"""
        entry = get_object_or_404(JournalEntry, id=entry_id, user=request.user)
        
        try:
            title = request.POST.get('title', '').strip()
            content = request.POST.get('content', '')
            is_public = request.POST.get('is_public') == 'on'
            tag_names = request.POST.getlist('tags')
            
            if not title:
                messages.error(request, 'Title is required.')
                return self.get(request, entry_id)
            
            if not content:
                messages.error(request, 'Content is required.')
                return self.get(request, entry_id)
            
            # Parse and validate EditorJS content
            try:
                content_data = json.loads(content)
            except json.JSONDecodeError:
                messages.error(request, 'Invalid content format.')
                return self.get(request, entry_id)
            
            # Update the journal entry
            entry.title = title
            entry.content = content_data
            entry.is_public = is_public
            entry.save()
            
            # Update tags
            entry.tags.clear()
            for tag_name in tag_names:
                if tag_name.strip():
                    tag, created = Tag.objects.get_or_create(
                        user=request.user,
                        name=tag_name.strip()
                    )
                    entry.tags.add(tag)
            
            messages.success(request, f'Journal entry "{title}" updated successfully!')
            return redirect("journal:dashboard")
            
        except Exception as e:
            messages.error(request, f'Error updating journal entry: {str(e)}')
            return self.get(request, entry_id)


class JournalListView(LoginRequiredMixin, View):
    """
    View for listing all journal entries with filtering options.
    """
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
        return render(request, "journal/entry_list.html", context)


class JournalDetailView(LoginRequiredMixin, View):
    """
    View for displaying a single journal entry.
    """
    def get(self, request, entry_id):
        entry = get_object_or_404(JournalEntry, id=entry_id, user=request.user)
        
        context = {
            'entry': entry,
        }
        return render(request, "journal/entry_detail.html", context)


class EditJournalView(LoginRequiredMixin, View):
    """
    View for editing an existing journal entry with EditorJS support.
    """
    def get(self, request, entry_id):
        entry = get_object_or_404(JournalEntry, id=entry_id, user=request.user)
        tags = Tag.objects.filter(user=request.user).order_by('name')
        
        context = {
            'entry': entry,
            'available_tags': tags,
        }
        return render(request, "journal/edit_journal.html", context)

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
                json.loads(content)
            except json.JSONDecodeError:
                messages.error(request, "Invalid content format.")
                return redirect('journal:edit_entry', entry_id=entry_id)

            # Update entry
            entry.title = title
            entry.content = content
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


@method_decorator(csrf_exempt, name='dispatch')
class TagAutocompleteView(LoginRequiredMixin, View):
    """
    AJAX view for tag autocomplete functionality.
    """
    def get(self, request):
        query = request.GET.get('q', '').strip()
        
        if not query:
            return JsonResponse({'tags': []})
        
        tags = Tag.objects.filter(
            user=request.user,
            name__icontains=query
        ).values_list('name', flat=True)[:10]
        
        return JsonResponse({
            'tags': list(tags)
        })