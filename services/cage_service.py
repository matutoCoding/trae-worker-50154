from typing import List, Optional, Tuple
from datetime import datetime
from db.database import SessionLocal
from models.cage import Cage, CageStatus
from models.booking import Booking, BookingStatus
from services.conflict_service import ConflictService
from services.approval_service import ApprovalService

class CageService:
    @staticmethod
    def create_cage(cage_code: str, room: str, capacity: int, animal_type: str, description: str = "") -> Tuple[bool, str, Optional[Cage]]:
        db = SessionLocal()
        try:
            existing = db.query(Cage).filter(Cage.cage_code == cage_code).first()
            if existing:
                return False, "笼位编号已存在", None
            
            cage = Cage(
                cage_code=cage_code,
                room=room,
                capacity=capacity,
                animal_type=animal_type,
                status=CageStatus.AVAILABLE,
                description=description
            )
            db.add(cage)
            db.commit()
            db.refresh(cage)
            return True, "笼位创建成功", cage
        except Exception as e:
            db.rollback()
            return False, str(e), None
        finally:
            db.close()

    @staticmethod
    def get_all_cages() -> List[Cage]:
        db = SessionLocal()
        try:
            cages = db.query(Cage).order_by(Cage.cage_code).all()
            return cages
        finally:
            db.close()

    @staticmethod
    def get_cage_by_id(cage_id: int) -> Optional[Cage]:
        db = SessionLocal()
        try:
            cage = db.query(Cage).filter(Cage.id == cage_id).first()
            return cage
        finally:
            db.close()

    @staticmethod
    def update_cage(cage_id: int, **kwargs) -> Tuple[bool, str]:
        db = SessionLocal()
        try:
            cage = db.query(Cage).filter(Cage.id == cage_id).first()
            if not cage:
                return False, "笼位不存在"
            
            for key, value in kwargs.items():
                if hasattr(cage, key):
                    setattr(cage, key, value)
            
            db.commit()
            return True, "更新成功"
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def set_cage_status(cage_id: int, status: CageStatus) -> Tuple[bool, str]:
        return CageService.update_cage(cage_id, status=status)

    @staticmethod
    def delete_cage(cage_id: int) -> Tuple[bool, str]:
        db = SessionLocal()
        try:
            cage = db.query(Cage).filter(Cage.id == cage_id).first()
            if not cage:
                return False, "笼位不存在"
            
            active_bookings = db.query(Booking).filter(
                Booking.cage_id == cage_id,
                Booking.status.notin_([BookingStatus.REJECTED, BookingStatus.CANCELLED, BookingStatus.COMPLETED])
            ).count()
            
            if active_bookings > 0:
                return False, "该笼位存在有效预约，无法删除"
            
            db.delete(cage)
            db.commit()
            return True, "删除成功"
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()
