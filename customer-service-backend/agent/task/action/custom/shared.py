from typing import Any
from urllib.parse import quote

from agent.conf.settings import settings
from agent.infra import http_client

logger = __import__("logging").getLogger(__name__)

def _base_url() -> str:
    return settings.commerce_api_base_url.rstrip("/")


def _extract_data(result: dict | None) -> dict | None:
    logger.info(f"fetch result: \n{result}")
    data = result.get("data") if isinstance(result, dict) else None
    return data if isinstance(data, dict) else None


async def fetch_order(order_id: str) -> dict | None:
    try:
        # 注意此处：
        # 文件头部 from agent.infra import http_client
        # 此处使用 http_client.http_client.get(url) 调用

        # 不要这样做：
        # 文件头部 from agent.infra.http_client import http_client
        # 此处使用 http_client.get(url) 调用
        # 会使拿到的 http_client 是 None
        r = await http_client.http_client.get(f"{_base_url()}/orders/{quote(order_id)}")
        return _extract_data(r.json())
    except Exception:
        return None


async def fetch_logistics(order_id: str) -> dict | None:
    try:
        r = await http_client.http_client.get(f"{_base_url()}/orders/{quote(order_id)}/logistics")
        return _extract_data(r.json())
    except Exception:
        return None


async def fetch_product(product_id: str) -> dict | None:
    try:
        r = await http_client.http_client.get(f"{_base_url()}/products/{quote(product_id)}")
        return _extract_data(r.json())
    except Exception:
        return None


def build_order_summary(payload: dict[str, Any]) -> str:
    parts = []
    if payload.get("amount"):
        parts.append(f"订单金额 ¥{payload['amount']}")
    items = payload.get("items") or []
    if items:
        titles = [str(item.get("title_snapshot") or "").strip()
                  for item in items[:2] if item.get("title_snapshot")]
        if titles:
            parts.append("商品：" + "、".join(titles))
    return "。".join(parts) + "。" if parts else ""


if __name__ == "__main__":
    import asyncio
    import json

    async def test():
        http_client.init_http_client()

        order = await fetch_order("B20260409001")
        print(json.dumps(order, ensure_ascii=False, indent=2))

        logistics = await fetch_logistics("B20260409001")
        print(json.dumps(logistics, ensure_ascii=False, indent=2))

        product = await fetch_product("SKU10006")
        print(json.dumps(product, ensure_ascii=False, indent=2))

        await http_client.close_http_client()
    
    result = asyncio.run(test())

"""
python -m agent.task.action.custom.shared
get_settings will be called only once...
{
  "order_id": "B20260409001",
  "status": "运输中",
  "status_desc": "包裹正在运输途中，请耐心等待。",
  "amount": "699.00",
  "created_at": "2026-04-09T20:30:00",
  "receiver_name": "王女士",
  "receiver_phone_masked": "139****5678",
  "receiver_address": "杭州市西湖区文三路 88 号",
  "items": [
    {
      "product_id": "SKU10006",
      "title": "罗技 MX Master 3S 鼠标",
      "quantity": 1,
      "price": "699.00"
    }
  ]
}
{
  "order_id": "B20260409001",
  "logistics_company": "顺丰速运",
  "tracking_number": "SF0005566778899",
  "status": "派送中",
  "status_desc": "快件已到达派送站点，正在安排派送。",
  "traces": [
    {
      "time": "2026-04-11T08:40:00",
      "desc": "快件已到达派送站点，正在安排派送。"
    },
    {
      "time": "2026-04-10T22:15:00",
      "desc": "快件已到达杭州转运中心。"
    },
    {
      "time": "2026-04-10T09:20:00",
      "desc": "商家已发货，顺丰已揽收。"
    }
  ]
}
{
  "product_id": "SKU10006",
  "title": "罗技 MX Master 3S 鼠标",
  "description": "静音微动，支持多设备切换，适合办公与设计。",
  "price": "699.00",
  "stock_status": "有货",
  "cover_url": "https://placehold.co/400x400/424242/ffffff?text=MX+Master+3S",
  "attributes": {
    "颜色": "石墨灰",
    "连接方式": "蓝牙/USB接收器",
    "适用系统": "Windows/macOS"
  }
}
"""