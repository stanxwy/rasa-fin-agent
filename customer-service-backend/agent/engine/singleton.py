import logging

from agent.chitchat.handler import ChitchatHandler
from agent.chitchat.responder import ChitchatResponder
from agent.clarify.messages_loader import ClarifyMessageLoader
from agent.clarify.responder import ClarifyResponder
from agent.domain.config_loader import DomainConfigLoader
from agent.domain.object_config_loader import ObjectConfigLoader
from agent.engine.dialogue_engine import DialogueEngine
from agent.knowledge.builder import build_provider_registry
from agent.knowledge.handler import KnowledgeHandler
from agent.knowledge.intents_loader import KnowledgeIntentLoader
from agent.knowledge.responder import KnowledgeResponder
from agent.plan.turn_planner import TurnPlanner
from agent.plan.turn_validator import TurnPlanValidator
from agent.prompts.history_builder import HistoryBuilder
from agent.task.action.builder import build_action_runner
from agent.task.command.processor import CommandProcessor
from agent.task.flow.executor import FlowExecutor
from agent.task.flow.loader import FlowLoader, validate_flow_actions
from agent.task.handler import TaskHandler

logger = logging.getLogger(__name__)

def build_dialogue_engine() -> DialogueEngine:
    logger.info("Initializing dialogue engine...")
    # 领域展示配置（人设等）先加载——所有渲染器通过构造函数注入，不再硬编码。
    domain = DomainConfigLoader().load_from_config_dir()
    persona = domain.persona

    # 业务对象配置（label / clarify_key）——供 HistoryBuilder 和 ClarifyResponder 使用。
    object_config = ObjectConfigLoader().load_from_config_dir()
    HistoryBuilder.configure(labels=object_config.labels)
    logger.info(f"Loaded {len(object_config.type_names)} object types from objects.yml")

    # 能力（action 注册表）必须先于"引用能力的配置（flow）"存在——DI 组合根的标准次序。
    action_runner = build_action_runner(persona=persona)

    flow_list = FlowLoader().load_from_config_dir()
    # 加载边界校验：yml 引用的 action 必须已注册，否则启动时即失败。
    validate_flow_actions(flow_list, action_runner.registry)
    logger.info(f"Loaded {len(flow_list.flows)} flows and {len(flow_list.slots)} slots from {FlowLoader.CONFIG_DIR}")

    knowledge_intents = KnowledgeIntentLoader().load_from_config_dir()
    logger.info(f"Loaded {len(knowledge_intents)} knowledge intents from {KnowledgeIntentLoader.CONFIG_DIR}")

    engine = DialogueEngine(
        turn_planner = TurnPlanner(),
        turn_plan_validator = TurnPlanValidator(),
        task_handler = TaskHandler(
            flows=flow_list,
            command_processor=CommandProcessor(),
            flow_executor=FlowExecutor(),
            action_runner=action_runner,
        ),
        knowledge_handler=KnowledgeHandler(
            knowledge_intents=knowledge_intents,
            provider_registry=build_provider_registry(),
            knowledge_responder=KnowledgeResponder(persona=persona),
        ),
        chitchat_handler=ChitchatHandler(responder=ChitchatResponder(persona=persona)),
        clarify_responder=ClarifyResponder(
            messages=ClarifyMessageLoader().load_from_config_dir(object_config.clarify_keys),
            persona=persona,
            object_clarify_keys=object_config.clarify_keys,
        ),
    )
    logger.info("Dialogue engine initialized...")
    return engine
