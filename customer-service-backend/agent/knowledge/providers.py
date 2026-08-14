import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from agent.domain.state import DialogueState
from agent.task.action.custom.shared import (
    fetch_account,
    fetch_card,
    fetch_deposit_products,
    fetch_fund_product,
    fetch_fund_products,
    fetch_loan_contract,
    fetch_loan_product,
    fetch_loan_products,
    fetch_transaction,
    fetch_transfer_records,
    fetch_wealth_product,
    fetch_wealth_products,
)

logger = logging.getLogger(__name__)


class KnowledgeChunk(BaseModel):
    content: str


class KnowledgeProvider(ABC):
    provider_id = ""

    @abstractmethod
    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]: ...


# ------------------------------------------------------------------ #
#  银行账户                                                           #
# ------------------------------------------------------------------ #

class BankAccountAPIProvider(KnowledgeProvider):
    provider_id = 'api.bank_account'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        account_no = state.focused_object.id
        data: dict[str, Any] | None = await fetch_account(account_no)
        if data is None:
            return [KnowledgeChunk(content=f"未查询到账户 {account_no} 的信息。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"银行账户信息:\n{text}")]


# ------------------------------------------------------------------ #
#  银行卡                                                             #
# ------------------------------------------------------------------ #

class BankCardAPIProvider(KnowledgeProvider):
    provider_id = 'api.bank_card'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        card_no = state.focused_object.id
        data: dict[str, Any] | None = await fetch_card(card_no)
        if data is None:
            return [KnowledgeChunk(content=f"未查询到银行卡 {card_no} 的信息。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"银行卡信息:\n{text}")]


# ------------------------------------------------------------------ #
#  信用卡                                                             #
# ------------------------------------------------------------------ #

class CreditCardAPIProvider(KnowledgeProvider):
    provider_id = 'api.credit_card'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        card_no = state.focused_object.id
        data: dict[str, Any] | None = await fetch_card(card_no)
        if data is None:
            return [KnowledgeChunk(content=f"未查询到信用卡 {card_no} 的信息。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"信用卡信息:\n{text}")]


# ------------------------------------------------------------------ #
#  存款产品                                                           #
# ------------------------------------------------------------------ #

class DepositAPIProvider(KnowledgeProvider):
    provider_id = 'api.deposit'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        product_code = state.focused_object.id
        products = await fetch_deposit_products()
        if products is None:
            return [KnowledgeChunk(content="未查询到存款产品信息。")]
        # 尝试按 product_code 精确匹配
        matched = [p for p in products if p.get("product_code") == product_code]
        if matched:
            text = json.dumps(matched[0], ensure_ascii=False, indent=2)
            return [KnowledgeChunk(content=f"存款产品信息:\n{text}")]
        # 无精确匹配则返回全部存款产品列表
        text = json.dumps(products, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"存款产品列表:\n{text}")]


# ------------------------------------------------------------------ #
#  贷款                                                               #
# ------------------------------------------------------------------ #

class LoanAPIProvider(KnowledgeProvider):
    provider_id = 'api.loan'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        identifier = state.focused_object.id
        # 先尝试作为合同号查询贷款合同
        contract = await fetch_loan_contract(identifier)
        if contract is not None:
            text = json.dumps(contract, ensure_ascii=False, indent=2)
            return [KnowledgeChunk(content=f"贷款合同信息:\n{text}")]
        # 再尝试作为产品编码查询贷款产品
        product = await fetch_loan_product(identifier)
        if product is not None:
            text = json.dumps(product, ensure_ascii=False, indent=2)
            return [KnowledgeChunk(content=f"贷款产品信息:\n{text}")]
        # 都查不到则返回贷款产品列表
        products = await fetch_loan_products()
        if products:
            text = json.dumps(products, ensure_ascii=False, indent=2)
            return [KnowledgeChunk(content=f"贷款产品列表:\n{text}")]
        return [KnowledgeChunk(content=f"未查询到贷款 {identifier} 的信息。")]


# ------------------------------------------------------------------ #
#  理财产品                                                           #
# ------------------------------------------------------------------ #

class WealthProductAPIProvider(KnowledgeProvider):
    provider_id = 'api.wealth_product'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        product_code = state.focused_object.id
        data: dict[str, Any] | None = await fetch_wealth_product(product_code)
        if data is None:
            # 查不到详情则返回理财产品列表
            products = await fetch_wealth_products()
            if products:
                text = json.dumps(products, ensure_ascii=False, indent=2)
                return [KnowledgeChunk(content=f"理财产品列表:\n{text}")]
            return [KnowledgeChunk(content=f"未查询到理财产品 {product_code} 的信息。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"理财产品信息:\n{text}")]


# ------------------------------------------------------------------ #
#  基金产品                                                           #
# ------------------------------------------------------------------ #

class FundProductAPIProvider(KnowledgeProvider):
    provider_id = 'api.fund_product'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        product_code = state.focused_object.id
        data: dict[str, Any] | None = await fetch_fund_product(product_code)
        if data is not None:
            text = json.dumps(data, ensure_ascii=False, indent=2)
            return [KnowledgeChunk(content=f"基金产品信息:\n{text}")]
        # 查不到详情则返回基金产品列表
        products = await fetch_fund_products()
        if products:
            text = json.dumps(products, ensure_ascii=False, indent=2)
            return [KnowledgeChunk(content=f"基金产品列表:\n{text}")]
        return [KnowledgeChunk(content=f"未查询到基金产品 {product_code} 的信息。")]


# ------------------------------------------------------------------ #
#  交易流水                                                           #
# ------------------------------------------------------------------ #

class TransactionAPIProvider(KnowledgeProvider):
    provider_id = 'api.transaction'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        transaction_no = state.focused_object.id
        data: dict[str, Any] | None = await fetch_transaction(transaction_no)
        if data is None:
            return [KnowledgeChunk(content=f"未查询到交易流水 {transaction_no} 的信息。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"交易流水信息:\n{text}")]


# ------------------------------------------------------------------ #
#  转账记录                                                           #
# ------------------------------------------------------------------ #

class TransferAPIProvider(KnowledgeProvider):
    provider_id = 'api.transfer'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        identifier = state.focused_object.id
        # 先尝试作为交易号查询单笔转账
        transaction = await fetch_transaction(identifier)
        if transaction is not None:
            text = json.dumps(transaction, ensure_ascii=False, indent=2)
            return [KnowledgeChunk(content=f"转账记录信息:\n{text}")]
        # 再尝试作为账户号查询转账记录列表
        records = await fetch_transfer_records(identifier)
        if records:
            text = json.dumps(records, ensure_ascii=False, indent=2)
            return [KnowledgeChunk(content=f"转账记录列表:\n{text}")]
        return [KnowledgeChunk(content=f"未查询到转账记录 {identifier} 的信息。")]


# ------------------------------------------------------------------ #
#  FAQ / RAG（预留）                                                   #
# ------------------------------------------------------------------ #

class FAQProvider(KnowledgeProvider):
    provider_id = 'faq.default'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(content="FAQ：未检索到相关问题")]


class RAGProvider(KnowledgeProvider):
    provider_id = 'rag.default'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(content="RAG：未检索到相关信息")]
