import json
import logging
from typing import Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts.prompt import PromptTemplate
from pydantic import RootModel

from agent.domain.state import DialogueState
from agent.infra.llm import llm
from agent.knowledge.intents import KnowledgeIntent
from agent.plan.models import TurnPlan
from agent.prompts.history_builder import HistoryBuilder
from agent.prompts.loader import load_prompt
from agent.task.flow.flows import FlowsList

logger = logging.getLogger(__name__)

_HISTORY_LENGTH = 10

class TurnPlanner:

    async def predict(self, state: DialogueState, flows: FlowsList, intents: dict[str, KnowledgeIntent]) -> TurnPlan:

        prompt_inputs = self._build_prompt_inputs(state, flows, intents)

        turn_plan = await self._predict_from_prompt_inputs(prompt_inputs)

        return turn_plan


    def _build_prompt_inputs(self, state: DialogueState, flows_list: FlowsList, intents: dict[str, KnowledgeIntent]) -> dict[str, Any]:

        user_msg = HistoryBuilder.render_user_message(state.pending_turn.user_message)

        current_conversation = HistoryBuilder.build(state.current_session().turns[-_HISTORY_LENGTH:])

        active_task_json = (state.active_task.model_dump_json() 
            if state.active_task is not None else None)

        interrupted_tasks_json = RootModel(state.paused_tasks or []).model_dump_json()

        focused_object_json = (state.focused_object.model_dump_json() 
            if state.focused_object is not None else None)

        available_flows_json = json.dumps(
            [{k: v for k, v in flow.model_dump(mode="json").items() if k != "steps"} for flow in flows_list.flows],
            ensure_ascii=False)
        
        knowledge_intents_json = json.dumps(
            [{"id": intent.id, "description": intent.description} for intent in intents.values()], 
            ensure_ascii=False)

        return {
            "user_message": user_msg,
            "current_conversation": current_conversation,
            "active_task_json": active_task_json,
            "interrupted_tasks_json": interrupted_tasks_json,
            "focused_object_json": focused_object_json,
            "available_flows_json": available_flows_json,
            "knowledge_intents_json": knowledge_intents_json
        }


    async def _predict_from_prompt_inputs(self, prompt_inputs: dict[str, Any]) -> TurnPlan:

        prompt_template_str = load_prompt("turn_plan")

        prompt_template = PromptTemplate.from_template(template=prompt_template_str, template_format="jinja2")

        chain = (prompt_template 
            | llm 
            | JsonOutputParser())

        logger.debug(f"Prompt inputs: {prompt_inputs}")
        logger.info("Generating TurnPlan...")
        llm_response_dict: dict[str, Any] = await chain.ainvoke(prompt_inputs)

        logger.info(f"\n{"+" * 50}\n"
            f"{json.dumps(llm_response_dict, ensure_ascii=False, indent=2)}"
            f"\n{"+" * 50}")

        return TurnPlan.from_dict(llm_response_dict)