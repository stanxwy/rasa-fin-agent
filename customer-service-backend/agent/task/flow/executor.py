import logging

from agent.domain.contexts import CollectedSystemContext
from agent.domain.messages import BotMessage, ObjectType
from agent.domain.state import DialogueState
from agent.task.action.base import ActionResult
from agent.task.action.runner import ActionCall, ActionRunner
from agent.task.flow.flows import FlowsList
from agent.task.flow.links import ConditionalLink, FallbackLink, StaticLink
from agent.task.flow.steps import (
    ActionFlowStep,
    CollectFlowStep,
    EndFlowStep,
    FlowStep,
    StartFlowStep,
)
from agent.task.flow.system_flow import begin_system_flow
from agent.utils.json_utils import to_json

logger = logging.getLogger(__name__)

_NEXT_STEP_ABSENT = "没有下一步"

class FlowExecutor:
    """
    流程执行器：推进yaml中定义的业务任务流程以及系统任务流程
    """

    async def run_task(self, state: DialogueState, flows: FlowsList, action_runner: ActionRunner) -> list[BotMessage]:

        messages: list[BotMessage] = []
        while True:  # 找要执行的流程步骤
            # 1. 推进流程以及内部step，当step的type类型是action是从advance_until_action中退出
            logger.info(f"Currently active \nSYSTEM TASK: {to_json(state.active_system_task)}, \nUSER TASK: {to_json(state.active_task)}")
            action_call: ActionCall = self.advance_until_action(state, flows)
            logger.info(f"ACTION CALL: {action_call}")
            # 2. 当action_name是action_listen的时候，本轮会话结束，并返回消息，等待下一轮的用户输入
            if action_call.action_name == "action_listen":
                break
            else:
                # 3. 如果是其他类型的action，则执行action
                action_result: ActionResult = await action_runner.run(action_call, state)
                logger.info(f"ACTION RESULT: {action_result}")
                state.set_slots(action_result.slot_updates)
                messages.extend(action_result.messages)
        # 4. 返回消息，等待下一轮的用户输入
        return messages


    def advance_until_action(self, state: DialogueState, flows: FlowsList) -> ActionCall:
        while True:
            # 1. 获取当前任务上下文对象：系统任务优先
            current_active_task = state.current_active_task()
            # 2. 如果当前没有任务，手动返回action_listen，等待用户输入
            # 两种典型情况：
            # - 业务流程刚跑完 end 步骤，active_task 被清空，又没有系统过场
            # - 用户刚启动会话，根本还没开任何任务
            if current_active_task is None:
                return ActionCall(action_name="action_listen")
            # 3. 获取当前流程对象
            flow = flows.get_flow_by_id(current_active_task.flow_id)
            # 4. 获取当前step
            step = flow.get_step_by_id(current_active_task.step_id)
            # 5. 运行当前step
            logger.info(f">>>>> Starting flow.step: [{flow.id}.{step.id}<{step.type}>]")
            action_call: ActionCall = self._run_step(step, state, flows)
            # 6. 如果step的类型是action,退出while true
            if action_call is not None:
                return action_call


    def _run_step(self, step: FlowStep, state: DialogueState, flows: FlowsList) -> ActionCall | None:
        if isinstance(step, StartFlowStep):
            return self._run_start_step(step, state)
        if isinstance(step, EndFlowStep):
            return self._run_end_step(state)
        if isinstance(step, CollectFlowStep):
            return self._run_collect_step(step, state, flows)
        if isinstance(step, ActionFlowStep):
            return self._run_action_step(step, state)

    def _run_start_step(self, step: StartFlowStep, state: DialogueState) -> None:
        # 1. 推进下一步
        self._advance_next_step(state, step)


    def _advance_next_step(self, state: DialogueState, step: FlowStep):
        # 1. 寻找下一个step id
        next_step_id = self._select_next_step(step, state)
        # 2. 更新当前任务上下文的step_id(给当前执行任务流程的上下文用)不做这个动作，出不来
        state.current_active_task().step_id = next_step_id
        logger.info(f"Cursor moved to next step: [{state.current_active_task().flow_id}.{next_step_id}]")

    def _select_next_step(self, step: FlowStep, state: DialogueState) -> str:
        logger.info(f"Determining next step {step.next}")
        for link in step.next:
            if isinstance(link, StaticLink):
                return link.target
            if (isinstance(link, ConditionalLink) 
                and self._eval_condition(state, link.condition)):
                    return link.target
            if isinstance(link, FallbackLink):
                return link.target
        return _NEXT_STEP_ABSENT


    def _eval_condition(self, state: DialogueState, condition: str) -> bool:
        data = {
            "slots": state.active_task.slots,
            # current_active_task：获取当前任务上下文对象：系统任务优先
            # model_dump：对象转字典
            "context": state.current_active_task().model_dump(mode="json")
        }
        return bool(eval(condition, {'__builtins__': None}, data))


    def _run_end_step(self, state: DialogueState) -> None:
        if state.active_system_task:
            # 清空state中系统任务流程上下文
            state.end_active_system_task()
        else:
            # 清空state中业务任务流程上下文
            state.end_active_task()


    def _run_action_step(self, step: ActionFlowStep, state: DialogueState) -> ActionCall:
        # 1. 推进下一步
        self._advance_next_step(state, step) # TODO: build action call first then advance to next step?
        # 2. 构造 ActionCall
        action_call  = self._build_action_call(state, step) 
        # 3. 退出内层让外层执行
        return action_call


    def _build_action_call(self, state: DialogueState, step: ActionFlowStep) -> ActionCall:
        # 1. 获取action_name (action_listen/action_response/action_xxx)
        # 2. 获取action_kwargs (构建参数)
        action_name = step.action
        action_kwargs = step.args
        # action_kwargs有可能有:结构有可能是一个str、dict、或者空字典{}
        # str: "context.response"
        if isinstance(action_kwargs, str):
            logger.info(f"Processing string type action kwargs: {action_kwargs}")
            action_kwargs = state.active_system_task.model_dump(mode="json")[action_kwargs.split(".")[1]]
        logger.info(f"Action kwargs to be passed: {action_kwargs}")
        return ActionCall(action_name=action_name, action_kwargs=action_kwargs)


    def _run_collect_step(self, step: CollectFlowStep, state: DialogueState, flows: FlowsList):
        # 1. 尝试自动补槽
        self._try_fill_slot_with_focused_object(state, step)
        # 2. 判断槽位是否已经填过
        if state.active_task.slots.get(step.slot_name):
            # 填过则直接执行下一步
            logger.info(f"Slot {step.slot_name} already filled")
            self._advance_next_step(state, step)
        else:
            # 没填过则启动系统过场：补槽任务
            logger.info(f"Slot {step.slot_name} not filled yet, starting system task to collect slot")
            begin_system_flow(state, flows, CollectedSystemContext(
                slot_name=step.slot_name,
                response=step.response.model_dump(mode="json"),
            ))


    def _try_fill_slot_with_focused_object(self, state: DialogueState, step: CollectFlowStep):
        if state.focused_object is None:
            logger.info("No FocusedObject to set slot")
            return
        if ((step.slot_name == 'order_number' and state.focused_object.type == ObjectType.ORDER)
            or (step.slot_name == "product_id" and state.focused_object.type == ObjectType.PRODUCT)):
            state.set_slots({step.slot_name: state.focused_object.id})
            logger.info(f"Slot {step.slot_name} set to {state.focused_object.id}")