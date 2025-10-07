from django.db import models
from django.utils import timezone
from datetime import timedelta
import random
import string


class EmailVerification(models.Model):
    """
    Model to store OTP codes for email verification.

    This model handles the generation and validation of 6-digit OTP codes
    sent to users during the email verification process.
    """

    user = models.ForeignKey(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="email_verifications",
        help_text="The user this OTP belongs to",
    )
    otp_code = models.CharField(max_length=6, help_text="6-digit OTP code")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="When this OTP expires")
    is_used = models.BooleanField(
        default=False, help_text="Whether this OTP has been used for verification"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Email Verification"
        verbose_name_plural = "Email Verifications"

    def save(self, *args, **kwargs):
        if not self.otp_code:
            self.otp_code = self.generate_otp()
        if not self.expires_at:
            # Set expiry to 10 minutes from now
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

    def is_expired(self) -> bool:
        """
        Check if the OTP has expired.

        Returns:
            bool: True if the OTP has expired, False otherwise
        """
        return timezone.now() > self.expires_at

    def is_valid(self) -> bool:
        """
        Check if the OTP is valid (not used and not expired).

        Returns:
            bool: True if the OTP is valid, False otherwise
        """
        return not self.is_used and not self.is_expired()

    def mark_as_used(self):
        self.is_used = True
        self.save(update_fields=["is_used"])

    @classmethod
    def create_for_user(cls, user) -> "EmailVerification":
        """
        Create a new OTP verification for a user.

        Args:
            user: The user to create the OTP for

        Returns:
            EmailVerification: The created verification instance
        """
        return cls.objects.create(user=user)

    @classmethod
    def get_valid_otp(cls, user, otp_code):
        """
        Get a valid OTP for a user and code.

        Args:
            user: The user to check
            otp_code: The OTP code to validate

        Returns:
            EmailVerification or None: The valid OTP instance or None if not found/invalid
        """
        try:
            verification = cls.objects.filter(
                user=user, otp_code=otp_code, is_used=False
            ).first()

            if verification and verification.is_valid():
                return verification
            return None
        except cls.DoesNotExist:
            return None

    def __str__(self):
        status = (
            "Used" if self.is_used else ("Expired" if self.is_expired() else "Valid")
        )
        return f"OTP for {self.user.username} - {self.otp_code} ({status})"
