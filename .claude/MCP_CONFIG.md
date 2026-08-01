# MCP Server Configuration

LangChain documentation MCPs are configured for on-demand use only.

## Enabled (This Machine Only)

MCPs are stored in `.claude/settings.local.json` (git-ignored, personal machine only).

**Configured servers:**
- `docs-langchain` - LangChain/LangGraph documentation search
- `reference-langchain` - LangChain/LangGraph API reference

## How to Use

### Enable for Current Session
MCPs auto-load when `.claude/settings.local.json` exists. Restart Claude Code after modifying config.

### Disable for Current Session
Move or rename `.claude/settings.local.json`:
```bash
mv .claude/settings.local.json .claude/settings.local.json.bak
```

### Disable Permanently
Delete `.claude/settings.local.json`:
```bash
rm .claude/settings.local.json
```

## Why Local-Only

- Not checked into git (only personal machine uses them)
- Team doesn't auto-load MCPs
- Reduces session resource usage for those who don't need docs
- Easy to toggle on/off per machine

## Available Tools When Enabled

```
mcp__docs-langchain__search_docs_by_lang_chain
mcp__docs-langchain__query_docs_filesystem_docs_by_lang_chain
mcp__docs-langchain__submit_feedback
mcp__reference-langchain__search_api
mcp__reference-langchain__get_symbol
```
