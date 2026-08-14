import logging

from agent.domain.contexts import SystemContext
from agent.domain.state import DialogueState
from agent.task.flow.flows import FlowsList

logger = logging.getLogger(__name__)


def begin_system_flow(state: DialogueState, flows: FlowsList, ctx: SystemContext) -> None:
    """
    启动一个系统流程（过场），并自动解析其入口步骤。

    把"查 flow -> 解析 start step -> 设置 step_id -> 启动"收敛到一处，
    避免每个调用方都手写 `flows.get_flow_by_id(...).start_step().id`，
    也让 flow id 只由 SystemContext 的 Literal 作为唯一真源，
    同时顺带校验引用的系统流程在配置里确实存在。
    """
    flow = flows.get_flow_by_id(ctx.flow_id)
    if flow is None:
        raise ValueError(f"System flow '{ctx.flow_id}' not found in flow config.")
    start_step = flow.start_step()
    if start_step is None:
        raise ValueError(f"System flow '{ctx.flow_id}' has no start step.")
    state.start_active_system_task(ctx.model_copy(update={"step_id": start_step.id}))
