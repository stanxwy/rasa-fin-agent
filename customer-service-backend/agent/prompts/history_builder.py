import json
from typing import Any

from agent.domain.messages import (
    BotMessage,
    FocusedObject,
    MessageType,
    UserMessage,
)
from agent.domain.state import Turn


class HistoryBuilder:

    # 对象标签映射，由 singleton 启动时通过 configure() 注入（来自 objects.yml）。
    _object_labels: dict[str, str] = {}

    @classmethod
    def configure(cls, labels: dict[str, str]) -> None:
        """注入对象标签配置（type → label），来自 objects.yml。"""
        cls._object_labels = labels

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
        label = cls._object_labels.get(object_msg.type, "业务对象")
        id = object_msg.id
        title = object_msg.title
        attributes: dict[str, Any] = object_msg.attributes
        return f"[label={label}, id={id}, title={title}, attributes={json.dumps(attributes, ensure_ascii=False)}]"