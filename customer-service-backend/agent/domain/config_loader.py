from pathlib import Path

import yaml
from pydantic import BaseModel


class DomainConfig(BaseModel):
    """领域级展示配置（人设等）。

    单一真源是 ``domain_config/domain.yml``；换领域只需替换该文件，
    内核渲染器通过构造函数注入 ``persona`` 消费，不再硬编码。
    """

    persona: str


class DomainConfigLoader:
    """加载 ``domain_config/domain.yml``。

    与 ``ClarifyMessageLoader`` / ``FlowLoader`` 同构：配置发现封装在 loader 内，
    ``load_many(paths)`` 保留供单测注入临时目录。
    """

    CONFIG_DIR = Path(__file__).resolve().parents[2] / "domain_config"

    def load_from_config_dir(self) -> DomainConfig:
        return self.load_many([self.CONFIG_DIR / "domain.yml"])

    def load_many(self, paths: list[Path]) -> DomainConfig:
        merged: dict = {}
        for path in paths:
            if not path.exists():
                raise FileNotFoundError(f"Domain config not found: {path}")
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            merged.update(data)
        return DomainConfig.model_validate(merged)
