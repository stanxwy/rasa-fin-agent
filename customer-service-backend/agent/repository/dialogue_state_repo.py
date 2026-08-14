import logging

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from agent.domain.state import DialogueState
from agent.models.dialogue_state import DialogueStateRecord
from agent.utils.json_utils import to_json

logger = logging.getLogger(__name__)

class DialogueStateRepository:

    def __init__(self, session: AsyncSession):
        self.session = session


    async def load_state(self, sender_id: str) -> DialogueState:
        select_stmt = select(DialogueStateRecord).where(DialogueStateRecord.sender_id == sender_id)

        result = await self.session.execute(select_stmt)

        state: DialogueStateRecord = result.scalar_one_or_none()

        if state:
            # state_dict = json.loads(state.state_json)
            return DialogueState.model_validate_json(state.state_json)

        return DialogueState(sender_id=sender_id)


    async def save_state(self, dialogue_state: DialogueState) -> int:

        state_json: str = dialogue_state.model_dump_json() # json.dumps(dialogue_state.model_dump(mode="json"))

        # NOTE: for MySQL-native upsert, use dialects.mysql.insert, NOT sqlalchemy.insert
        # this enables ON DUPLICATE KEY UPDATE semantics
        insert_stmt = insert(DialogueStateRecord).values(
            sender_id=dialogue_state.sender_id, 
            state_json=state_json
        )

        upsert_stmt = insert_stmt.on_duplicate_key_update(
            state_json=insert_stmt.inserted.state_json
        )

        result = await self.session.execute(upsert_stmt)

        await self.session.commit() # TODO? must commit? test!
        logger.info(f"Saved state for {dialogue_state.sender_id}: {result}")
        logger.info(to_json(dialogue_state, exclude={"sessions"}))
        return result.rowcount