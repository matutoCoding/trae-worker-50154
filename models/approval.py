import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from db.database import Base

class ApprovalNode(enum.Enum):
    ADVISOR = 'advisor'
    FACILITY_MANAGER = 'facility_manager'
    ETHICS_COMMITTEE = 'ethics_committee'

class ApprovalStatus(enum.Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

class Approval(Base):
    __tablename__ = 'approvals'
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False)
    approver_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    node = Column(Enum(ApprovalNode), nullable=False)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    comments = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    booking = relationship('Booking', back_populates='approvals')
    approver = relationship('User', back_populates='approvals')
    
    def __repr__(self):
        return f'<Approval {self.node.value}: {self.status.value}>'
