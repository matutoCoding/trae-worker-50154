from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'animal_lab.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    from models.user import User
    from models.cage import Cage
    from models.booking import Booking
    from models.approval import Approval
    from models.access import AccessRegistration
    Base.metadata.create_all(bind=engine)

def create_sample_data():
    from models.user import User, UserRole
    from models.cage import Cage, CageStatus
    db = SessionLocal()
    
    if db.query(User).count() == 0:
        users = [
            User(username='student1', name='张同学', role=UserRole.RESEARCHER, password='123456'),
            User(username='advisor1', name='李教授', role=UserRole.ADVISOR, password='123456'),
            User(username='manager1', name='王管理员', role=UserRole.FACILITY_MANAGER, password='123456'),
            User(username='ethics1', name='赵委员', role=UserRole.ETHICS_COMMITTEE, password='123456'),
        ]
        db.add_all(users)
    
    if db.query(Cage).count() == 0:
        cages = [
            Cage(cage_code='A-001', room='A区1室', capacity=5, animal_type='小鼠', status=CageStatus.AVAILABLE),
            Cage(cage_code='A-002', room='A区1室', capacity=5, animal_type='小鼠', status=CageStatus.AVAILABLE),
            Cage(cage_code='A-003', room='A区2室', capacity=3, animal_type='大鼠', status=CageStatus.AVAILABLE),
            Cage(cage_code='B-001', room='B区1室', capacity=2, animal_type='豚鼠', status=CageStatus.AVAILABLE),
            Cage(cage_code='B-002', room='B区1室', capacity=8, animal_type='斑马鱼', status=CageStatus.AVAILABLE),
            Cage(cage_code='C-001', room='C区1室', capacity=1, animal_type='非人灵长类', status=CageStatus.AVAILABLE),
        ]
        db.add_all(cages)
    
    db.commit()
    db.close()
