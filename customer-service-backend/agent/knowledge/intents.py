from pydantic import BaseModel


class KnowledgeIntent(BaseModel):
    id: str
    description: str
    provider_ids: list[str] = []
    # 纯 str：对象类型由领域配置（knowledge_intents.yml）声明，
    # 不再耦合 ObjectType 枚举。`turn_validator` 用 StrEnum 相等性比较，类型放宽无行为变化。
    requires_object: str | None = None
