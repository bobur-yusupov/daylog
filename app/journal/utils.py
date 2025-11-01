import secrets

def generate_share_token() -> str:
    """Generate a unique share token."""
    return secrets.token_urlsafe(32)
