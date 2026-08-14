import logging

from agent.domain.contexts import (
    CanceledSystemContext,
    InterruptedSystemContext,
    ResumedSystemContext,
    StartedSystemContext,
    TaskContext,
)
from agent.domain.state import DialogueState
from agent.task.command.models import (
    CancelFlowCommand,
    Command,
    ResumeFlowCommand,
    SetSlotsCommand,
    StartFlowCommand,
)
from agent.task.flow.flows import FlowsList
from agent.task.flow.system_flow import begin_system_flow

logger = logging.getLogger(__name__)

class CommandProcessor:
    """
    [
        StartFlowCommand(command="start_flow", flow="refund_request"),
        SetSlotsCommand(command="set_slots", slots={"order_number": "A001"}),
    ]
    """
    def run(self,
        commands: list[Command],
        state: DialogueState,
        flows: FlowsList,
    ) -> None:
        for command in commands:
            self._apply(command, state, flows)

    def _apply(self,
        command: Command,
        state: DialogueState,
        flows: FlowsList,
    ) -> None:
        logger.info(f"[{state.current_session_id}] Processing command: {command}")
        if isinstance(command, StartFlowCommand):
            self._handle_start_flow(command, state, flows)
        elif isinstance(command, SetSlotsCommand):
            self._handle_set_slots(command, state)
        elif isinstance(command, CancelFlowCommand):
            self._handle_cancel_flow(state, flows)
        elif isinstance(command, ResumeFlowCommand):
            self._handle_resume_flow(command, state, flows)

    @staticmethod
    def _activate_started_system_flow(
            state: DialogueState, 
            flows: FlowsList, 
            started_flow_id: str, started_flow_name: str):
        begin_system_flow(state, flows, StartedSystemContext(
            started_flow_id=started_flow_id,
            started_flow_name=started_flow_name,
        ))

    @staticmethod
    def _activate_interrupted_system_flow(
            state: DialogueState, 
            flows: FlowsList, 
            interrupted_flow_id: str,interrupted_flow_name: str,
            started_flow_id: str, started_flow_name: str):
        begin_system_flow(state, flows, InterruptedSystemContext(
            interrupted_flow_id=interrupted_flow_id,
            interrupted_flow_name=interrupted_flow_name,
            started_flow_id=started_flow_id,
            started_flow_name=started_flow_name
        ))

    @staticmethod
    def _activate_resumed_system_flow(
            state: DialogueState, 
            flows: FlowsList,
            resumed_flow_id: str, resumed_flow_name: str):
        begin_system_flow(state, flows, ResumedSystemContext(
            resumed_flow_id=resumed_flow_id,
            resumed_flow_name=resumed_flow_name
        ))

    @staticmethod
    def _activate_canceled_system_flow(
            state: DialogueState,
            flows: FlowsList,
            canceled_flow_id: str, canceled_flow_name: str):
        begin_system_flow(state, flows, CanceledSystemContext(
            canceled_flow_id=canceled_flow_id,
            canceled_flow_name=canceled_flow_name
        ))


    def _handle_start_flow_v1(self, command: StartFlowCommand, state: DialogueState, flows: FlowsList) -> None:
        biz_flow_id = command.flow
        biz_flow = flows.get_flow_by_id(biz_flow_id)
        biz_flow_name = flows.get_readable_flow_name(biz_flow_id)
        
        start_step = biz_flow.start_step()
        state.start_active_task(TaskContext(flow_id=biz_flow_id, step_id=start_step.id))

        self._activate_started_system_flow(
            state, flows, biz_flow_id, biz_flow_name,
        )

    def _handle_start_flow(self, command: StartFlowCommand, state: DialogueState, flows: FlowsList) -> None:
        
        state.end_active_system_task()

        # 防御:不允许直接启动 system_ 开头的内部流程
        biz_flow_id = command.flow
        if biz_flow_id.startswith("system_"):
            raise ValueError(f"Cannot start system flow: '{biz_flow_id}'")

        # 校验:流程必须存在
        biz_flow = flows.get_flow_by_id(biz_flow_id)
        if biz_flow is None:
            raise ValueError(f"Unknown flow: '{biz_flow_id}'.")
        biz_flow_name = flows.get_readable_flow_name(biz_flow_id)

        # 校验:流程必须有起点
        start_step = biz_flow.start_step()
        if start_step is None:
            raise ValueError(f"No start step in user flow '{biz_flow_id}'")

        active_task = state.active_task

        # ===== 情况一:当前有活跃任务 =====
        if active_task is not None:
            logger.info(f"[{state.current_session_id}] Current active flow '{active_task.flow_id}'.")
            # 同一个流程：不重复启动
            if active_task.flow_id == biz_flow_id:
                logger.info(f"[{state.current_session_id}] Flow '{biz_flow_id}' to be started is already active.")
                return

            # 不是同一个流程：把当前任务放进暂停栈
            logger.info(f"[{state.current_session_id}] Flow '{biz_flow_id}' to be started is different from current active flow '{active_task.flow_id}'.")
            state.interrupt_active_task()

            # 试着从暂停栈恢复要开的流程
            resumed = state.resume_paused_task(biz_flow_id)
            if not resumed:
                # 要开的流程不在暂停栈 → 新建
                logger.info(f"[{state.current_session_id}] Flow '{biz_flow_id}' is not in paused tasks, starting a new one.")
                state.start_active_task(TaskContext(flow_id=biz_flow_id, step_id=start_step.id))

            # 激活"打断"过场
            logger.info(f"[{state.current_session_id}] Flow '{active_task.flow_id}' interrupted, new flow '{biz_flow_id}' started.")
            self._activate_interrupted_system_flow(
                state, flows, 
                interrupted_flow_id=active_task.flow_id, 
                interrupted_flow_name=flows.get_readable_flow_name(active_task.flow_id),
                started_flow_id=biz_flow_id, 
                started_flow_name=biz_flow_name)
            return

        # ===== 情况二:当前没有活跃任务 =====
        # 试着恢复同名任务
        logger.info(f"[{state.current_session_id}] No active flow in current session.")
        resumed = state.resume_paused_task(biz_flow_id)
        if resumed:
            logger.info(f"[{state.current_session_id}] Flow '{biz_flow_id}' resumed from paused tasks.")
            # 要开的流程在暂停栈 → 激活"恢复"过场
            self._activate_resumed_system_flow(
                state, flows, 
                resumed_flow_id=biz_flow_id, 
                resumed_flow_name=biz_flow_name)
            return

        logger.info(f"[{state.current_session_id}] Flow '{biz_flow_id}' is not in paused tasks, starting a new one.")
        # 要开的流程从没做过 → 新建
        state.start_active_task(TaskContext(flow_id=biz_flow_id, step_id=start_step.id))
        self._activate_started_system_flow(
            state, flows, biz_flow_id, biz_flow_name
        )


    def _handle_set_slots(self, command: SetSlotsCommand, state: DialogueState):
        state.set_slots(command.slots)


    def _handle_cancel_flow(self, state: DialogueState, flows: FlowsList):
        active_task = state.active_task

        state.cancel_active_task()

        self._activate_canceled_system_flow(
            state, flows, 
            canceled_flow_id=active_task.flow_id, 
            canceled_flow_name=flows.get_readable_flow_name(active_task.flow_id)
        )


    def _handle_resume_flow(self, command: ResumeFlowCommand, state: DialogueState, flows: FlowsList):
        # ===== 第一步:确定要恢复哪个流程 =====
        biz_flow = command.flow
        if biz_flow is not None:
            # 指名恢复:用户明确说了恢复哪个
            target_flow = flows.get_flow_by_id(biz_flow)
            if target_flow is None:
                raise ValueError(f"Unknown flow '{biz_flow}'.")
            target_flow_id = target_flow.id
            target_flow_name = target_flow.name
            logger.info(f"[{state.current_session_id}] Resuming specified flow '{target_flow_name}'.")
        else:
            # 不指名恢复:用户只说"继续刚才的" → 取暂停栈栈顶(最近挂起的)
            if not state.paused_tasks:
                logger.info(f"[{state.current_session_id}] No paused tasks to resume in session.")
                return
            top_paused = state.paused_tasks[-1]
            target_flow_id = top_paused.flow_id
            target_flow_name = flows.get_readable_flow_name(target_flow_id)
            logger.info(f"[{state.current_session_id}] Resuming unspecified flow '{target_flow_name}' from paused tasks.")

        # ===== 第二步:按"当前有没有活跃任务"恢复 =====
        active_task = state.active_task
        if active_task is not None:
            logger.info(f"[{state.current_session_id}] Current active flow '{active_task.flow_id}'.")
            if active_task.flow_id == target_flow_id:
                logger.info(f"[{state.current_session_id}] Flow '{target_flow_id}' to be resumed is already active.")
                return  # 1) 已经在办它,不重复
            
            state.interrupt_active_task()
            if not state.resume_paused_task(target_flow_id):
                logger.info(f"[{state.current_session_id}] Flow '{target_flow_id}' is not in paused tasks, rollback interrupted flow '{active_task.flow_id}'.")
                state.resume_paused_task()  # 2) 恢复失败,回退（将state.interrupted_active_task()压入栈顶的任务出栈）
                return

            logger.info(f"[{state.current_session_id}] Flow '{active_task.flow_id}' interrupted, flow '{target_flow_id}' resumed.")
            self._activate_interrupted_system_flow(  # 3) 打断当前+恢复目标
                state, flows, 
                interrupted_flow_id=active_task.flow_id, 
                interrupted_flow_name=flows.get_readable_flow_name(active_task.flow_id),
                started_flow_id=target_flow_id, 
                started_flow_name=target_flow_name)
        else:
            logger.info(f"[{state.current_session_id}] No active flow currently in session.")
            if not state.resume_paused_task(biz_flow):  # ④没任务,直接恢复
                logger.info(f"[{state.current_session_id}] Flow '{target_flow_id}' is not in paused tasks.")
                return

            logger.info(f"[{state.current_session_id}] Flow '{target_flow_id}' resumed.")
            resumed = state.active_task
            self._activate_resumed_system_flow(
                state, flows, 
                resumed.flow_id, 
                flows.get_readable_flow_name(resumed.flow_id))