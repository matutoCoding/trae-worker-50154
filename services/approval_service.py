from typing import Optional, Tuple, List
from datetime import datetime
from sqlalchemy.orm import joinedload
from db.database import SessionLocal
from models.booking import Booking, BookingStatus
from models.approval import Approval, ApprovalNode, ApprovalStatus
from models.user import User, UserRole

class ApprovalService:
    NODE_TRANSITION = {
        BookingStatus.DRAFT: BookingStatus.PENDING_ADVISOR,
        BookingStatus.PENDING_ADVISOR: BookingStatus.PENDING_FACILITY,
        BookingStatus.PENDING_FACILITY: BookingStatus.PENDING_ETHICS,
        BookingStatus.PENDING_ETHICS: BookingStatus.APPROVED,
    }

    NODE_TO_ROLE = {
        ApprovalNode.ADVISOR: UserRole.ADVISOR,
        ApprovalNode.FACILITY_MANAGER: UserRole.FACILITY_MANAGER,
        ApprovalNode.ETHICS_COMMITTEE: UserRole.ETHICS_COMMITTEE,
    }

    STATUS_TO_NODE = {
        BookingStatus.PENDING_ADVISOR: ApprovalNode.ADVISOR,
        BookingStatus.PENDING_FACILITY: ApprovalNode.FACILITY_MANAGER,
        BookingStatus.PENDING_ETHICS: ApprovalNode.ETHICS_COMMITTEE,
    }

    NODE_PREVIOUS_STATUS = {
        ApprovalNode.ADVISOR: BookingStatus.DRAFT,
        ApprovalNode.FACILITY_MANAGER: BookingStatus.PENDING_ADVISOR,
        ApprovalNode.ETHICS_COMMITTEE: BookingStatus.PENDING_FACILITY,
    }

    PREVIOUS_STATUS_TO_NODE = {
        BookingStatus.PENDING_ADVISOR: ApprovalNode.ADVISOR,
        BookingStatus.PENDING_FACILITY: ApprovalNode.FACILITY_MANAGER,
    }

    NODE_DISPLAY_NAME = {
        ApprovalNode.ADVISOR: '导师',
        ApprovalNode.FACILITY_MANAGER: '管理员',
        ApprovalNode.ETHICS_COMMITTEE: '伦理委员',
    }

    @staticmethod
    def submit_for_approval(booking_id: int) -> Tuple[bool, str]:
        db = SessionLocal()
        try:
            booking = db.query(Booking).filter(Booking.id == booking_id).first()
            if not booking:
                return False, "预约不存在"

            if booking.status != BookingStatus.DRAFT:
                return False, "只有草稿状态的预约可以提交审批"

            target_status = BookingStatus.PENDING_ADVISOR
            target_node = ApprovalService.STATUS_TO_NODE[target_status]
            approver = db.query(User).filter(User.role == ApprovalService.NODE_TO_ROLE[target_node]).first()
            if not approver:
                return False, "系统中没有导师审批人"

            approval = Approval(
                booking_id=booking.id,
                approver_id=approver.id,
                node=target_node,
                status=ApprovalStatus.PENDING
            )
            db.add(approval)

            booking.status = target_status
            booking.reject_reason = None
            booking.updated_at = datetime.now()

            db.commit()
            return True, "已提交导师审批"
        except Exception as e:
            db.rollback()
            return False, f"提交失败：{str(e)}"
        finally:
            db.close()

    @staticmethod
    def approve(booking_id: int, approver_id: int, comments: Optional[str] = None) -> Tuple[bool, str]:
        db = SessionLocal()
        try:
            booking = db.query(Booking).filter(Booking.id == booking_id).first()
            if not booking:
                return False, "预约不存在"

            current_node = ApprovalService.STATUS_TO_NODE.get(booking.status)
            if not current_node:
                return False, f"当前状态({booking.status.value})不支持审批"

            approval = db.query(Approval).filter(
                Approval.booking_id == booking_id,
                Approval.node == current_node,
                Approval.status == ApprovalStatus.PENDING
            ).first()

            if not approval:
                return False, "找不到待审批记录"

            if approval.approver_id != approver_id:
                return False, "您没有权限审批此节点"

            approval.status = ApprovalStatus.APPROVED
            approval.comments = comments
            approval.updated_at = datetime.now()

            next_status = ApprovalService.NODE_TRANSITION.get(booking.status)
            current_node_name = ApprovalService.NODE_DISPLAY_NAME[current_node]

            if next_status:
                booking.status = next_status
                booking.updated_at = datetime.now()

                if next_status == BookingStatus.APPROVED:
                    db.commit()
                    return True, "预约已通过全部审批，可以进行准入登记"
                else:
                    next_node = ApprovalService.STATUS_TO_NODE[next_status]
                    next_approver = db.query(User).filter(
                        User.role == ApprovalService.NODE_TO_ROLE[next_node]
                    ).first()
                    if not next_approver:
                        db.rollback()
                        return False, f"系统中没有{ApprovalService.NODE_DISPLAY_NAME[next_node]}审批人"

                    existing_pending = db.query(Approval).filter(
                        Approval.booking_id == booking.id,
                        Approval.node == next_node,
                        Approval.status == ApprovalStatus.PENDING
                    ).first()
                    if not existing_pending:
                        next_approval = Approval(
                            booking_id=booking.id,
                            approver_id=next_approver.id,
                            node=next_node,
                            status=ApprovalStatus.PENDING
                        )
                        db.add(next_approval)

                    db.commit()
                    next_node_name = ApprovalService.NODE_DISPLAY_NAME[next_node]
                    return True, f"已通过{current_node_name}审批，进入{next_node_name}审批"
            else:
                db.commit()
                return True, "审批完成"
        except Exception as e:
            db.rollback()
            return False, f"审批失败：{str(e)}"
        finally:
            db.close()

    @staticmethod
    def reject(booking_id: int, approver_id: int, reject_reason: str) -> Tuple[bool, str]:
        db = SessionLocal()
        try:
            booking = db.query(Booking).filter(Booking.id == booking_id).first()
            if not booking:
                return False, "预约不存在"

            current_node = ApprovalService.STATUS_TO_NODE.get(booking.status)
            if not current_node:
                return False, f"当前状态({booking.status.value})不支持驳回"

            approval = db.query(Approval).filter(
                Approval.booking_id == booking_id,
                Approval.node == current_node,
                Approval.status == ApprovalStatus.PENDING
            ).first()

            if not approval:
                return False, "找不到待审批记录"

            if approval.approver_id != approver_id:
                return False, "您没有权限驳回此节点"

            approval.status = ApprovalStatus.REJECTED
            approval.comments = reject_reason
            approval.updated_at = datetime.now()

            previous_status = ApprovalService.NODE_PREVIOUS_STATUS[current_node]
            booking.status = previous_status
            booking.reject_reason = reject_reason
            booking.updated_at = datetime.now()

            if previous_status != BookingStatus.DRAFT:
                previous_node = ApprovalService.PREVIOUS_STATUS_TO_NODE.get(previous_status)
                if previous_node:
                    previous_approver = db.query(User).filter(
                        User.role == ApprovalService.NODE_TO_ROLE[previous_node]
                    ).first()
                    if previous_approver:
                        existing_pending = db.query(Approval).filter(
                            Approval.booking_id == booking.id,
                            Approval.node == previous_node,
                            Approval.status == ApprovalStatus.PENDING
                        ).first()
                        if not existing_pending:
                            retry_approval = Approval(
                                booking_id=booking.id,
                                approver_id=previous_approver.id,
                                node=previous_node,
                                status=ApprovalStatus.PENDING
                            )
                            db.add(retry_approval)

            db.commit()

            current_node_name = ApprovalService.NODE_DISPLAY_NAME[current_node]
            if previous_status == BookingStatus.DRAFT:
                return True, f"{current_node_name}已驳回，预约退回申请人修改"
            else:
                previous_node = ApprovalService.PREVIOUS_STATUS_TO_NODE.get(previous_status)
                prev_node_name = ApprovalService.NODE_DISPLAY_NAME.get(previous_node, "上一节点") if previous_node else "上一节点"
                return True, f"{current_node_name}已驳回，退回{prev_node_name}重新审批"
        except Exception as e:
            db.rollback()
            return False, f"驳回失败：{str(e)}"
        finally:
            db.close()

    @staticmethod
    def get_approvals_for_user(user_id: int) -> List[Approval]:
        db = SessionLocal()
        try:
            approvals = db.query(Approval).options(
                joinedload(Approval.booking).joinedload(Booking.cage),
                joinedload(Approval.booking).joinedload(Booking.researcher)
            ).filter(
                Approval.approver_id == user_id,
                Approval.status == ApprovalStatus.PENDING
            ).order_by(Approval.created_at.desc()).all()

            for a in approvals:
                _ = a.booking.cage.cage_code if a.booking and a.booking.cage else None
                _ = a.booking.researcher.name if a.booking and a.booking.researcher else None

            return approvals
        finally:
            db.close()

    @staticmethod
    def get_approval_history(booking_id: int) -> List[Approval]:
        db = SessionLocal()
        try:
            approvals = db.query(Approval).options(
                joinedload(Approval.approver)
            ).filter(
                Approval.booking_id == booking_id
            ).order_by(Approval.created_at.asc()).all()

            for a in approvals:
                _ = a.approver.name if a.approver else None

            return approvals
        finally:
            db.close()
