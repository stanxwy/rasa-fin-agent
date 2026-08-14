import logging
from typing import Any
from urllib.parse import quote

from agent.conf.settings import settings
from agent.infra import http_client

logger = logging.getLogger(__name__)


def _base_url() -> str:
    return settings.backend_api_base_url.rstrip("/")


def _extract_data(result: dict | None) -> dict | None:
    logger.info(f"fetch result: \n{result}")
    data = result.get("data") if isinstance(result, dict) else None
    return data if isinstance(data, dict) else None


def _extract_list(result: dict | None) -> list[dict] | None:
    data = _extract_data(result)
    if data is None:
        return None
    items = data.get("list")
    return items if isinstance(items, list) else None


# ------------------------------------------------------------------ #
#  银行账户                                                           #
# ------------------------------------------------------------------ #

async def fetch_account(account_no: str) -> dict | None:
    try:
        r = await http_client.http_client.get(
            f"{_base_url()}/api/v1/accounts/{quote(account_no)}"
        )
        return _extract_data(r.json())
    except Exception:
        return None


async def fetch_customer_accounts(customer_no: str) -> list[dict] | None:
    try:
        r = await http_client.http_client.get(
            f"{_base_url()}/api/v1/customers/{quote(customer_no)}/accounts"
        )
        return _extract_list(r.json())
    except Exception:
        return None


# ------------------------------------------------------------------ #
#  银行卡                                                             #
# ------------------------------------------------------------------ #

async def fetch_card(card_no: str) -> dict | None:
    try:
        r = await http_client.http_client.get(
            f"{_base_url()}/api/v1/cards/{quote(card_no)}"
        )
        return _extract_data(r.json())
    except Exception:
        return None


async def fetch_customer_cards(
    customer_no: str, card_type: str | None = None
) -> list[dict] | None:
    try:
        url = f"{_base_url()}/api/v1/customers/{quote(customer_no)}/cards"
        if card_type:
            url += f"?card_type={quote(card_type)}"
        r = await http_client.http_client.get(url)
        return _extract_list(r.json())
    except Exception:
        return None


# ------------------------------------------------------------------ #
#  信用卡                                                             #
# ------------------------------------------------------------------ #

async def fetch_credit_card(card_no: str) -> dict | None:
    """查询信用卡详情，复用银行卡详情接口。"""
    return await fetch_card(card_no)


async def fetch_customer_credit_cards(customer_no: str) -> list[dict] | None:
    """查询客户信用卡列表，复用银行卡列表接口并按 card_type=credit 过滤。"""
    return await fetch_customer_cards(customer_no, card_type="credit")


# ------------------------------------------------------------------ #
#  存款产品                                                           #
# ------------------------------------------------------------------ #

async def fetch_account_products(
    account_type: str | None = None,
) -> list[dict] | None:
    try:
        url = f"{_base_url()}/api/v1/account-products"
        if account_type:
            url += f"?account_type={quote(account_type)}"
        r = await http_client.http_client.get(url)
        return _extract_list(r.json())
    except Exception:
        return None


async def fetch_deposit_products() -> list[dict] | None:
    """查询存款类产品，按 account_type=demand_deposit 过滤。"""
    return await fetch_account_products(account_type="demand_deposit")


# ------------------------------------------------------------------ #
#  贷款                                                               #
# ------------------------------------------------------------------ #

async def fetch_loan_products() -> list[dict] | None:
    try:
        r = await http_client.http_client.get(
            f"{_base_url()}/api/v1/loan/products"
        )
        return _extract_list(r.json())
    except Exception:
        return None


async def fetch_loan_product(product_code: str) -> dict | None:
    try:
        r = await http_client.http_client.get(
            f"{_base_url()}/api/v1/loan/products/{quote(product_code)}"
        )
        return _extract_data(r.json())
    except Exception:
        return None


async def fetch_loan_contract(contract_no: str) -> dict | None:
    try:
        r = await http_client.http_client.get(
            f"{_base_url()}/api/v1/loan/contracts/{quote(contract_no)}"
        )
        return _extract_data(r.json())
    except Exception:
        return None


# ------------------------------------------------------------------ #
#  理财产品                                                           #
# ------------------------------------------------------------------ #

async def fetch_wealth_products() -> list[dict] | None:
    try:
        r = await http_client.http_client.get(
            f"{_base_url()}/api/v1/wealth/products"
        )
        return _extract_list(r.json())
    except Exception:
        return None


async def fetch_wealth_product(product_code: str) -> dict | None:
    try:
        r = await http_client.http_client.get(
            f"{_base_url()}/api/v1/wealth/products/{quote(product_code)}"
        )
        return _extract_data(r.json())
    except Exception:
        return None


# ------------------------------------------------------------------ #
#  基金产品                                                           #
#  基金类理财产品：权益策略(equity)、混合策略(mixed)、固定收益(fixed_income)  #
# ------------------------------------------------------------------ #

_FUND_PRODUCT_TYPES = {"equity", "mixed", "fixed_income"}


async def fetch_fund_products() -> list[dict] | None:
    """查询基金类理财产品列表。"""
    try:
        all_products: list[dict] | None = None
        for ptype in _FUND_PRODUCT_TYPES:
            r = await http_client.http_client.get(
                f"{_base_url()}/api/v1/wealth/products?product_type={ptype}"
            )
            items = _extract_list(r.json())
            if items:
                all_products = (all_products or []) + items
        return all_products
    except Exception:
        return None


async def fetch_fund_product(product_code: str) -> dict | None:
    """查询基金产品详情，复用理财产品详情接口。"""
    return await fetch_wealth_product(product_code)


# ------------------------------------------------------------------ #
#  交易流水                                                           #
# ------------------------------------------------------------------ #

async def fetch_transaction(transaction_no: str) -> dict | None:
    try:
        r = await http_client.http_client.get(
            f"{_base_url()}/api/v1/transactions/{quote(transaction_no)}"
        )
        return _extract_data(r.json())
    except Exception:
        return None


async def fetch_account_transactions(
    account_no: str, transaction_type: str | None = None
) -> list[dict] | None:
    try:
        url = (
            f"{_base_url()}/api/v1/accounts/{quote(account_no)}/transactions"
            f"?page_no=1&page_size=20"
        )
        if transaction_type:
            url += f"&transaction_type={quote(transaction_type)}"
        r = await http_client.http_client.get(url)
        return _extract_list(r.json())
    except Exception:
        return None


# ------------------------------------------------------------------ #
#  转账记录                                                           #
# ------------------------------------------------------------------ #

async def fetch_transfer_records(account_no: str) -> list[dict] | None:
    """查询账户的转账记录，复用交易明细接口并按 transaction_type=transfer 过滤。"""
    return await fetch_account_transactions(account_no, transaction_type="transfer")
