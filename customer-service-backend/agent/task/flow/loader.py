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
