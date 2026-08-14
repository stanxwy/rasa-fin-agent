from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class ObjectMeta(BaseModel):
    """单个业务对象类型的展示元数据。"""
    label: str
    clarify_key: str


class ObjectConfig:
    """从 objects.yml 加载的业务对象配置。

    提供 label / clarify_key 的查询接口，供 HistoryBuilder 和 ClarifyResponder 使用。
    """

    def __init__(self, objects: dict[str, ObjectMeta]) -> None:
        self._objects = objects

    @property
    def type_names(self) -> list[str]:
        """所有已注册的对象类型名。"""
        return list(self._objects.keys())

    @property
    def labels(self) -> dict[str, str]:
        """type → label 映射，供 HistoryBuilder 使用。"""
        return {k: v.label for k, v in self._objects.items()}

    @property
    def clarify_keys(self) -> dict[str, str]:
        """type → clarify_key 映射，供 ClarifyResponder 使用。"""
        return {k: v.clarify_key for k, v in self._objects.items()}


class ObjectConfigLoader:
    """从 domain_config/domain.yml 的 objects 段加载业务对象配置。"""

    CONFIG_DIR = Path(__file__).resolve().parents[2] / "domain_config"

    def load_from_config_dir(self) -> ObjectConfig:
        path = self.CONFIG_DIR / "domain.yml"
        return self.load(path)

    def load(self, path: Path) -> ObjectConfig:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        raw_objects: dict = data.get("objects", {})
        if not raw_objects:
            raise ValueError(f"No 'objects' section found in {path}")
        objects = {
            key: ObjectMeta(**meta)
            for key, meta in raw_objects.items()
        }
        return ObjectConfig(objects)
