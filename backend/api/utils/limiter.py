"""
Shared rate limiter instance.

All route modules should import `limiter` from here instead of creating
their own instances, so that rate-limit state is shared and consistent.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
