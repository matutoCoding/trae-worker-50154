from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from db.database import Base

class AccessRegistration(Base):
    __tablename__ = 'access_registrations'
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False)
    access_code = Column(String(50), unique=True, nullable=False)
    registered_by = Column(String(100), nullable=False)
    registered_at = Column(DateTime, default=datetime.now)
    entry_time = Column(DateTime)
    exit_time = Column(DateTime)
    remarks = Column(Text)
    is_active = Column(Boolean, default=True)
    
    booking = relationship('Booking', back_populates='access_registration')
    
    def __repr__(self):
        return f'<Access {self.access_code}>'
