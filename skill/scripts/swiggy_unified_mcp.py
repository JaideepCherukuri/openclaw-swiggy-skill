"""
Unified Swiggy MCP Server for OpenClaw.
Proxies swiggy-food, swiggy-instamart, and swiggy-dineout behind a single stdio MCP server.
Shares one OAuth token to avoid triple-login.
"""
import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from datetime import timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

# We only import standard mcp types and Server/stdio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientMetadata, OAuthClientInformationFull, OAuthToken
from mcp import ClientSession

import mcp.types as types

logging.basicConfig(level=logging.ERROR) # Only output MCP protocol to stdout
logger = logging.getLogger("swiggy_unified_mcp")

TOKEN_FILE = Path.home() / ".swiggy_tokens_unified.json"

# Similar token storage and OAuth logic to Voice AI
class FileTokenStorage(TokenStorage):
    def __init__(self, path: Path = TOKEN_FILE):
        self._path = path
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except: pass
        return {}
    def _save(self):
        self._path.write_text(json.dumps(self._data, indent=2, default=str))

    async def get_tokens(self) -> OAuthToken | None:
        raw = self._data.get("tokens")
        return OAuthToken(**raw) if raw else None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self._data["tokens"] = tokens.model_dump()
        self._save()

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        raw = self._data.get("client_info")
        return OAuthClientInformationFull(**raw) if raw else None

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self._data["client_info"] = client_info.model_dump()
        self._save()

async def _redirect_handler(auth_url: str) -> None:
    # In a headless environment, we print this to stderr so the user can see it in mcporter logs
    sys.stderr.write(f"\n[SWIGGY AUTH REQUIRED] Open this link to login: {auth_url}\n")
    sys.stderr.flush()

_auth_result = {"code": None, "state": None, "event": threading.Event()}
class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]
        if code:
            _auth_result["code"] = code
            _auth_result["state"] = state
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Login Successful! Return to OpenClaw.")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Login Failed")
        _auth_result["event"].set()
    def log_message(self, format, *args): pass

async def _callback_handler() -> tuple[str, str | None]:
    _auth_result["code"] = None
    _auth_result["state"] = None
    _auth_result["event"].clear()
    server = HTTPServer(("localhost", 39025), _CallbackHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    
    sys.stderr.write(f"\n[SWIGGY AUTH] Waiting for callback on localhost:39025/callback ...\n")
    sys.stderr.flush()
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _auth_result["event"].wait)
    server.shutdown()
    
    return _auth_result["code"], _auth_result["state"]

def create_oauth_provider() -> OAuthClientProvider:
    return OAuthClientProvider(
        server_url="https://mcp.swiggy.com",
        client_metadata=OAuthClientMetadata(
            redirect_uris=["http://localhost:39025/callback"],
            token_endpoint_auth_method="none",
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            client_name="OpenClaw Swiggy Unified MCP",
            scope="mcp:tools mcp:resources mcp:prompts"
        ),
        storage=FileTokenStorage(),
        redirect_handler=_redirect_handler,
        callback_handler=_callback_handler,
        timeout=120.0,
    )

async def main():
    app = Server("swiggy-unified-mcp")
    auth = create_oauth_provider()
    
    endpoints = {
        "food": "https://mcp.swiggy.com/food?scope=home",
        "instamart": "https://mcp.swiggy.com/im?scope=home",
        "dineout": "https://mcp.swiggy.com/dineout?scope=home"
    }
    
    sessions = {}
    
    sys.stderr.write("Initializing Swiggy endpoints...\n")
    
    from contextlib import AsyncExitStack
    async with AsyncExitStack() as stack:
        for name, url in endpoints.items():
            streams = await stack.enter_async_context(
                streamablehttp_client(url=url, auth=auth, timeout=timedelta(seconds=30), sse_read_timeout=timedelta(seconds=300))
            )
            session = await stack.enter_async_context(ClientSession(streams[0], streams[1]))
            await session.initialize()
            sessions[name] = session
        
        sys.stderr.write("Successfully connected to Food, Instamart, and Dineout.\n")
        
        # Build unified tool list
        tool_map = {} # tool_name -> session_name
        
        @app.list_tools()
        async def list_tools() -> list[types.Tool]:
            all_tools = []
            for name, session in sessions.items():
                res = await session.list_tools()
                for t in res.tools:
                    # deduplicate by name
                    if t.name not in tool_map:
                        tool_map[t.name] = name
                        all_tools.append(t)
            return all_tools
            
        @app.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            if name not in tool_map:
                raise ValueError(f"Tool {name} not found in any Swiggy endpoint")
            
            session_name = tool_map[name]
            session = sessions[session_name]
            
            res = await session.call_tool(name, arguments)
            return res.content

        # Run stdio server
        sys.stderr.write("Starting unified stdio server...\n")
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
