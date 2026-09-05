def test_bearer_auth_headers_returns_authorization_mapping():
    from xavani_cli.mcp_config import _bearer_auth_headers

    headers = _bearer_auth_headers("my-server")

    assert headers == {"Authorization": "Bearer ${MCP_MY_SERVER_API_KEY}"}
