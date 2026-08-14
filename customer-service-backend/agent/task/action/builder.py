import importlib
import inspect
import logging
import pkgutil

from agent.task.action.base import Action
from agent.task.action.builtin.action_listen import ActionListen
from agent.task.action.builtin.action_response import ActionResponse
from agent.task.action.registry import ActionRegistry
from agent.task.action.runner import ActionRunner

logger = logging.getLogger(__name__)

def register_builtin_actions(action_runner: ActionRunner, persona: str = ""):
    """
    Register built-in actions explicitly.

    Built-in actions are tightly coupled to the core conversation loop
    (e.g., listening for user input, producing bot responses). They are
    registered manually to make dependencies and lifecycle explicit.
    """
    action_listen = ActionListen()
    action_response = ActionResponse(persona=persona)
    action_runner.registry.register(action_listen)
    action_runner.registry.register(action_response)


def register_custom_actions(action_runner: ActionRunner):
    """
    Auto-discover and register custom actions under `agent.task.action.custom`.

    This mechanism follows the Open–Closed Principle:
    - The registration logic is closed for modification.
    - New actions can be added by simply creating new modules or classes.

    Rules:
    - Only scans modules directly under `custom/`, not sub-packages.
    - Only registers classes defined in the scanned module
      (imported classes are skipped to avoid duplicate registration).
    - Classes must inherit from `Action` and define a unique `name`.

    Example:
        To add a new action:
        1. Create `agent/task/action/custom/lookup_coupon.py`
        2. Define `class LookupCouponAction(Action):`
        3. Set `name = "action_lookup_coupon"`
        4. Implement `async def run(...)`
        5. Reference `"action_lookup_coupon"` in flow YAML

    No changes to this file are required.
    """
    package = importlib.import_module("agent.task.action.custom")

    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__, prefix=f"{package.__name__}."):
        logger.info(f"Checking module: {module_name}")

        # Skip sub-packages (only register actions from flat modules)
        if is_pkg:
            logger.info(f"Skipping sub-package: {module_name}")
            continue

        module = importlib.import_module(module_name)
        for _, obj in inspect.getmembers(module, inspect.isclass):
            logger.info(f"Inspecting class {obj.__name__} in module {module_name}")
            if not issubclass(obj, Action) or obj is Action:
                logger.info(f"Skipping non-Action class {obj.__name__} in module {module_name}")
                continue

            # Only register classes defined in this module
            # Prevents re-registering actions imported across modules
            if obj.__module__ != module.__name__:
                logger.info(f"Skipping imported class {obj.__name__} from module {obj.__module__}")
                continue

            # Check for required Action attributes
            if not getattr(obj, "name", None):
                raise ValueError(f"Action {obj.__name__} must define a `name` attribute")
            
            action_runner.registry.register(obj())
            logger.info(f"Registered class {obj.__name__} ({module_name})")


def build_action_runner(persona: str = "") -> ActionRunner:
    """
    Build and initialize the global ActionRunner.

    Responsibilities:
    1. Create the ActionRegistry
    2. Register built-in actions
    3. Auto-discover and register custom actions

    Args:
        persona: 领域人设文案，注入到 action_response 的 rephrase/generate 提示词。

    Returns:
        A fully initialized ActionRunner ready for dispatch.
    """
    action_runner = ActionRunner(ActionRegistry())
    register_builtin_actions(action_runner, persona=persona)
    register_custom_actions(action_runner)
    return action_runner