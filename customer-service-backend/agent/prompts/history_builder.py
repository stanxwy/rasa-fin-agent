import json
from typing import Any

from agent.domain.messages import (
    BotMessage,
    FocusedObject,
    MessageType,
    ObjectType,
    UserMessage,
)
from agent.domain.state import Turn


class HistoryBuilder:

    @staticmethod
    def build(turns: list[Turn]) -> str:
        msgs: list[str] = []
        for turn in turns:
            user_message = turn.user_message
            user_message_str = HistoryBuilder._render_user_message(user_message)
            msgs.append(f"USER: {user_message_str}")

            for bot_msg in turn.bot_messages:
                bot_msg_str = HistoryBuilder._render_bot_message(bot_msg)
                msgs.append(f"BOT: {bot_msg_str}")
        return "\n".join(msgs)

    @staticmethod
    def render_user_message(user_message: UserMessage) -> str:
        return HistoryBuilder._render_user_message(user_message)

    @staticmethod
    def _render_user_message(user_message: UserMessage) -> str:
        if user_message.type == MessageType.TEXT:
            return HistoryBuilder._render_text_msg(user_message.text)
        else:
            return HistoryBuilder._render_obj_msg(user_message.object)

    @classmethod
    def _render_bot_message(cls, bot_msg: BotMessage) -> str:
        if bot_msg.text:
            return HistoryBuilder._render_text_msg(bot_msg.text)
        else:
            return HistoryBuilder._render_obj_msg(bot_msg.object) # should not come here


    @staticmethod
    def _render_text_msg(text: str) -> str:
        return text.strip()

    @classmethod
    def _render_obj_msg(cls, object_msg: FocusedObject) -> str:
        label = "订单对象" if object_msg.type == ObjectType.ORDER else "商品对象"
        id = object_msg.id
        title = object_msg.title
        attributes: dict[str, Any] = object_msg.attributes
        # attributes_str = " ".join([f"{key}={value}" for key, value in attributes.items()])
        return f"[label={label}, id={id}, title={title}, attributes={json.dumps(attributes, ensure_ascii=False)}]"


if __name__ == '__main__':
    def test_build_single_text_turn():
        user_msg = UserMessage(
            sender_id="user_001",
            message_id="msg_001",
            type=MessageType.TEXT,
            text="我想查询订单信息"
        )
        bot_msg1 = BotMessage(text="你好")
        bot_msg2 = BotMessage(text="请提供订单编号")

        turn = Turn(
            turn_id="turn_001",
            user_message=user_msg,
            bot_messages=[bot_msg1, bot_msg2]
        )
        result = HistoryBuilder.build([turn])
        print(f"结果:\n{result}")

    def test_build_with_object_message():
        focused_obj = FocusedObject(
            id="order_12345",
            type="order",
            title="iPhone 15 Pro Max",
            attributes={"price": "9999", "status": "已发货"}
        )
        user_msg = UserMessage(
            sender_id="user_001",
            message_id="msg_001",
            type=MessageType.OBJECT,
            object=focused_obj
        )

        bot_msg = BotMessage(text="我看到您点击了这个订单，请问需要什么帮助？")

        turn = Turn(
            turn_id="turn_001",
            user_message=user_msg,
            bot_messages=[bot_msg]
        )
        result = HistoryBuilder.build([turn])
        print(f"结果:\n{result}")

    test_build_single_text_turn()
    test_build_with_object_message()

"""
ython -m agent.prompts.history_builder
结果:
USER: 我想查询订单信息
BOT: 你好
BOT: 请提供订单编号
结果:
USER: [label=订单对象, id=order_12345, title=iPhone 15 Pro Max, attributes=price=9999 status=已发货]
BOT: 我看到您点击了这个订单，请问需要什么帮助？
"""