from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from ..models import Tag


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
