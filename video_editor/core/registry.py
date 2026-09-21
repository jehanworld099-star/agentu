"""Registry for video-editing actions.

Every action lives in its own file under core/actions/ and has the
signature:

    def run(input_path: str, output_path: str, params: dict) -> str:
        ...

Register it with @register_action("name", params_schema) so the
Streamlit UI, and later the LLM planner, can discover what actions exist
and what parameters each one takes.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

ActionFunc = Callable[[str, str, Dict[str, Any]], str]

_ACTIONS: Dict[str, Dict[str, Any]] = {}


def register_action(name: str, params_schema: Optional[Dict[str, Any]] = None):
    """Decorator that registers an action under `name`.

    params_schema is a JSON-schema-like dict describing the `params`
    argument the action expects, e.g.:
        {"start": {"type": "string", "description": "clip start time"}}
    """

    def decorator(func: ActionFunc) -> ActionFunc:
        if name in _ACTIONS:
            raise ValueError(f"Action '{name}' is already registered")
        _ACTIONS[name] = {
            "func": func,
            "params_schema": params_schema or {},
        }
        return func

    return decorator


def get_action(name: str) -> ActionFunc:
    try:
        return _ACTIONS[name]["func"]
    except KeyError:
        raise KeyError(
            f"No action registered under '{name}'. Known actions: {sorted(_ACTIONS)}"
        ) from None


def list_actions() -> List[str]:
    return sorted(_ACTIONS)


def get_actions_schema() -> Dict[str, Any]:
    """Return a JSON-serializable schema of every registered action.

    Intended for the future LLM planner: it can read this to know what
    actions exist and what parameters each one takes.
    """
    return {
        name: {"params_schema": info["params_schema"]} for name, info in _ACTIONS.items()
    }
