from enum import StrEnum

from pydantic import BaseModel, Field


class ObjectType(StrEnum):
    """
    聚焦对象类型。用枚举取代散落的魔法字符串，便于类型检查与重命名。
    序列化后仍是裸字符串（"order"/"product"），前后端契约不变。

    注意：对象类型的展示元数据（label、clarify_key）已提取到
    ``domain_config/objects.yml``，由 ``ObjectConfigLoader`` 加载。
    新增对象类型时需同时在此枚举和 objects.yml 中添加。
    """
    ORDER = "order"
    PRODUCT = "product"
    BANK_ACCOUNT = "bank_account"
    BANK_CARD = "bank_card"
    CREDIT_CARD = "credit_card"
    DEPOSIT = "deposit"
    LOAN = "loan"
    WEALTH_PRODUCT = "wealth_product"
    FUND_PRODUCT = "fund_product"
    TRANSACTION = "transaction"
    TRANSFER = "transfer"


class FocusedObject(BaseModel):
    id: str
    type: ObjectType
    title: str | None = None
    attributes: dict = Field(default_factory=dict)


class MessageType(StrEnum):
    TEXT = "text"
    OBJECT = "object"


class UserMessage(BaseModel):
    sender_id: str
    message_id: str
    type: MessageType
    text: str | None = None
    object: FocusedObject | None = None
    # 消息时间（epoch 秒）。用于前端展示发送时间。
    timestamp: float | None = None


class BotMessage(BaseModel):
    text: str | None = None
    object: FocusedObject | None = None
    # 消息时间（epoch 秒）。用于前端展示发送时间。
    timestamp: float | None = None


class ProcessResult(BaseModel):
    sender_id: str
    message_id: str
    messages: list[BotMessage]
