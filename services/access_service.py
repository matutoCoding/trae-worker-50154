from typing import List, Optional, Tuple
from datetime import datetime
import uuid
from sqlalchemy.orm import joinedload
from db.database import SessionLocal
from models.access import AccessRegistration
from models.booking import Booking, BookingStatus
from models.user import User

class AccessService:
    @staticmethod
    def generate_access_code() -> str:
        return f"ACC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    @staticmethod
    def create_access_registration(booking_id: int, registered_by: str) -> Tuple[bool, str, Optional[AccessRegistration]]:
        db = SessionLocal()
        try:
            booking = db.query(Booking).options(
                joinedload(Booking.cage),
                joinedload(Booking.researcher)
            ).filter(Booking.id == booking_id).first()
            if not booking:
                return False, "预约不存在", None

            if booking.status != BookingStatus.APPROVED:
                return False, "只有审批通过的预约才能进行准入登记", None

            existing = db.query(AccessRegistration).filter(
                AccessRegistration.booking_id == booking_id,
                AccessRegistration.is_active == True
            ).first()

            if existing:
                return False, "该预约已存在有效的准入登记", None

            access_code = AccessService.generate_access_code()
            registration = AccessRegistration(
                booking_id=booking_id,
                access_code=access_code,
                registered_by=registered_by,
                is_active=True
            )

            db.add(registration)
            db.commit()
            db.refresh(registration)

            _ = registration.booking.cage.cage_code if registration.booking and registration.booking.cage else None
            _ = registration.booking.researcher.name if registration.booking and registration.booking.researcher else None

            return True, "准入登记成功", registration
        except Exception as e:
            db.rollback()
            return False, f"登记失败：{str(e)}", None
        finally:
            db.close()

    @staticmethod
    def record_entry(access_code: str) -> Tuple[bool, str]:
        db = SessionLocal()
        try:
            registration = db.query(AccessRegistration).options(
                joinedload(AccessRegistration.booking).joinedload(Booking.cage),
                joinedload(AccessRegistration.booking).joinedload(Booking.researcher)
            ).filter(
                AccessRegistration.access_code == access_code,
                AccessRegistration.is_active == True
            ).first()

            if not registration:
                return False, "无效的准入码"

            if registration.entry_time:
                return False, "已登记进入，请勿重复登记"

            booking = registration.booking
            now = datetime.now()

            if now < booking.start_time:
                return False, f"未到准入时间，最早可进入时间：{booking.start_time.strftime('%Y-%m-%d %H:%M')}"

            if now > booking.end_time:
                return False, "预约时段已过期"

            registration.entry_time = now
            db.commit()
            return True, "进入登记成功"
        except Exception as e:
            db.rollback()
            return False, f"进入登记失败：{str(e)}"
        finally:
            db.close()

    @staticmethod
    def record_exit(access_code: str) -> Tuple[bool, str]:
        db = SessionLocal()
        try:
            registration = db.query(AccessRegistration).options(
                joinedload(AccessRegistration.booking).joinedload(Booking.cage),
                joinedload(AccessRegistration.booking).joinedload(Booking.researcher)
            ).filter(
                AccessRegistration.access_code == access_code,
                AccessRegistration.is_active == True
            ).first()

            if not registration:
                return False, "无效的准入码"

            if not registration.entry_time:
                return False, "未进行进入登记"

            if registration.exit_time:
                return False, "已登记离开，请勿重复登记"

            registration.exit_time = datetime.now()
            registration.is_active = False

            booking = registration.booking
            if booking.status == BookingStatus.APPROVED:
                booking.status = BookingStatus.COMPLETED
                booking.updated_at = datetime.now()

            db.commit()
            return True, "离开登记成功，预约已完成"
        except Exception as e:
            db.rollback()
            return False, f"离开登记失败：{str(e)}"
        finally:
            db.close()

    @staticmethod
    def get_access_by_code(access_code: str) -> Optional[AccessRegistration]:
        db = SessionLocal()
        try:
            registration = db.query(AccessRegistration).options(
                joinedload(AccessRegistration.booking).joinedload(Booking.cage),
                joinedload(AccessRegistration.booking).joinedload(Booking.researcher)
            ).filter(
                AccessRegistration.access_code == access_code
            ).first()

            if registration:
                _ = registration.booking.cage.cage_code if registration.booking and registration.booking.cage else None
                _ = registration.booking.researcher.name if registration.booking and registration.booking.researcher else None

            return registration
        finally:
            db.close()

    @staticmethod
    def get_access_by_booking(booking_id: int) -> Optional[AccessRegistration]:
        db = SessionLocal()
        try:
            registration = db.query(AccessRegistration).options(
                joinedload(AccessRegistration.booking).joinedload(Booking.cage),
                joinedload(AccessRegistration.booking).joinedload(Booking.researcher)
            ).filter(
                AccessRegistration.booking_id == booking_id
            ).first()

            if registration:
                _ = registration.booking.cage.cage_code if registration.booking and registration.booking.cage else None
                _ = registration.booking.researcher.name if registration.booking and registration.booking.researcher else None

            return registration
        finally:
            db.close()

    @staticmethod
    def get_all_access_registrations() -> List[AccessRegistration]:
        db = SessionLocal()
        try:
            registrations = db.query(AccessRegistration).options(
                joinedload(AccessRegistration.booking).joinedload(Booking.cage),
                joinedload(AccessRegistration.booking).joinedload(Booking.researcher)
            ).order_by(
                AccessRegistration.registered_at.desc()
            ).all()

            for r in registrations:
                _ = r.booking.cage.cage_code if r.booking and r.booking.cage else None
                _ = r.booking.researcher.name if r.booking and r.booking.researcher else None

            return registrations
        finally:
            db.close()

    @staticmethod
    def get_active_access_registrations() -> List[AccessRegistration]:
        db = SessionLocal()
        try:
            registrations = db.query(AccessRegistration).options(
                joinedload(AccessRegistration.booking).joinedload(Booking.cage),
                joinedload(AccessRegistration.booking).joinedload(Booking.researcher)
            ).filter(
                AccessRegistration.is_active == True
            ).order_by(AccessRegistration.registered_at.desc()).all()

            for r in registrations:
                _ = r.booking.cage.cage_code if r.booking and r.booking.cage else None
                _ = r.booking.researcher.name if r.booking and r.booking.researcher else None

            return registrations
        finally:
            db.close()
