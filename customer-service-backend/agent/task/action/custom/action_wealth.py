import logging
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


class ActionPurchaseWealth(Action):
    name = "action_purchase_wealth"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            product_code = action_kwargs.get("product_code", "")
            amount = action_kwargs.get("amount")
            share = action_kwargs.get("share")
            result = await purchase_wealth(
                product_code=product_code,
                amount=amount,
                share=share,
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
            product_code = action_kwargs.get("product_code", "")
            share = action_kwargs.get("share")
            amount = action_kwargs.get("amount")
            result = await redeem_wealth(
                product_code=product_code,
                share=share,
                amount=amount,
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
            order_no = action_kwargs.get("order_no", "")
            result = await confirm_wealth_order(order_no)
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
            order_no = action_kwargs.get("order_no", "")
            result = await cancel_wealth_order(order_no)
            if result:
                return ActionResult(messages=[BotMessage(text="理财订单撤销成功")])
            else:
                return ActionResult(messages=[BotMessage(text="理财订单撤销失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)