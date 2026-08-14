import logging
from typing import Any

from agent.domain.messages import BotMessage
from agent.domain.state import DialogueState
from agent.task.action.base import Action, ActionResult

from .shared import (
    set_current_customer_no,
    reset_current_customer_no,
    submit_repayment,
    create_repayment_authorization,
    submit_fee_reduction,
)

logger = logging.getLogger(__name__)


class ActionSubmitRepayment(Action):
    name = "action_submit_repayment"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            contract_no = action_kwargs.get("contract_no", "")
            amount = action_kwargs.get("amount", 0)
            repayment_method = action_kwargs.get("repayment_method", "bank_card")
            result = await submit_repayment(
                contract_no=contract_no,
                amount=amount,
                repayment_method=repayment_method,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="还款提交成功")])
            else:
                return ActionResult(messages=[BotMessage(text="还款提交失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionCreateRepaymentAuthorization(Action):
    name = "action_create_repayment_authorization"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            contract_no = action_kwargs.get("contract_no", "")
            auto_repay = action_kwargs.get("auto_repay", True)
            result = await create_repayment_authorization(
                contract_no=contract_no,
                auto_repay=auto_repay,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="自动还款授权创建成功")])
            else:
                return ActionResult(messages=[BotMessage(text="自动还款授权创建失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionSubmitFeeReduction(Action):
    name = "action_submit_fee_reduction"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            contract_no = action_kwargs.get("contract_no", "")
            reason = action_kwargs.get("reason", "")
            amount = action_kwargs.get("amount")
            result = await submit_fee_reduction(
                contract_no=contract_no,
                reason=reason,
                amount=amount,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="费用减免申请提交成功")])
            else:
                return ActionResult(messages=[BotMessage(text="费用减免申请提交失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)