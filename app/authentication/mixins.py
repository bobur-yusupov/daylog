from django.http import HttpRequest
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

class AnonymousRequiredMixin:
    """
    Mixin to handle anonymous user functionality.
    Provides methods to check if the user is anonymous and to get the user's name.
    """
    redirect_url = '/'

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        """
        Redirects authenticated users to the specified redirect URL.
        """
        if not request.user.is_anonymous:
            return redirect(self.redirect_url)
        return super().dispatch(request, *args, **kwargs)


class BootstrapFormMixin:
    """
    Mixin to add Bootstrap styling to form fields.
    """
    def apply_bootstrap_styling(self):
        """Apply Bootstrap form-control class to all form fields."""
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})