import logging
from typing import Any

from agent.domain.messages import BotMessage
from agent.domain.state import DialogueState
from agent.task.action.base import Action, ActionResult

from .shared import (
    set_current_customer_no,
    reset_current_customer_no,
    submit_credit_application,
    submit_loan_application,
    disburse_loan,
)

logger = logging.getLogger(__name__)


def _slots(state: DialogueState) -> dict[str, Any]:
    return state.active_task.slots if state.active_task else {}


class ActionSubmitCreditApplication(Action):
    name = "action_submit_credit_application"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            product_code = s.get("product_code", action_kwargs.get("product_code", ""))
            apply_limit_amount = s.get("apply_limit_amount", s.get("loan_amount", s.get("amount", action_kwargs.get("apply_limit_amount", 0))))
            result = await submit_credit_application(
                product_code=product_code,
                apply_limit_amount=apply_limit_amount,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="授信申请提交成功")])
            else:
                return ActionResult(messages=[BotMessage(text="授信申请提交失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionSubmitLoanApplication(Action):
    name = "action_submit_loan_application"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            limit_no = s.get("limit_no", s.get("product_code", action_kwargs.get("limit_no", "")))
            apply_amount = s.get("apply_amount", s.get("loan_amount", s.get("amount", action_kwargs.get("apply_amount", 0))))
            apply_term_months = int(s.get("apply_term_months", s.get("term_months", action_kwargs.get("apply_term_months", 12))) or 12)
            repayment_method = s.get("repayment_method", action_kwargs.get("repayment_method", "equal_installment"))
            result = await submit_loan_application(
                limit_no=limit_no,
                apply_amount=apply_amount,
                apply_term_months=apply_term_months,
                repayment_method=repayment_method,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="贷款申请提交成功")])
            else:
                return ActionResult(messages=[BotMessage(text="贷款申请提交失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionDisburseLoan(Action):
    name = "action_disburse_loan"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            contract_no = s.get("contract_no", action_kwargs.get("contract_no", ""))
            account_no = s.get("account_no", action_kwargs.get("account_no", ""))
            disbursement_amount = s.get("disbursement_amount", s.get("amount", action_kwargs.get("disbursement_amount", 0)))
            result = await disburse_loan(
                contract_no=contract_no,
                account_no=account_no,
                disbursement_amount=disbursement_amount,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="贷款放款成功")])
            else:
                return ActionResult(messages=[BotMessage(text="贷款放款失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)
