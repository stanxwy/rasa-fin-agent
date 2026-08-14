import logging
from datetime import date
from typing import Any

from agent.domain.messages import BotMessage
from agent.domain.state import DialogueState
from agent.task.action.base import Action, ActionResult

from .shared import (
    set_current_customer_no,
    reset_current_customer_no,
    purchase_wealth,
    redeem_wealth,
    confirm_wealth_order,
    cancel_wealth_order,
)

logger = logging.getLogger(__name__)


def _slots(state: DialogueState) -> dict[str, Any]:
    return state.active_task.slots if state.active_task else {}


class ActionPurchaseWealth(Action):
    name = "action_purchase_wealth"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            product_code = s.get("product_code", action_kwargs.get("product_code", ""))
            account_no = s.get("account_no", action_kwargs.get("account_no", ""))
            purchase_amount = s.get("purchase_amount", s.get("amount", action_kwargs.get("purchase_amount", 0)))
            result = await purchase_wealth(
                product_code=product_code,
                account_no=account_no,
                purchase_amount=purchase_amount,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="理财申购成功")])
            else:
                return ActionResult(messages=[BotMessage(text="理财申购失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionRedeemWealth(Action):
    name = "action_redeem_wealth"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            account_no = s.get("account_no", action_kwargs.get("account_no", ""))
            position_id = int(s.get("position_id", action_kwargs.get("position_id", 0)) or 0)
            redeem_share = s.get("redeem_share", s.get("share", action_kwargs.get("redeem_share", 0)))
            result = await redeem_wealth(
                account_no=account_no,
                position_id=position_id,
                redeem_share=redeem_share,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="理财赎回成功")])
            else:
                return ActionResult(messages=[BotMessage(text="理财赎回失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionConfirmWealthOrder(Action):
    name = "action_confirm_wealth_order"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            order_no = s.get("order_no", action_kwargs.get("order_no", ""))
            confirmed_amount = s.get("confirmed_amount", action_kwargs.get("confirmed_amount", 0))
            confirmed_share = s.get("confirmed_share", action_kwargs.get("confirmed_share", 0))
            confirmed_nav = s.get("confirmed_nav", action_kwargs.get("confirmed_nav", 0))
            confirmed_date = s.get("confirmed_date", action_kwargs.get("confirmed_date", date.today().isoformat()))
            result = await confirm_wealth_order(
                order_no=order_no,
                confirmed_amount=confirmed_amount,
                confirmed_share=confirmed_share,
                confirmed_nav=confirmed_nav,
                confirmed_date=confirmed_date,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="理财订单确认成功")])
            else:
                return ActionResult(messages=[BotMessage(text="理财订单确认失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionCancelWealthOrder(Action):
    name = "action_cancel_wealth_order"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            order_no = s.get("order_no", action_kwargs.get("order_no", ""))
            cancel_reason = s.get("cancel_reason", action_kwargs.get("cancel_reason", ""))
            result = await cancel_wealth_order(
                order_no=order_no,
                cancel_reason=cancel_reason,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="理财订单撤销成功")])
            else:
                return ActionResult(messages=[BotMessage(text="理财订单撤销失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)
