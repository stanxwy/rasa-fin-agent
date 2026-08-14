import logging
import time
import uuid
from typing import Any

from pydantic import BaseModel

from agent.domain.contexts import SystemContext, TaskContext
from agent.domain.messages import BotMessage, FocusedObject, UserMessage
from agent.utils.json_utils import to_json

logger = logging.getLogger(__name__)

_SESSION_TIMEOUT = 60 * 60

class Turn(BaseModel):
    turn_id: str
    user_message: UserMessage
    bot_messages: list[BotMessage]

class Session(BaseModel):
    session_id: str
    started_at: float
    last_activity_at: float
    closed_at: float | None = None
    turns: list[Turn] = []

class DialogueState(BaseModel):
    sender_id: str
    active_task: TaskContext | None = None
    paused_tasks: list[TaskContext] = []
    active_system_task: SystemContext | None = None
    focused_object: FocusedObject | None = None
    sessions: list[Session] = []
    current_session_id: str | None = None
    pending_turn: Turn | None = None

    # --------------任务相关--------------------------
    def start_active_task(self, active_task: TaskContext):
        """
        把传进来的 TaskContext 设为活跃任务。
        调用时机：当 TurnPlanner 判断用户发起了一个新业务任务时。
        :param active_task:
        :return:
        """
        self.active_task = active_task

    def end_active_task(self):
        """
        结束业务任务
        调用时机：当业务任务流程跑到 end 步骤时。
        :return:
        """
        self.active_task = None

    def cancel_active_task(self):
        """
        取消业务任务
        把活跃任务和当前系统过场都清空
        调用时机：用户主动说"算了不退了"这类取消意图时。
        :return:
        """
        self.active_task = None
        self.active_system_task = None

    def interrupt_active_task(self):
        """
        中断活跃任务
        把当前活跃任务 移到挂起列表，再清空活跃任务。
        调用时机：用户在任务 A 中途切到任务 B 时。
        :return:
        """
        self.paused_tasks.append(self.active_task)
        self.active_task = None

    def resume_paused_task(self, flow_id: str | None = None) -> bool:
        """
        恢复业务任务:流程ID

        如果用户没有明确指定需要恢复的具体任务，那么 flow_id = None，恢复最近的任务
        如果用户明确指定需要恢复的具体任务：
        则按 flow_id 在挂起列表里找到这个任务，恢复为活跃任务，并从挂起列表里移除。

        调用时机：用户说"继续刚才的退款"这类意图时。

        注意：任务被恢复时，step_id 和 slots 都还在，所以可以从挂起前的位置接着跑，不用从头来。

        :return: 恢复成功或失败
        """

        # 1. 判断栈中是否存在中断的业务任务
        if not self.paused_tasks:
            return False

        # 2. 如果业务流程ID不存在
        if flow_id is None:
            self.active_task = self.paused_tasks.pop()
            return True

        # 2. 如果业务流程ID存在
        for i, paused_task in enumerate(self.paused_tasks):
            if paused_task.flow_id == flow_id:
                # 激活
                self.active_task = paused_task
                # 删除
                del self.paused_tasks[i]
                return True

        return False

    def start_active_system_task(self, active_system_task: SystemContext):
        """
        开启系统流程
        调用时机：每当系统要插播过场白（任务开始、打断、取消、恢复、收集槽位）时。
        :param active_system_task:
        :return:
        """
        self.active_system_task = active_system_task

    def end_active_system_task(self):
        """
        结束系统流程
        :return:
        """
        self.active_system_task = None
        
    def current_active_task(self) -> TaskContext | SystemContext:
        """
        返回当前正在执行的任务（系统流程、业务任务）
        先获取系统流程 如果获取不到 获取业务任务
        - 如果有系统流程，先返回系统流程
        - 否则返回业务任务

        为什么系统流程优先？
        因为系统流程往往是要插播一句过场白，必须先说完，然后才能让位给业务任务继续。
        :return:
        """
        return self.active_system_task or self.active_task

    # --------------槽位相关--------------------------
    def set_slots(self, slots: dict[str, Any]):
        if self.active_task:
            self.active_task.slots.update(slots)
        else:
            logger.warning("No active task to set slots")

    def remove_slot(self, slot_name: str):
        if self.active_task:
            self.active_task.slots.pop(slot_name)
        else:
            logger.warning("No active task to remove slots")

    # -------------- session相关 --------------------------
    def current_session(self) -> Session | None:
        """
        获取当前会话对象
        根据 current_session_id 在 sessions 里找出当前会话。
        :return:
        """
        for session in self.sessions:
            if session.session_id == self.current_session_id:
                return session

        return None

    def start_session(self):
        """
        开启新会话
        创建一个新的 Session，加进 sessions 列表，并把它设为当前会话。
        :return:
        """
        if self.current_session() is None:
            now = time.time()
            session_id = str(uuid.uuid4())
            session = Session(
                session_id=session_id,
                started_at=now,
                last_activity_at=now
            )
            self.sessions.append(session)
            self.current_session_id = session_id

    def validate_current_session(self) -> bool:
        """
        校验当前会话是否过期。
        如果过期，关闭当前会话并清空 current_session_id。
        返回 True 表示会话有效，False 表示已过期。
        """
        session = self.current_session()
        if session is None:
            return False

        now = time.time()
        if now - session.last_activity_at > _SESSION_TIMEOUT:
            self.close_current_session()
            return False

        # 会话续期
        session.last_activity_at = now
        return True

    def close_current_session(self):
        """
        关闭当前会话
        给当前会话打上关闭时间戳，再把 current_session_id 置空。
        :return:
        """
        if self.current_session() is not None:
            self.current_session().closed_at = time.time()
            self.current_session_id = None

    def reset_runtime_state_for_new_session(self):
        """
        重置会话状态
        session会话超时新会话开始前的"清理工作"。
        注意：
        - 它只清运行时字段：当前任务、挂起任务、系统过场、聚焦对象
        - 它不清 sessions：历史会话需要保留
        :return:
        """
        self.active_task = None
        self.active_system_task = None
        self.paused_tasks = []
        self.focused_object = None
        self.pending_turn = None
        self.current_session_id = None

    # --------------turn相关--------------------------
    def begin_turn(self, message: UserMessage):
        """
        开始一个turn
        收到用户消息后，把它装进一个新的 turn 对象
        先放到 pending_turn，而不是直接进 session。
        :param message:
        :return:
        """
        if self.current_session():
            self.pending_turn = Turn(
                turn_id=str(uuid.uuid4()),
                user_message=message,
                bot_messages=[]
            )

    def commit_turn(self):
        """
        提交一个turn
        本轮处理完成（机器人回复也填好了）后
        把 pending_turn 追加到当前会话的 turns 里，再把 pending_turn 清空。
        :return:
        """
        if self.current_session():
            self.current_session().turns.append(self.pending_turn)
            self.pending_turn = None

    def last_turn_messages(self) -> list[BotMessage]:
        """
        返回当前会话中最后提交的那个 turn 的机器人消息。

        service 层用它来从 state 投影出 ProcessResult，
        避免 bot_messages 在 state 和 ProcessResult 之间重复写入。
        没有当前会话或会话里还没有 turn 时返回空列表。
        """
        session = self.current_session()
        if session and session.turns:
            return session.turns[-1].bot_messages
        return []

    # --------------FocusedObject相关--------------------------
    def set_focused_object(self, focused_object: FocusedObject):
        """
        设置聚焦对象
        调用时机：
        用户发的不是文本而是一条对象消息时,例如前端点了订单卡片
        需要把这个对象设为当前关注的对象。
        :param focused_object:
        """
        self.focused_object = focused_object

    def log_stat(self):
        logger.info(f"[{self.current_session_id}] User message: {self.pending_turn.user_message.text or self.pending_turn.user_message.object}")
        logger.info(f"[{self.current_session_id}] Active system task: {to_json(self.active_system_task)}")
        logger.info(f"[{self.current_session_id}] Active user task: {to_json(self.active_task)}")
        logger.info(f"[{self.current_session_id}] Paused tasks: {[] if not self.paused_tasks else [to_json(task) for task in self.paused_tasks]}")
        logger.info(f"[{self.current_session_id}] Focused object: {to_json(self.focused_object)}")