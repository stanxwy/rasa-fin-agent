from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Template

if TYPE_CHECKING:
    from agent.domain.state import DialogueState


def render_template(text: str, state: "DialogueState") -> str:
    """Render a Jinja2 template string against the dialogue state.

    Shares the exact render context used by flow ``response.text`` so that all
    bot copy — whether from flow yml or clarify messages — goes through one
    rendering path. ``slots`` is empty when there is no active task.
    """
    return Template(text).render(
        slots=state.active_task.slots if state.active_task else {},
        context=state.current_active_task(),
    )
