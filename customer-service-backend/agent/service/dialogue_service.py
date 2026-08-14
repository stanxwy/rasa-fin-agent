# atguigu/service/dialogue_service.py

from agent.domain.messages import ProcessResult, UserMessage
from agent.domain.state import DialogueState, Session
from agent.engine.dialogue_engine import DialogueEngine
from agent.repository.dialogue_state_repo import DialogueStateRepository


class DialogueService:

    def __init__(self, 
        dialogue_state_repo: DialogueStateRepository,
        dialogue_engine: DialogueEngine):
        self.dialogue_state_repo = dialogue_state_repo
        self.dialogue_engine = dialogue_engine

    async def process_message(self, user_message: UserMessage) -> ProcessResult:

        dialogue_state: DialogueState = await self.dialogue_state_repo.load_state(user_message.sender_id)

        dialogue_state = await self.dialogue_engine.process_message(dialogue_state, user_message)

        await self.dialogue_state_repo.save_state(dialogue_state)

        return ProcessResult(
            sender_id=user_message.sender_id,
            message_id=user_message.message_id,
            messages=dialogue_state.last_turn_messages(),
        )


    async def load_chat_history(
        self, sender_id: str, session_id: str | None = None
    ) -> list[Session]:
        """
        Load the sender's chat history as domain sessions.

        When `session_id` is provided, only that session is returned —
        this is how the frontend shows "current session only".

        Returns raw domain objects (no DTO mapping) so the service stays
        protocol-agnostic. The HTTP layer converts these via
        `agent.converters.chat_converter`.
        """
        state = await self.dialogue_state_repo.load_state(sender_id)
        if session_id:
            return [s for s in state.sessions if s.session_id == session_id]
        return state.sessions

    async def list_sessions(
        self, sender_id: str
    ) -> tuple[list[Session], str | None]:
        """
        Return the sender's sessions and the current session id.

        The HTTP layer maps these into `SessionSummary` objects, flagging
        which session is the active one.
        """
        state = await self.dialogue_state_repo.load_state(sender_id)
        return state.sessions, state.current_session_id

    async def reset_session(self, sender_id: str) -> None:
        """
        Close the sender's current session so the next message starts a
        brand-new one. Used by the UI "新对话" button.
        """
        state = await self.dialogue_state_repo.load_state(sender_id)
        state.close_current_session()
        await self.dialogue_state_repo.save_state(state)

    async def delete_session(self, sender_id: str, session_id: str) -> bool:
        """
        Permanently remove a single session for the sender.

        Returns True if a session was actually removed. If the deleted
        session happened to be the current one, `current_session_id` is
        cleared so the UI falls back to a fresh "new conversation" view.
        """
        state = await self.dialogue_state_repo.load_state(sender_id)
        before = len(state.sessions)
        state.sessions = [s for s in state.sessions if s.session_id != session_id]
        if state.current_session_id == session_id:
            state.current_session_id = None
        if len(state.sessions) != before:
            await self.dialogue_state_repo.save_state(state)
            return True
        return False