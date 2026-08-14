"""
DTO <-> Domain converters for chat-related objects.

These pure functions are responsible for:
- Mapping Pydantic request/response models to domain models
- Ensuring protocol-agnostic reuse

Why this exists:
- Keeps HTTP layer thin (Single Responsibility Principle)
- Enables reuse across HTTP, WebSocket, gRPC, and background consumers
- Simplifies unit testing (no FastAPI / Request dependency)

Rules:
- No I/O
- No business logic
- No framework imports (except Pydantic)
"""
import time
import uuid
from datetime import datetime, timezone

from agent.api.schemas import (
    ChatBotMessage,
    ChatObject,
    ChatRequest,
    ChatResponse,
    HistoryMessage,
    HistoryResponse,
    SessionsResponse,
    SessionSummary,
)
from agent.domain.messages import (
    BotMessage,
    FocusedObject,
    MessageType,
    ProcessResult,
    UserMessage,
)
from agent.domain.state import Session


def _to_iso(ts: float | None) -> str | None:
    """把 epoch 秒转换为 ISO 8601 (UTC) 字符串；无值返回 None。"""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def build_user_message(chat_request: ChatRequest) -> UserMessage:
    """
    Convert a ChatRequest DTO into a domain-level UserMessage.

    This function is pure and framework-independent, allowing reuse
    across HTTP endpoints, WebSocket handlers, and async consumers.
    """
    return UserMessage(
        sender_id=chat_request.sender_id,
        message_id=chat_request.message_id if chat_request.message_id else str(uuid.uuid4()),
        type=MessageType.TEXT if chat_request.text else MessageType.OBJECT,
        text=chat_request.text,
        object=FocusedObject(**chat_request.object.model_dump(mode='json')) if chat_request.object else None,
        timestamp=time.time(),
    )

def build_chat_response(process_result: ProcessResult) -> ChatResponse:
    return ChatResponse(
        sender_id=process_result.sender_id,
        message_id=process_result.message_id,
        messages=[
            ChatBotMessage(
                text=bot_msg.text,
                object=ChatObject(**bot_msg.object.model_dump(mode='json')) if bot_msg.object else None,
                timestamp=_to_iso(bot_msg.timestamp),
            )
            for bot_msg in process_result.messages
        ]
    )


def build_user_history_message(session_id: str, user_message: UserMessage) -> HistoryMessage:
    user_obj = ChatObject(**user_message.object.model_dump()) if user_message.object else None
    return HistoryMessage(
        session_id=session_id,
        role="user",
        text=user_message.text,
        object=user_obj,
        timestamp=_to_iso(user_message.timestamp),
    )


def build_bot_history_message(session_id: str, bot_message: BotMessage) -> HistoryMessage:
    bot_obj = ChatObject(**bot_message.object.model_dump()) if bot_message.object else None
    return HistoryMessage(
        session_id=session_id,
        role="bot",
        text=bot_message.text,
        object=bot_obj,
        timestamp=_to_iso(bot_message.timestamp),
    )


def build_history_response(
    sender_id: str,
    sessions: list[Session],
    session_id: str | None = None,
) -> HistoryResponse:
    """
    Convert domain sessions into the HTTP history response.

    Flattens every (or, when `session_id` is given, only the matching)
    session's turns into a single ordered list of `HistoryMessage`,
    preserving each message's owning `session_id`.
    """
    messages: list[HistoryMessage] = []
    target = [s for s in sessions if s.session_id == session_id] if session_id else sessions
    for session in target:
        for turn in session.turns:
            messages.append(build_user_history_message(session.session_id, turn.user_message))
            messages.extend(
                build_bot_history_message(session.session_id, bot_msg)
                for bot_msg in turn.bot_messages
            )
    return HistoryResponse(sender_id=sender_id, messages=messages)


def _session_preview(session: Session) -> str | None:
    """取会话预览文本：优先最近一条用户文本，回退到首条客服文本。"""
    for turn in reversed(session.turns):
        if turn.user_message and turn.user_message.text:
            return turn.user_message.text[:40]
    for turn in session.turns:
        for bot_msg in turn.bot_messages:
            if bot_msg.text:
                return bot_msg.text[:40]
    return None


def build_sessions_response(
    sender_id: str,
    sessions: list[Session],
    current_session_id: str | None = None,
) -> SessionsResponse:
    """
    将会话列表转换为 HTTP 响应。

    按最近活跃时间倒序排列，并标注哪个是当前会话。
    """
    items: list[SessionSummary] = []
    for session in sessions:
        message_count = sum(
            len(turn.bot_messages) + (1 if turn.user_message else 0)
            for turn in session.turns
        )
        items.append(
            SessionSummary(
                session_id=session.session_id,
                started_at=_to_iso(session.started_at) or "",
                last_activity_at=_to_iso(session.last_activity_at) or "",
                message_count=message_count,
                preview=_session_preview(session),
                is_current=(session.session_id == current_session_id),
            )
        )
    items.sort(key=lambda x: x.last_activity_at, reverse=True)
    return SessionsResponse(sender_id=sender_id, sessions=items)
