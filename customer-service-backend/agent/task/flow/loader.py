from pathlib import Path
from typing import Any

import yaml

from agent.task.action.registry import ActionRegistry
from agent.task.flow.flows import Flow, FlowsList, FlowSlot
from agent.task.flow.steps import ActionFlowStep, CollectFlowStep, FlowStep

"""
yaml -> dict -> data model
"""

class FlowLoader:

    # 配置文件目录（yml 发现逻辑的单一真相，避免散落到组合根）。
    # loader.py 位于 agent/task/flow/，仓库根在其上 3 层。
    CONFIG_DIR = Path(__file__).resolve().parents[3] / "domain_config"

    def load_from_config_dir(self) -> FlowsList:
        """
        从默认配置目录加载全部流程定义。

        文件发现（哪些 yml、过滤 .yml/.yaml）封装在此处，
        调用方无需关心文件系统细节——与 prompts/loader.py 的 load_prompt 同构。
        load_many(paths) 仍保留，便于单测注入临时目录。
        """
        paths = [
            p for p in self.CONFIG_DIR.iterdir()
            if p.is_file() and p.suffix in (".yml", ".yaml")
        ]
        if not paths:
            raise FileNotFoundError(f"No flow YAML found in {self.CONFIG_DIR}")
        return self.load_many(paths)

    def load_many(self, paths: list[Path]) -> FlowsList:
        """
        load flows and slots from multiple yaml files
        and merge them into a single list/dict managed by FlowsList model
        duplicate slot name is not allowed
        """
        total_flows: list[Flow] = []
        total_slots: dict[str, FlowSlot] = {}
        for path in paths:
            flow_list_model = self.load(path)

            # merge flows loaded from a yml file into a single flows list managed by FlowsList
            total_flows.extend(flow_list_model.flows)

            # merge slots loaded from a yml file into a single slots dict managed by FlowsList
            # raise exception if duplicate slot name (from different yml files) is found
            duplicate_slot_names = set(total_slots) & set(flow_list_model.slots)
            if duplicate_slot_names:
                duplicates = ", ".join(sorted(duplicate_slot_names))
                raise ValueError(
                    f"Duplicate slot name found: {duplicates} in {path}"
                )
            total_slots.update(flow_list_model.slots)
        return FlowsList(flows=total_flows, slots=total_slots)


    def load(self, path: Path) -> FlowsList:
        """
        load flows and slots as dict from a yaml file
        then convert to data model
        """
        with open(path, 'r', encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f)

        json_slots = data.get('slots', {})
        model_slots: dict[str, FlowSlot] = self._load_slots(json_slots)

        json_flows = data.get('flows', {})
        model_flows: list[Flow] = self._load_flows(json_flows, model_slots)

        return FlowsList(slots=model_slots, flows=model_flows)


    def _load_slots(self, yaml_slots_data: dict[str, Any]) -> dict[str, FlowSlot]:
        model_slots = {}
        for slot_name, slot_dict in yaml_slots_data.items():
            model_slots[slot_name] = FlowSlot(
                # NOTE that slot_name is the key of the loaded slot_dict
                # which is not in the unpacked slot_dict argument list
                # *pass separately*
                name=slot_name,
                **slot_dict
            )
        return model_slots


    def _load_flows(self, 
        yaml_flows_data: dict[str, Any], 
        slots_definition: dict[str, FlowSlot]
    ) -> list[Flow]:

        model_flows: list[Flow] = []
        for flow_id, flow_dict in yaml_flows_data.items():
            model_steps = [FlowStep.from_dict(step) for step in flow_dict.get('steps', [])]
            uniq_slots = self._collect_flow_slots(slots_definition, model_steps)
            model_flows.append(
                Flow(
                    id=flow_id,
                    description=flow_dict.get('description', ''),
                    name=flow_dict.get('name'),
                    steps=model_steps,
                    slots=uniq_slots
                )
            )
        return model_flows


    def _collect_flow_slots(self, 
        slots_definition: dict[str, FlowSlot],
        steps: list[FlowStep]
    ) -> list[FlowSlot]:
        """
        collect all slots used in the steps passed in
        :param slots_definition: complete slots definition loaded form yaml till now
        :param steps: steps used in current flow
        :return: unique and valid slots used in current flow
        """
        uniq_slots = {step.slot_name for step in steps if isinstance(step, CollectFlowStep)}
        valid_uniq_slots = [slots_definition[slot_name] 
            for slot_name in uniq_slots if slot_name in slots_definition]
        return valid_uniq_slots


def validate_flow_actions(flows_list: FlowsList, registry: ActionRegistry) -> None:
    """
    加载边界的完整性校验：所有 ActionFlowStep 引用的 action 必须已在 ActionRegistry 注册。

    合法 action 集合的单一真源是 registry（即各 Action 子类的 name），
    YAML 只是引用这些名字。因此校验放在加载边界，而非领域模型内部：
    - FlowsList / ActionFlowStep 保持纯领域模型（action: str，无任何 registry 依赖），单测自由；
    - 新增 action = 加一个 Action 子类 + 在 yml 引用，无需改动领域层；
    - yml 写了未注册的名字 -> 启动加载即清晰报错，而非运行期 KeyError。
    """
    unknown = sorted({
        step.action
        for flow in flows_list.flows
        for step in flow.steps
        if isinstance(step, ActionFlowStep) and not registry.is_registered(step.action)
    })
    if unknown:
        raise ValueError(
            f"Flow(s) reference unknown action(s): {', '.join(unknown)}. "
            f"Available actions: {', '.join(sorted(registry._actions))}"
        )


if __name__ == '__main__':
    base_path = Path(__file__).resolve().parents[3]
    user_flow_path = base_path / 'domain_config' / 'user_flows.yml'
    system_flow_path = base_path / 'domain_config' / 'system_flows.yml'
    loader = FlowLoader()
    flows_list = loader.load_many([user_flow_path, system_flow_path])
    print(flows_list.model_dump_json(indent=2))


"""
python -m agent.task.flow.loader
{
  "flows": [
    {
      "id": "onboarding",
      "description": "在聊天窗口初次打开时欢迎用户，并介绍助手可处理的电商服务。这个 flow 通常由系统主动触发。",
      "steps": [
        {
          "id": "start",
          "type": "start",
          "next": [
            {
              "target": "respond"
            }
          ],
          "description": ""
        },
        {
          "id": "respond",
          "type": "action",
          "next": [
            {
              "target": "end"
            }
          ],
          "description": ""
        },
        {
          "id": "end",
          "type": "end",
          "next": [],
          "description": ""
        }
      ],
      "slots": [],
      "name": "欢迎引导"
    },
    {
      "id": "order_status_query",
      "description": "帮用户查询订单当前的处理状态，例如待付款、待发货、已发货或已完成。",
      "steps": [
        {
          "id": "start",
          "type": "start",
          "next": [
            {
              "target": "ask_order_number"
            }
          ],
          "description": ""
        },
        {
          "id": "ask_order_number",
          "type": "collect",
          "next": [
            {
              "target": "lookup_order_status"
            }
          ],
          "description": ""
        },
        {
          "id": "lookup_order_status",
          "type": "action",
          "next": [
            {
              "target": "show_order_status"
            }
          ],
          "description": ""
        },
        {
          "id": "show_order_status",
          "type": "action",
          "next": [
            {
              "target": "end"
            }
          ],
          "description": ""
        },
        {
          "id": "end",
          "type": "end",
          "next": [],
          "description": ""
        }
      ],
      "slots": [
        {
          "name": "order_number",
          "type": "text",
          "label": "订单号",
          "description": "用户的订单号"
        }
      ],
      "name": "订单状态查询"
    },
    {
      "id": "logistics_tracking",
      "description": "帮用户查询订单物流进度、物流单号和配送公司信息。",
      "steps": [
        {
          "id": "start",
          "type": "start",
          "next": [
            {
              "target": "ask_order_number"
            }
          ],
          "description": ""
        },
        {
          "id": "ask_order_number",
          "type": "collect",
          "next": [
            {
              "target": "lookup_logistics"
            }
          ],
          "description": ""
        },
        {
          "id": "lookup_logistics",
          "type": "action",
          "next": [
            {
              "target": "show_logistics"
            }
          ],
          "description": ""
        },
        {
          "id": "show_logistics",
          "type": "action",
          "next": [
            {
              "target": "end"
            }
          ],
          "description": ""
        },
        {
          "id": "end",
          "type": "end",
          "next": [],
          "description": ""
        }
      ],
      "slots": [
        {
          "name": "order_number",
          "type": "text",
          "label": "订单号",
          "description": "用户的订单号"
        }
      ],
      "name": "物流查询"
    },
    {
      "id": "refund_request",
      "description": "帮用户提交简单的退款申请，收集订单号和退款原因。",
      "steps": [
        {
          "id": "start",
          "type": "start",
          "next": [
            {
              "target": "ask_order_number"
            }
          ],
          "description": ""
        },
        {
          "id": "ask_order_number",
          "type": "collect",
          "next": [
            {
              "target": "ask_refund_reason"
            }
          ],
          "description": ""
        },
        {
          "id": "ask_refund_reason",
          "type": "collect",
          "next": [
            {
              "target": "refund_submitted"
            }
          ],
          "description": ""
        },
        {
          "id": "refund_submitted",
          "type": "action",
          "next": [
            {
              "target": "end"
            }
          ],
          "description": ""
        },
        {
          "id": "end",
          "type": "end",
          "next": [],
          "description": ""
        }
      ],
      "slots": [
        {
          "name": "order_number",
          "type": "text",
          "label": "订单号",
          "description": "用户的订单号"
        },
        {
          "name": "refund_reason",
          "type": "text",
          "label": "退款原因",
          "description": "申请退款的原因"
        }
      ],
      "name": "退款申请"
    },
    {
      "id": "system_task_started",
      "description": "Flow for acknowledging that a new task has started",
      "steps": [
        {
          "id": "start",
          "type": "start",
          "next": [
            {
              "target": "acknowledge"
            }
          ],
          "description": ""
        },
        {
          "id": "acknowledge",
          "type": "action",
          "next": [
            {
              "target": "end"
            }
          ],
          "description": ""
        },
        {
          "id": "end",
          "type": "end",
          "next": [],
          "description": ""
        }
      ],
      "slots": [],
      "name": "task started acknowledgement"
    },
    {
      "id": "system_task_resumed",
      "description": "Flow for acknowledging that a paused task has been resumed",
      "steps": [
        {
          "id": "start",
          "type": "start",
          "next": [
            {
              "target": "acknowledge"
            }
          ],
          "description": ""
        },
        {
          "id": "acknowledge",
          "type": "action",
          "next": [
            {
              "target": "end"
            }
          ],
          "description": ""
        },
        {
          "id": "end",
          "type": "end",
          "next": [],
          "description": ""
        }
      ],
      "slots": [],
      "name": "task resumed acknowledgement"
    },
    {
      "id": "system_collect_information",
      "description": "Flow for asking the user for a slot value during a collect step",
      "steps": [
        {
          "id": "start",
          "type": "start",
          "next": [
            {
              "target": "ask"
            }
          ],
          "description": ""
        },
        {
          "id": "ask",
          "type": "action",
          "next": [
            {
              "target": "listen"
            }
          ],
          "description": ""
        },
        {
          "id": "listen",
          "type": "action",
          "next": [
            {
              "target": "end"
            }
          ],
          "description": ""
        },
        {
          "id": "end",
          "type": "end",
          "next": [],
          "description": ""
        }
      ],
      "slots": [],
      "name": "collect information"
    },
    {
      "id": "system_task_interrupted",
      "description": "Flow for acknowledging that the current task has been interrupted",
      "steps": [
        {
          "id": "start",
          "type": "start",
          "next": [
            {
              "target": "acknowledge"
            }
          ],
          "description": ""
        },
        {
          "id": "acknowledge",
          "type": "action",
          "next": [
            {
              "target": "end"
            }
          ],
          "description": ""
        },
        {
          "id": "end",
          "type": "end",
          "next": [],
          "description": ""
        }
      ],
      "slots": [],
      "name": "task interrupted acknowledgement"
    },
    {
      "id": "system_task_canceled",
      "description": "Flow for acknowledging that the current task was canceled",
      "steps": [
        {
          "id": "start",
          "type": "start",
          "next": [
            {
              "target": "acknowledge"
            }
          ],
          "description": ""
        },
        {
          "id": "acknowledge",
          "type": "action",
          "next": [
            {
              "target": "end"
            }
          ],
          "description": ""
        },
        {
          "id": "end",
          "type": "end",
          "next": [],
          "description": ""
        }
      ],
      "slots": [],
      "name": "task canceled acknowledgement"
    },
    {
      "id": "system_cannot_handle",
      "description": "Flow for handling requests the assistant cannot support",
      "steps": [
        {
          "id": "start",
          "type": "start",
          "next": [
            {
              "target": "clarification_rejected"
            },
            {
              "target": "not_supported"
            },
            {
              "target": "no_relevant_answer"
            },
            {
              "target": "ask_rephrase"
            }
          ],
          "description": ""
        },
        {
          "id": "clarification_rejected",
          "type": "action",
          "next": [
            {
              "target": "end"
            }
          ],
          "description": ""
        },
        {
          "id": "not_supported",
          "type": "action",
          "next": [
            {
              "target": "end"
            }
          ],
          "description": ""
        },
        {
          "id": "no_relevant_answer",
          "type": "action",
          "next": [
            {
              "target": "end"
            }
          ],
          "description": ""
        },
        {
          "id": "ask_rephrase",
          "type": "action",
          "next": [
            {
              "target": "end"
            }
          ],
          "description": ""
        },
        {
          "id": "end",
          "type": "end",
          "next": [],
          "description": ""
        }
      ],
      "slots": [],
      "name": "cannot handle request"
    }
  ],
  "slots": {
    "order_number": {
      "name": "order_number",
      "type": "text",
      "label": "订单号",
      "description": "用户的订单号"
    },
    "order_status": {
      "name": "order_status",
      "type": "text",
      "label": "订单状态",
      "description": "订单当前状态"
    },
    "order_summary": {
      "name": "order_summary",
      "type": "text",
      "label": "订单摘要",
      "description": "订单摘要信息"
    },
    "tracking_number": {
      "name": "tracking_number",
      "type": "text",
      "label": "物流单号",
      "description": "物流单号"
    },
    "logistics_company": {
      "name": "logistics_company",
      "type": "text",
      "label": "物流公司",
      "description": "物流公司名称"
    },
    "logistics_status": {
      "name": "logistics_status",
      "type": "text",
      "label": "物流进度",
      "description": "物流当前进度"
    },
    "product_id": {
      "name": "product_id",
      "type": "text",
      "label": "商品ID",
      "description": "当前咨询商品的唯一标识"
    },
    "refund_reason": {
      "name": "refund_reason",
      "type": "text",
      "label": "退款原因",
      "description": "申请退款的原因"
    }
  }
}
"""