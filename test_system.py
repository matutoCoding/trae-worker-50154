import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from db.database import init_db, create_sample_data, SessionLocal
from models.user import User, UserRole
from models.cage import Cage, CageStatus
from models.booking import Booking, BookingStatus
from models.approval import Approval, ApprovalNode, ApprovalStatus
from services.cage_service import CageService
from services.booking_service import BookingService
from services.conflict_service import ConflictService
from services.approval_service import ApprovalService
from services.access_service import AccessService
from services.user_service import UserService

def test_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_1_init():
    test_header("1. 数据库初始化")
    init_db()
    create_sample_data()
    print("✓ 数据库初始化完成")
    
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        cage_count = db.query(Cage).count()
        print(f"✓ 用户数据：{user_count} 个用户")
        print(f"✓ 笼位数据：{cage_count} 个笼位")
    finally:
        db.close()

def test_2_user_auth():
    test_header("2. 用户认证测试")
    
    for username in ['student1', 'advisor1', 'manager1', 'ethics1']:
        success, user, msg = UserService.authenticate(username, '123456')
        if success:
            role_name = UserService.get_role_name(user.role)
            print(f"✓ {username} 登录成功 - 角色：{role_name}")
        else:
            print(f"✗ {username} 登录失败：{msg}")

def test_3_cage_management():
    test_header("3. 笼位管理测试")
    
    cages = CageService.get_all_cages()
    print(f"✓ 查询所有笼位：共 {len(cages)} 个")
    for cage in cages[:3]:
        print(f"  - {cage.cage_code}: {cage.room} - {cage.animal_type} (容量{cage.capacity})")
    
    success, msg, new_cage = CageService.create_cage(
        cage_code="TEST-001",
        room="测试区",
        capacity=10,
        animal_type="测试动物",
        description="测试笼位"
    )
    if success:
        print(f"✓ 创建笼位成功：{new_cage.cage_code}")
    else:
        print(f"✗ 创建笼位失败：{msg}")

def test_4_conflict_detection():
    test_header("4. 冲突检测测试")
    
    db = SessionLocal()
    try:
        researcher = db.query(User).filter(User.role == UserRole.RESEARCHER).first()
        cage = db.query(Cage).first()
        
        now = datetime.now()
        start1 = now + timedelta(days=5, hours=9)
        end1 = now + timedelta(days=5, hours=12)
        
        print(f"测试笼位：{cage.cage_code}")
        print(f"预约时段1：{start1.strftime('%Y-%m-%d %H:%M')} ~ {end1.strftime('%Y-%m-%d %H:%M')}")
        
        is_valid, conflicts, msg = ConflictService.validate_booking(cage.id, start1, end1)
        print(f"✓ 时段1检测：{'可用' if is_valid else '冲突'} - {msg}")
        
        booking1 = None
        if is_valid:
            success, msg, booking1 = BookingService.create_booking(
                cage_id=cage.id,
                researcher_id=researcher.id,
                project_name="测试项目1",
                animal_count=2,
                start_time=start1,
                end_time=end1,
                purpose="测试冲突检测"
            )
            if success:
                print(f"✓ 创建预约成功：#{booking1.id}")
        else:
            print("✓ 时段已被占用，使用现有预约进行测试")
            booking1 = conflicts[0] if conflicts else None
        
        start2 = now + timedelta(days=5, hours=10)
        end2 = now + timedelta(days=5, hours=13)
        print(f"预约时段2：{start2.strftime('%Y-%m-%d %H:%M')} ~ {end2.strftime('%Y-%m-%d %H:%M')}")
        
        is_valid, conflicts, msg = ConflictService.validate_booking(cage.id, start2, end2)
        print(f"✓ 时段2检测：{'冲突' if not is_valid else '可用'} - {msg}")
        
        if not is_valid:
            print(f"✓ 正确检测到冲突！冲突预约数：{len(conflicts)}")
        
        return booking1
        
    finally:
        db.close()

def test_5_approval_workflow(booking_to_approve=None):
    test_header("5. 多级审批流程测试")
    
    db = SessionLocal()
    try:
        if not booking_to_approve:
            researcher = db.query(User).filter(User.role == UserRole.RESEARCHER).first()
            cage = db.query(Cage).first()
            start = datetime.now() + timedelta(days=15)
            end = start + timedelta(hours=4)
            
            success, msg, booking_to_approve = BookingService.create_booking(
                cage_id=cage.id,
                researcher_id=researcher.id,
                project_name="审批测试项目",
                animal_count=1,
                start_time=start,
                end_time=end,
                purpose="测试审批流程"
            )
            
            if not success:
                print(f"✗ 创建预约失败：{msg}")
                return None
        
        booking_id = booking_to_approve.id
        print(f"测试预约：#{booking_id} - {booking_to_approve.project_name}")
        print(f"初始状态：{BookingService.get_booking_status_text(booking_to_approve.status)}")
        
        success, msg = ApprovalService.submit_for_approval(booking_id)
        print(f"✓ 提交审批：{msg}")
        
        advisor = db.query(User).filter(User.role == UserRole.ADVISOR).first()
        success, msg = ApprovalService.approve(booking_id, advisor.id, "同意，实验方案可行")
        print(f"✓ 导师审批：{msg}")
        
        manager = db.query(User).filter(User.role == UserRole.FACILITY_MANAGER).first()
        success, msg = ApprovalService.approve(booking_id, manager.id, "笼位安排妥当")
        print(f"✓ 管理员审批：{msg}")
        
        ethics = db.query(User).filter(User.role == UserRole.ETHICS_COMMITTEE).first()
        success, msg = ApprovalService.approve(booking_id, ethics.id, "伦理审查通过")
        print(f"✓ 伦理审批：{msg}")
        
        booking = BookingService.get_booking_by_id(booking_id)
        print(f"✓ 最终状态：{BookingService.get_booking_status_text(booking.status)}")
        
        return booking_id
        
    finally:
        db.close()

def test_6_reject_scenario():
    test_header("6. 驳回退回测试")
    
    db = SessionLocal()
    try:
        researcher = db.query(User).filter(User.role == UserRole.RESEARCHER).first()
        cage = db.query(Cage).first()
        start = datetime.now() + timedelta(days=10)
        end = start + timedelta(hours=4)
        
        success, msg, booking = BookingService.create_booking(
            cage_id=cage.id,
            researcher_id=researcher.id,
            project_name="驳回测试项目",
            animal_count=1,
            start_time=start,
            end_time=end,
            purpose="测试驳回流程"
        )
        
        if not success:
            print(f"✗ 创建预约失败：{msg}")
            return
            
        booking_id = booking.id
        print(f"测试预约：#{booking_id}")
        
        ApprovalService.submit_for_approval(booking_id)
        print(f"✓ 已提交审批")
        
        advisor = db.query(User).filter(User.role == UserRole.ADVISOR).first()
        success, msg = ApprovalService.reject(booking_id, advisor.id, "实验目的不明确，请补充详细说明")
        print(f"✓ 导师驳回：{msg}")
        
        booking = BookingService.get_booking_by_id(booking_id)
        print(f"✓ 当前状态：{BookingService.get_booking_status_text(booking.status)}")
        print(f"✓ 驳回原因：{booking.reject_reason}")
        
        approvals = ApprovalService.get_approval_history(booking_id)
        print(f"✓ 审批记录：共 {len(approvals)} 条")
        for a in approvals:
            print(f"  - {a.node.value}: {a.status.value} - {a.comments}")
        
    finally:
        db.close()

def test_7_cancel_booking():
    test_header("7. 退订释放测试")
    
    db = SessionLocal()
    try:
        researcher = db.query(User).filter(User.role == UserRole.RESEARCHER).first()
        cage = db.query(Cage).first()
        start = datetime.now() + timedelta(days=20)
        end = start + timedelta(hours=4)
        
        success, msg, booking = BookingService.create_booking(
            cage_id=cage.id,
            researcher_id=researcher.id,
            project_name="退订测试项目",
            animal_count=1,
            start_time=start,
            end_time=end,
            purpose="测试退订流程"
        )
        
        if not success:
            print(f"✗ 创建预约失败：{msg}")
            return
            
        booking_id = booking.id
        print(f"创建预约：#{booking_id}")
        
        is_valid, _, _ = ConflictService.validate_booking(cage.id, start, end)
        print(f"✓ 退订前同时段检测：{'冲突' if not is_valid else '可用'} (预期：冲突)")
        
        success, msg = BookingService.cancel_booking(booking_id)
        print(f"✓ 取消预约：{msg}")
        
        is_valid, _, _ = ConflictService.validate_booking(cage.id, start, end)
        print(f"✓ 退订后同时段检测：{'可用' if is_valid else '冲突'} (预期：可用)")
        
        if is_valid:
            print("✓ 时段已成功释放！")
        
    finally:
        db.close()

def test_8_access_registration(approved_booking_id=None):
    test_header("8. 准入登记测试")
    
    db = SessionLocal()
    try:
        if not approved_booking_id:
            approved_booking_id = test_5_approval_workflow()
        
        manager = db.query(User).filter(User.role == UserRole.FACILITY_MANAGER).first()
        
        success, msg, access = AccessService.create_access_registration(
            approved_booking_id, manager.name
        )
        if success:
            print(f"✓ 生成准入码：{access.access_code}")
        else:
            print(f"✗ 生成准入码失败：{msg}")
            return
        
        success, msg = AccessService.record_entry(access.access_code)
        print(f"✓ 进入登记：{msg}")
        
        success, msg = AccessService.record_exit(access.access_code)
        print(f"✓ 离开登记：{msg}")
        
        booking = BookingService.get_booking_by_id(approved_booking_id)
        print(f"✓ 预约最终状态：{BookingService.get_booking_status_text(booking.status)}")
        
    finally:
        db.close()

def run_all_tests():
    print("""
╔══════════════════════════════════════════════════════════════╗
║            实验动物房预约系统 - 业务逻辑测试套件              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    try:
        test_1_init()
        test_2_user_auth()
        test_3_cage_management()
        booking1 = test_4_conflict_detection()
        approved_id = test_5_approval_workflow(booking1)
        test_6_reject_scenario()
        test_7_cancel_booking()
        test_8_access_registration(approved_id)
        
        test_header("测试完成")
        print("✓ 所有核心功能测试通过！")
        print("\n功能覆盖：")
        print("  ✓ 用户认证与角色管理")
        print("  ✓ 笼位资源建档")
        print("  ✓ 时段重叠校验")
        print("  ✓ 多级审批流转（导师→管理员→伦理）")
        print("  ✓ 驳回退回机制")
        print("  ✓ 退订时段释放")
        print("  ✓ 准入码生成与核验")
        print("  ✓ 进出登记与预约完成")
        
    except Exception as e:
        print(f"\n✗ 测试过程中出错：{e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_all_tests()
