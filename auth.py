"""
Authentication module for MarketApp API.

Implements HTTP Basic Authentication using credentials from environment variables
stored in Kubernetes secrets.
"""

import os
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash, generate_password_hash
import logging

logger = logging.getLogger(__name__)

auth = HTTPBasicAuth()


# Load credentials from environment variables
API_USERNAME = os.environ.get("API_USERNAME")
API_PASSWORD = os.environ.get("API_PASSWORD")

# For production, you can store hashed passwords
# This allows you to store pre-hashed passwords in secrets
API_PASSWORD_HASH = os.environ.get("API_PASSWORD_HASH")


@auth.verify_password
def verify_password(username, password):
    """
    Verify username and password for API access.
    
    Supports two modes:
    1. Plain password comparison (API_PASSWORD env var)
    2. Hashed password comparison (API_PASSWORD_HASH env var)
    
    Args:
        username: Username provided in the request
        password: Password provided in the request
    
    Returns:
        True if authentication succeeds, False otherwise
    """
    if not API_USERNAME:
        logger.warning("API_USERNAME not configured. Authentication disabled!")
        return False
    
    if username != API_USERNAME:
        logger.warning(f"Authentication failed: Invalid username '{username}'")
        return False
    
    # Check hashed password first (more secure)
    if API_PASSWORD_HASH:
        if check_password_hash(API_PASSWORD_HASH, password):
            logger.info(f"User '{username}' authenticated successfully (hashed)")
            return True
        else:
            logger.warning(f"Authentication failed: Invalid password for user '{username}'")
            return False
    
    # Fall back to plain password (simpler but less secure)
    if API_PASSWORD:
        if password == API_PASSWORD:
            logger.info(f"User '{username}' authenticated successfully (plain)")
            return True
        else:
            logger.warning(f"Authentication failed: Invalid password for user '{username}'")
            return False
    
    logger.error("Neither API_PASSWORD nor API_PASSWORD_HASH is configured!")
    return False


@auth.error_handler
def auth_error(status):
    """
    Custom error handler for authentication failures.
    
    Returns:
        JSON response with error message
    """
    return {
        "error": "Unauthorized",
        "message": "Authentication required. Please provide valid credentials.",
        "status": status
    }, status


def is_auth_configured():
    """
    Check if authentication is properly configured.
    
    Returns:
        True if auth credentials are set, False otherwise
    """
    return bool(API_USERNAME and (API_PASSWORD or API_PASSWORD_HASH))


def get_password_hash(password):
    """
    Generate a password hash for storing in Kubernetes secrets.
    
    Usage:
        python -c "from auth import get_password_hash; print(get_password_hash('your_password'))"
    
    Args:
        password: Plain text password
    
    Returns:
        Password hash string
    """
    return generate_password_hash(password)
