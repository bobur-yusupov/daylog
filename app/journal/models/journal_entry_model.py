from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
import secrets

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
    share_token = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Unique token for sharing this entry via a link."),
    )
    tags = models.ManyToManyField(Tag, blank=True)

    class Meta:
        verbose_name = _("Journal Entry")
        verbose_name_plural = _("Journal Entries")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} by {self.user.username}"

    def generate_share_token(self):
        """Generate a unique share token for this entry."""
        if not self.share_token:
            self.share_token = secrets.token_urlsafe(32)
            self.save(update_fields=["share_token"])
        return self.share_token

    def revoke_share_token(self):
        """Revoke the share token for this entry."""
        self.share_token = None
        self.save(update_fields=["share_token"])
