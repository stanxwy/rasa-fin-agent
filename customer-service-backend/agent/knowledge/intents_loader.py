from pathlib import Path

import yaml

from agent.knowledge.intents import KnowledgeIntent


class KnowledgeIntentLoader:
    """加载 ``flow_config/knowledge_intents.yml`` → ``dict[str, KnowledgeIntent]``。

    与 ``FlowLoader`` / ``ClarifyMessageLoader`` 同构：配置发现封装在 loader 内，
    ``load_many(paths)`` 保留供单测注入临时目录。``requires_object`` 已是纯 ``str``，
    不再耦合 ``ObjectType`` 枚举，换领域时 yml 直接声明自己的对象类型即可。
    """

    CONFIG_DIR = Path(__file__).resolve().parents[2] / "flow_config"
    REQUIRED_KEY = "intents"

    def load_from_config_dir(self) -> dict[str, KnowledgeIntent]:
        return self.load_many([self.CONFIG_DIR / "knowledge_intents.yml"])

    def load_many(self, paths: list[Path]) -> dict[str, KnowledgeIntent]:
        intents: dict[str, KnowledgeIntent] = {}
        for path in paths:
            if not path.exists():
                raise FileNotFoundError(f"Knowledge intent config not found: {path}")
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            raw = data.get(self.REQUIRED_KEY, {})
            for intent_id, fields in raw.items():
                intents[intent_id] = KnowledgeIntent.model_validate(fields)
        return intents
