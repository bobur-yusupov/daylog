from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class ProfileForm(forms.ModelForm):
    """
    Form for updating user profile information.
    """

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
