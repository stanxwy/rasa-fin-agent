import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from agent.domain.messages import BotMessage, ObjectType
from agent.domain.state import DialogueState
from agent.infra.llm import llm
from agent.infra.observability.logging import log_llm_response, log_prompt_stage
from agent.plan.models import ClarifyReason
from agent.prompts.history_builder import HistoryBuilder
from agent.prompts.loader import load_prompt
from agent.utils.templating import render_template

logger = logging.getLogger(__name__)

class ClarifyResponder:

    # 直映 reason：文案 key 名 == reason.value；字面量只在 ClarifyReason 枚举里写一次。
    DIRECT_REASONS = frozenset({
        ClarifyReason.MISSING_TRACK,
        ClarifyReason.MULTIPLE_TRACKS,
        ClarifyReason.MISSING_TASK_COMMANDS,
        ClarifyReason.MISSING_KNOWLEDGE_INTENT,
        ClarifyReason.MISSING_FOCUSED_OBJECT,
    })
    # 以下 key 不是枚举成员，是「按对象类型派生 / 兜底」的呈现层 key，
    # 字面量留在此处是唯一合理落点（无法从 ClarifyReason 派生）。
    OBJECT_ORDER_KEY = "object_requires_order"
    OBJECT_PRODUCT_KEY = "object_requires_product"
    OBJECT_BANK_ACCOUNT_KEY = "object_requires_bank_account"
    OBJECT_BANK_CARD_KEY = "object_requires_bank_card"
    OBJECT_CREDIT_CARD_KEY = "object_requires_credit_card"
    OBJECT_DEPOSIT_KEY = "object_requires_deposit"
    OBJECT_LOAN_KEY = "object_requires_loan"
    OBJECT_WEALTH_PRODUCT_KEY = "object_requires_wealth_product"
    OBJECT_FUND_PRODUCT_KEY = "object_requires_fund_product"
    OBJECT_TRANSACTION_KEY = "object_requires_transaction"
    OBJECT_TRANSFER_KEY = "object_requires_transfer"
    FALLBACK_KEY = "fallback"

    _OBJECT_KEY_MAP = {
        ObjectType.ORDER: OBJECT_ORDER_KEY,
        ObjectType.PRODUCT: OBJECT_PRODUCT_KEY,
        ObjectType.BANK_ACCOUNT: OBJECT_BANK_ACCOUNT_KEY,
        ObjectType.BANK_CARD: OBJECT_BANK_CARD_KEY,
        ObjectType.CREDIT_CARD: OBJECT_CREDIT_CARD_KEY,
        ObjectType.DEPOSIT: OBJECT_DEPOSIT_KEY,
        ObjectType.LOAN: OBJECT_LOAN_KEY,
        ObjectType.WEALTH_PRODUCT: OBJECT_WEALTH_PRODUCT_KEY,
        ObjectType.FUND_PRODUCT: OBJECT_FUND_PRODUCT_KEY,
        ObjectType.TRANSACTION: OBJECT_TRANSACTION_KEY,
        ObjectType.TRANSFER: OBJECT_TRANSFER_KEY,
    }

    @classmethod
    def required_message_keys(cls) -> frozenset[str]:
        """yml 必须提供的文案 key 集合（加载期校验用）。

        单一真源：直映 reason 的 key 由枚举派生，仅派生/兜底 key 为字面量；
        ``ClarifyMessageLoader`` 直接复用本方法，避免在 loader 里重复声明字符串。
        """
        return frozenset({r.value for r in cls.DIRECT_REASONS}) | frozenset(
            cls._OBJECT_KEY_MAP.values()
        ) | frozenset({cls.FALLBACK_KEY})

    def __init__(self, messages: dict[str, str], persona: str = ""):
        self._messages = messages
        self._persona = persona

    async def respond(self, state: DialogueState, reason: ClarifyReason) -> list[BotMessage]:

        clarify_message = self.build_clarify_message(reason=reason, state=state)
        user_message = state.pending_turn.user_message
        user_message_str = HistoryBuilder.render_user_message(user_message)
        history_str = HistoryBuilder.build(state.current_session().turns[-10:])
        focused_object_str = state.focused_object.model_dump_json() if state.focused_object is not None else None

        prompt_template_str = load_prompt("clarify_respond")
        prompt_template = PromptTemplate.from_template(template=prompt_template_str, template_format="jinja2")
        chain = (prompt_template
            | log_prompt_stage()
            | llm
            | log_llm_response()
            | StrOutputParser())

        rewritten = await chain.ainvoke({
            "user_message": user_message_str,
            "history": history_str,
            "focused_object": focused_object_str,
            "clarify_message": clarify_message,
            "reason": reason.value,
            "persona": self._persona,
        })
        return [BotMessage(text=rewritten)]


    def build_clarify_message(
            self,
            reason: ClarifyReason,
            state: DialogueState,
    ) -> str:
        key = self._resolve_key(reason, state.focused_object)
        template = self._messages.get(key, self._messages["fallback"])
        return render_template(template, state)

    def _resolve_key(self, reason: ClarifyReason, focused_object) -> str:
        if reason is ClarifyReason.OBJECT_REQUIRES_INTENT:
            if focused_object is not None:
                key = self._OBJECT_KEY_MAP.get(focused_object.type)
                if key is not None:
                    return key
            return self.FALLBACK_KEY
        if reason in self.DIRECT_REASONS:
            return reason.value
        return self.FALLBACK_KEY
