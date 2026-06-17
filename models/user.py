import enum
from sqlalchemy import Column, Integer, String, Enum, Boolean
from sqlalchemy.orm import relationship
from db.database import Base

class UserRole(enum.Enum):
    RESEARCHER = 'researcher'
    ADVISOR = 'advisor'
    FACILITY_MANAGER = 'facility_manager'
    ETHICS_COMMITTEE = 'ethics_committee'

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    password = Column(String(100), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    
    bookings = relationship('Booking', back_populates='researcher')
    approvals = relationship('Approval', back_populates='approver')
    
    def __repr__(self):
        return f'<User {self.name} ({self.role.value})>'
