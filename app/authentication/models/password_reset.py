from django.db import models
from django.utils import timezone
from datetime import timedelta
import random
import string


class PasswordReset(models.Model):
    """
    Model to store OTP codes for password reset requests.

    This model handles the generation and validation of 6-digit OTP codes
    sent to users during the password reset process.
    """

    user = models.ForeignKey(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="password_resets",
        help_text="The user this password reset OTP belongs to",
    )
    otp_code = models.CharField(max_length=6, help_text="6-digit OTP code for password reset")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="When this OTP expires")
    is_used = models.BooleanField(
        default=False, help_text="Whether this OTP has been used for password reset"
    )
    attempts = models.IntegerField(
        default=0, help_text="Number of verification attempts made with this OTP"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Password Reset"
        verbose_name_plural = "Password Resets"

    def save(self, *args, **kwargs):
        if not self.otp_code:
            self.otp_code = self.generate_otp()
        if not self.expires_at:
            # Set expiry to 10 minutes from now (same as email verification)
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    @staticmethod
    def generate_otp() -> str:
        """
        Generate a 6-digit OTP code.

        Returns:
            str: A 6-digit numeric string
        """
        return "".join(random.choices(string.digits, k=6))

    @classmethod
    def create_for_user(cls, user):
        """
        Create a new password reset OTP for a user.
        Invalidates any existing unused OTPs for the user.

        Args:
            user: The user requesting password reset

        Returns:
            PasswordReset: The created password reset instance
        """
        # Mark any existing unused OTPs as used
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        # Create new OTP
        return cls.objects.create(user=user)

    def is_valid(self) -> bool:
        """
        Check if the OTP is still valid (not used, not expired, and under attempt limit).

        Returns:
            bool: True if OTP is valid, False otherwise
        """
        max_attempts = 5  # Same as email verification
        return (
            not self.is_used 
            and timezone.now() < self.expires_at 
            and self.attempts < max_attempts
        )

    def increment_attempts(self):
        """
        Increment the number of attempts for this OTP.
        """
        self.attempts += 1
        self.save(update_fields=["attempts"])

    def mark_as_used(self):
        """
        Mark this OTP as used.
        """
        self.is_used = True
        self.save(update_fields=["is_used"])

    def __str__(self):
        return f"Password reset OTP for {self.user.email} - {'Valid' if self.is_valid() else 'Invalid'}"