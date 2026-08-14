"""
HTTP layer for chat endpoints.

Responsibilities:
- Define HTTP routes and methods
- Validate incoming requests via Pydantic models
- Delegate business logic to services
- Transform domain models into HTTP responses

This module MUST NOT contain:
- Business rules
- Domain logic
- Complex data mapping

All request/response mapping logic lives in `agent.converters`.
This keeps endpoints thin, testable, and reusable across protocols
(e.g. HTTP, WebSocket, gRPC, background jobs).
"""
from fastapi import APIRouter, Depends

from agent.api.dependencies import get_dialogue_service
from agent.api.schemas import (
    ChatRequest,
    ChatResponse,
    HistoryResponse,
    SessionDeleteRequest,
    SessionsResponse,
)
from agent.converters.chat_converter import (
    build_chat_response,
    build_history_response,
    build_sessions_response,
    build_user_message,
)
from agent.domain.messages import ProcessResult
from agent.service.dialogue_service import DialogueService

router = APIRouter()

@router.post("/api/chat")
async def chat_endpoint(
    chat_request: ChatRequest,
    dialogue_service: DialogueService = Depends(get_dialogue_service)
) -> ChatResponse:
    """
    Handle an incoming chat request.

    Flow:
    1. Convert HTTP request DTO -> domain model
    2. Delegate processing to DialogueService
    3. Convert domain result -> HTTP response DTO

    Note:
    - This endpoint is intentionally kept thin.
    - All mapping logic resides in `agent.converters.chat_converter`.
    """
    user_message = build_user_message(chat_request)

    process_result: ProcessResult = await dialogue_service.process_message(user_message)

    return build_chat_response(process_result)


@router.get("/api/chat/history")
async def history(
    sender_id: str,
    session_id: str | None = None,
    service: DialogueService = Depends(get_dialogue_service)
) -> HistoryResponse:
    """
    Retrieve the chat history for a given sender.

    When `session_id` is provided, only that session is returned — this is
    how the frontend shows "current session only".

    Flow:
    1. Delegate to DialogueService to load domain sessions
    2. Convert domain sessions -> HTTP response DTO via converter

    Note:
    - This endpoint is intentionally kept thin.
    - All mapping logic resides in `agent.converters.chat_converter`.
    """
    sessions = await service.load_chat_history(sender_id, session_id)
    return build_history_response(sender_id, sessions, session_id)


@router.get("/api/chat/sessions")
async def list_sessions(
    sender_id: str,
    service: DialogueService = Depends(get_dialogue_service)
) -> SessionsResponse:
    """
    Return the sender's conversation list (sessions).

    Each session carries a preview, message count, and an `is_current`
    flag so the UI can default to the active conversation.
    """
    sessions, current_session_id = await service.list_sessions(sender_id)
    return build_sessions_response(sender_id, sessions, current_session_id)


@router.post("/api/chat/session/reset")
async def reset_session(
    sender_id: str,
    service: DialogueService = Depends(get_dialogue_service)
):
    """
    Close the sender's current session so the next message starts a new one.
    Backs the UI "新对话" button.
    """
    await service.reset_session(sender_id)
    return {"ok": True}


@router.post("/api/chat/session/delete")
async def delete_session(
    payload: SessionDeleteRequest,
    service: DialogueService = Depends(get_dialogue_service)
):
    """
    Permanently delete a single conversation (session) for the sender.
    Backs the UI per-session "删除" button.
    """
    deleted = await service.delete_session(payload.sender_id, payload.session_id)
    return {"deleted": deleted}