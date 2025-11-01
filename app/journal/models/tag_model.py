from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from common.models import AbstractBaseModel


class Tag(AbstractBaseModel):
    user = models.ForeignKey(
        to=get_user_model(), 
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        help_text=_("The user who created this tag."),
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("Name"),
        help_text=_("A short descriptive name for this tag."),
    )

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_user_tag")
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()

        if self.name is None:
            raise ValidationError({"name": _("Tag name cannot be empty.")})
        
        self.name = self.name.strip().lower()

        if not self.name:
            raise ValidationError({"name": _("Tag name cannot be empty.")})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
