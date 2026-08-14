import logging
from typing import Any

from agent.domain.messages import BotMessage
from agent.domain.state import DialogueState
from agent.task.action.base import Action, ActionResult

from .shared import (
    set_current_customer_no,
    reset_current_customer_no,
    create_customer,
    update_customer,
    submit_customer_identity,
    submit_customer_kyc,
    submit_customer_risk_assessment,
    add_customer_contact,
)

logger = logging.getLogger(__name__)


class ActionCreateCustomer(Action):
    name = "action_create_customer"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            customer_type = action_kwargs.get("customer_type", "personal")
            customer_name = action_kwargs.get("customer_name", "")
            branch_code = action_kwargs.get("branch_code", "")
            channel_code = action_kwargs.get("channel_code", "MOBILE_BANK")
            result = await create_customer(
                customer_type=customer_type,
                customer_name=customer_name,
                branch_code=branch_code,
                channel_code=channel_code,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="客户创建成功")])
            else:
                return ActionResult(messages=[BotMessage(text="客户创建失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionUpdateCustomer(Action):
    name = "action_update_customer"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            customer_no = action_kwargs.get("customer_no", "")
            result = await update_customer(customer_no, **action_kwargs)
            if result:
                return ActionResult(messages=[BotMessage(text="客户信息更新成功")])
            else:
                return ActionResult(messages=[BotMessage(text="客户信息更新失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionSubmitIdentity(Action):
    name = "action_submit_identity"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            customer_no = action_kwargs.get("customer_no", "")
            identity_no = action_kwargs.get("identity_no", "")
            identity_name = action_kwargs.get("identity_name", "")
            identity_valid_to = action_kwargs.get("identity_valid_to")
            result = await submit_customer_identity(
                customer_no=customer_no,
                identity_no=identity_no,
                identity_name=identity_name,
                identity_valid_to=identity_valid_to,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="实名认证提交成功")])
            else:
                return ActionResult(messages=[BotMessage(text="实名认证提交失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionSubmitKYC(Action):
    name = "action_submit_kyc"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            customer_no = action_kwargs.get("customer_no", "")
            kyc_data = action_kwargs.get("kyc_data", {})
            result = await submit_customer_kyc(
                customer_no=customer_no,
                kyc_data=kyc_data,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="KYC 信息提交成功")])
            else:
                return ActionResult(messages=[BotMessage(text="KYC 信息提交失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionSubmitRiskAssessment(Action):
    name = "action_submit_risk_assessment"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            customer_no = action_kwargs.get("customer_no", "")
            risk_level = action_kwargs.get("risk_level", "")
            assessment_result = action_kwargs.get("assessment_result", "")
            result = await submit_customer_risk_assessment(
                customer_no=customer_no,
                risk_level=risk_level,
                assessment_result=assessment_result,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="风险测评提交成功")])
            else:
                return ActionResult(messages=[BotMessage(text="风险测评提交失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionAddContact(Action):
    name = "action_add_contact"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            customer_no = action_kwargs.get("customer_no", "")
            contact_type = action_kwargs.get("contact_type", "mobile")
            contact_value = action_kwargs.get("contact_value", "")
            is_primary = action_kwargs.get("is_primary", False)
            result = await add_customer_contact(
                customer_no=customer_no,
                contact_type=contact_type,
                contact_value=contact_value,
                is_primary=is_primary,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="联系方式添加成功")])
            else:
                return ActionResult(messages=[BotMessage(text="联系方式添加失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)