import logging
from typing import Any

from agent.domain.messages import BotMessage
from agent.domain.state import DialogueState
from agent.task.action.base import Action, ActionResult

from .shared import (
    set_current_customer_no,
    reset_current_customer_no,
    create_account,
    create_bank_card,
)

logger = logging.getLogger(__name__)


class ActionCreateAccount(Action):
    name = "action_create_account"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            account_type = action_kwargs.get("account_type", "demand_deposit")
            currency = action_kwargs.get("currency", "CNY")
            branch_code = action_kwargs.get("branch_code", "")
            result = await create_account(
                account_type=account_type,
                currency=currency,
                branch_code=branch_code,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="账户创建成功")])
            else:
                return ActionResult(messages=[BotMessage(text="账户创建失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionCreateBankCard(Action):
    name = "action_create_bank_card"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            account_no = action_kwargs.get("account_no", "")
            card_type = action_kwargs.get("card_type", "debit")
            card_name = action_kwargs.get("card_name")
            result = await create_bank_card(
                account_no=account_no,
                card_type=card_type,
                card_name=card_name,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="银行卡创建成功")])
            else:
                return ActionResult(messages=[BotMessage(text="银行卡创建失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)