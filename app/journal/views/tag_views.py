from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView, DeleteView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy

from ..models import Tag


@method_decorator(csrf_exempt, name="dispatch")
class TagAutocompleteView(LoginRequiredMixin, View):
    """
    AJAX view for tag autocomplete functionality.
    """

    def get(self, request):
        query = request.GET.get("q", "").strip()

        if not query:
            return JsonResponse({"tags": []})

        tags = Tag.objects.filter(user=request.user, name__icontains=query).values_list(
            "name", flat=True
        )[:10]

        return JsonResponse({"tags": list(tags)})


class TagListView(LoginRequiredMixin, ListView):
    """
    View for displaying a list of tags.
    """

    model = Tag
    template_name = "journal/tag_list.html"
    context_object_name = "tags"

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)


class TagUpdateView(LoginRequiredMixin, UpdateView):
    """
    View for updating a tag.
    """

    model = Tag
    template_name = "journal/tag_form.html"
    fields = ["name"]
    success_url = reverse_lazy("journal:tag_list")

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)


class TagDeleteView(LoginRequiredMixin, DeleteView):
    """
    View for deleting a tag.
    """

    model = Tag
    template_name = "journal/tag_confirm_delete.html"
    success_url = reverse_lazy("journal:tag_list")

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)
