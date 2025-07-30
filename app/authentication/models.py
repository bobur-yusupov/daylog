from django.contrib.auth.models import AbstractUser
from django.db import models
from uuid import uuid4


class User(AbstractUser):
    """
    Custom User model that extends Django's AbstractUser.
    Uses UUID as primary key and adds created_at/updated_at fields.
    """
    # Override the default id field with UUID
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.username

