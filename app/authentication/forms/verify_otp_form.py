from django import forms
from django.utils.translation import gettext_lazy as _
from authentication.mixins import BootstrapFormMixin


class VerifyOTPForm(BootstrapFormMixin, forms.Form):
    otp_code = forms.CharField(
        label=_("Verification Code"),
        max_length=6,
        widget=forms.TextInput(attrs={"placeholder": _("Enter the 6-digit code")}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styling()

    def clean_otp_code(self):
        otp = self.cleaned_data.get("otp_code")
        if not otp.isdigit() or len(otp) != 6:
            raise forms.ValidationError(_("Please enter a valid 6-digit code."))
        return otp
