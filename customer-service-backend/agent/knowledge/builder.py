import importlib
import inspect
import logging

from agent.knowledge.providers import KnowledgeProvider
from agent.knowledge.registry import KnowledgeProviderRegistry

logger = logging.getLogger(__name__)


def discover_providers() -> list[KnowledgeProvider]:
    """
    自动发现 ``agent.knowledge.providers`` 模块中所有 KnowledgeProvider 子类并实例化。

    与 ``agent.task.action.builder.register_custom_actions`` 同构：
    - 扫描目标模块中定义的类（跳过导入的类与基类）
    - 类必须继承 KnowledgeProvider 且定义了非空 ``provider_id``
    - 实例化后返回列表，供 KnowledgeProviderRegistry 使用

    新增 Provider 时只需在 providers.py 中定义类即可，无需修改本函数或 singleton.py。
    """
    module = importlib.import_module("agent.knowledge.providers")
    providers: list[KnowledgeProvider] = []

    for _, obj in inspect.getmembers(module, inspect.isclass):
        if not issubclass(obj, KnowledgeProvider) or obj is KnowledgeProvider:
            continue
        # 只注册在该模块中定义的类，跳过跨模块导入的类
        if obj.__module__ != module.__name__:
            continue
        if not getattr(obj, "provider_id", None):
            raise ValueError(
                f"KnowledgeProvider {obj.__name__} must define a non-empty `provider_id` attribute"
            )
        providers.append(obj())
        logger.info(f"Registered knowledge provider {obj.__name__} ({obj.provider_id})")

    return providers


def build_provider_registry() -> KnowledgeProviderRegistry:
    """构建 KnowledgeProviderRegistry，自动发现所有 Provider。"""
    return KnowledgeProviderRegistry(discover_providers())
