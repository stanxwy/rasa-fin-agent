from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from agent.domain.messages import BotMessage
from agent.domain.state import DialogueState
from agent.infra.llm import llm
from agent.infra.observability.logging import log_llm_response, log_prompt_stage
from agent.prompts.history_builder import HistoryBuilder
from agent.prompts.loader import load_prompt
from agent.task.action.base import Action, ActionResult
from agent.utils.templating import render_template


class ActionResponse(Action):

    name = "action_response"

    def __init__(self, persona: str = ""):
        self._persona = persona

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        mode = action_kwargs.get("mode", "static")
        if mode == "static":
            response_template = action_kwargs['text']
            response_rendered = self._render_text_from_jinja(response_template, state)
            return ActionResult(messages=[BotMessage(text=response_rendered)])

        elif mode == "rephrase":
            response_template = action_kwargs['text']
            response_rendered = self._render_text_from_jinja(response_template, state)
            prompt_text = self._resolve_prompt(action_kwargs)
            message = await self._call_llm(prompt_text, state, response_rendered)
            return ActionResult(messages=[BotMessage(text=message)])

        elif mode == "generate":
            prompt_text = self._resolve_prompt(action_kwargs)
            message = await self._call_llm(prompt_text, state)
            return ActionResult(messages=[BotMessage(text=message)])

        else:
            raise ValueError(f"Invalid mode in action_response: {mode}")

    def _resolve_prompt(self, action_kwargs: dict[str, Any]) -> str:
        """rephrase/generate 的提示词：优先用 ``prompt_template`` 引用共享 jinja2，
        否则回退内联 ``prompt``（兼容旧写法）。"""
        template_name = action_kwargs.get("prompt_template")
        if template_name:
            return load_prompt(template_name)
        if "prompt" in action_kwargs:
            return action_kwargs["prompt"]
        raise ValueError("action_response rephrase/generate requires 'prompt_template' or 'prompt'")

    def _render_text_from_jinja(self, response_template: str, state: DialogueState) -> str:
        return render_template(response_template, state)

    async def _call_llm(self, prompt_text: str, state: DialogueState, response_rendered: str = "") -> str:
        prompt_template = PromptTemplate.from_template(template = prompt_text, template_format = "jinja2")
        chain = (prompt_template 
            | log_prompt_stage() 
            | llm 
            | log_llm_response()
            | StrOutputParser())

        bot_message = await chain.ainvoke({
            "history": HistoryBuilder.build(state.current_session().turns),
            "user_message": HistoryBuilder.render_user_message(state.pending_turn.user_message),
            "current_response": response_rendered,
            "persona": self._persona,
        })
        return bot_message

if __name__ == '__main__':
    import asyncio

    from agent.domain.contexts import TaskContext

    state = DialogueState(sender_id="u123", active_task=TaskContext(flow_id="f123", slots={"order_number": "12345"}))
    action = ActionResponse(persona="你是一个中文电商客服助手，语气自然、友好、简洁。")
    result = asyncio.run(action.run(state, {"mode": "static", "text": "好的，订单{{ slots.order_number }}的退款申请已提交"}))
    print(result)

"""
python -m agent.task.action.builtin.action_response
get_settings will be called only once...
messages=[BotMessage(text='好的，订单12345的退款申请已提交', object=None)] slot_updates={}
"""