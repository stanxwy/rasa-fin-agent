import logging
import time

from agent.chitchat.handler import ChitchatHandler
from agent.clarify.responder import ClarifyResponder
from agent.domain.contexts import TaskContext
from agent.domain.messages import BotMessage, MessageType, ObjectType, UserMessage
from agent.domain.state import DialogueState
from agent.knowledge.handler import KnowledgeHandler
from agent.plan.models import ClarifyReason, TurnPlan, TurnPlanValidationResult
from agent.plan.turn_planner import TurnPlanner
from agent.plan.turn_validator import TurnPlanValidator
from agent.task.command.models import Command, SetSlotsCommand
from agent.task.flow.flows import FlowsList
from agent.task.handler import TaskHandler

logger = logging.getLogger(__name__)

class DialogueEngine:

    def __init__(self,
        turn_planner: TurnPlanner,
        turn_plan_validator: TurnPlanValidator,
        task_handler: TaskHandler,
        knowledge_handler: KnowledgeHandler,
        chitchat_handler: ChitchatHandler,
        clarify_responder: ClarifyResponder,
    ) -> None:
        self.turn_planner = turn_planner
        self.turn_plan_validator = turn_plan_validator
        self.task_handler = task_handler
        self.knowledge_handler = knowledge_handler
        self.chitchat_handler = chitchat_handler
        self.clarify_responder = clarify_responder
        

    async def process_message(self, 
        dialogue_state: DialogueState,
        user_message: UserMessage
    ) -> DialogueState:
        logger.info("Start TURN " + ">" * 100)
        self._prepare_session(dialogue_state)

        self._begin_turn(dialogue_state, user_message)
        dialogue_state.log_stat()

        if user_message.type == MessageType.TEXT:
            messages = await self._handle_text_message(dialogue_state)
        else:
            dialogue_state.set_focused_object(user_message.object)
            messages = await self._handle_object_message(user_message, dialogue_state)

        self._commit_turn(dialogue_state, messages)
        logger.info("End TURN " + "<" * 100)
        return dialogue_state


    def _prepare_session(self, dialogue_state: DialogueState) -> None:
        if not dialogue_state.validate_current_session():
            dialogue_state.reset_runtime_state_for_new_session()
            dialogue_state.start_session()

    def _begin_turn(self, 
        dialogue_state: DialogueState, 
        user_message: UserMessage
    ) -> None:
        dialogue_state.begin_turn(user_message)

    def _commit_turn(self, 
        dialogue_state: DialogueState,
        bot_messages: list[BotMessage]
    ) -> None:
        now = time.time()
        for bot_msg in bot_messages:
            if bot_msg.timestamp is None:
                bot_msg.timestamp = now
        dialogue_state.pending_turn.bot_messages.extend(bot_messages)
        dialogue_state.commit_turn()


    async def _handle_text_message(self, dialogue_state: DialogueState) -> list[BotMessage]:
        available_flows = self.task_handler.flows
        available_intents = self.knowledge_handler.knowledge_intents

        turn_plan: TurnPlan = await self.turn_planner.predict(
            dialogue_state, 
            available_flows, 
            available_intents)

        validated: TurnPlanValidationResult = self.turn_plan_validator.validate(
            dialogue_state, 
            turn_plan, 
            available_flows, 
            available_intents)

        if not validated.valid:
            return await self.clarify_responder.respond(dialogue_state, validated.reason)

        if turn_plan.task is not None:
            return await self.task_handler.handle(
                commands=turn_plan.task.commands,
                state=dialogue_state,
            )
        elif turn_plan.knowledge is not None:
            return await self.knowledge_handler.handle(
                intents=turn_plan.knowledge.intents,
                state=dialogue_state,
            )
        else:
            return await self.chitchat_handler.handle(state = dialogue_state)


    async def _handle_object_message(self,
        message: UserMessage,
        state: DialogueState,
    ) -> list[BotMessage]:
        
        commands: list[Command] = self._resolve_object_commands(
            message=message,
            state=state,
            flows=self.task_handler.flows,
        )

        # scenario 1: object matches slot required in active task flow
        if commands:
            return await self.task_handler.handle(commands=commands, state=state)

        # scenario 2: slot required in active task flow already has value
        # or slot required in active task flow does not match object
        # or active task does not require any slot
        if state.active_task is not None:
            return await self.task_handler.handle(commands=[], state=state)

        # scenario 3: no active task, clarify intent for object message
        return await self.clarify_responder.respond(
            state=state,
            reason=ClarifyReason.OBJECT_REQUIRES_INTENT,
        )

    def _resolve_object_commands(
        self, 
        message: UserMessage,
        state: DialogueState,
        flows: FlowsList
    ) -> list[Command]:
        focused_object = message.object
        if focused_object is None:
            return []
        object_type = focused_object.type

        if object_type == ObjectType.ORDER:
            if self._flow_has_unfilled_collect_slot(state, flows, "order_number"):
                return [SetSlotsCommand(command="set_slots", slots={"order_number": focused_object.id})]
            return []

        if object_type == ObjectType.PRODUCT:
            if self._flow_has_unfilled_collect_slot(state, flows, "product_id"):
                return [SetSlotsCommand(command="set_slots", slots={"product_id": focused_object.id})]
            return []

        return []

    def _flow_has_unfilled_collect_slot(
        self,
        state: DialogueState,
        flows: FlowsList,
        slot_name: str
    ) -> bool:
        """
        check if active task exists
        check if flow in active task is valid
        check if slots in active task already has value
        check if flow has a step to collect this slot
        """
        active_task: TaskContext = state.active_task
        if active_task is None:
            return False

        # defensive check: should not happen
        flow_id = active_task.flow_id
        flow = flows.get_flow_by_id(flow_id)
        if flow is None:
            return False

        # slot already filled
        if slot_name in active_task.slots:
            return False

        # NOTE: why not check (slot_name in active_task.slots.keys())
        # is slots in TaskContext initialized when active_task is created?
        # NO! active_task.slots will be an empty dict when active_task is created, 
        # it stores the slots to be filled
        # for step in flow.steps:
        #     if isinstance(step, CollectFlowStep) and step.slot_name == slot_name:
        #         return True
        # return False
        return slot_name in flow.collect_step_slot_names
        