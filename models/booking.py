import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from db.database import Base

class BookingStatus(enum.Enum):
    DRAFT = 'draft'
    PENDING_ADVISOR = 'pending_advisor'
    PENDING_FACILITY = 'pending_facility'
    PENDING_ETHICS = 'pending_ethics'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    CANCELLED = 'cancelled'
    COMPLETED = 'completed'

class Booking(Base):
    __tablename__ = 'bookings'
    
    id = Column(Integer, primary_key=True, index=True)
    cage_id = Column(Integer, ForeignKey('cages.id'), nullable=False)
    researcher_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    project_name = Column(String(200), nullable=False)
    animal_count = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    purpose = Column(Text, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.DRAFT)
    reject_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    cage = relationship('Cage', back_populates='bookings')
    researcher = relationship('User', back_populates='bookings')
    approvals = relationship('Approval', back_populates='booking', order_by='Approval.created_at')
    access_registration = relationship('AccessRegistration', back_populates='booking', uselist=False)
    
    def __repr__(self):
        return f'<Booking #{self.id} {self.status.value}>'
