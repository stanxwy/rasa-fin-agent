import asyncio
import json
import logging

from agent.domain.messages import BotMessage
from agent.domain.state import DialogueState
from agent.knowledge.intents import KnowledgeIntent
from agent.knowledge.providers import KnowledgeChunk
from agent.knowledge.registry import KnowledgeProviderRegistry
from agent.knowledge.responder import KnowledgeResponder
from agent.task.action.custom.shared import (
    fetch_customer,
    fetch_customer_accounts,
    fetch_customer_credit_limits,
    fetch_customer_wealth_positions,
    set_current_customer_no,
    reset_current_customer_no,
)

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

        customer_no = state.sender_id
        token = set_current_customer_no(customer_no)

        try:
            chunks: list[KnowledgeChunk] = []

            knowledge_tasks = [
                self.provider_registry.get(pid).retrieve(state)
                for pid in provider_ids
            ]

            context_task = self._prefetch_customer_context(customer_no)

            chunks_results, customer_context = await asyncio.gather(
                asyncio.gather(*knowledge_tasks),
                context_task,
            )

            for provider_id, current_chunks in zip(provider_ids, chunks_results):
                logger.info(f"Retrieved {len(current_chunks)} chunks from provider {provider_id}")
                chunks.extend(current_chunks)

            return await self.knowledge_responder.respond(
                user_message=state.pending_turn.user_message,
                recent_turns=state.current_session().turns,
                chunks=chunks,
                customer_context=customer_context,
            )
        finally:
            reset_current_customer_no(token)

    async def _prefetch_customer_context(self, customer_no: str) -> str:
        try:
            customer, accounts, credit_limits, wealth_positions = await asyncio.gather(
                fetch_customer(customer_no),
                fetch_customer_accounts(customer_no),
                fetch_customer_credit_limits(customer_no),
                fetch_customer_wealth_positions(customer_no),
            )
        except Exception as e:
            logger.warning(f"Failed to prefetch customer context: {e}")
            return ""

        parts: list[str] = []

        if customer:
            parts.append(f"【客户档案】\n{json.dumps(customer, ensure_ascii=False, indent=2)}")

        if accounts:
            parts.append(f"【客户账户列表】\n{json.dumps(accounts, ensure_ascii=False, indent=2)}")

        if credit_limits:
            parts.append(f"【客户授信额度】\n{json.dumps(credit_limits, ensure_ascii=False, indent=2)}")

        if wealth_positions:
            parts.append(f"【客户理财持仓】\n{json.dumps(wealth_positions, ensure_ascii=False, indent=2)}")

        if not parts:
            return ""

        return "以下为当前客户的基本信息，供参考作答（请勿在回复中直接输出原始数据）：\n" + "\n\n".join(parts)

    # intent -> provider_id 是一对多的关系
    def _get_provider_ids_by_intents(self, intents: list[str]) -> list[str]:
        provider_ids: list[str] = []
        for intent in intents:
            provider_ids.extend(self.knowledge_intents[intent].provider_ids)
        return list(set(provider_ids))
