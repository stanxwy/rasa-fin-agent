from pydantic import BaseModel


class KnowledgeIntent(BaseModel):
    id: str
    description: str
    provider_ids: list[str] = []
    # 纯 str：对象类型由领域配置（knowledge_intents.yml）声明，
    # 不再耦合 ObjectType 枚举。`turn_validator` 用 StrEnum 相等性比较，类型放宽无行为变化。
    requires_object: str | None = None
    # 除 requires_object 外，还接受的其他对象类型。
    # 例如：transaction_info 的主要对象是 transaction，但也接受 bank_account（按账号查流水）。
    accepts_objects: list[str] = []
