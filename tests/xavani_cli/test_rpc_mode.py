# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

import io
import json

from xavani_cli.rpc_mode import RpcSession, serve


def make_session(chat_reply: str = "hello back") -> RpcSession:
    return RpcSession(
        chat_fn=lambda message: chat_reply,
        tools_fn=lambda: [{"name": "terminal"}],
    )


class TestHandleFrame:
    def test_ping_roundtrip(self):
        response = make_session().handle_frame({"id": 1, "method": "ping"})
        assert response["id"] == 1
        assert response["result"]["pong"] is True
        assert isinstance(response["result"]["version"], str)

    def test_chat_happy_path(self):
        response = make_session("the answer").handle_frame(
            {"id": "a", "method": "chat", "params": {"message": "q"}}
        )
        assert response == {"id": "a", "result": {"reply": "the answer"}}

    def test_chat_validation_error(self):
        for params in ({}, {"message": ""}, {"message": "   "}):
            response = make_session().handle_frame(
                {"id": 2, "method": "chat", "params": params}
            )
            assert "error" in response and response["id"] == 2

    def test_tools_list_passthrough(self):
        response = make_session().handle_frame({"id": 3, "method": "tools/list"})
        assert response["result"]["tools"] == [{"name": "terminal"}]

    def test_missing_id_or_method_rejected(self):
        session = make_session()
        for frame in ({"method": "ping"}, {"id": 4}, {}):
            response = session.handle_frame(frame)
            assert "frame must have id and method" in response["error"]

    def test_unknown_method(self):
        response = make_session().handle_frame({"id": 5, "method": "nope"})
        assert response["error"] == "unknown method: nope"


class TestToolCards:
    def test_tool_request_creates_awaiting_card(self):
        session = make_session()
        response = session.handle_frame({
            "id": 6, "method": "tool_request",
            "params": {"tool": "terminal", "args": {"cmd": "ls"}},
        })
        card = response["result"]
        assert card["status"] == "awaiting_response"
        assert card["tool"] == "terminal"
        assert len(card["card_id"]) == 12

    def test_approve_and_deny_transitions(self):
        session = make_session()
        card_id = session.handle_frame({
            "id": 7, "method": "tool_request",
            "params": {"tool": "write_file"},
        })["result"]["card_id"]
        approved = session.handle_frame({
            "id": 8, "method": "tool_response",
            "params": {"card_id": card_id, "decision": "approve"},
        })
        assert approved["result"]["status"] == "approved"
        assert session.resolved_cards()[card_id]["status"] == "approved"

        other_id = session.handle_frame({
            "id": 9, "method": "tool_request",
            "params": {"tool": "patch"},
        })["result"]["card_id"]
        denied = session.handle_frame({
            "id": 10, "method": "tool_response",
            "params": {"card_id": other_id, "decision": "deny"},
        })
        assert denied["result"]["status"] == "denied"

    def test_unknown_card_id_errors(self):
        response = make_session().handle_frame({
            "id": 11, "method": "tool_response",
            "params": {"card_id": "ghost", "decision": "approve"},
        })
        assert response["error"] == "unknown card_id"

    def test_bad_decision_errors(self):
        session = make_session()
        card_id = session.handle_frame({
            "id": 12, "method": "tool_request", "params": {"tool": "t"},
        })["result"]["card_id"]
        response = session.handle_frame({
            "id": 13, "method": "tool_response",
            "params": {"card_id": card_id, "decision": "maybe"},
        })
        assert "approve' or 'deny'" in response["error"]


class TestHandleLine:
    def test_invalid_json_yields_error_with_null_id(self):
        out = make_session().handle_line("{not json")
        payload = json.loads(out)
        assert payload["id"] is None
        assert "invalid json" in payload["error"]

    def test_non_object_json_rejected(self):
        payload = json.loads(make_session().handle_line("[1,2]"))
        assert "JSON object" in payload["error"]

    def test_blank_line_returns_empty_string(self):
        assert make_session().handle_line("") == ""
        assert make_session().handle_line("   ") == ""

    def test_response_is_one_newline_terminated_compact_line(self):
        out = make_session().handle_line('{"id": 1, "method": "ping"}')
        assert out.endswith("\n")
        assert out.count("\n") == 1


class TestServe:
    def test_end_to_end_three_frames(self):
        input_stream = io.StringIO(
            '{"id": 1, "method": "ping"}\n'
            '{"id": 2, "method": "chat", "params": {"message": "hi"}}\n'
            '{"id": 3, "method": "chat"}\n'
        )
        output_stream = io.StringIO()
        serve(input_stream, output_stream, make_session())
        lines = output_stream.getvalue().splitlines()
        assert len(lines) == 3
        first, second, third = (json.loads(line) for line in lines)
        assert first["result"]["pong"] is True
        assert second["result"]["reply"] == "hello back"
        assert "error" in third
