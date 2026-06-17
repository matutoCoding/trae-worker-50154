import enum
from sqlalchemy import Column, Integer, String, Enum, Boolean
from sqlalchemy.orm import relationship
from db.database import Base

class CageStatus(enum.Enum):
    AVAILABLE = 'available'
    OCCUPIED = 'occupied'
    MAINTENANCE = 'maintenance'

class Cage(Base):
    __tablename__ = 'cages'
    
    id = Column(Integer, primary_key=True, index=True)
    cage_code = Column(String(50), unique=True, index=True, nullable=False)
    room = Column(String(100), nullable=False)
    capacity = Column(Integer, nullable=False)
    animal_type = Column(String(50), nullable=False)
    status = Column(Enum(CageStatus), default=CageStatus.AVAILABLE)
    description = Column(String(500))
    
    bookings = relationship('Booking', back_populates='cage')
    
    def __repr__(self):
        return f'<Cage {self.cage_code} ({self.animal_type})>'
