"""
Curator — MCP Server
Exposes the Weight engine as tools Claude Code can call.

Tools:
  observe(text)  — process input, update conception space
  surface()      — return currently relevant conceptions as context
  inspect()      — dump full conception space for debugging

Setup in Claude Code (~/.claude/settings.json):
  {
    "mcpServers": {
      "curator": {
        "command": "python3",
        "args": ["/path/to/hcic/curator/mcp_server.py"],
        "env": {
          "ANTHROPIC_API_KEY": "your_key_here"
        }
      }
    }
  }
"""

import os
import sys
import json
import asyncio

sys.path.insert(0, os.path.dirname(__file__))
from schema import connect, surface as surface_fn, SignalQuality, _compute_current_recency
from observe import observe as observe_fn

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ─── DB ──────────────────────────────────────────────────────────────────────

# Store DB next to this file so it persists between Claude Code sessions
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "curator_mcp.db")
conn = connect(DB_PATH)

# ─── Server ──────────────────────────────────────────────────────────────────

server = Server("curator")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="observe",
            description="""Process input and update the Curator's conception space.
Call this when the user expresses a preference, corrects you, shares context about 
their project, workflow, or working style. The Curator extracts atomic conceptions, 
weights them by confidence and recency, and handles contradictions by creating 
competing conceptions rather than overwriting. Call observe() before surface() 
at the start of a session with any known context.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The input to observe and process into conceptions"
                    },
                    "source": {
                        "type": "string",
                        "description": "Where this input came from (e.g. 'user', 'correction', 'file')",
                        "default": "claude_code"
                    }
                },
                "required": ["text"]
            }
        ),
        types.Tool(
            name="surface",
            description="""Return currently relevant conceptions from the Curator's conception space.
Call this at the start of each session and before responding to complex requests.
Returns conceptions ordered by recency first (governs the present), then confidence 
(governs the persistent). Use the returned context naturally — do not announce the 
memory system to the user.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "signal_quality": {
                        "type": "number",
                        "description": "Clarity of current context, 0.0 to 1.0. Use 0.9 for session start, lower for ambiguous requests.",
                        "default": 0.9
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max conceptions to surface",
                        "default": 8
                    }
                }
            }
        ),
        types.Tool(
            name="inspect",
            description="""Show the full conception space for debugging.
Returns all conceptions with their recency and confidence values.
Use when you want to understand what the Curator currently knows.""",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:

    if name == "observe":
        text = arguments.get("text", "").strip()
        source = arguments.get("source", "claude_code")

        if not text:
            return [types.TextContent(type="text", text="Error: text is required")]

        result = observe_fn(conn, text, source=source)
        sq = result["signal_quality"]

        summary_parts = [
            f"signal_quality: {sq['score']:.2f} ({sq['reason']})",
            f"extracted: {len(result['conceptions_extracted'])} conception(s)"
        ]

        for action in result["actions"]:
            a = action["action"]
            if a == "created":
                summary_parts.append(f"created conception #{action['id']}")
            elif a == "confirmed":
                summary_parts.append(f"confirmed #{action['id']} (confidence +{action['delta']:.2f})")
            elif a == "competing_conception_created":
                explicit = " [explicit correction]" if action.get("explicit_instruction") else ""
                summary_parts.append(
                    f"contradiction: weakened #{action['existing_id']}, "
                    f"created competing #{action['new_id']}{explicit}"
                )

        return [types.TextContent(type="text", text="\n".join(summary_parts))]

    elif name == "surface":
        signal_quality = arguments.get("signal_quality", 0.9)
        limit = arguments.get("limit", 8)

        sq = SignalQuality(score=signal_quality, reason="requested")
        conceptions = surface_fn(conn, sq, limit=limit)

        if not conceptions:
            return [types.TextContent(type="text", text="No conceptions above threshold yet.")]

        lines = ["Active context from conception space:\n"]
        for i, c in enumerate(conceptions, 1):
            lines.append(
                f"{i}. {c.content}\n"
                f"   recency: {c.recency:.2f} | confidence: {c.confidence:.2f}"
            )

        total = conn.execute("SELECT COUNT(*) FROM conceptions").fetchone()[0]
        lines.append(f"\n({len(conceptions)} surfaced of {total} total conceptions)")

        return [types.TextContent(type="text", text="\n".join(lines))]

    elif name == "inspect":
        rows = conn.execute(
            "SELECT id, content, recency, confidence, last_updated FROM conceptions ORDER BY recency DESC"
        ).fetchall()

        if not rows:
            return [types.TextContent(type="text", text="Conception space is empty.")]

        lines = [f"Conception space ({len(rows)} total):\n"]
        for row in rows:
            live_recency = _compute_current_recency(row[1], row[2], row[4])
            status = "active" if live_recency >= 0.15 else "faded"
            lines.append(
                f"#{row[0]} [{status}] rec={live_recency:.3f} conf={row[2]:.3f}\n"
                f"  {row[3][:80]}"
            )

        return [types.TextContent(type="text", text="\n".join(lines))]

    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


# ─── Entry point ─────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
