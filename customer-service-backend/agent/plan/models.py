from enum import StrEnum

from pydantic import BaseModel

from agent.task.command.models import Command


class TaskTurnPlan(BaseModel):
    commands: list[Command] = []

    @classmethod
    def from_dict(cls, data: dict) -> "TaskTurnPlan":
        return cls(commands=[Command.from_dict(command) for command in data["commands"]])


class KnowledgeTurnPlan(BaseModel):
    intents: list[str] = []

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeTurnPlan":
        return cls(intents=data["intents"])


class ChitchatTurnPlan(BaseModel):
    ...


"""
{
  "task": {
    "commands": [
      {"command": "start_flow", "flow": "refund_request"}
    ]
  },
  "knowledge": {
    "intents": ["refund_policy"]
  },
  "chitchat": null
}
"""
class TurnPlan(BaseModel):
    task: TaskTurnPlan | None = None
    knowledge: KnowledgeTurnPlan | None = None
    chitchat: ChitchatTurnPlan | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "TurnPlan":
        return cls(
            task=TaskTurnPlan.from_dict(data["task"]) 
                if data.get("task") is not None else None,

            knowledge=KnowledgeTurnPlan.from_dict(data["knowledge"]) 
                if data.get("knowledge") is not None else None,
            
            chitchat=ChitchatTurnPlan() 
                if data.get("chitchat") is not None else None,
        )


class ClarifyReason(StrEnum):
    MISSING_TRACK = "missing_track"
    MULTIPLE_TRACKS = "multiple_tracks"

    MISSING_TASK_COMMANDS = "missing_task_commands"
    INVALID_TASK_COMMANDS = "invalid_task_commands"
    MULTIPLE_TASK_FLOWS = "multiple_task_flows"
    UNKNOWN_TASK_FLOW = "unknown_task_flow"

    MISSING_KNOWLEDGE_INTENT = "missing_knowledge_intent"
    MISSING_FOCUSED_OBJECT = "missing_focused_object"
    OBJECT_REQUIRES_INTENT = "object_requires_intent"

class TurnPlanValidationResult(BaseModel):
    valid: bool
    reason: ClarifyReason | None = None


if __name__ == '__main__':
    import json
    json_str1 = """
    {
      "task": {
        "commands": [
          {"command": "start_flow", "flow": "refund_request"}
        ]
      },
      "knowledge": null,
      "chitchat": null
    }
    """

    turn_plan1 = TurnPlan.from_dict(json.loads(json_str1))
    print(turn_plan1)

    json_str2 = """
    {
      "task": {
        "commands": [
          {"command": "set_slots", "slots": {"order_number": "A001"}}
        ]
      },
      "knowledge": null,
      "chitchat": null
    }
    """
    # 转成dict
    turn_plan2 = TurnPlan.from_dict(json.loads(json_str2))
    print(turn_plan2)


"""
python -m agent.plan.models                                                                                                      
task=TaskTurnPlan(commands=[StartFlowCommand(command='start_flow', flow='refund_request')]) knowledge=None chitchat=None                                                                                                
task=TaskTurnPlan(commands=[SetSlotsCommand(command='set_slots', slots={'order_number': 'A001'})]) knowledge=None chitchat=None
"""