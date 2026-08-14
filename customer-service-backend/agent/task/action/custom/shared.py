import contextvars
import logging
import uuid
from typing import Any
from urllib.parse import quote

from agent.conf.settings import settings
from agent.infra import http_client

logger = logging.getLogger(__name__)

# 跨协程传递当前客户号，供 fetch 函数构造鉴权头使用。
_current_customer_no: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_customer_no", default=None
)


def set_current_customer_no(customer_no: str | None) -> contextvars.Token[str | None]:
    """在 Provider 入口设置当前客户号，fetch 函数会自动带上鉴权头。"""
    return _current_customer_no.set(customer_no)


def reset_current_customer_no(token: contextvars.Token[str | None]) -> None:
    _current_customer_no.reset(token)


def _base_url() -> str:
    return settings.backend_api_base_url.rstrip("/")


def _make_headers() -> dict[str, str]:
    """构造中台 API 鉴权头。客户号来自 contextvar，由 Provider 设置。"""
    headers: dict[str, str] = {"X-Channel-Code": "MOBILE_BANK"}
    customer_no = _current_customer_no.get()
    if customer_no:
        headers["Authorization"] = f"Bearer {customer_no}"
    return headers


def _make_idempotent_key() -> str:
    """生成幂等请求号，供 POST/PATCH 接口使用。"""
    return uuid.uuid4().hex.upper()


async def _get(url: str) -> Any:
    """统一 GET 请求：记录请求 URL，附加鉴权头。"""
    logger.info(f"[fin-backend] GET {url}")
    return await http_client.http_client.get(url, headers=_make_headers())


async def _post(url: str, payload: dict | None = None) -> Any:
    """统一 POST 请求：自动注入 request_no 幂等键，记录请求。"""
    body = payload or {}
    if "request_no" not in body:
        body["request_no"] = _make_idempotent_key()
    logger.info(f"[fin-backend] POST {url} body_keys={list(body.keys())}")
    return await http_client.http_client.post(url, json=body, headers=_make_headers())


async def _patch(url: str, payload: dict | None = None) -> Any:
    """统一 PATCH 请求：记录请求。"""
    body = payload or {}
    logger.info(f"[fin-backend] PATCH {url} body_keys={list(body.keys())}")
    return await http_client.http_client.patch(url, json=body, headers=_make_headers())


def _extract_data(result: dict | None) -> dict | None:
    data = result.get("data") if isinstance(result, dict) else None
    return data if isinstance(data, dict) else None


def _extract_list(result: dict | None) -> list[dict] | None:
    data = _extract_data(result)
    if data is None:
        return None
    items = data.get("list")
    return items if isinstance(items, list) else None


def _extract_id(result: dict | None) -> str | None:
    """从 POST/PATCH 响应中提取新建资源的 ID。"""
    data = _extract_data(result)
    if data is None:
        return None
    for key in ("customer_no", "account_no", "card_no", "transaction_no",
                "contract_no", "application_no", "order_no", "repayment_no",
                "reduction_no", "request_no", "id"):
        val = data.get(key)
        if val:
            return str(val)
    return None


# ====================================================================== #
#  foundation — 基础配置接口                                                #
# ====================================================================== #

async def fetch_account_products(
    account_type: str | None = None,
) -> list[dict] | None:
    try:
        url = f"{_base_url()}/api/v1/account-products"
        if account_type:
            url += f"?account_type={quote(account_type)}"
        r = await _get(url)
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_account_products failed: {e}")
        return None


async def fetch_deposit_products() -> list[dict] | None:
    """查询存款类产品，按 account_type=demand_deposit 过滤。"""
    return await fetch_account_products(account_type="demand_deposit")


async def fetch_service_products(
    service_type: str | None = None,
) -> list[dict] | None:
    try:
        url = f"{_base_url()}/api/v1/service-products"
        if service_type:
            url += f"?service_type={quote(service_type)}"
        r = await _get(url)
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_service_products failed: {e}")
        return None


async def fetch_branches(
    branch_status: str | None = None,
    province: str | None = None,
    city: str | None = None,
) -> list[dict] | None:
    try:
        url = f"{_base_url()}/api/v1/branches"
        params: list[str] = []
        if branch_status:
            params.append(f"branch_status={quote(branch_status)}")
        if province:
            params.append(f"province={quote(province)}")
        if city:
            params.append(f"city={quote(city)}")
        if params:
            url += "?" + "&".join(params)
        r = await _get(url)
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_branches failed: {e}")
        return None


async def fetch_channels(
    channel_type: str | None = None,
    channel_status: str | None = None,
) -> list[dict] | None:
    try:
        url = f"{_base_url()}/api/v1/channels"
        params: list[str] = []
        if channel_type:
            params.append(f"channel_type={quote(channel_type)}")
        if channel_status:
            params.append(f"channel_status={quote(channel_status)}")
        if params:
            url += "?" + "&".join(params)
        r = await _get(url)
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_channels failed: {e}")
        return None


async def fetch_currencies() -> list[dict] | None:
    try:
        r = await _get(f"{_base_url()}/api/v1/currencies")
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_currencies failed: {e}")
        return None


async def fetch_risk_levels(
    risk_level_type: str | None = None,
) -> list[dict] | None:
    try:
        url = f"{_base_url()}/api/v1/risk-levels"
        if risk_level_type:
            url += f"?risk_level_type={quote(risk_level_type)}"
        r = await _get(url)
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_risk_levels failed: {e}")
        return None


async def fetch_employees(
    employee_status: str | None = None,
) -> list[dict] | None:
    try:
        url = f"{_base_url()}/api/v1/employees"
        if employee_status:
            url += f"?employee_status={quote(employee_status)}"
        r = await _get(url)
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_employees failed: {e}")
        return None


# ====================================================================== #
#  customers — 客户接口                                                    #
# ====================================================================== #

async def create_customer(
    customer_type: str,
    customer_name: str,
    branch_code: str,
    channel_code: str,
    **extra,
) -> dict | None:
    """POST /customers — 创建个人或企业客户。"""
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "customer_type": customer_type,
            "customer_name": customer_name,
            "branch_code": branch_code,
            "channel_code": channel_code,
        }
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(f"{_base_url()}/api/v1/customers", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"create_customer failed: {e}")
        return None


async def fetch_customer(customer_no: str) -> dict | None:
    try:
        r = await _get(f"{_base_url()}/api/v1/customers/{quote(customer_no)}")
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_customer failed: {e}")
        return None


async def update_customer(customer_no: str, **fields) -> dict | None:
    """PATCH /customers/{no} — 更新客户基础信息。"""
    try:
        payload = {"request_no": _make_idempotent_key()}
        payload.update({k: v for k, v in fields.items() if v is not None})
        r = await _patch(
            f"{_base_url()}/api/v1/customers/{quote(customer_no)}", payload
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"update_customer failed: {e}")
        return None


async def fetch_customer_status_history(
    customer_no: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict] | None:
    try:
        url = f"{_base_url()}/api/v1/customers/{quote(customer_no)}/status-history"
        params: list[str] = []
        if start_date:
            params.append(f"start_date={quote(start_date)}")
        if end_date:
            params.append(f"end_date={quote(end_date)}")
        if params:
            url += "?" + "&".join(params)
        r = await _get(url)
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_customer_status_history failed: {e}")
        return None


async def submit_customer_identity(
    customer_no: str,
    identity_no: str,
    identity_name: str,
    identity_valid_to: str | None = None,
) -> dict | None:
    """POST /customers/{no}/identities — 提交实名认证信息。"""
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "identity_no": identity_no,
            "identity_name": identity_name,
        }
        if identity_valid_to:
            payload["identity_valid_to"] = identity_valid_to
        r = await _post(
            f"{_base_url()}/api/v1/customers/{quote(customer_no)}/identities",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"submit_customer_identity failed: {e}")
        return None


async def add_customer_contact(
    customer_no: str,
    contact_type: str,
    contact_value: str,
    is_primary: bool = False,
) -> dict | None:
    """POST /customers/{no}/contacts — 新增客户联系方式。"""
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "contact_type": contact_type,
            "contact_value": contact_value,
            "is_primary": is_primary,
        }
        r = await _post(
            f"{_base_url()}/api/v1/customers/{quote(customer_no)}/contacts",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"add_customer_contact failed: {e}")
        return None


async def submit_customer_kyc(
    customer_no: str,
    kyc_data: dict,
) -> dict | None:
    """POST /customers/{no}/kyc — 提交 KYC 信息。"""
    try:
        payload = {"request_no": _make_idempotent_key()}
        payload.update(kyc_data)
        r = await _post(
            f"{_base_url()}/api/v1/customers/{quote(customer_no)}/kyc", payload
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"submit_customer_kyc failed: {e}")
        return None


async def submit_customer_risk_assessment(
    customer_no: str,
    risk_level: str,
    assessment_result: str,
) -> dict | None:
    """POST /customers/{no}/risk-assessments — 提交客户风险测评。"""
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "risk_level": risk_level,
            "assessment_result": assessment_result,
        }
        r = await _post(
            f"{_base_url()}/api/v1/customers/{quote(customer_no)}/risk-assessments",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"submit_customer_risk_assessment failed: {e}")
        return None


async def bind_customer_device(
    customer_no: str,
    device_type: str,
    device_id: str | None = None,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "device_type": device_type,
        }
        if device_id:
            payload["device_id"] = device_id
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(
            f"{_base_url()}/api/v1/customers/{quote(customer_no)}/devices",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"bind_customer_device failed: {e}")
        return None


async def upsert_beneficial_owner(
    customer_no: str,
    beneficial_owner_id: str | None = None,
    **extra,
) -> dict | None:
    try:
        payload = {"request_no": _make_idempotent_key()}
        if beneficial_owner_id:
            payload["beneficial_owner_id"] = beneficial_owner_id
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(
            f"{_base_url()}/api/v1/customers/{quote(customer_no)}/beneficial-owners",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"upsert_beneficial_owner failed: {e}")
        return None


async def add_customer_tag(
    customer_no: str,
    tag_code: str,
    tag_value: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "tag_code": tag_code,
        }
        if tag_value:
            payload["tag_value"] = tag_value
        r = await _post(
            f"{_base_url()}/api/v1/customers/{quote(customer_no)}/tags",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"add_customer_tag failed: {e}")
        return None


# ====================================================================== #
#  accounts — 账户与交易接口                                                 #
# ====================================================================== #

async def fetch_account(account_no: str) -> dict | None:
    try:
        r = await _get(f"{_base_url()}/api/v1/accounts/{quote(account_no)}")
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_account failed: {e}")
        return None


async def fetch_customer_accounts(customer_no: str) -> list[dict] | None:
    try:
        r = await _get(f"{_base_url()}/api/v1/customers/{quote(customer_no)}/accounts")
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_customer_accounts failed: {e}")
        return None


async def fetch_card(card_no: str) -> dict | None:
    try:
        r = await _get(f"{_base_url()}/api/v1/cards/{quote(card_no)}")
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_card failed: {e}")
        return None


async def fetch_customer_cards(
    customer_no: str, card_type: str | None = None
) -> list[dict] | None:
    try:
        url = f"{_base_url()}/api/v1/customers/{quote(customer_no)}/cards"
        if card_type:
            url += f"?card_type={quote(card_type)}"
        r = await _get(url)
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_customer_cards failed: {e}")
        return None


async def fetch_credit_card(card_no: str) -> dict | None:
    """查询信用卡详情，复用银行卡详情接口。"""
    return await fetch_card(card_no)


async def fetch_customer_credit_cards(customer_no: str) -> list[dict] | None:
    """查询客户信用卡列表，复用银行卡列表接口并按 card_type=credit 过滤。"""
    return await fetch_customer_cards(customer_no, card_type="credit")


async def fetch_transaction(transaction_no: str) -> dict | None:
    try:
        r = await _get(f"{_base_url()}/api/v1/transactions/{quote(transaction_no)}")
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_transaction failed: {e}")
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
        r = await _get(url)
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_account_transactions failed: {e}")
        return None


async def fetch_transfer_records(account_no: str) -> list[dict] | None:
    """查询账户的转账记录，复用交易明细接口并按 transaction_type=transfer 过滤。"""
    return await fetch_account_transactions(account_no, transaction_type="transfer")


async def create_account(
    account_type: str,
    currency: str,
    branch_code: str,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "account_type": account_type,
            "currency": currency,
            "branch_code": branch_code,
        }
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(f"{_base_url()}/api/v1/accounts", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"create_account failed: {e}")
        return None


async def create_bank_card(
    account_no: str,
    card_type: str,
    card_name: str | None = None,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "card_type": card_type,
        }
        if card_name:
            payload["card_name"] = card_name
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(
            f"{_base_url()}/api/v1/accounts/{quote(account_no)}/cards",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"create_bank_card failed: {e}")
        return None


async def change_account_status(
    account_no: str,
    target_status: str,
    reason: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "target_status": target_status,
        }
        if reason:
            payload["reason"] = reason
        r = await _post(
            f"{_base_url()}/api/v1/accounts/{quote(account_no)}/status-changes",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"change_account_status failed: {e}")
        return None


async def create_transaction(
    account_no: str,
    transaction_type: str,
    amount: float,
    counterparty_account_no: str | None = None,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "account_no": account_no,
            "transaction_type": transaction_type,
            "amount": amount,
        }
        if counterparty_account_no:
            payload["counterparty_account_no"] = counterparty_account_no
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(f"{_base_url()}/api/v1/transactions", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"create_transaction failed: {e}")
        return None


async def fetch_account_ledgers(
    account_no: str,
    ledger_type: str | None = None,
) -> list[dict] | None:
    try:
        url = f"{_base_url()}/api/v1/accounts/{quote(account_no)}/ledgers"
        if ledger_type:
            url += f"?ledger_type={quote(ledger_type)}"
        r = await _get(url)
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_account_ledgers failed: {e}")
        return None


async def create_fund_freeze(
    account_no: str,
    freeze_amount: float,
    reason: str | None = None,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "account_no": account_no,
            "freeze_amount": freeze_amount,
        }
        if reason:
            payload["reason"] = reason
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(f"{_base_url()}/api/v1/fund-freezes", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"create_fund_freeze failed: {e}")
        return None


async def operate_fund_freeze(
    freeze_no: str,
    operation_type: str,
    amount: float | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "operation_type": operation_type,
        }
        if amount is not None:
            payload["amount"] = amount
        r = await _post(
            f"{_base_url()}/api/v1/fund-freezes/{quote(freeze_no)}/operations",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"operate_fund_freeze failed: {e}")
        return None


async def create_reconciliation_batch(
    batch_date: str,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "batch_date": batch_date,
        }
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(f"{_base_url()}/api/v1/reconciliation/batches", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"create_reconciliation_batch failed: {e}")
        return None


async def confirm_reconciliation_results(
    batch_no: str,
    items: list[dict],
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "batch_no": batch_no,
            "items": items,
        }
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(f"{_base_url()}/api/v1/reconciliation/results", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"confirm_reconciliation_results failed: {e}")
        return None


async def create_reconciliation_adjustment(
    batch_no: str,
    adjustment_type: str,
    amount: float,
    reason: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "batch_no": batch_no,
            "adjustment_type": adjustment_type,
            "amount": amount,
        }
        if reason:
            payload["reason"] = reason
        r = await _post(
            f"{_base_url()}/api/v1/reconciliation/adjustments", payload
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"create_reconciliation_adjustment failed: {e}")
        return None


async def approve_reconciliation_adjustment(
    adjustment_no: str,
    approval_result: str = "approved",
    remark: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "approval_result": approval_result,
        }
        if remark:
            payload["remark"] = remark
        r = await _post(
            f"{_base_url()}/api/v1/reconciliation/adjustments/{quote(adjustment_no)}/approval",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"approve_reconciliation_adjustment failed: {e}")
        return None


async def post_reconciliation_adjustment(
    adjustment_no: str,
    effective_date: str | None = None,
) -> dict | None:
    try:
        payload = {"request_no": _make_idempotent_key()}
        if effective_date:
            payload["effective_date"] = effective_date
        r = await _post(
            f"{_base_url()}/api/v1/reconciliation/adjustments/{quote(adjustment_no)}/post",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"post_reconciliation_adjustment failed: {e}")
        return None


# ====================================================================== #
#  wealth — 理财接口                                                        #
# ====================================================================== #

async def fetch_wealth_products() -> list[dict] | None:
    try:
        r = await _get(f"{_base_url()}/api/v1/wealth/products")
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_wealth_products failed: {e}")
        return None


async def fetch_wealth_product(product_code: str) -> dict | None:
    try:
        r = await _get(f"{_base_url()}/api/v1/wealth/products/{quote(product_code)}")
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_wealth_product failed: {e}")
        return None


async def fetch_wealth_product_navs(
    product_code: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict] | None:
    try:
        url = (
            f"{_base_url()}/api/v1/wealth/products/{quote(product_code)}/navs"
            f"?page_size=30"
        )
        if start_date:
            url += f"&start_date={quote(start_date)}"
        if end_date:
            url += f"&end_date={quote(end_date)}"
        r = await _get(url)
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_wealth_product_navs failed: {e}")
        return None


async def fetch_fund_products() -> list[dict] | None:
    """查询基金类理财产品列表。"""
    _FUND_PRODUCT_TYPES = {"equity", "mixed", "fixed_income"}
    try:
        all_products: list[dict] | None = None
        for ptype in _FUND_PRODUCT_TYPES:
            r = await _get(
                f"{_base_url()}/api/v1/wealth/products?product_type={ptype}"
            )
            items = _extract_list(r.json())
            if items:
                all_products = (all_products or []) + items
        return all_products
    except Exception as e:
        logger.warning(f"fetch_fund_products failed: {e}")
        return None


async def fetch_fund_product(product_code: str) -> dict | None:
    """查询基金产品详情，复用理财产品详情接口。"""
    return await fetch_wealth_product(product_code)


async def purchase_wealth(
    product_code: str,
    amount: float | None = None,
    share: float | None = None,
) -> dict | None:
    """POST /wealth/orders/purchase — 发起理财申购。"""
    try:
        payload = {"request_no": _make_idempotent_key(), "product_code": product_code}
        if amount is not None:
            payload["purchase_amount"] = amount
        if share is not None:
            payload["purchase_share"] = share
        r = await _post(
            f"{_base_url()}/api/v1/wealth/orders/purchase", payload
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"purchase_wealth failed: {e}")
        return None


async def redeem_wealth(
    product_code: str,
    share: float | None = None,
    amount: float | None = None,
) -> dict | None:
    """POST /wealth/orders/redeem — 发起理财赎回。"""
    try:
        payload = {"request_no": _make_idempotent_key(), "product_code": product_code}
        if share is not None:
            payload["redeem_share"] = share
        if amount is not None:
            payload["redeem_amount"] = amount
        r = await _post(
            f"{_base_url()}/api/v1/wealth/orders/redeem", payload
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"redeem_wealth failed: {e}")
        return None


async def confirm_wealth_order(order_no: str) -> dict | None:
    """POST /wealth/orders/{no}/confirm — 确认理财订单。"""
    try:
        r = await _post(
            f"{_base_url()}/api/v1/wealth/orders/{quote(order_no)}/confirm",
            {"request_no": _make_idempotent_key()},
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"confirm_wealth_order failed: {e}")
        return None


async def cancel_wealth_order(order_no: str) -> dict | None:
    """POST /wealth/orders/{no}/cancel — 撤销理财订单。"""
    try:
        r = await _post(
            f"{_base_url()}/api/v1/wealth/orders/{quote(order_no)}/cancel",
            {"request_no": _make_idempotent_key()},
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"cancel_wealth_order failed: {e}")
        return None


async def fetch_wealth_order(order_no: str) -> dict | None:
    try:
        r = await _get(f"{_base_url()}/api/v1/wealth/orders/{quote(order_no)}")
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_wealth_order failed: {e}")
        return None


async def fetch_customer_wealth_positions(customer_no: str) -> list[dict] | None:
    try:
        r = await _get(
            f"{_base_url()}/api/v1/customers/{quote(customer_no)}/wealth/positions"
        )
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_customer_wealth_positions failed: {e}")
        return None


async def fetch_wealth_incomes(
    customer_no: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict] | None:
    try:
        url = (
            f"{_base_url()}/api/v1/customers/{quote(customer_no)}/wealth/incomes"
            f"?page_size=100"
        )
        if start_date:
            url += f"&start_date={quote(start_date)}"
        if end_date:
            url += f"&end_date={quote(end_date)}"
        r = await _get(url)
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_wealth_incomes failed: {e}")
        return None


async def settle_wealth_income(
    income_no: str,
) -> dict | None:
    try:
        r = await _post(
            f"{_base_url()}/api/v1/wealth/incomes/{quote(income_no)}/settle",
            {"request_no": _make_idempotent_key()},
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"settle_wealth_income failed: {e}")
        return None


# ====================================================================== #
#  loans — 信贷接口                                                        #
# ====================================================================== #

async def fetch_loan_products() -> list[dict] | None:
    try:
        r = await _get(f"{_base_url()}/api/v1/loan/products")
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_loan_products failed: {e}")
        return None


async def fetch_loan_product(product_code: str) -> dict | None:
    try:
        r = await _get(f"{_base_url()}/api/v1/loan/products/{quote(product_code)}")
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_loan_product failed: {e}")
        return None


async def submit_credit_application(
    product_code: str,
    amount: float,
    term_months: int,
    **extra,
) -> dict | None:
    """POST /credit/applications — 提交授信申请。"""
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "product_code": product_code,
            "amount": amount,
            "term_months": term_months,
        }
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(f"{_base_url()}/api/v1/credit/applications", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"submit_credit_application failed: {e}")
        return None


async def fetch_credit_application(credit_application_no: str) -> dict | None:
    try:
        r = await _get(
            f"{_base_url()}/api/v1/credit/applications/{quote(credit_application_no)}"
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_credit_application failed: {e}")
        return None


async def fetch_customer_credit_limits(customer_no: str) -> list[dict] | None:
    try:
        r = await _get(
            f"{_base_url()}/api/v1/customers/{quote(customer_no)}/credit-limits"
        )
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_customer_credit_limits failed: {e}")
        return None


async def submit_loan_application(
    product_code: str,
    amount: float,
    term_months: int,
    **extra,
) -> dict | None:
    """POST /loan/applications — 提交贷款申请。"""
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "product_code": product_code,
            "amount": amount,
            "term_months": term_months,
        }
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(f"{_base_url()}/api/v1/loan/applications", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"submit_loan_application failed: {e}")
        return None


async def fetch_loan_application(application_no: str) -> dict | None:
    try:
        r = await _get(
            f"{_base_url()}/api/v1/loan/applications/{quote(application_no)}"
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_loan_application failed: {e}")
        return None


async def fetch_loan_contract(contract_no: str) -> dict | None:
    try:
        r = await _get(
            f"{_base_url()}/api/v1/loan/contracts/{quote(contract_no)}"
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_loan_contract failed: {e}")
        return None


async def disburse_loan(contract_no: str, amount: float | None = None) -> dict | None:
    """POST /loan/contracts/{no}/disbursements — 发起贷款放款。"""
    try:
        payload = {"request_no": _make_idempotent_key()}
        if amount is not None:
            payload["disburse_amount"] = amount
        r = await _post(
            f"{_base_url()}/api/v1/loan/contracts/{quote(contract_no)}/disbursements",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"disburse_loan failed: {e}")
        return None


async def add_credit_approval_record(
    credit_application_no: str,
    approval_result: str,
    approval_remark: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "approval_result": approval_result,
        }
        if approval_remark:
            payload["approval_remark"] = approval_remark
        r = await _post(
            f"{_base_url()}/api/v1/credit/applications/{quote(credit_application_no)}/approval-records",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"add_credit_approval_record failed: {e}")
        return None


async def change_loan_application_status(
    application_no: str,
    target_status: str,
    reason: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "target_status": target_status,
        }
        if reason:
            payload["reason"] = reason
        r = await _post(
            f"{_base_url()}/api/v1/loan/applications/{quote(application_no)}/status-changes",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"change_loan_application_status failed: {e}")
        return None


async def add_loan_approval_record(
    application_no: str,
    approval_result: str,
    approval_remark: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "approval_result": approval_result,
        }
        if approval_remark:
            payload["approval_remark"] = approval_remark
        r = await _post(
            f"{_base_url()}/api/v1/loan/applications/{quote(application_no)}/approval-records",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"add_loan_approval_record failed: {e}")
        return None


async def add_loan_sign_record(
    contract_no: str,
    sign_type: str = "electronic",
    remark: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "sign_type": sign_type,
        }
        if remark:
            payload["remark"] = remark
        r = await _post(
            f"{_base_url()}/api/v1/loan/contracts/{quote(contract_no)}/sign-records",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"add_loan_sign_record failed: {e}")
        return None


# ====================================================================== #
#  repayments — 还款与逾期接口                                               #
# ====================================================================== #

async def fetch_repayment_schedules(contract_no: str) -> list[dict] | None:
    try:
        r = await _get(
            f"{_base_url()}/api/v1/loan/contracts/{quote(contract_no)}/repayment-schedules"
        )
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_repayment_schedules failed: {e}")
        return None


async def fetch_repayment_bills(customer_no: str) -> list[dict] | None:
    try:
        r = await _get(
            f"{_base_url()}/api/v1/repayment/bills?customer_no={quote(customer_no)}&page_size=100"
        )
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_repayment_bills failed: {e}")
        return None


async def fetch_repayment_detail(repayment_no: str) -> dict | None:
    try:
        r = await _get(
            f"{_base_url()}/api/v1/repayments/{quote(repayment_no)}"
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_repayment_detail failed: {e}")
        return None


async def create_repayment_authorization(
    contract_no: str,
    auto_repay: bool = True,
) -> dict | None:
    """POST /repayment/authorizations — 创建自动还款授权。"""
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "contract_no": contract_no,
            "auto_repay": auto_repay,
        }
        r = await _post(
            f"{_base_url()}/api/v1/repayment/authorizations", payload
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"create_repayment_authorization failed: {e}")
        return None


async def submit_repayment(
    contract_no: str,
    amount: float,
    repayment_method: str = "bank_card",
) -> dict | None:
    """POST /repayments — 发起正常还款。"""
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "contract_no": contract_no,
            "amount": amount,
            "repayment_method": repayment_method,
        }
        r = await _post(f"{_base_url()}/api/v1/repayments", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"submit_repayment failed: {e}")
        return None


async def fetch_overdues(customer_no: str) -> list[dict] | None:
    try:
        r = await _get(
            f"{_base_url()}/api/v1/overdues?customer_no={quote(customer_no)}&page_size=100"
        )
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_overdues failed: {e}")
        return None


async def submit_fee_reduction(
    contract_no: str,
    reason: str,
    amount: float | None = None,
) -> dict | None:
    """POST /fee-reductions — 发起费用减免申请。"""
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "contract_no": contract_no,
            "reason": reason,
        }
        if amount is not None:
            payload["reduction_amount"] = amount
        r = await _post(f"{_base_url()}/api/v1/fee-reductions", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"submit_fee_reduction failed: {e}")
        return None


async def generate_repayment_bills(
    contract_no: str | None = None,
    customer_no: str | None = None,
    bill_month: str | None = None,
) -> dict | None:
    try:
        payload = {"request_no": _make_idempotent_key()}
        if contract_no:
            payload["contract_no"] = contract_no
        if customer_no:
            payload["customer_no"] = customer_no
        if bill_month:
            payload["bill_month"] = bill_month
        r = await _post(
            f"{_base_url()}/api/v1/repayment/bills/generate", payload
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"generate_repayment_bills failed: {e}")
        return None


async def refresh_overdues(
    customer_no: str | None = None,
    contract_no: str | None = None,
) -> dict | None:
    try:
        payload = {"request_no": _make_idempotent_key()}
        if customer_no:
            payload["customer_no"] = customer_no
        if contract_no:
            payload["contract_no"] = contract_no
        r = await _post(f"{_base_url()}/api/v1/overdues/refresh", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"refresh_overdues failed: {e}")
        return None


async def approve_fee_reduction(
    reduction_no: str,
    approval_result: str = "approved",
    remark: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "approval_result": approval_result,
        }
        if remark:
            payload["remark"] = remark
        r = await _post(
            f"{_base_url()}/api/v1/fee-reductions/{quote(reduction_no)}/approval",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"approve_fee_reduction failed: {e}")
        return None


# ====================================================================== #
#  risk — 风险与合规接口                                                    #
# ====================================================================== #

async def report_risk_event(
    event_type: str,
    event_level: str,
    customer_no: str | None = None,
    contract_no: str | None = None,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "event_type": event_type,
            "event_level": event_level,
        }
        if customer_no:
            payload["customer_no"] = customer_no
        if contract_no:
            payload["contract_no"] = contract_no
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(f"{_base_url()}/api/v1/risk/events", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"report_risk_event failed: {e}")
        return None


async def fetch_risk_event(event_no: str) -> dict | None:
    try:
        r = await _get(
            f"{_base_url()}/api/v1/risk/events/{quote(event_no)}"
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_risk_event failed: {e}")
        return None


async def complete_manual_review_task(
    task_no: str,
    review_result: str,
    remark: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "review_result": review_result,
        }
        if remark:
            payload["remark"] = remark
        r = await _post(
            f"{_base_url()}/api/v1/manual-review/tasks/{quote(task_no)}/complete",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"complete_manual_review_task failed: {e}")
        return None


async def fetch_blacklists(
    blacklist_type: str | None = None,
    customer_no: str | None = None,
) -> list[dict] | None:
    try:
        url = f"{_base_url()}/api/v1/blacklists"
        params: list[str] = []
        if blacklist_type:
            params.append(f"blacklist_type={quote(blacklist_type)}")
        if customer_no:
            params.append(f"customer_no={quote(customer_no)}")
        if params:
            url += "?" + "&".join(params)
        r = await _get(url)
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_blacklists failed: {e}")
        return None


async def add_blacklist(
    blacklist_type: str,
    customer_no: str | None = None,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "blacklist_type": blacklist_type,
        }
        if customer_no:
            payload["customer_no"] = customer_no
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(f"{_base_url()}/api/v1/blacklists", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"add_blacklist failed: {e}")
        return None


async def submit_aml_case(
    case_type: str,
    customer_no: str | None = None,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "case_type": case_type,
        }
        if customer_no:
            payload["customer_no"] = customer_no
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(f"{_base_url()}/api/v1/aml/cases", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"submit_aml_case failed: {e}")
        return None


async def review_aml_case(
    case_no: str,
    review_result: str,
    remark: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "review_result": review_result,
        }
        if remark:
            payload["remark"] = remark
        r = await _post(
            f"{_base_url()}/api/v1/aml/cases/{quote(case_no)}/review-results",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"review_aml_case failed: {e}")
        return None


async def fetch_aml_report(report_no: str) -> dict | None:
    try:
        r = await _get(
            f"{_base_url()}/api/v1/aml/reports/{quote(report_no)}"
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_aml_report failed: {e}")
        return None


# ====================================================================== #
#  collections — 催收接口                                                   #
# ====================================================================== #

async def create_collection_case(
    customer_no: str,
    case_type: str,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "customer_no": customer_no,
            "case_type": case_type,
        }
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(f"{_base_url()}/api/v1/collection/cases", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"create_collection_case failed: {e}")
        return None


async def fetch_collection_case(case_no: str) -> dict | None:
    try:
        r = await _get(
            f"{_base_url()}/api/v1/collection/cases/{quote(case_no)}"
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_collection_case failed: {e}")
        return None


async def add_collection_action(
    case_no: str,
    action_type: str,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "action_type": action_type,
        }
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(
            f"{_base_url()}/api/v1/collection/cases/{quote(case_no)}/actions",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"add_collection_action failed: {e}")
        return None


async def add_collection_contact(
    case_no: str,
    contact_type: str,
    contact_value: str | None = None,
    is_primary: bool = False,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "contact_type": contact_type,
            "is_primary": is_primary,
        }
        if contact_value:
            payload["contact_value"] = contact_value
        r = await _post(
            f"{_base_url()}/api/v1/collection/cases/{quote(case_no)}/contacts",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"add_collection_contact failed: {e}")
        return None


async def add_collection_promise(
    case_no: str,
    promise_date: str,
    promise_amount: float,
    remark: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "promise_date": promise_date,
            "promise_amount": promise_amount,
        }
        if remark:
            payload["remark"] = remark
        r = await _post(
            f"{_base_url()}/api/v1/collection/cases/{quote(case_no)}/promises",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"add_collection_promise failed: {e}")
        return None


async def add_collection_repayment(
    case_no: str,
    amount: float,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "amount": amount,
        }
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(
            f"{_base_url()}/api/v1/collection/cases/{quote(case_no)}/repayments",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"add_collection_repayment failed: {e}")
        return None


async def add_collection_legal_case(
    case_no: str,
    legal_type: str,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "legal_type": legal_type,
        }
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(
            f"{_base_url()}/api/v1/collection/cases/{quote(case_no)}/legal-cases",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"add_collection_legal_case failed: {e}")
        return None


async def add_collection_write_off(
    case_no: str,
    write_off_amount: float,
    reason: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "write_off_amount": write_off_amount,
        }
        if reason:
            payload["reason"] = reason
        r = await _post(
            f"{_base_url()}/api/v1/collection/cases/{quote(case_no)}/write-offs",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"add_collection_write_off failed: {e}")
        return None


async def approve_collection_write_off(
    write_off_no: str,
    approval_result: str = "approved",
    remark: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "approval_result": approval_result,
        }
        if remark:
            payload["remark"] = remark
        r = await _post(
            f"{_base_url()}/api/v1/collection/write-offs/{quote(write_off_no)}/approval",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"approve_collection_write_off failed: {e}")
        return None


async def post_collection_write_off(
    write_off_no: str,
    effective_date: str | None = None,
) -> dict | None:
    try:
        payload = {"request_no": _make_idempotent_key()}
        if effective_date:
            payload["effective_date"] = effective_date
        r = await _post(
            f"{_base_url()}/api/v1/collection/write-offs/{quote(write_off_no)}/post",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"post_collection_write_off failed: {e}")
        return None


async def add_collection_restructure(
    case_no: str,
    restructure_type: str,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "restructure_type": restructure_type,
        }
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(
            f"{_base_url()}/api/v1/collection/cases/{quote(case_no)}/restructures",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"add_collection_restructure failed: {e}")
        return None


async def approve_collection_restructure(
    restructure_no: str,
    approval_result: str = "approved",
    remark: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "approval_result": approval_result,
        }
        if remark:
            payload["remark"] = remark
        r = await _post(
            f"{_base_url()}/api/v1/collection/restructures/{quote(restructure_no)}/approval",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"approve_collection_restructure failed: {e}")
        return None


async def effective_collection_restructure(
    restructure_no: str,
    effective_date: str | None = None,
) -> dict | None:
    try:
        payload = {"request_no": _make_idempotent_key()}
        if effective_date:
            payload["effective_date"] = effective_date
        r = await _post(
            f"{_base_url()}/api/v1/collection/restructures/{quote(restructure_no)}/effective",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"effective_collection_restructure failed: {e}")
        return None


async def dispose_collection_collateral(
    case_no: str,
    disposal_type: str,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "disposal_type": disposal_type,
        }
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(
            f"{_base_url()}/api/v1/collection/cases/{quote(case_no)}/collateral-disposals",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"dispose_collection_collateral failed: {e}")
        return None


async def fetch_collection_performance_daily(
    date: str | None = None,
) -> list[dict] | None:
    try:
        url = f"{_base_url()}/api/v1/collection/performance-daily"
        if date:
            url += f"?date={quote(date)}"
        r = await _get(url)
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_collection_performance_daily failed: {e}")
        return None


# ====================================================================== #
#  operations — 运营支撑接口                                                 #
# ====================================================================== #

async def fetch_customer_notifications(customer_no: str) -> list[dict] | None:
    try:
        r = await _get(
            f"{_base_url()}/api/v1/customers/{quote(customer_no)}/notifications?page_size=100"
        )
        return _extract_list(r.json())
    except Exception as e:
        logger.warning(f"fetch_customer_notifications failed: {e}")
        return None


async def send_notification(
    customer_no: str,
    notification_type: str,
    content: str,
) -> dict | None:
    """POST /notifications — 发送业务通知。"""
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "customer_no": customer_no,
            "notification_type": notification_type,
            "content": content,
        }
        r = await _post(f"{_base_url()}/api/v1/notifications", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"send_notification failed: {e}")
        return None


async def create_support_ticket(
    customer_no: str,
    ticket_type: str,
    content: str,
) -> dict | None:
    """POST /support/tickets — 创建客服工单。"""
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "customer_no": customer_no,
            "ticket_type": ticket_type,
            "content": content,
        }
        r = await _post(f"{_base_url()}/api/v1/support/tickets", payload)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"create_support_ticket failed: {e}")
        return None


async def create_workflow_instance(
    workflow_type: str,
    **extra,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "workflow_type": workflow_type,
        }
        payload.update({k: v for k, v in extra.items() if v is not None})
        r = await _post(
            f"{_base_url()}/api/v1/workflow/instances", payload
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"create_workflow_instance failed: {e}")
        return None


async def fetch_workflow_instance(instance_no: str) -> dict | None:
    try:
        r = await _get(
            f"{_base_url()}/api/v1/workflow/instances/{quote(instance_no)}"
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_workflow_instance failed: {e}")
        return None


async def complete_workflow_task(
    task_no: str,
    task_result: str = "completed",
    remark: str | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "task_result": task_result,
        }
        if remark:
            payload["remark"] = remark
        r = await _post(
            f"{_base_url()}/api/v1/workflow/tasks/{quote(task_no)}/complete",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"complete_workflow_task failed: {e}")
        return None


async def fetch_support_ticket(ticket_no: str) -> dict | None:
    try:
        r = await _get(
            f"{_base_url()}/api/v1/support/tickets/{quote(ticket_no)}"
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_support_ticket failed: {e}")
        return None


async def feedback_support_ticket(
    ticket_no: str,
    feedback_type: str,
    content: str | None = None,
    rating: int | None = None,
) -> dict | None:
    try:
        payload = {
            "request_no": _make_idempotent_key(),
            "feedback_type": feedback_type,
        }
        if content:
            payload["content"] = content
        if rating is not None:
            payload["rating"] = rating
        r = await _post(
            f"{_base_url()}/api/v1/support/tickets/{quote(ticket_no)}/feedback",
            payload,
        )
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"feedback_support_ticket failed: {e}")
        return None


async def fetch_metrics_daily(
    date: str | None = None,
) -> dict | None:
    try:
        url = f"{_base_url()}/api/v1/metrics/daily"
        if date:
            url += f"?date={quote(date)}"
        r = await _get(url)
        return _extract_data(r.json())
    except Exception as e:
        logger.warning(f"fetch_metrics_daily failed: {e}")
        return None
