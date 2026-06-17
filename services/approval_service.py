from typing import Optional, Tuple, List
from datetime import datetime
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

    @staticmethod
    def submit_for_approval(booking_id: int) -> Tuple[bool, str]:
        db = SessionLocal()
        try:
            booking = db.query(Booking).filter(Booking.id == booking_id).first()
            if not booking:
                return False, "预约不存在"
            
            if booking.status != BookingStatus.DRAFT:
                return False, "只有草稿状态的预约可以提交审批"
            
            current_node = ApprovalService.STATUS_TO_NODE.get(BookingStatus.PENDING_ADVISOR)
            approver = db.query(User).filter(User.role == ApprovalService.NODE_TO_ROLE[current_node]).first()
            if not approver:
                return False, "系统中没有对应审批人"
            
            approval = Approval(
                booking_id=booking.id,
                approver_id=approver.id,
                node=current_node,
                status=ApprovalStatus.PENDING
            )
            db.add(approval)
            
            booking.status = BookingStatus.PENDING_ADVISOR
            booking.updated_at = datetime.now()
            
            db.commit()
            return True, "已提交导师审批"
        except Exception as e:
            db.rollback()
            return False, str(e)
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
                return False, "当前状态不支持审批"
            
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
            if next_status:
                booking.status = next_status
                booking.updated_at = datetime.now()
                
                if next_status != BookingStatus.APPROVED:
                    next_node = ApprovalService.STATUS_TO_NODE[next_status]
                    next_approver = db.query(User).filter(
                        User.role == ApprovalService.NODE_TO_ROLE[next_node]
                    ).first()
                    if next_approver:
                        next_approval = Approval(
                            booking_id=booking.id,
                            approver_id=next_approver.id,
                            node=next_node,
                            status=ApprovalStatus.PENDING
                        )
                        db.add(next_approval)
                    else:
                        return False, "系统中没有下一节点审批人"
                
                db.commit()
                
                if next_status == BookingStatus.APPROVED:
                    return True, "预约已通过全部审批，可以进行准入登记"
                else:
                    return True, f"已通过{current_node.value}审批，进入下一节点"
            else:
                db.commit()
                return True, "审批完成"
        except Exception as e:
            db.rollback()
            return False, str(e)
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
                return False, "当前状态不支持驳回"
            
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
            
            db.commit()
            
            if previous_status == BookingStatus.DRAFT:
                return True, "已驳回，预约退回申请人修改"
            else:
                prev_node_name = {v: k for k, v in ApprovalService.NODE_PREVIOUS_STATUS.items()}.get(previous_status, "上一节点")
                return True, f"已驳回，退回{prev_node_name.value}重新处理"
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def get_approvals_for_user(user_id: int) -> List[Approval]:
        db = SessionLocal()
        try:
            approvals = db.query(Approval).filter(
                Approval.approver_id == user_id,
                Approval.status == ApprovalStatus.PENDING
            ).order_by(Approval.created_at.desc()).all()
            return approvals
        finally:
            db.close()

    @staticmethod
    def get_approval_history(booking_id: int) -> List[Approval]:
        db = SessionLocal()
        try:
            approvals = db.query(Approval).filter(
                Approval.booking_id == booking_id
            ).order_by(Approval.created_at.asc()).all()
            return approvals
        finally:
            db.close()
