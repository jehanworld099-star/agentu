"""Demo action: copies the input file unchanged.

Used to prove the project/version/registry pipeline works end-to-end
before any real editing feature exists. Add new actions as new files in
this package, each with the same run(input_path, output_path, params)
signature, registered via @register_action.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict

from core.logger import get_logger
from core.registry import register_action

logger = get_logger(__name__)


@register_action("noop", params_schema={})
def run(input_path: str, output_path: str, params: Dict[str, Any]) -> str:
    input_path_p = Path(input_path)
    output_path_p = Path(output_path)
    output_path_p.parent.mkdir(parents=True, exist_ok=True)

    logger.info("noop: copying %s -> %s", input_path_p, output_path_p)
    shutil.copy2(input_path_p, output_path_p)
    return str(output_path_p)
