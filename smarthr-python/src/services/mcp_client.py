"""Optional MCP HTTP gateway client.

The application can work without an MCP server. When enabled, this client calls a
JSON-RPC compatible HTTP gateway and degrades to disabled responses on errors.
"""

from typing import Any, Dict

import httpx

from src.config import settings


class McpClient:
    def is_enabled(self) -> bool:
        return bool(settings.mcp_enabled and settings.mcp_gateway_url)

    async def list_tools(self) -> Dict[str, Any]:
        if not self.is_enabled():
            return {"enabled": False, "tools": []}
        return await self._rpc("tools/list", {})

    async def call_tool(self, name: str, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if not self.is_enabled():
            return {
                "enabled": False,
                "status": "skipped",
                "message": "MCP 未启用，已回退到内部 tools/skills。",
            }
        return await self._rpc("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })

    async def _rpc(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": "smarthr",
            "method": method,
            "params": params,
        }
        try:
            async with httpx.AsyncClient(timeout=settings.mcp_timeout_seconds) as client:
                response = await client.post(settings.mcp_gateway_url, json=payload)
                response.raise_for_status()
                data = response.json()
                if "error" in data:
                    return {"enabled": True, "status": "error", "error": data["error"]}
                return {"enabled": True, "status": "ok", "result": data.get("result")}
        except Exception as exc:
            return {
                "enabled": True,
                "status": "error",
                "error": str(exc),
                "fallback": "internal_tools",
            }


mcp_client = McpClient()
