"""Internal tool registry for Agent skills."""

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional


ToolHandler = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]


@dataclass
class ToolDefinition:
    name: str
    description: str
    inputSchema: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[ToolHandler] = None

    def public_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.inputSchema,
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def list_tools(self) -> List[Dict[str, Any]]:
        return [tool.public_dict() for tool in self._tools.values()]

    async def call(self, name: str, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            return {"status": "error", "message": f"未知工具: {name}"}
        if not tool.handler:
            return {"status": "error", "message": f"工具未绑定处理器: {name}"}
        return await tool.handler(arguments or {})


tool_registry = ToolRegistry()
