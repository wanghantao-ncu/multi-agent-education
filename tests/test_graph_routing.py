"""Unit tests for graph routing branches."""

from core.graph.routing.router import route_next_node


def test_route_teach_branch():
    state = {"next_action": "teach"}
    assert route_next_node(state) == "teach"


def test_route_hint_branch():
    state = {"next_action": "hint"}
    assert route_next_node(state) == "hint_node"


def test_route_end_branch():
    state = {"next_action": "end"}
    assert route_next_node(state) == "end"

