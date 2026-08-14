import logging

from agent.domain.messages import BotMessage
from agent.domain.state import DialogueState
from agent.task.action.runner import ActionRunner
from agent.task.command.models import Command
from agent.task.command.processor import CommandProcessor
from agent.task.flow.executor import FlowExecutor
from agent.task.flow.flows import FlowsList

logger = logging.getLogger(__name__)

class TaskHandler:
    def __init__(
        self,
        flows: FlowsList,
        command_processor: CommandProcessor,
        flow_executor: FlowExecutor,
        action_runner: ActionRunner
    ):
        self.flows = flows
        self.command_processor = command_processor
        self.flow_executor = flow_executor
        self.action_runner = action_runner


    async def handle(self, commands: list[Command], state: DialogueState) -> list[BotMessage]:
        """
        {
            'task': {
                'commands': [
                    {'command': 'start_flow', 'flow': 'logistics_tracking'}, 
                    {'command': 'set_slots', 'slots': {'order_number': 'B20260401002'}}
                ]
            }, '
            knowledge': None, 
            'chitchat': None
        }
        """
        # 阶段1:把命令应用到 state
        self.command_processor.run(commands, state, self.flows)

        # 阶段2:推进流程,生成回复
        logger.info("=" * 20 + " FLOW EXECUTION START " + "=" * 20)
        messages = await self.flow_executor.run_task(
            state, self.flows, self.action_runner
        )
        logger.info("=" * 20 + " FLOW EXECUTION END " + "=" * 20)
        return messages