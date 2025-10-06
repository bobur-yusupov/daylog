# Email Configuration Setup Guide

## Overview
This guide explains how to set up email functionality for the DayLog application, particularly for sending welcome emails during user registration.

## The Issue
The SMTP authentication error `(530, b'5.7.0 Authentication Required')` occurs when Gmail's SMTP server rejects the authentication attempt. This typically happens when:

1. Environment variables are incorrectly named
2. Gmail App Passwords are not being used
3. SMTP settings are misconfigured

## Solution

### 1. Environment Variable Configuration
The `.env` file has been updated with the correct variable names that match Django's expected settings:

```properties
# Email Configuration
EMAIL_HOST_PASSWORD="your-app-password-here"
EMAIL_HOST="smtp.gmail.com"
EMAIL_HOST_USER="your-email@gmail.com"
EMAIL_PORT=587
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL="your-email@gmail.com"
```

**Key Changes Made:**
- Changed `EMAIL_PASSWORD` to `EMAIL_HOST_PASSWORD` to match Django's expected setting name
- Removed quotes from boolean values (Django handles the string-to-boolean conversion)

### 2. Gmail App Password Setup

For Gmail SMTP to work, you need to use an **App Password**, not your regular Gmail password.

#### Steps to Generate Gmail App Password:

1. **Enable 2-Factor Authentication** on your Gmail account (required for App Passwords)
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Enable 2-Step Verification if not already enabled

2. **Generate App Password:**
   - Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
   - Select "Mail" as the app type
   - Copy the generated 16-character password (it will look like: `abcd efgh ijkl mnop`)

3. **Update .env file:**
   ```properties
   EMAIL_HOST_PASSWORD="abcd efgh ijkl mnop"  # Your generated app password
   EMAIL_HOST_USER="your-email@gmail.com"     # Your Gmail address
   ```

### 3. Django Settings
The Django settings in `config/settings/base.py` are configured to read these environment variables:

```python
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "webmaster@localhost")
```

### 4. Code Improvements
The `RegisterView` has been updated with:

- **Error handling:** Prevents registration failure if email sending fails
- **Proper configuration usage:** Uses `settings.DEFAULT_FROM_EMAIL` instead of hardcoded email
- **Logging:** Records email sending success/failure for debugging

## Alternative Email Solutions

If Gmail SMTP continues to cause issues, consider these alternatives:

### 1. Django Console Backend (Development Only)
For development, you can use Django's console backend to print emails to the console:

```python
# In config/settings/dev.py
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

### 2. File Backend (Development Only)
Save emails to files instead of sending them:

```python
# In config/settings/dev.py
EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = BASE_DIR / "tmp" / "emails"
```

### 3. Other Email Services
Consider using dedicated email services:

#### SendGrid
```python
# Install: pip install sendgrid
EMAIL_BACKEND = "sendgrid_backend.SendgridBackend"
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
```

#### Mailgun
```python
# Install: pip install django-mailgun
EMAIL_BACKEND = "django_mailgun.MailgunBackend"
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_SENDER_DOMAIN = os.getenv("MAILGUN_SENDER_DOMAIN")
```

## Testing Email Configuration

### 1. Django Shell Test
```python
python manage.py shell

from django.core.mail import send_mail
from django.conf import settings

try:
    send_mail(
        'Test Email',
        'This is a test email from DayLog.',
        settings.DEFAULT_FROM_EMAIL,
        ['test@example.com'],
        fail_silently=False,
    )
    print("Email sent successfully!")
except Exception as e:
    print(f"Email failed: {e}")
```

### 2. Check Django Settings
```python
python manage.py shell

from django.conf import settings
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
# Don't print EMAIL_HOST_PASSWORD for security reasons
print(f"EMAIL_HOST_PASSWORD is set: {bool(settings.EMAIL_HOST_PASSWORD)}")
```

## Security Considerations

1. **Never commit `.env` files** - They contain sensitive credentials
2. **Use App Passwords** - Never use your actual Gmail password
3. **Rotate credentials** - Regenerate app passwords periodically
4. **Environment-specific settings** - Use different credentials for development/production

## Troubleshooting

### Common Issues:

1. **"Authentication Required" Error**
   - Verify you're using an App Password, not regular password
   - Check that 2FA is enabled on Gmail
   - Ensure EMAIL_HOST_PASSWORD matches the app password exactly

2. **"SMTPServerDisconnected" Error**
   - Check network connectivity
   - Verify EMAIL_HOST and EMAIL_PORT are correct
   - Ensure EMAIL_USE_TLS is True for Gmail

3. **"SMTPRecipientsRefused" Error**
   - Verify the recipient email address is valid
   - Check if sender email is properly configured

### Debug Steps:

1. Check environment variables are loaded:
   ```python
   import os
   print(os.getenv("EMAIL_HOST_PASSWORD"))  # Should not be None
   ```

2. Test SMTP connection manually:
   ```python
   import smtplib
   server = smtplib.SMTP('smtp.gmail.com', 587)
   server.starttls()
   server.login('your-email@gmail.com', 'your-app-password')
   server.quit()
   print("SMTP connection successful!")
   ```

## Production Deployment

For production:

1. Use environment variables specific to your hosting platform
2. Consider using managed email services (SendGrid, SES, etc.)
3. Implement proper error monitoring and logging
4. Set up email delivery monitoring and bounce handling

## Next Steps

After fixing the SMTP configuration:

1. Test user registration with email sending
2. Monitor application logs for email-related errors
3. Consider implementing email templates for better formatting
4. Add email verification for new user accounts