import logging

from agent.domain.messages import BotMessage
from agent.domain.state import DialogueState
from agent.knowledge.intents import KnowledgeIntent
from agent.knowledge.providers import KnowledgeChunk
from agent.knowledge.registry import KnowledgeProviderRegistry
from agent.knowledge.responder import KnowledgeResponder

logger = logging.getLogger(__name__)

class KnowledgeHandler:

    def __init__(
        self,
        knowledge_intents: dict[str, KnowledgeIntent],
        provider_registry: KnowledgeProviderRegistry,
        knowledge_responder: KnowledgeResponder):

        self.knowledge_intents = knowledge_intents
        self.provider_registry = provider_registry
        self.knowledge_responder = knowledge_responder


    async def handle(self, intents: list[str], state: DialogueState) -> list[BotMessage]:

        provider_ids: list[str] = self._get_provider_ids_by_intents(intents)
        logger.info(f"Retrieving knowledge from providers {provider_ids}")

        chunks: list[KnowledgeChunk] = []
        for provider_id in provider_ids:
            provider = self.provider_registry.get(provider_id)

            logger.info(f"Retrieving knowledge from provider {provider_id}")
            current_chunks = await provider.retrieve(state)
            logger.info(f"Retrieved {len(current_chunks)} chunks from provider {provider_id}")

            chunks.extend(current_chunks)

        return await self.knowledge_responder.respond(
            user_message=state.pending_turn.user_message,
            recent_turns=state.current_session().turns,
            chunks=chunks
        )

    # intent -> provider_id 是一对多的关系
    def _get_provider_ids_by_intents(self, intents: list[str]) -> list[str]:
        provider_ids: list[str] = []
        for intent in intents:
            provider_ids.extend(self.knowledge_intents[intent].provider_ids)
        return list(set(provider_ids))