import sys
import asyncio
from datetime import timedelta
from contextlib import AsyncExitStack
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
from swiggy_unified_mcp import create_oauth_provider, TOKEN_FILE

async def _test_login():
    sys.stderr.write("Starting standalone login flow...\n")
    auth = create_oauth_provider()
    
    sys.stderr.write("Connecting to https://mcp.swiggy.com/food?scope=home...\n")
    async with AsyncExitStack() as stack:
        streams = await stack.enter_async_context(
            streamablehttp_client(
                url="https://mcp.swiggy.com/food?scope=home", 
                auth=auth, 
                timeout=timedelta(seconds=30), 
                sse_read_timeout=timedelta(seconds=300)
            )
        )
        session = await stack.enter_async_context(ClientSession(streams[0], streams[1]))
        await session.initialize()
        
        res = await session.list_tools()
        sys.stderr.write(f"Login successful! Found {len(res.tools)} tools on food endpoint.\n")
        sys.stderr.write(f"Tokens saved to: {TOKEN_FILE}\n")

if __name__ == "__main__":
    asyncio.run(_test_login())
