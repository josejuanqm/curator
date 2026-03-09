# Curator — Claude Code Integration

Replaces Claude Code's static CLAUDE.md memory with a live weight-based conception space.

## How it works

Claude Code calls three tools automatically:
- **`surface()`** — at session start, returns currently weighted conceptions as context
- **`observe(text)`** — when you share context, make corrections, or express preferences
- **`inspect()`** — anytime you want to see the full conception space

Unlike CLAUDE.md, the Curator:
- Weights conceptions by recency and confidence
- Creates competing conceptions on contradiction — doesn't overwrite
- Decays stale context proportional to confidence
- Grows more accurate through confirming signal

## Setup

**1. Add to Claude Code settings**

Edit `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "curator": {
      "command": "/path/to/hcic/.venv/bin/python3",
      "args": ["/path/to/hcic/curator/mcp_server.py"],
      "env": {
        "ANTHROPIC_API_KEY": "your_key_here"
      }
    }
  }
}
```

Replace `/path/to/hcic` with your actual path. Use the venv Python to get sqlite-vec.

**2. Add to your CLAUDE.md** (optional but recommended)

```markdown
## Memory

You have access to the Curator memory system via MCP tools.

At the start of each session:
1. Call `surface()` to load your active context
2. Use the returned conceptions naturally — don't announce the memory system

When the user:
- Corrects you → call `observe(text)` with the correction
- Expresses a preference → call `observe(text)`  
- Shares project context → call `observe(text)`
- Asks what you remember → call `inspect()`
```

**3. Restart Claude Code**

The Curator MCP server starts automatically when Claude Code launches.

## What gets stored

The Curator stores conceptions — atomic facts about you, your project, and your working style. Examples:

- "User prefers 2-space indentation in all projects"
- "User is building a mobile app in Swift called Krill"  
- "User wants concise responses without unnecessary explanation"

Each conception has:
- **Recency** — how present it is. Decays over time, faster if low confidence.
- **Confidence** — how certain. Grows through confirming signal, shrinks on contradiction.

## Data

Conceptions are stored in `curator_mcp.db` next to the server file. Persists between sessions. Delete the file to start fresh.
