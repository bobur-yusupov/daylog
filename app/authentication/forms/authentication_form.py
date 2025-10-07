from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from authentication.mixins import BootstrapFormMixin


class CustomAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    """
    Custom login form with Bootstrap styling.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styling()

        self.fields["username"].widget.attrs.update({"placeholder": _("Username")})
        self.fields["password"].widget.attrs.update({"placeholder": _("Password")})
