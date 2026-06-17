from typing import List, Optional, Tuple
from datetime import datetime
from db.database import SessionLocal
from models.booking import Booking, BookingStatus
from services.conflict_service import ConflictService
from services.approval_service import ApprovalService

class BookingService:
    @staticmethod
    def create_booking(cage_id: int, researcher_id: int, project_name: str,
                       animal_count: int, start_time: datetime, end_time: datetime,
                       purpose: str) -> Tuple[bool, str, Optional[Booking]]:
        is_valid, _, message = ConflictService.validate_booking(cage_id, start_time, end_time)
        if not is_valid:
            return False, message, None
        
        db = SessionLocal()
        try:
            booking = Booking(
                cage_id=cage_id,
                researcher_id=researcher_id,
                project_name=project_name,
                animal_count=animal_count,
                start_time=start_time,
                end_time=end_time,
                purpose=purpose,
                status=BookingStatus.DRAFT
            )
            db.add(booking)
            db.commit()
            db.refresh(booking)
            return True, "预约创建成功", booking
        except Exception as e:
            db.rollback()
            return False, str(e), None
        finally:
            db.close()

    @staticmethod
    def update_booking(booking_id: int, **kwargs) -> Tuple[bool, str]:
        db = SessionLocal()
        try:
            booking = db.query(Booking).filter(Booking.id == booking_id).first()
            if not booking:
                return False, "预约不存在"
            
            if booking.status != BookingStatus.DRAFT:
                return False, "只有草稿状态的预约可以修改"
            
            cage_id = kwargs.get('cage_id', booking.cage_id)
            start_time = kwargs.get('start_time', booking.start_time)
            end_time = kwargs.get('end_time', booking.end_time)
            
            if 'cage_id' in kwargs or 'start_time' in kwargs or 'end_time' in kwargs:
                is_valid, _, message = ConflictService.validate_booking(
                    cage_id, start_time, end_time, exclude_booking_id=booking_id
                )
                if not is_valid:
                    return False, message
            
            for key, value in kwargs.items():
                if hasattr(booking, key):
                    setattr(booking, key, value)
            
            booking.updated_at = datetime.now()
            db.commit()
            return True, "更新成功"
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def cancel_booking(booking_id: int) -> Tuple[bool, str]:
        db = SessionLocal()
        try:
            booking = db.query(Booking).filter(Booking.id == booking_id).first()
            if not booking:
                return False, "预约不存在"
            
            if booking.status in [BookingStatus.CANCELLED, BookingStatus.REJECTED, BookingStatus.COMPLETED]:
                return False, "该预约状态不允许取消"
            
            booking.status = BookingStatus.CANCELLED
            booking.updated_at = datetime.now()
            db.commit()
            return True, "预约已取消，时段已释放"
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def get_booking_by_id(booking_id: int) -> Optional[Booking]:
        db = SessionLocal()
        try:
            booking = db.query(Booking).filter(Booking.id == booking_id).first()
            return booking
        finally:
            db.close()

    @staticmethod
    def get_bookings_by_researcher(researcher_id: int) -> List[Booking]:
        db = SessionLocal()
        try:
            bookings = db.query(Booking).filter(
                Booking.researcher_id == researcher_id
            ).order_by(Booking.created_at.desc()).all()
            return bookings
        finally:
            db.close()

    @staticmethod
    def get_all_bookings() -> List[Booking]:
        db = SessionLocal()
        try:
            bookings = db.query(Booking).order_by(Booking.created_at.desc()).all()
            return bookings
        finally:
            db.close()

    @staticmethod
    def get_bookings_by_status(status: BookingStatus) -> List[Booking]:
        db = SessionLocal()
        try:
            bookings = db.query(Booking).filter(
                Booking.status == status
            ).order_by(Booking.created_at.desc()).all()
            return bookings
        finally:
            db.close()

    @staticmethod
    def submit_booking(booking_id: int) -> Tuple[bool, str]:
        return ApprovalService.submit_for_approval(booking_id)

    @staticmethod
    def get_booking_status_text(status: BookingStatus) -> str:
        status_map = {
            BookingStatus.DRAFT: '草稿',
            BookingStatus.PENDING_ADVISOR: '待导师审批',
            BookingStatus.PENDING_FACILITY: '待管理员审批',
            BookingStatus.PENDING_ETHICS: '待伦理审批',
            BookingStatus.APPROVED: '已通过',
            BookingStatus.REJECTED: '已拒绝',
            BookingStatus.CANCELLED: '已取消',
            BookingStatus.COMPLETED: '已完成',
        }
        return status_map.get(status, status.value)
