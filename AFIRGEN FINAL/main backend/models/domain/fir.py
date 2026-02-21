"""
FIR (First Information Report) domain model.

Represents the structure and data of a First Information Report.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class FIRData:
    """
    FIR data model.
    
    Represents all the information contained in a First Information Report.
    """
    # FIR Identification
    fir_number: str
    police_station: str
    district: str
    state: str
    year: str
    date: str
    information_received: str
    
    # Complainant Details
    complainant_name: str
    date_of_birth: str
    nationality: str
    father_husband_name: str
    complainant_address: str
    complainant_contact: str
    
    # Incident Details
    date_from: str
    date_to: str
    place_of_occurrence: str
    address_of_occurrence: str
    incident_description: str
    summary: str
    
    # Optional Complainant Details
    passport_number: Optional[str] = ""
    occupation: Optional[str] = ""
    
    # Optional Incident Details
    time_from: Optional[str] = ""
    time_to: Optional[str] = ""
    reasons_for_delayed_reporting: Optional[str] = "No delay reported"
    
    # Legal Provisions
    acts: Optional[List[str]] = None
    sections: Optional[List[str]] = None
    
    # Suspect Details
    suspect_details: str = "Unknown"
    
    # Investigation Details
    io_name: str = "Inspector Rajesh Kumar"
    io_rank: str = "Inspector"
    witnesses: Optional[str] = ""
    action_taken: Optional[str] = ""
    investigation_status: str = "Preliminary investigation started"
    date_of_despatch: str = ""
    
    def __post_init__(self) -> None:
        """Initialize default values for lists"""
        if self.acts is None:
            self.acts = ['IPC 379 (Theft)', 'IPC 34 (Common Intention)', 'IPC 506 (Criminal Intimidation)']
        if self.sections is None:
            self.sections = ['IPC 379', 'IPC 34', 'IPC 506']
    
    def to_dict(self) -> dict:
        """Convert FIR data to dictionary for template rendering"""
        return {
            'fir_number': self.fir_number,
            'police_station': self.police_station,
            'district': self.district,
            'state': self.state,
            'year': self.year,
            'date': self.date,
            'Information recieved': self.information_received,
            
            'complainant_name': self.complainant_name,
            'dateofbirth': self.date_of_birth,
            'Nationality': self.nationality,
            'father_name/husband_name': self.father_husband_name,
            'complainant_address': self.complainant_address,
            'complainant_contact': self.complainant_contact,
            'passport_number': self.passport_number,
            'occupation': self.occupation,
            
            'Date from': self.date_from,
            'Date to': self.date_to,
            'Time from': self.time_from,
            'Time to': self.time_to,
            'Place of Occurrence': self.place_of_occurrence,
            'Address of Occurrence': self.address_of_occurrence,
            'incident_description': self.incident_description,
            'reasons_for_delayed_reporting': self.reasons_for_delayed_reporting,
            'summary': self.summary,
            
            'Acts': self.acts,
            'Sections': self.sections,
            
            'Suspect_details': self.suspect_details,
            
            'io_name': self.io_name,
            'io_rank': self.io_rank,
            'witnesses': self.witnesses,
            'action_taken': self.action_taken,
            'investigation_status': self.investigation_status,
            'date_of_despatch': self.date_of_despatch,
        }
    
    @classmethod
    def from_session_state(cls, session_state: dict) -> "FIRData":
        """Create FIR data from session state"""
        now = datetime.now()
        present_date = now.strftime("%d %B %Y")
        present_time = now.strftime("%H:%M:%S")
        
        return cls(
            fir_number=session_state.get('fir_number', 'N/A'),
            police_station='Central Police Station',
            district='Metro City',
            state='State of Example',
            year=present_date.split()[-1],
            date=present_date,
            information_received=f"{present_date} at {present_time}",
            
            complainant_name=session_state.get('complainant_name', 'John Doe'),
            date_of_birth=session_state.get('date_of_birth', '01 January 1990'),
            nationality=session_state.get('nationality', 'Indian'),
            father_husband_name=session_state.get('father_name', 'Richard Doe'),
            complainant_address=session_state.get('complainant_address', '123 Main St.'),
            complainant_contact=session_state.get('complainant_contact', '9876543210'),
            passport_number=session_state.get('passport_number', ''),
            occupation=session_state.get('occupation', ''),
            
            date_from=session_state.get('date_from', present_date),
            date_to=session_state.get('date_to', present_date),
            time_from=session_state.get('time_from', ''),
            time_to=session_state.get('time_to', ''),
            place_of_occurrence=session_state.get('occurrence_place', 'Central Park, Metro City'),
            address_of_occurrence=session_state.get('occurrence_address', 'Near the fountain area, Central Park, Metro City'),
            incident_description=session_state.get('incident_description', ''),
            reasons_for_delayed_reporting=session_state.get('delay_reason', 'No delay reported'),
            summary=session_state.get('summary', ''),
            
            acts=session_state.get('Acts', ['IPC 379 (Theft)', 'IPC 34 (Common Intention)', 'IPC 506 (Criminal Intimidation)']),
            sections=session_state.get('Sections', ['IPC 379', 'IPC 34', 'IPC 506']),
            
            suspect_details=session_state.get('suspect_details', 'Unknown'),
            
            io_name=session_state.get('io_name', 'Inspector Rajesh Kumar'),
            io_rank=session_state.get('io_rank', 'Inspector'),
            witnesses=session_state.get('witnesses', ''),
            action_taken=session_state.get('action_taken', ''),
            investigation_status=session_state.get('investigation_status', 'Preliminary investigation started'),
            date_of_despatch=present_date,
        )
