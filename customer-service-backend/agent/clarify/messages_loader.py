from __future__ import annotations

from pathlib import Path

import yaml

from agent.clarify.responder import ClarifyResponder


class ClarifyMessageLoader:
    """加载澄清话术（bot 对外文案）。

    配置发现逻辑内聚于此，与 ``FlowLoader`` 同构：默认从 ``domain_config`` 目录
    收集 ``clarify_messages`` 段，``load_many`` 仍公开以便单测注入临时目录。

    必填 key 集合由 ``ClarifyResponder.required_message_keys()`` 单一提供，
    本 loader 不重复声明文案 key 字符串（避免与 ``ClarifyReason`` 漂移）。
    """

    CONFIG_DIR = Path(__file__).resolve().parents[2] / "domain_config"

    def load_from_config_dir(self, object_clarify_keys: dict[str, str]) -> dict[str, str]:
        paths = [
            p for p in self.CONFIG_DIR.iterdir()
            if p.is_file() and p.suffix in (".yml", ".yaml")
        ]
        return self.load_many(paths, object_clarify_keys)

    def load_many(self, paths: list[Path], object_clarify_keys: dict[str, str]) -> dict[str, str]:
        merged: dict[str, str] = {}
        for path in paths:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            section = data.get("clarify_messages")
            if isinstance(section, dict):
                merged.update(section)

        if not merged:
            raise FileNotFoundError(
                f"No 'clarify_messages' section found in {paths}"
            )
        missing = [k for k in ClarifyResponder.required_message_keys(object_clarify_keys) if k not in merged]
        if missing:
            raise ValueError(f"clarify_messages missing required keys: {missing}")
        return merged
