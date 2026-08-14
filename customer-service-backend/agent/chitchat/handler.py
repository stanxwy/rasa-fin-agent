from agent.chitchat.responder import ChitchatResponder
from agent.domain.messages import BotMessage
from agent.domain.state import DialogueState


class ChitchatHandler:
    def __init__(self, responder: ChitchatResponder):
        self.responder = responder

    async def handle(self, state: DialogueState) -> list[BotMessage]:
        pending_turn = state.pending_turn
        user_message = pending_turn.user_message
        recent_turns = state.current_session().turns

        return await self.responder.respond(
            user_message=user_message,
            recent_turns=recent_turns,
        )