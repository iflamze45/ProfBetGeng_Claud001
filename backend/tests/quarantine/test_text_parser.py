import pytest
from backend.services.text_parser import RawTextParser

def test_raw_text_parser():
    sample_text = """
    Booking Code: BC123XYZ

    Arsenal vs Chelsea
    02/10 15:30
    1X2
    Arsenal
    1.75
    
    Manchester U vs Man City
    02/11 18:00
    Over/Under
    Over 2.5
    1.80
    """
    
    parser = RawTextParser()
    ticket = parser.parse(sample_text)
    
    assert ticket.booking_code == "BC123XYZ"
    assert len(ticket.selections) == 2
    
    sel1 = ticket.selections[0]
    assert sel1.event_name.strip() == "Arsenal vs Chelsea"
    assert sel1.market.strip() == "1X2"
    assert sel1.pick.strip() == "Arsenal"
    assert sel1.odds == 1.75
    assert sel1.kick_off == "02/10 15:30"
    
    sel2 = ticket.selections[1]
    assert sel2.event_name.strip() == "Manchester U vs Man City"
    assert sel2.market.strip() == "Over/Under"
    assert sel2.pick.strip() == "Over 2.5"
    assert sel2.odds == 1.80
    assert sel2.kick_off == "02/11 18:00"

def test_raw_text_parser_messy_input():
    sample_text = """
    BC29XVG
    some random text 
    Real Madrid - Barcelona
    1X2
    Real Madrid
    2.10
    """
    
    parser = RawTextParser()
    ticket = parser.parse(sample_text)
    
    assert ticket.booking_code == "BC29XVG"
    assert len(ticket.selections) == 1
    
    sel1 = ticket.selections[0]
    assert sel1.event_name.strip() == "Real Madrid - Barcelona"
    assert sel1.market.strip() == "1X2"
    assert sel1.pick.strip() == "Real Madrid"
    assert sel1.odds == 2.10
