from typing import Optional, Tuple
from db.database import SessionLocal
from models.user import User, UserRole

class UserService:
    @staticmethod
    def authenticate(username: str, password: str) -> Tuple[bool, Optional[User], str]:
        db = SessionLocal()
        try:
            user = db.query(User).filter(
                User.username == username,
                User.is_active == True
            ).first()
            
            if not user:
                return False, None, "用户不存在"
            
            if user.password != password:
                return False, None, "密码错误"
            
            return True, user, "登录成功"
        finally:
            db.close()

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            return user
        finally:
            db.close()

    @staticmethod
    def get_role_name(role: UserRole) -> str:
        role_map = {
            UserRole.RESEARCHER: '科研人员',
            UserRole.ADVISOR: '导师',
            UserRole.FACILITY_MANAGER: '动物房管理员',
            UserRole.ETHICS_COMMITTEE: '伦理委员',
        }
        return role_map.get(role, role.value)

    @staticmethod
    def get_all_users() -> list[User]:
        db = SessionLocal()
        try:
            users = db.query(User).order_by(User.name).all()
            return users
        finally:
            db.close()
