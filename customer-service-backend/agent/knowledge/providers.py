import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from agent.domain.state import DialogueState
from agent.task.action.custom.shared import (
    fetch_account,
    fetch_account_products,
    fetch_account_transactions,
    fetch_card,
    fetch_credit_application,
    fetch_customer,
    fetch_customer_credit_limits,
    fetch_customer_notifications,
    fetch_customer_status_history,
    fetch_customer_wealth_positions,
    fetch_deposit_products,
    fetch_fund_product,
    fetch_fund_products,
    fetch_loan_application,
    fetch_loan_contract,
    fetch_loan_product,
    fetch_loan_products,
    fetch_overdues,
    fetch_repayment_bills,
    fetch_repayment_detail,
    fetch_repayment_schedules,
    fetch_service_products,
    fetch_transaction,
    fetch_transfer_records,
    fetch_wealth_incomes,
    fetch_wealth_order,
    fetch_wealth_product,
    fetch_wealth_product_navs,
    fetch_wealth_products,
    reset_current_customer_no,
    set_current_customer_no,
)

logger = logging.getLogger(__name__)


class KnowledgeChunk(BaseModel):
    content: str


class KnowledgeProvider(ABC):
    provider_id = ""

    @abstractmethod
    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]: ...


class BaseAPIProvider(KnowledgeProvider):
    """API Provider 基类：自动设置当前客户号到 contextvar，并记录 knowledge chunks。

    子类只需实现 ``_retrieve``，无需关心鉴权头和日志。
    """

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        token = set_current_customer_no(state.sender_id)
        try:
            chunks = await self._retrieve(state)
        finally:
            reset_current_customer_no(token)
        for chunk in chunks:
            preview = chunk.content[:500]
            logger.info(f"[knowledge] provider={self.provider_id} chunk={preview}")
        return chunks

    @abstractmethod
    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]: ...


# ------------------------------------------------------------------ #
#  银行账户                                                           #
# ------------------------------------------------------------------ #

class BankAccountAPIProvider(BaseAPIProvider):
    provider_id = 'api.bank_account'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        account_no = state.focused_object.id
        data: dict[str, Any] | None = await fetch_account(account_no)
        if data is None:
            return [KnowledgeChunk(content=f"未查询到账户 {account_no} 的信息。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"银行账户信息:\n{text}")]


# ------------------------------------------------------------------ #
#  银行卡                                                             #
# ------------------------------------------------------------------ #

class BankCardAPIProvider(BaseAPIProvider):
    provider_id = 'api.bank_card'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        card_no = state.focused_object.id
        data: dict[str, Any] | None = await fetch_card(card_no)
        if data is None:
            return [KnowledgeChunk(content=f"未查询到银行卡 {card_no} 的信息。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"银行卡信息:\n{text}")]


# ------------------------------------------------------------------ #
#  信用卡                                                             #
# ------------------------------------------------------------------ #

class CreditCardAPIProvider(BaseAPIProvider):
    provider_id = 'api.credit_card'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        card_no = state.focused_object.id
        data: dict[str, Any] | None = await fetch_card(card_no)
        if data is None:
            return [KnowledgeChunk(content=f"未查询到信用卡 {card_no} 的信息。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"信用卡信息:\n{text}")]


# ------------------------------------------------------------------ #
#  存款产品                                                           #
# ------------------------------------------------------------------ #

class DepositAPIProvider(BaseAPIProvider):
    provider_id = 'api.deposit'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
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

class LoanAPIProvider(BaseAPIProvider):
    provider_id = 'api.loan'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
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
#  理财产品列表                                                       #
# ------------------------------------------------------------------ #

class WealthProductListProvider(BaseAPIProvider):
    provider_id = 'api.wealth_product_list'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        products = await fetch_wealth_products()
        if not products:
            return [KnowledgeChunk(content="未查询到可售理财产品。")]
        text = json.dumps(products, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"可售理财产品列表:\n{text}")]


# ------------------------------------------------------------------ #
#  理财产品详情                                                       #
# ------------------------------------------------------------------ #

class WealthProductDetailProvider(BaseAPIProvider):
    provider_id = 'api.wealth_product'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        product_code = state.focused_object.id if state.focused_object else ""
        if not product_code:
            return [KnowledgeChunk(content="请先指定要查询的理财产品。")]
        data: dict[str, Any] | None = await fetch_wealth_product(product_code)
        if data is None:
            return [KnowledgeChunk(content=f"未查询到理财产品 {product_code} 的信息。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"理财产品信息:\n{text}")]


# ------------------------------------------------------------------ #
#  基金产品                                                           #
# ------------------------------------------------------------------ #

class FundProductAPIProvider(BaseAPIProvider):
    provider_id = 'api.fund_product'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
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

class TransactionAPIProvider(BaseAPIProvider):
    provider_id = 'api.transaction'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        identifier = state.focused_object.id
        obj_type = state.focused_object.type
        # 用户发送的是银行账户 → 按账号查询交易流水列表
        if str(obj_type) == "bank_account":
            records = await fetch_account_transactions(identifier)
            if records:
                text = json.dumps(records, ensure_ascii=False, indent=2)
                return [KnowledgeChunk(content=f"账户 {identifier} 的交易流水:\n{text}")]
            return [KnowledgeChunk(content=f"未查询到账户 {identifier} 的交易流水。")]
        # 默认：按交易号查询单笔交易详情
        data: dict[str, Any] | None = await fetch_transaction(identifier)
        if data is None:
            return [KnowledgeChunk(content=f"未查询到交易流水 {identifier} 的信息。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"交易流水信息:\n{text}")]


# ------------------------------------------------------------------ #
#  转账记录                                                           #
# ------------------------------------------------------------------ #

class TransferAPIProvider(BaseAPIProvider):
    provider_id = 'api.transfer'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
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
#  账户产品目录                                                       #
# ------------------------------------------------------------------ #

class AccountProductCatalogProvider(BaseAPIProvider):
    provider_id = 'api.account_product_catalog'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        products = await fetch_account_products()
        if not products:
            return [KnowledgeChunk(content="未查询到账户产品信息。")]
        text = json.dumps(products, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"账户产品列表:\n{text}")]


# ------------------------------------------------------------------ #
#  服务产品目录                                                       #
# ------------------------------------------------------------------ #

class ServiceProductCatalogProvider(BaseAPIProvider):
    provider_id = 'api.service_product_catalog'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        products = await fetch_service_products()
        if not products:
            return [KnowledgeChunk(content="未查询到服务产品信息。")]
        text = json.dumps(products, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"服务产品列表:\n{text}")]


# ------------------------------------------------------------------ #
#  客户档案                                                           #
# ------------------------------------------------------------------ #

class CustomerProfileProvider(BaseAPIProvider):
    provider_id = 'api.customer_profile'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        customer_no = state.sender_id
        data: dict[str, Any] | None = await fetch_customer(customer_no)
        if data is None:
            return [KnowledgeChunk(content=f"未查询到客户 {customer_no} 的档案信息。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"客户档案信息:\n{text}")]


# ------------------------------------------------------------------ #
#  客户状态历史                                                       #
# ------------------------------------------------------------------ #

class CustomerStatusHistoryProvider(BaseAPIProvider):
    provider_id = 'api.customer_status_history'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        customer_no = state.sender_id
        records = await fetch_customer_status_history(customer_no)
        if not records:
            return [KnowledgeChunk(content=f"未查询到客户 {customer_no} 的状态变更历史。")]
        text = json.dumps(records, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"客户状态变更历史:\n{text}")]


# ------------------------------------------------------------------ #
#  理财净值                                                           #
# ------------------------------------------------------------------ #

class WealthNavsProvider(BaseAPIProvider):
    provider_id = 'api.wealth_navs'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        product_code = state.focused_object.id if state.focused_object else ""
        if not product_code:
            return [KnowledgeChunk(content="请先指定要查询净值的理财产品。")]
        records = await fetch_wealth_product_navs(product_code)
        if not records:
            return [KnowledgeChunk(content=f"未查询到理财产品 {product_code} 的净值数据。")]
        text = json.dumps(records, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"理财产品 {product_code} 的净值数据:\n{text}")]


# ------------------------------------------------------------------ #
#  理财收益                                                           #
# ------------------------------------------------------------------ #

class WealthIncomeProvider(BaseAPIProvider):
    provider_id = 'api.wealth_income'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        customer_no = state.sender_id
        records = await fetch_wealth_incomes(customer_no)
        if not records:
            return [KnowledgeChunk(content=f"未查询到客户 {customer_no} 的理财收益记录。")]
        text = json.dumps(records, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"理财收益记录:\n{text}")]


# ------------------------------------------------------------------ #
#  理财订单详情                                                       #
# ------------------------------------------------------------------ #

class WealthOrderProvider(BaseAPIProvider):
    provider_id = 'api.wealth_order'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        order_no = state.focused_object.id if state.focused_object else ""
        if not order_no:
            return [KnowledgeChunk(content="请先指定要查询的理财订单。")]
        data: dict[str, Any] | None = await fetch_wealth_order(order_no)
        if data is None:
            return [KnowledgeChunk(content=f"未查询到理财订单 {order_no} 的信息。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"理财订单信息:\n{text}")]


# ------------------------------------------------------------------ #
#  授信申请详情                                                       #
# ------------------------------------------------------------------ #

class CreditApplicationProvider(BaseAPIProvider):
    provider_id = 'api.credit_application'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        identifier = state.focused_object.id if state.focused_object else ""
        if not identifier:
            return [KnowledgeChunk(content="请先指定授信申请号。")]
        data: dict[str, Any] | None = await fetch_credit_application(identifier)
        if data is None:
            return [KnowledgeChunk(content=f"未查询到授信申请 {identifier} 的信息。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"授信申请信息:\n{text}")]


# ------------------------------------------------------------------ #
#  贷款申请详情                                                       #
# ------------------------------------------------------------------ #

class LoanApplicationProvider(BaseAPIProvider):
    provider_id = 'api.loan_application'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        identifier = state.focused_object.id if state.focused_object else ""
        if not identifier:
            return [KnowledgeChunk(content="请先指定贷款申请号。")]
        data: dict[str, Any] | None = await fetch_loan_application(identifier)
        if data is None:
            return [KnowledgeChunk(content=f"未查询到贷款申请 {identifier} 的信息。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"贷款申请信息:\n{text}")]


# ------------------------------------------------------------------ #
#  还款计划                                                           #
# ------------------------------------------------------------------ #

class RepaymentScheduleProvider(BaseAPIProvider):
    provider_id = 'api.repayment_schedule'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        contract_no = state.focused_object.id if state.focused_object else ""
        if not contract_no:
            return [KnowledgeChunk(content="请先指定贷款合同号。")]
        records = await fetch_repayment_schedules(contract_no)
        if not records:
            return [KnowledgeChunk(content=f"未查询到合同 {contract_no} 的还款计划。")]
        text = json.dumps(records, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"还款计划列表:\n{text}")]


# ------------------------------------------------------------------ #
#  还款详情                                                           #
# ------------------------------------------------------------------ #

class RepaymentDetailProvider(BaseAPIProvider):
    provider_id = 'api.repayment_detail'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        repayment_no = state.focused_object.id if state.focused_object else ""
        if not repayment_no:
            return [KnowledgeChunk(content="请先指定还款编号。")]
        data: dict[str, Any] | None = await fetch_repayment_detail(repayment_no)
        if data is None:
            return [KnowledgeChunk(content=f"未查询到还款 {repayment_no} 的信息。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"还款详情:\n{text}")]


# ------------------------------------------------------------------ #
#  还款账单                                                           #
# ------------------------------------------------------------------ #

class RepaymentBillProvider(BaseAPIProvider):
    provider_id = 'api.repayment_bill'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        customer_no = state.sender_id
        records = await fetch_repayment_bills(customer_no)
        if not records:
            return [KnowledgeChunk(content=f"未查询到客户 {customer_no} 的还款账单。")]
        text = json.dumps(records, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"还款账单列表:\n{text}")]


# ------------------------------------------------------------------ #
#  逾期记录                                                           #
# ------------------------------------------------------------------ #

class OverdueProvider(BaseAPIProvider):
    provider_id = 'api.overdue'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        customer_no = state.sender_id
        records = await fetch_overdues(customer_no)
        if not records:
            return [KnowledgeChunk(content=f"未查询到客户 {customer_no} 的逾期记录。")]
        text = json.dumps(records, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"逾期记录:\n{text}")]


# ------------------------------------------------------------------ #
#  授信额度                                                           #
# ------------------------------------------------------------------ #

class CreditLimitProvider(BaseAPIProvider):
    provider_id = 'api.credit_limit'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        customer_no = state.sender_id
        records = await fetch_customer_credit_limits(customer_no)
        if not records:
            return [KnowledgeChunk(content=f"未查询到客户 {customer_no} 的授信额度。")]
        text = json.dumps(records, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"授信额度信息:\n{text}")]


# ------------------------------------------------------------------ #
#  理财持仓                                                           #
# ------------------------------------------------------------------ #

class WealthPositionProvider(BaseAPIProvider):
    provider_id = 'api.wealth_position'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        customer_no = state.sender_id
        records = await fetch_customer_wealth_positions(customer_no)
        if not records:
            return [KnowledgeChunk(content=f"未查询到客户 {customer_no} 的理财持仓。")]
        text = json.dumps(records, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"理财持仓信息:\n{text}")]


# ------------------------------------------------------------------ #
#  客户通知                                                           #
# ------------------------------------------------------------------ #

class NotificationProvider(BaseAPIProvider):
    provider_id = 'api.notification'

    async def _retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        customer_no = state.sender_id
        records = await fetch_customer_notifications(customer_no)
        if not records:
            return [KnowledgeChunk(content=f"未查询到客户 {customer_no} 的通知记录。")]
        text = json.dumps(records, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"客户通知记录:\n{text}")]


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
