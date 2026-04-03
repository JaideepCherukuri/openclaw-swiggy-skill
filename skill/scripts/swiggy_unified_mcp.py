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
                        
                        # Strip misleading widget instructions from upstream
                        if "interactive widget" in t.description:
                            t.description = t.description.replace(
                                "This tool call rendered an interactive widget in the chat. The user can already see the result — do not repeat it in text or with another visualization.",
                                "IMPORTANT: After calling this tool, YOU MUST use the 'present_swiggy_options' tool to display the results to the user with images and buttons. Do NOT assume the user can see any widget natively."
                            )
                        
                        all_tools.append(t)
            
            # Add native presentation tool
            all_tools.append(types.Tool(
                name="present_swiggy_options",
                description="Present a formatted list of Swiggy options (Food/Instamart/Dineout) natively to the user with images and buttons. ALWAYS use this tool to show options instead of writing Markdown.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chat_id": {"type": "string", "description": "The user's chat_id from the incoming context"},
                        "options": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "type": {"type": "string", "enum": ["food", "instamart", "dineout"]},
                                    "rating": {"type": "string"},
                                    "distance": {"type": "string"},
                                    "deals": {"type": "array", "items": {"type": "string"}},
                                    "imageUrl": {"type": "string"},
                                    "price": {"type": "string", "description": "Price of the item, e.g. 250 or ₹250"},
                                    "isVeg": {"type": "boolean", "description": "True if item is vegetarian, false if non-veg"},
                                    "isBestseller": {"type": "boolean", "description": "True if item is a bestseller"},
                                    "totalRatings": {"type": "string", "description": "Number of ratings, e.g. '86' or '2.4K+'"},
                                    "description": {"type": "string", "description": "Brief description of the item"}
                                },
                                "required": ["id", "name", "type"]
                            }
                        }
                    },
                    "required": ["chat_id", "options"]
                }
            ))
            return all_tools
            
        @app.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            if name == "present_swiggy_options":
                import subprocess
                import tempfile
                import urllib.request
                import json
                
                chat_id = arguments.get("chat_id")
                options = arguments.get("options", [])
                
                for opt in options:
                    media_arg = None
                    img_url = opt.get("imageUrl")
                    if img_url:
                        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                            try:
                                req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                                with urllib.request.urlopen(req) as response, open(tf.name, 'wb') as out_file:
                                    out_file.write(response.read())
                                
                                comp_path = tf.name + "_comp.jpg"
                                subprocess.run(["ffmpeg", "-i", tf.name, "-vf", "scale=800:-1", "-q:v", "8", comp_path, "-y"], capture_output=True)
                                media_arg = comp_path
                            except Exception as e:
                                pass
                                
                    lines = []
                    
                    # Name and price
                    title_parts = []
                    if opt.get("isBestseller"):
                        title_parts.append("🔥 Bestseller")
                        
                    if opt.get("type") in ["food", "instamart"] and "isVeg" in opt:
                        if opt.get("isVeg") is True:
                            title_parts.append("Veg")
                        elif opt.get("isVeg") is False:
                            title_parts.append("Non-Veg")
                    
                    name_part = opt.get('name', 'Unknown')
                    if opt.get("price"):
                        price = opt['price']
                        if isinstance(price, (int, float)):
                            name_part += f" (₹{price})"
                        else:
                            name_part += f" (₹{price})"
                    
                    title_parts.append(f"**{name_part}**")
                    
                    lines.append(" • ".join(title_parts))
                    
                    if opt.get("description"):
                        lines.append(f"_{opt['description']}_")

                    # Stats line
                    stats = []
                    if opt.get("rating"): 
                        rating_text = f"⭐ {opt['rating']}"
                        if opt.get("totalRatings"):
                            rating_text += f" ({opt['totalRatings']})"
                        stats.append(rating_text)
                    if opt.get("distance"): stats.append(f"📍 {opt['distance']}")
                    if stats:
                        lines.append(" • ".join(stats))
                    
                    deals = opt.get("deals")
                    if deals and len(deals) > 0:
                        lines.append("🏷️ " + ", ".join(deals))
                        
                    text = "\n".join(lines)
                    
                    btn_type = opt.get("type", "food")
                    if btn_type == "dineout":
                        btn = {"text": "Book a Table 📅", "callback_data": f"/book {opt.get('id')}"}
                    else:
                        btn = {"text": "Add to Cart 🛒", "callback_data": f"/add {opt.get('id')}"}
                        
                    buttons_json = json.dumps([[btn]])
                    
                    cmd = ["openclaw", "message", "send", "--target", chat_id, "--message", text, "--buttons", buttons_json]
                    if media_arg:
                        cmd.extend(["--media", media_arg])
                        
                    subprocess.run(cmd)
                    
                return [types.TextContent(type="text", text=f"Successfully presented {len(options)} options via OpenClaw Gateway.")]

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
