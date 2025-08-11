from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from common.models import AbstractBaseModel

class Tag(AbstractBaseModel):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')
        ordering = ['-created_at']
        unique_together = [['user', 'name']]

    def __str__(self) -> str:
        return self.name

class JournalEntry(AbstractBaseModel):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.JSONField()
    is_public = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, blank=True)

    class Meta:
        verbose_name = _('Journal Entry')
        verbose_name_plural = _('Journal Entries')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.title} by {self.user.username}"