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

# ==================== 测试辅助函数（失败即明确退出） ====================

def test_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def fail_test(msg):
    """测试失败：明确打印错误信息并以非0状态退出"""
    print(f"\n✗ [测试失败] {msg}")
    print(f"  退出码：1")
    sys.exit(1)

def assert_true(condition, msg):
    if not condition:
        fail_test(msg)
    print(f"✓ {msg}")

def assert_success(result_tuple, action_desc):
    """校验服务层返回的 (success, message, ...) 元组，失败即退出"""
    success = result_tuple[0]
    message = result_tuple[1] if len(result_tuple) > 1 else ''
    if not success:
        fail_test(f"{action_desc} 失败 - {message}")
    print(f"✓ {action_desc} 成功 - {message}")
    return result_tuple

def assert_status(actual, expected, desc):
    if actual != expected:
        fail_test(f"{desc}: 预期={expected.value}, 实际={actual.value}")
    print(f"✓ {desc}: {actual.value}")

# ==================== 测试用例 ====================

def get_test_entities(db):
    """一次性获取测试所需的各类实体，避免每个测试重复查询"""
    researcher = db.query(User).filter(User.role == UserRole.RESEARCHER).first()
    advisor = db.query(User).filter(User.role == UserRole.ADVISOR).first()
    manager = db.query(User).filter(User.role == UserRole.FACILITY_MANAGER).first()
    ethics = db.query(User).filter(User.role == UserRole.ETHICS_COMMITTEE).first()
    cage = db.query(Cage).first()
    if not all([researcher, advisor, manager, ethics, cage]):
        fail_test("样例数据缺失，无法继续测试")
    return researcher, advisor, manager, ethics, cage

def test_1_init_and_data():
    test_header("1. 数据库初始化 & 基础数据校验")
    init_db()
    create_sample_data()
    print("✓ 数据库初始化完成")

    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        cage_count = db.query(Cage).count()
        assert_true(user_count >= 4, f"用户数={user_count}，应>=4")
        assert_true(cage_count >= 1, f"笼位数={cage_count}，应>=1")
        roles_present = {r[0] for r in db.query(User.role).distinct().all()}
        for required in [UserRole.RESEARCHER, UserRole.ADVISOR,
                         UserRole.FACILITY_MANAGER, UserRole.ETHICS_COMMITTEE]:
            assert_true(required in roles_present, f"存在角色 {required.value}")
    finally:
        db.close()

def test_2_user_auth():
    test_header("2. 用户认证测试")
    credentials = [
        ('student1', UserRole.RESEARCHER),
        ('advisor1', UserRole.ADVISOR),
        ('manager1', UserRole.FACILITY_MANAGER),
        ('ethics1', UserRole.ETHICS_COMMITTEE),
    ]
    for username, expected_role in credentials:
        success, user, msg = UserService.authenticate(username, '123456')
        assert_true(success, f"用户 {username} 登录认证通过")
        assert_true(user.role == expected_role,
                    f"用户 {username} 角色正确 ({expected_role.value})")
        role_name = UserService.get_role_name(user.role)
        print(f"  -> {username} 角色名: {role_name}")

def test_3_cage_management():
    test_header("3. 笼位管理测试")
    cages = CageService.get_all_cages()
    assert_true(len(cages) >= 1, f"查询笼位数量={len(cages)}")
    for cage in cages[:3]:
        _ = cage.cage_code  # 触发属性访问确保不报错
        print(f"  - {cage.cage_code}: {cage.room} - {cage.animal_type}")

    result = CageService.create_cage(
        cage_code="TEST-AUTO-001",
        room="自动化测试区",
        capacity=8,
        animal_type="小鼠",
        description="自动测试用笼位"
    )
    assert_success(result, "创建测试笼位")

def test_4_conflict_detection():
    test_header("4. 冲突检测测试")
    db = SessionLocal()
    try:
        researcher, advisor, manager, ethics, cage = get_test_entities(db)
        now = datetime.now()
        start1 = now + timedelta(days=5, hours=9)
        end1 = now + timedelta(days=5, hours=12)

        is_valid, conflicts, msg = ConflictService.validate_booking(cage.id, start1, end1)
        assert_true(is_valid, f"首次检测时段可用 ({start1:%H:%M}-{end1:%H:%M})")

        result = BookingService.create_booking(
            cage_id=cage.id, researcher_id=researcher.id,
            project_name="冲突检测基线预约", animal_count=2,
            start_time=start1, end_time=end1, purpose="基线预约"
        )
        assert_success(result, "创建基线预约")
        baseline_booking = result[2]

        start2 = now + timedelta(days=5, hours=10)
        end2 = now + timedelta(days=5, hours=13)
        is_valid2, conflicts2, msg2 = ConflictService.validate_booking(cage.id, start2, end2)
        assert_true(not is_valid2, f"重叠时段({start2:%H:%M}-{end2:%H:%M})正确检测到冲突")
        assert_true(len(conflicts2) >= 1, f"返回冲突预约数量={len(conflicts2)}")

        return baseline_booking
    finally:
        db.close()

def full_approve_chain(booking_id, advisor, manager, ethics):
    """完整审批链路：导师→管理员→伦理，逐步验证状态"""
    print("  [链路] 导师审批通过...")
    r = ApprovalService.approve(booking_id, advisor.id, "导师同意")
    assert_success(r, "导师审批")
    b = BookingService.get_booking_by_id(booking_id)
    assert_status(b.status, BookingStatus.PENDING_FACILITY, "导师通过后状态")

    print("  [链路] 管理员审批通过...")
    r = ApprovalService.approve(booking_id, manager.id, "管理员同意")
    assert_success(r, "管理员审批")
    b = BookingService.get_booking_by_id(booking_id)
    assert_status(b.status, BookingStatus.PENDING_ETHICS, "管理员通过后状态")

    print("  [链路] 伦理委员审批通过...")
    r = ApprovalService.approve(booking_id, ethics.id, "伦理同意")
    assert_success(r, "伦理审批")
    b = BookingService.get_booking_by_id(booking_id)
    assert_status(b.status, BookingStatus.APPROVED, "伦理通过后状态")
    return True

def test_5_approval_normal(baseline_booking):
    test_header("5. 正常多级审批链路 (导师→管理员→伦理)")
    db = SessionLocal()
    try:
        researcher, advisor, manager, ethics, cage = get_test_entities(db)

        # 新建一个独立预约用于审批测试
        start = datetime.now() + timedelta(days=15)
        end = start + timedelta(hours=4)
        result = BookingService.create_booking(
            cage_id=cage.id, researcher_id=researcher.id,
            project_name="正常审批链路测试", animal_count=1,
            start_time=start, end_time=end, purpose="完整链路"
        )
        assert_success(result, "创建审批测试预约")
        booking = result[2]

        # 提交审批
        r = ApprovalService.submit_for_approval(booking.id)
        assert_success(r, "提交审批")
        b = BookingService.get_booking_by_id(booking.id)
        assert_status(b.status, BookingStatus.PENDING_ADVISOR, "提交后状态")

        # 检查导师待办
        advisor_todos = ApprovalService.get_approvals_for_user(advisor.id)
        has_todo = any(a.booking_id == booking.id for a in advisor_todos)
        assert_true(has_todo, "提交后导师待办列表中存在该预约")

        # 完整链路
        full_approve_chain(booking.id, advisor, manager, ethics)

        history = ApprovalService.get_approval_history(booking.id)
        print(f"  审批记录数: {len(history)}")
        for a in history:
            _ = a.approver.name if a.approver else None
            print(f"    - {a.node.value}: {a.status.value} by {a.approver.name if a.approver else '-'}")

        return booking.id  # 返回伦理通过的预约ID，供准入登记复用
    finally:
        db.close()

def test_6_multi_reject_loop():
    test_header("6. 多级驳回循环 (管理员驳回→导师, 伦理驳回→管理员)")
    db = SessionLocal()
    try:
        researcher, advisor, manager, ethics, cage = get_test_entities(db)

        # 新建预约
        start = datetime.now() + timedelta(days=12)
        end = start + timedelta(hours=4)
        result = BookingService.create_booking(
            cage_id=cage.id, researcher_id=researcher.id,
            project_name="驳回循环测试", animal_count=3,
            start_time=start, end_time=end, purpose="循环驳回测试"
        )
        assert_success(result, "创建驳回测试预约")
        booking_id = result[2].id

        # 提交审批
        r = ApprovalService.submit_for_approval(booking_id)
        assert_success(r, "提交审批")

        # --- 第1次: 导师通过 ---
        r = ApprovalService.approve(booking_id, advisor.id, "导师通过(第1次)")
        assert_success(r, "导师第1次通过")
        b = BookingService.get_booking_by_id(booking_id)
        assert_status(b.status, BookingStatus.PENDING_FACILITY, "状态→待管理员")

        # --- 第1次: 管理员驳回 → 应该回到导师待办 ---
        r = ApprovalService.reject(booking_id, manager.id, "材料不完整，请导师重审")
        assert_success(r, "管理员驳回(第1次)")
        b = BookingService.get_booking_by_id(booking_id)
        assert_status(b.status, BookingStatus.PENDING_ADVISOR, "管理员驳回后状态→待导师")

        # 关键校验：导师待办列表里是否重新出现
        advisor_todos = ApprovalService.get_approvals_for_user(advisor.id)
        pending_for_advisor = [a for a in advisor_todos
                               if a.booking_id == booking_id and a.status == ApprovalStatus.PENDING]
        assert_true(len(pending_for_advisor) >= 1,
                    f"管理员驳回后，导师待办中重新出现 (找到 {len(pending_for_advisor)} 条PENDING)")

        # --- 第2次: 导师重新通过 ---
        r = ApprovalService.approve(booking_id, advisor.id, "导师通过(第2次, 已补材料)")
        assert_success(r, "导师第2次通过")
        b = BookingService.get_booking_by_id(booking_id)
        assert_status(b.status, BookingStatus.PENDING_FACILITY, "状态→待管理员")

        # --- 第2次: 管理员通过 ---
        r = ApprovalService.approve(booking_id, manager.id, "管理员通过(第2次)")
        assert_success(r, "管理员通过")
        b = BookingService.get_booking_by_id(booking_id)
        assert_status(b.status, BookingStatus.PENDING_ETHICS, "状态→待伦理")

        # --- 第1次: 伦理驳回 → 应该回到管理员待办 ---
        r = ApprovalService.reject(booking_id, ethics.id, "伦理不合规，请管理员复核")
        assert_success(r, "伦理驳回")
        b = BookingService.get_booking_by_id(booking_id)
        assert_status(b.status, BookingStatus.PENDING_FACILITY, "伦理驳回后状态→待管理员")

        # 关键校验：管理员待办列表里是否重新出现
        manager_todos = ApprovalService.get_approvals_for_user(manager.id)
        pending_for_manager = [a for a in manager_todos
                               if a.booking_id == booking_id and a.status == ApprovalStatus.PENDING]
        assert_true(len(pending_for_manager) >= 1,
                    f"伦理驳回后，管理员待办中重新出现 (找到 {len(pending_for_manager)} 条PENDING)")

        # --- 管理员再次通过 ---
        r = ApprovalService.approve(booking_id, manager.id, "管理员通过(第3次, 已复核)")
        assert_success(r, "管理员再次通过")
        b = BookingService.get_booking_by_id(booking_id)
        assert_status(b.status, BookingStatus.PENDING_ETHICS, "状态→待伦理")

        # --- 伦理最终通过 ---
        r = ApprovalService.approve(booking_id, ethics.id, "伦理最终通过")
        assert_success(r, "伦理最终通过")
        b = BookingService.get_booking_by_id(booking_id)
        assert_status(b.status, BookingStatus.APPROVED, "最终状态→已通过")

        print("✓ 多级驳回-重审-再通过 循环完整验证成功！")
    finally:
        db.close()

def test_7_draft_edit_after_reject():
    test_header("7. 导师驳回→草稿编辑(改时段+冲突校验)→重新提交审批")
    db = SessionLocal()
    try:
        researcher, advisor, manager, ethics, cage = get_test_entities(db)
        now = datetime.now()

        # 新建预约并提交
        start = now + timedelta(days=8, hours=9)
        end = now + timedelta(days=8, hours=12)
        result = BookingService.create_booking(
            cage_id=cage.id, researcher_id=researcher.id,
            project_name="草稿编辑原始项目", animal_count=1,
            start_time=start, end_time=end, purpose="原始说明"
        )
        assert_success(result, "创建草稿编辑测试预约")
        booking_id = result[2].id

        r = ApprovalService.submit_for_approval(booking_id)
        assert_success(r, "提交审批")

        # 导师驳回 → 回到草稿
        r = ApprovalService.reject(booking_id, advisor.id, "项目说明太简单，请补充")
        assert_success(r, "导师驳回")
        b = BookingService.get_booking_by_id(booking_id)
        assert_status(b.status, BookingStatus.DRAFT, "驳回后状态→草稿")
        assert_true(b.reject_reason is not None and "项目说明" in b.reject_reason,
                    f"驳回原因正确记录: {b.reject_reason}")

        # 科研人员在草稿中修改：项目说明、动物数量、时段
        new_start = now + timedelta(days=9, hours=14)
        new_end = now + timedelta(days=9, hours=17)
        r = BookingService.update_booking(
            booking_id,
            project_name="草稿编辑-已修改项目名",
            animal_count=5,
            purpose="已补充详细实验目的与步骤说明",
            start_time=new_start,
            end_time=new_end
        )
        assert_success(r, "草稿编辑保存(改项目/数量/时段)")

        # 验证修改已生效
        b2 = BookingService.get_booking_by_id(booking_id)
        assert_true(b2.project_name == "草稿编辑-已修改项目名", "项目名修改生效")
        assert_true(b2.animal_count == 5, f"动物数量修改生效: {b2.animal_count}")
        assert_true(b2.purpose == "已补充详细实验目的与步骤说明", "目的说明修改生效")
        assert_true(abs((b2.start_time - new_start).total_seconds()) < 1, "开始时间修改生效")
        assert_true(abs((b2.end_time - new_end).total_seconds()) < 1, "结束时间修改生效")

        # --- 冲突校验测试：先建一个占用预约，再尝试把草稿预约改成相同时段 ---
        start_conflict = now + timedelta(days=10, hours=9)
        end_conflict = now + timedelta(days=10, hours=12)
        r2 = BookingService.create_booking(
            cage_id=cage.id, researcher_id=researcher.id,
            project_name="冲突占位预约", animal_count=1,
            start_time=start_conflict, end_time=end_conflict, purpose="占位"
        )
        assert_success(r2, "创建冲突占位预约")

        # 尝试把草稿预约改为冲突时段，应该被拒绝
        r3 = BookingService.update_booking(
            booking_id,
            start_time=start_conflict,
            end_time=end_conflict
        )
        assert_true(not r3[0], f"修改为冲突时段正确被拒绝: {r3[1]}")
        print(f"  冲突校验返回: {r3[1]}")

        # 草稿修改后重新提交审批
        r = ApprovalService.submit_for_approval(booking_id)
        assert_success(r, "修改后重新提交审批")
        b3 = BookingService.get_booking_by_id(booking_id)
        assert_status(b3.status, BookingStatus.PENDING_ADVISOR, "重新提交后状态→待导师")

        # 完整审批直到通过
        full_approve_chain(booking_id, advisor, manager, ethics)
        print("✓ 草稿编辑-冲突校验-重新提交-全链路审批 完整验证成功！")
    finally:
        db.close()

def test_8_cancel_release():
    test_header("8. 退订释放时段")
    db = SessionLocal()
    try:
        researcher, advisor, manager, ethics, cage = get_test_entities(db)
        start = datetime.now() + timedelta(days=20, hours=9)
        end = datetime.now() + timedelta(days=20, hours=12)

        result = BookingService.create_booking(
            cage_id=cage.id, researcher_id=researcher.id,
            project_name="退订测试", animal_count=1,
            start_time=start, end_time=end, purpose="退订"
        )
        assert_success(result, "创建退订测试预约")
        booking_id = result[2].id

        is_valid_before, _, _ = ConflictService.validate_booking(cage.id, start, end)
        assert_true(not is_valid_before, "退订前同笼位同时段检测到冲突(预期)")

        r = BookingService.cancel_booking(booking_id)
        assert_success(r, "取消预约")
        b = BookingService.get_booking_by_id(booking_id)
        assert_status(b.status, BookingStatus.CANCELLED, "取消后状态")

        is_valid_after, _, _ = ConflictService.validate_booking(cage.id, start, end)
        assert_true(is_valid_after, "退订后同笼位同时段已释放(可重新预约)")
    finally:
        db.close()

def test_9_access_registration(pre_approved_id=None):
    test_header("9. 准入登记完整链路 (当前时段→进入→离开→完成)")
    db = SessionLocal()
    try:
        researcher, advisor, manager, ethics, cage = get_test_entities(db)
        now = datetime.now()

        if pre_approved_id:
            booking_id = pre_approved_id
            # 复用test_5通过的预约，但它的时间是+15天，不能直接进入
            # 所以需要额外创建一个"当前正在进行"的预约
            create_new = False
            b_check = BookingService.get_booking_by_id(booking_id)
            if b_check.start_time > now or b_check.end_time < now:
                print(f"  预约 #{booking_id} 时段不在当前，新建一个当前时段预约...")
                create_new = True
        else:
            create_new = True

        if create_new:
            # 第1阶段：先创建一个"未来1秒开始"的预约，通过validate_booking的时间校验
            start_future = now + timedelta(seconds=1)
            end_current = now + timedelta(hours=2)
            result = BookingService.create_booking(
                cage_id=cage.id, researcher_id=researcher.id,
                project_name="准入登记-当前时段预约", animal_count=2,
                start_time=start_future, end_time=end_current,
                purpose="准入登记全链路测试"
            )
            assert_success(result, "创建准入测试预约(初始未来时段)")
            booking_id = result[2].id

            # 第2阶段：绕过validate_booking，直接DB把开始时间改到过去，模拟正在进行中的预约
            db2 = SessionLocal()
            try:
                b_to_update = db2.query(Booking).filter(Booking.id == booking_id).first()
                # 开始时间设为10分钟前，结束时间维持2小时后
                b_to_update.start_time = now - timedelta(minutes=10)
                b_to_update.end_time = now + timedelta(hours=2)
                db2.commit()
                print(f"  已调整预约时段: {b_to_update.start_time:%H:%M} ~ {b_to_update.end_time:%H:%M} (当前 {now:%H:%M})")
            finally:
                db2.close()

            # 提交并完整审批
            r = ApprovalService.submit_for_approval(booking_id)
            assert_success(r, "提交审批")
            full_approve_chain(booking_id, advisor, manager, ethics)

        # 生成准入码
        b = BookingService.get_booking_by_id(booking_id)
        assert_status(b.status, BookingStatus.APPROVED, "准入前状态→已通过")

        r = AccessService.create_access_registration(booking_id, manager.name)
        assert_success(r, "生成准入登记")
        access = r[2]
        access_code = access.access_code
        assert_true(access_code and access_code.startswith("ACC-"),
                    f"准入码格式正确: {access_code}")
        print(f"  准入码: {access_code}")

        # 验证关联数据可访问
        assert_true(access.booking is not None, "准入码关联预约已加载")
        _ = access.booking.cage.cage_code if access.booking and access.booking.cage else None
        _ = access.booking.researcher.name if access.booking and access.booking.researcher else None
        print(f"  笼位: {access.booking.cage.cage_code}, 申请人: {access.booking.researcher.name}")

        # 重复生成应失败
        r_dup = AccessService.create_access_registration(booking_id, manager.name)
        assert_true(not r_dup[0], f"重复生成准入码正确被拒绝: {r_dup[1]}")

        # 登记进入
        r = AccessService.record_entry(access_code)
        assert_success(r, "登记进入")
        entry_reg = AccessService.get_access_by_code(access_code)
        assert_true(entry_reg.entry_time is not None, "进入时间已记录")
        print(f"  进入时间: {entry_reg.entry_time:%Y-%m-%d %H:%M:%S}")

        # 重复进入应失败
        r_dup_entry = AccessService.record_entry(access_code)
        assert_true(not r_dup_entry[0], f"重复进入登记正确被拒绝: {r_dup_entry[1]}")

        # 登记离开
        r = AccessService.record_exit(access_code)
        assert_success(r, "登记离开")
        exit_reg = AccessService.get_access_by_code(access_code)
        assert_true(exit_reg.exit_time is not None, "离开时间已记录")
        assert_true(exit_reg.is_active == False, "准入码已失效")
        print(f"  离开时间: {exit_reg.exit_time:%Y-%m-%d %H:%M:%S}")

        # 验证预约状态变为COMPLETED
        b_final = BookingService.get_booking_by_id(booking_id)
        assert_status(b_final.status, BookingStatus.COMPLETED, "离开登记后预约状态→已完成")

        print("✓ 准入登记全链路(生成→进入→离开→完成)完整验证成功！")
    finally:
        db.close()

def test_10_pending_todos_smoke():
    test_header("10. 各角色待办&关联数据加载冒烟测试")
    db = SessionLocal()
    try:
        researcher, advisor, manager, ethics, cage = get_test_entities(db)

        for role_user, role_name in [(advisor, "导师"), (manager, "管理员"), (ethics, "伦理")]:
            todos = ApprovalService.get_approvals_for_user(role_user.id)
            print(f"  {role_name}({role_user.name}) 待办数: {len(todos)}")
            for todo in todos[:3]:
                # 验证关联数据不崩溃
                cage_code = todo.booking.cage.cage_code if todo.booking and todo.booking.cage else '-'
                researcher_name = todo.booking.researcher.name if todo.booking and todo.booking.researcher else '-'
                project = todo.booking.project_name if todo.booking else '-'
                print(f"    - #{todo.booking_id} {project} | 笼位:{cage_code} 申请人:{researcher_name}")

        # 我的预约列表关联数据
        my_bookings = BookingService.get_bookings_by_researcher(researcher.id)
        print(f"  科研人员({researcher.name}) 预约数: {len(my_bookings)}")
        for bk in my_bookings[:3]:
            cage_code = bk.cage.cage_code if bk.cage else '-'
            status_text = BookingService.get_booking_status_text(bk.status)
            print(f"    - #{bk.id} {bk.project_name} | 笼位:{cage_code} 状态:{status_text}")

        # 准入登记列表
        all_access = AccessService.get_all_access_registrations()
        print(f"  准入登记记录数: {len(all_access)}")
        for acc in all_access[:3]:
            cage_code = acc.booking.cage.cage_code if acc.booking and acc.booking.cage else '-'
            researcher_name = acc.booking.researcher.name if acc.booking and acc.booking.researcher else '-'
            print(f"    - {acc.access_code} | 笼位:{cage_code} 申请人:{researcher_name}")

        print("✓ 所有关联数据加载均正常，无报错退出")
    finally:
        db.close()

# ==================== 主入口 ====================

def run_all_tests():
    print("""
╔══════════════════════════════════════════════════════════════╗
║    实验动物房预约系统 - 严格业务逻辑测试套件 (失败即退出)     ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # 删除旧数据库确保环境干净
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'animal_lab.db')
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("(已删除旧数据库，保证测试环境纯净)\n")
        except PermissionError:
            print("(旧数据库被占用，将在其上继续测试...)\n")

    try:
        test_1_init_and_data()
        test_2_user_auth()
        test_3_cage_management()
        baseline = test_4_conflict_detection()
        approved_id = test_5_approval_normal(baseline)
        test_6_multi_reject_loop()
        test_7_draft_edit_after_reject()
        test_8_cancel_release()
        test_9_access_registration(approved_id)
        test_10_pending_todos_smoke()

        test_header("全部测试通过")
        print("""
✓ 所有 10 大测试模块完整通过！退出码: 0

功能覆盖清单 (均含失败时明确退出码):
  ✓ [1] 数据库初始化 & 角色/笼位完整性校验
  ✓ [2] 四角色用户认证 & 角色映射
  ✓ [3] 笼位CRUD管理
  ✓ [4] 时段冲突检测算法（基线预约+重叠检测）
  ✓ [5] 正常审批链路: 导师→管理员→伦理 (每步状态校验+待办可见)
  ✓ [6] 多级驳回循环: 管理员驳回→导师重审, 伦理驳回→管理员重审 (待办验证)
  ✓ [7] 导师驳回→草稿编辑(项目/数量/时段)→冲突重校验→重新提交→全链路通过
  ✓ [8] 退订取消后时段正确释放
  ✓ [9] 准入登记全链路: 当前时段预约→审批→准入码→进入→离开→预约已完成
  ✓ [10] 各角色待办/我的预约/准入登记关联数据稳定加载（无DetachedInstanceError）
""")
        sys.exit(0)

    except SystemExit:
        raise
    except Exception as e:
        print(f"\n✗ 测试过程中抛出未捕获异常：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    run_all_tests()
