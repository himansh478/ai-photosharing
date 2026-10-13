from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Shared limiter instance for the app and blueprints.
# Limits are per client IP. Guests at one venue often share a single Wi-Fi address,
# so the limits are sized for a crowd behind one IP, not for a single person.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["600 per minute"],
    headers_enabled=True,
)
