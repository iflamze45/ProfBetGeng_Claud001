import re
from typing import Optional, List, Dict, Any
from ..models import SportybetSelection, SportybetTicket

class RawTextParser:
    """
    Deterministic clipboard parser for raw SportyBet slips.
    Extracts structured data from unstructured text walls dumped from the clipboard.
    
    Zero tokens. Millisecond execution.
    """
    def __init__(self):
        # Odds are usually strictly formatted with decimal points (e.g., 1.50, 12.00)
        self.odds_pattern = re.compile(r'^\s*(\d+\.\d{2})\s*$')
        
        # Booking codes are usually 5-10 alphanumeric characters (often starting with BC)
        self.booking_code_pattern = re.compile(r'(?:Booking Code|Code)[\s:]*([a-zA-Z0-9]{5,10})|^(BC[a-zA-Z0-9]{3,8})$', re.IGNORECASE)
        
        # Detecting event names via the standard "Team A vs Team B" or "Team A - Team B"
        self.team_vs_pattern = re.compile(r'(.+?)\s+(?:v(?:s)?\.?|-)\s+(.+)', re.IGNORECASE)
        
        # Detecting dates like "02/10 15:30" or "Oct 02 15:30"
        self.date_pattern = re.compile(r'(\d{2}/\d{2}(?:/\d{4})?\s+\d{2}:\d{2}|[A-Za-z]{3}\s+\d{2}\s+\d{2}:\d{2})')

    def parse(self, raw_text: str) -> SportybetTicket:
        """
        Parses a multiline string and returns a structured SportybetTicket.
        Assumes a repeating block structure common in copy-pasted web content.
        """
        # Clean and filter empty lines
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        
        # 1. Extract Booking Code if present
        booking_code = "UNKNOWN_BC"
        for line in lines[:10]: # Usually at the top
            bc_match = self.booking_code_pattern.search(line)
            if bc_match:
                # Group 1 is for "Booking Code: XYZ", Group 2 is for standalone "BCXYZ"
                booking_code = (bc_match.group(1) or bc_match.group(2)).upper()
                break
                
        selections: List[SportybetSelection] = []
        current_sel: Dict[str, Any] = {}
        
        # 2. Iterate through lines to build selection blocks
        # A typical block: Event Name -> Date -> Market -> Pick -> Odds
        for line in lines:
            
            # End of an item block is usually the Odds number
            odds_match = self.odds_pattern.match(line)
            if odds_match:
                current_sel['odds'] = float(odds_match.group(1))
                
                # We have hit the odds. Package what we have so far.
                if 'event_name' in current_sel and 'pick' in current_sel:
                    selections.append(SportybetSelection(
                        event_id=f"evt_{len(selections)+1}",
                        event_name=current_sel.get('event_name', 'Unknown Event'),
                        market=current_sel.get('market', 'Unknown Market'),
                        pick=current_sel.get('pick', 'Unknown Pick'),
                        odds=current_sel['odds'],
                        kick_off=current_sel.get('kick_off')
                    ))
                
                # Reset for the next leg
                current_sel = {}
                continue
                
            # Is it an event line?
            if self.team_vs_pattern.search(line):
                current_sel['event_name'] = line
                continue
                
            # Is it a date/time line?
            if self.date_pattern.search(line):
                current_sel['kick_off'] = line
                continue
                
            # If we've found an event name, the remaining strings are usually market and pick
            if 'event_name' in current_sel:
                if 'market' not in current_sel:
                    current_sel['market'] = line
                else:
                    # If market is filled, subsequent unclassified text before the odds is usually the pick
                    # Sometimes picks span multiple lines. We'll overwrite to get the most immediate line to the odds
                    current_sel['pick'] = line
                    
        # If the ticket had a total stake or total odds at the bottom, we could parse that too,
        # but for now we focus on extracting individual legs safely.
        
        return SportybetTicket(
            booking_code=booking_code,
            selections=selections
        )
