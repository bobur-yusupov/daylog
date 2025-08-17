from django.db import models
from uuid import uuid4


class AbstractBaseModel(models.Model):
    """
    An abstract base model that provides common fields for all models.
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False, unique=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
