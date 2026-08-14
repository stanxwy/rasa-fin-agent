import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from agent.domain.state import DialogueState
from agent.task.action.custom.shared import fetch_logistics, fetch_order, fetch_product

logger = logging.getLogger(__name__)

class KnowledgeChunk(BaseModel):
    content: str
    

class KnowledgeProvider(ABC):
    provider_id = ""

    @abstractmethod
    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]: ...


class ProductAPIProvider(KnowledgeProvider):
    provider_id = 'api.product'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        product_id = state.focused_object.id
        data: dict[str, Any] = await fetch_product(product_id)
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"商品信息:\n{text}")]

class OrderAPIProvider(KnowledgeProvider):
    provider_id = 'api.order'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        order_number = state.focused_object.id
        order_payload, logistics_payload = await asyncio.gather(
            fetch_order(order_number),
            fetch_logistics(order_number),
        )
        return [
            KnowledgeChunk(
                content="订单与物流信息：\n"
                        + json.dumps({
                        "order_number": order_number,
                        "order": order_payload,
                        "logistics": logistics_payload,
                         },ensure_ascii=False,indent=2)
            )
        ]

class FAQProvider(KnowledgeProvider):
    provider_id = 'faq.default'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        # TODO
        return [KnowledgeChunk(content="FAQ：未检索到相关问题")]

class RAGProvider(KnowledgeProvider):
    provider_id = 'rag.default'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        # TODO
        return [KnowledgeChunk(content="RAG：未检索到相关信息")]