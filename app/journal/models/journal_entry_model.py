from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from common.models import AbstractBaseModel
from .tag_model import Tag
from journal import utils


class JournalEntry(AbstractBaseModel):
    user = models.ForeignKey(
        verbose_name=_("User"),
        to=get_user_model(), 
        on_delete=models.CASCADE, 
        db_index=True,
        help_text=_("The user who created this journal entry."),
    )
    title = models.CharField(
        verbose_name=_("Title"),
        max_length=255,
        help_text=_("A short descriptive title for this entry."),
    )
    content = models.JSONField(
        verbose_name=_("Content"),
        help_text=_("The main content of the journal entry in JSON format."),
    )
    is_public = models.BooleanField(
        verbose_name=_("Is Public"),
        default=False,
        db_index=True,
        help_text=_("Whether this entry is public or private."),
    )
    share_token = models.CharField(
        verbose_name=_("Share Token"),
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Unique token for sharing this entry via a link."),
    )
    tags = models.ManyToManyField(
        to=Tag,
        verbose_name=_("Tags"),
        blank=True,
        help_text=_("Tags associated with this journal entry."),
    )

    class Meta:
        verbose_name = _("Journal Entry")
        verbose_name_plural = _("Journal Entries")
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["is_public"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} by {self.user.username}"

    def generate_share_token(self):
        """Generate a unique share token for this entry."""
        if not self.share_token:
            self.share_token = utils.generate_share_token()
            self.save(update_fields=["share_token"])
        return self.share_token

    def revoke_share_token(self) -> None:
        """Revoke the share token for this entry."""
        self.share_token = None
        self.save(update_fields=["share_token"])
