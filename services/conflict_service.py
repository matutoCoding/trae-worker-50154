from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy import and_, or_
from db.database import SessionLocal
from models.booking import Booking, BookingStatus
from models.cage import Cage

class ConflictService:
    @staticmethod
    def check_time_overlap(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
        return start1 < end2 and start2 < end1

    @staticmethod
    def check_cage_conflict(cage_id: int, start_time: datetime, end_time: datetime, exclude_booking_id: Optional[int] = None) -> List[Booking]:
        db = SessionLocal()
        try:
            query = db.query(Booking).filter(
                Booking.cage_id == cage_id,
                Booking.status.notin_([BookingStatus.REJECTED, BookingStatus.CANCELLED]),
                or_(
                    and_(Booking.start_time < end_time, Booking.end_time > start_time)
                )
            )
            
            if exclude_booking_id:
                query = query.filter(Booking.id != exclude_booking_id)
            
            conflicts = query.all()
            return conflicts
        finally:
            db.close()

    @staticmethod
    def validate_booking(cage_id: int, start_time: datetime, end_time: datetime, exclude_booking_id: Optional[int] = None) -> Tuple[bool, List[Booking], str]:
        if start_time >= end_time:
            return False, [], "开始时间必须早于结束时间"
        
        if start_time < datetime.now():
            return False, [], "不能预约过去的时间段"
        
        conflicts = ConflictService.check_cage_conflict(cage_id, start_time, end_time, exclude_booking_id)
        
        if conflicts:
            conflict_info = "; ".join([
                f"预约#{b.id} ({b.start_time.strftime('%Y-%m-%d %H:%M')} - {b.end_time.strftime('%Y-%m-%d %H:%M')})"
                for b in conflicts
            ])
            return False, conflicts, f"时段冲突：{conflict_info}"
        
        return True, [], "时段可用"

    @staticmethod
    def get_cage_bookings_in_range(cage_id: int, start_date: datetime, end_date: datetime) -> List[Booking]:
        db = SessionLocal()
        try:
            bookings = db.query(Booking).filter(
                Booking.cage_id == cage_id,
                Booking.status.notin_([BookingStatus.REJECTED, BookingStatus.CANCELLED]),
                Booking.start_time < end_date,
                Booking.end_time > start_date
            ).all()
            return bookings
        finally:
            db.close()

    @staticmethod
    def get_available_cages(start_time: datetime, end_time: datetime, animal_type: Optional[str] = None) -> List[Cage]:
        db = SessionLocal()
        try:
            query = db.query(Cage)
            
            if animal_type:
                query = query.filter(Cage.animal_type == animal_type)
            
            all_cages = query.all()
            
            available_cages = []
            for cage in all_cages:
                is_valid, _, _ = ConflictService.validate_booking(cage.id, start_time, end_time)
                if is_valid:
                    available_cages.append(cage)
            
            return available_cages
        finally:
            db.close()
