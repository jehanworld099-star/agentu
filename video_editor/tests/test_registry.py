import json

import pytest

from core import registry
from core.actions import noop  # noqa: F401 -- registers "noop"


def test_noop_registered():
    assert "noop" in registry.list_actions()


def test_get_unknown_action_raises():
    with pytest.raises(KeyError):
        registry.get_action("does-not-exist")


def test_registering_same_name_twice_raises():
    @registry.register_action("only-once", {})
    def _run(input_path, output_path, params):
        return output_path

    with pytest.raises(ValueError):

        @registry.register_action("only-once", {})
        def _run_again(input_path, output_path, params):
            return output_path


def test_schema_is_json_serializable():
    schema = registry.get_actions_schema()
    json.dumps(schema)
    assert "noop" in schema
