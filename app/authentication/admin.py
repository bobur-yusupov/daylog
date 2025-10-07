from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from authentication.models import EmailVerification

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin configuration.
    """

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_email_verified",
        "is_staff",
        "created_at",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "is_email_verified", "created_at")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("-created_at",)

    # Add email verification and timestamps to the fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Email Verification", {"fields": ("is_email_verified",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at", "id")


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    """
    Admin configuration for EmailVerification model.
    """
    
    list_display = (
        "user",
        "otp_code",
        "created_at",
        "expires_at",
        "is_used",
        "is_expired_display",
        "is_valid_display",
    )
    
    list_filter = (
        "is_used",
        "created_at",
        "expires_at",
    )
    
    search_fields = (
        "user__username",
        "user__email",
        "otp_code",
    )
    
    ordering = ("-created_at",)
    
    readonly_fields = (
        "created_at",
        "is_expired_display",
        "is_valid_display",
    )
    
    def is_expired_display(self, obj):
        """Display if the OTP is expired"""
        return obj.is_expired()
    is_expired_display.short_description = "Is Expired"
    is_expired_display.boolean = True
    
    def is_valid_display(self, obj):
        """Display if the OTP is valid"""
        return obj.is_valid()
    is_valid_display.short_description = "Is Valid"
    is_valid_display.boolean = True
    
    def has_add_permission(self, request):
        """Prevent manual creation of OTP codes through admin"""
        return False
    
    def get_readonly_fields(self, request, obj=None):
        """Make most fields readonly for existing objects"""
        if obj:  # Editing existing object
            return self.readonly_fields + ("user", "otp_code", "expires_at")
        return self.readonly_fields
