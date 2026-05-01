import logging
from typing import Dict, List, Optional
from datetime import datetime
from ..models import SocialTicket, MirrorAction

logger = logging.getLogger("pbg.mirror_protocol")

class MirrorProtocol:
    """
    Manages the public 'Social Intelligence' feed where users publish 
    verified tickets to be mirrored by the collective bankroll.
    """
    
    def __init__(self):
        self.broadcast_feed: list[SocialTicket] = []
        self.mirror_history: Dict[str, list[MirrorAction]] = {}

    def publish_signal(self, ticket: SocialTicket):
        """Adds a verified signal to the sovereign community feed."""
        # Check for duplicates or spam
        self.broadcast_feed.insert(0, ticket)
        if len(self.broadcast_feed) > 100:
            self.broadcast_feed.pop()
        logger.info(f"SIGNAL_BROADCAST: Ticket {ticket.ticket_id} by {ticket.username}")

    def mirror_signal(self, action: MirrorAction):
        """Records a mirror event and updates ticket metadata."""
        if action.target_ticket_id not in self.mirror_history:
            self.mirror_history[action.target_ticket_id] = []
        
        self.mirror_history[action.target_ticket_id].append(action)
        
        # Increment counter in feed
        for ticket in self.broadcast_feed:
            if ticket.ticket_id == action.target_ticket_id:
                ticket.mirrors_count += 1
                break
        
        logger.info(f"SIGNAL_MIRRORED: {action.source_username} following {action.target_ticket_id}")

# Singleton
mirror_hub = MirrorProtocol()
