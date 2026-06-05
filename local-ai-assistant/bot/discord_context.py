import logging
from typing import List, Set

logger = logging.getLogger(__name__)

class DiscordContextManager:
    def __init__(self, allowed_channels: List[str] = None, admin_users: List[str] = None):
        self.allowed_channels: Set[str] = set(allowed_channels) if allowed_channels else set()
        self.admin_users: Set[str] = set(admin_users) if admin_users else set()
        # Ensure that no multiple requests are being processed at the same time for the same user
        self.active_requests: Set[str] = set()

    def is_channel_allowed(self, channel_id: str) -> bool:
        if not self.allowed_channels or "" in self.allowed_channels:
            return True # Allow all if not specified
        return str(channel_id) in self.allowed_channels

    def is_admin(self, user_id: str) -> bool:
        return str(user_id) in self.admin_users

    def add_active_request(self, user_id: str) -> bool:
        """Returns True if request was added, False if user already has an active request."""
        uid_str = str(user_id)
        if uid_str in self.active_requests:
            return False
        self.active_requests.add(uid_str)
        return True

    def remove_active_request(self, user_id: str):
        uid_str = str(user_id)
        if uid_str in self.active_requests:
            self.active_requests.remove(uid_str)
