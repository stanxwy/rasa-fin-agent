from typing import Literal

from pydantic import BaseModel


class ChatObject(BaseModel):
    id: str
    type: str
    title: str | None = None
    attributes: dict = {}


class ChatRequest(BaseModel):
    sender_id: str
    message_id: str | None = None
    text: str | None = None
    object: ChatObject | None = None


class ChatBotMessage(BaseModel):
    text: str | None = None
    object: ChatObject | None = None
    # 消息时间（ISO 8601 字符串，UTC）。前端据此展示发送时间。
    timestamp: str | None = None


class ChatResponse(BaseModel):
    sender_id: str
    message_id: str
    messages: list[ChatBotMessage]


class HistoryMessage(BaseModel):
    role: Literal["user", "bot"]
    text: str | None = None
    object: ChatObject | None = None
    # 消息时间（ISO 8601 字符串，UTC）。前端据此展示发送时间。
    timestamp: str | None = None
    # 所属会话 ID。前端据此按会话分组 / 筛选。
    session_id: str | None = None

class HistoryResponse(BaseModel):
    sender_id: str
    messages: list[HistoryMessage]


class SessionSummary(BaseModel):
    session_id: str
    # 会话创建 / 最近活跃时间（ISO 8601 字符串，UTC）。
    started_at: str
    last_activity_at: str
    # 会话内消息条数
    message_count: int
    # 会话预览（最近一条用户/客服文本，截断）。
    preview: str | None = None
    # 是否为当前进行中的会话
    is_current: bool = False

class SessionsResponse(BaseModel):
    sender_id: str
    sessions: list[SessionSummary]


class SessionDeleteRequest(BaseModel):
    sender_id: str
    session_id: str