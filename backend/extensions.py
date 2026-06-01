from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Shared limiter instance for the app and blueprints
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
