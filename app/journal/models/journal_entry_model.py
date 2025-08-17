from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from common.models import AbstractBaseModel
from .tag_model import Tag


class JournalEntry(AbstractBaseModel):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, db_index=True)
    title = models.CharField(
        verbose_name=_("Title"),
        max_length=255,
        help_text=_("A short descriptive title for this entry."),
    )
    content = models.JSONField()
    is_public = models.BooleanField(default=False, db_index=True)
    tags = models.ManyToManyField(Tag, blank=True)

    class Meta:
        verbose_name = _("Journal Entry")
        verbose_name_plural = _("Journal Entries")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} by {self.user.username}"
