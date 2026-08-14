# agent/chitchat/responder.py

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from agent.domain.messages import BotMessage, UserMessage
from agent.domain.state import Turn
from agent.infra.llm import llm
from agent.infra.observability.logging import log_llm_response, log_prompt_stage
from agent.prompts.history_builder import HistoryBuilder
from agent.prompts.loader import load_prompt


class ChitchatResponder:

    def __init__(self, persona: str = ""):
        self._persona = persona

    async def respond(self,
        user_message: UserMessage,
        recent_turns: list[Turn]
    ) -> list[BotMessage]:

        prompt_template_str = load_prompt("chitchat_respond")
        prompt_template = PromptTemplate.from_template(prompt_template_str, template_format="jinja2")
        chain = (prompt_template
            | log_prompt_stage()
            | llm
            | log_llm_response()
            | StrOutputParser())

        response = await chain.ainvoke({
            "user_message": HistoryBuilder.render_user_message(user_message),
            "history": HistoryBuilder.build(recent_turns),
            "persona": self._persona,
        })
        return [BotMessage(text=response)]