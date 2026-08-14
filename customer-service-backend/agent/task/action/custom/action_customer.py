import logging
from datetime import date, timedelta
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


def _slots(state: DialogueState) -> dict[str, Any]:
    return state.active_task.slots if state.active_task else {}


class ActionCreateCustomer(Action):
    name = "action_create_customer"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            customer_type = s.get("customer_type", action_kwargs.get("customer_type", "personal"))
            customer_name = s.get("customer_name", action_kwargs.get("customer_name", ""))
            branch_code = s.get("branch_code", action_kwargs.get("branch_code", ""))
            channel_code = s.get("channel_code", action_kwargs.get("channel_code", "MOBILE_BANK"))
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
            s = _slots(state)
            customer_no = s.get("customer_no", state.sender_id)
            fields = {k: v for k, v in s.items() if k != "customer_no"}
            fields.update({k: v for k, v in action_kwargs.items() if k != "customer_no"})
            result = await update_customer(customer_no, **fields)
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
            s = _slots(state)
            customer_no = s.get("customer_no", state.sender_id)
            identity_type = s.get("identity_type", action_kwargs.get("identity_type", "id_card"))
            identity_no = s.get("identity_no", action_kwargs.get("identity_no", ""))
            legal_name = s.get("legal_name", s.get("identity_name", action_kwargs.get("legal_name", "")))
            identity_valid_to = s.get("identity_valid_to", action_kwargs.get("identity_valid_to"))
            result = await submit_customer_identity(
                customer_no=customer_no,
                identity_type=identity_type,
                identity_no=identity_no,
                legal_name=legal_name,
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
            s = _slots(state)
            customer_no = s.get("customer_no", state.sender_id)
            occupation = s.get("occupation", action_kwargs.get("occupation", ""))
            industry = s.get("industry", action_kwargs.get("industry", ""))
            annual_income_amount = s.get("annual_income_amount", action_kwargs.get("annual_income_amount", 0))
            income_currency_code = s.get("income_currency_code", action_kwargs.get("income_currency_code", "CNY"))
            fund_source = s.get("fund_source", action_kwargs.get("fund_source", ""))
            employment_status = s.get("employment_status", action_kwargs.get("employment_status", "employed"))
            result = await submit_customer_kyc(
                customer_no=customer_no,
                occupation=occupation,
                industry=industry,
                annual_income_amount=annual_income_amount,
                income_currency_code=income_currency_code,
                fund_source=fund_source,
                employment_status=employment_status,
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
            s = _slots(state)
            customer_no = s.get("customer_no", state.sender_id)
            assessment_type = s.get("assessment_type", action_kwargs.get("assessment_type", "customer"))
            assessment_score = int(s.get("assessment_score", action_kwargs.get("assessment_score", 0)) or 0)
            valid_from = s.get("valid_from", action_kwargs.get("valid_from", date.today().isoformat()))
            valid_to = s.get("valid_to", action_kwargs.get("valid_to", (date.today() + timedelta(days=365)).isoformat()))
            adjust_reason = s.get("adjust_reason", s.get("risk_level", s.get("assessment_result", action_kwargs.get("adjust_reason", ""))))
            result = await submit_customer_risk_assessment(
                customer_no=customer_no,
                assessment_type=assessment_type,
                assessment_score=assessment_score,
                valid_from=valid_from,
                valid_to=valid_to,
                adjust_reason=adjust_reason,
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
            s = _slots(state)
            customer_no = s.get("customer_no", state.sender_id)
            contact_type = s.get("contact_type", action_kwargs.get("contact_type", "mobile"))
            contact_value = s.get("contact_value", action_kwargs.get("contact_value", ""))
            is_primary = s.get("is_primary", action_kwargs.get("is_primary", False))
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
