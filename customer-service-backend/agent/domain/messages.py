from enum import StrEnum

from pydantic import BaseModel, Field


class ObjectType(StrEnum):
    """
    聚焦对象类型。用枚举取代散落的魔法字符串，便于类型检查与重命名。
    序列化后仍是裸字符串（"order"/"product"），前后端契约不变。
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


if __name__ == '__main__':
    fo = FocusedObject(id="1", type="order", title="标题")
    print(type(fo), fo)

    dumped = fo.model_dump()
    json_dict = fo.model_dump(mode='json')
    json_string = fo.model_dump_json()
    json_bytes = fo.model_dump_json().encode('utf-8')

    from_dumped = FocusedObject.model_validate(dumped)
    from_dict = FocusedObject.model_validate(json_dict)
    from_string = FocusedObject.model_validate_json(json_string)
    from_bytes = FocusedObject.model_validate_json(json_bytes.decode('utf-8'))

    
    print(type(dumped), dumped)
    print(type(json_dict), json_dict)
    print(type(json_string), json_string)
    print(type(json_bytes), json_bytes)

    print(type(from_dumped), from_dumped)
    print(type(from_dict), from_dict)
    print(type(from_string), from_string)
    print(type(from_bytes), from_bytes)

"""
python -m agent.domain.messages
<class '__main__.FocusedObject'> id='1' type='order' title='标题' attributes={}
<class 'dict'> {'id': '1', 'type': 'order', 'title': '标题', 'attributes': {}}
<class 'dict'> {'id': '1', 'type': 'order', 'title': '标题', 'attributes': {}}
<class 'str'> {"id":"1","type":"order","title":"标题","attributes":{}}
<class 'bytes'> b'{"id":"1","type":"order","title":"\xe6\xa0\x87\xe9\xa2\x98","attributes":{}}'
<class '__main__.FocusedObject'> id='1' type='order' title='标题' attributes={}
<class '__main__.FocusedObject'> id='1' type='order' title='标题' attributes={}
<class '__main__.FocusedObject'> id='1' type='order' title='标题' attributes={}
<class '__main__.FocusedObject'> id='1' type='order' title='标题' attributes={}
"""