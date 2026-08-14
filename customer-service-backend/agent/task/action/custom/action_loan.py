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


class ActionSubmitCreditApplication(Action):
    name = "action_submit_credit_application"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            product_code = action_kwargs.get("product_code", "")
            amount = action_kwargs.get("amount", 0)
            term_months = action_kwargs.get("term_months", 12)
            result = await submit_credit_application(
                product_code=product_code,
                amount=amount,
                term_months=term_months,
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
            product_code = action_kwargs.get("product_code", "")
            amount = action_kwargs.get("amount", 0)
            term_months = action_kwargs.get("term_months", 12)
            result = await submit_loan_application(
                product_code=product_code,
                amount=amount,
                term_months=term_months,
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
            contract_no = action_kwargs.get("contract_no", "")
            amount = action_kwargs.get("amount")
            result = await disburse_loan(
                contract_no=contract_no,
                amount=amount,
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