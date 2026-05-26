# IlsSage

**AI Agent for Ionic Liquid Solubility of GAS** — a specialized framework for material science computations, with multiple user interfaces (Web UI / TUI / MCP server) for flexible access.

## Features

- **Crystal & Molecule Structure Generation** — Generate various crystal structures and molecules
- **Property Database Query** — Search ionic liquid and gas solubility properties
- **DFT Feature Retrieval** — Access DFT-calculated molecular features
- **Novel Ion Generation** — Generate novel ionic liquid molecules using machine learning
- **Binding Energy Prediction** — Predict binding energy between molecular structures

## Installation

**Requirements:** Python >= 3.11 and Node.js >= 20 are recommended. We suggest using Conda to create an isolated environment:

```bash
# 1. Create conda environment
conda create -n ilssage python=3.11 nodejs=20 numpy scipy rdkit openbabel tiktoken -y
conda activate ilssage

# 2. Clone the repository
git clone https://github.com/pxlxingliang/ilssage.git
cd ilssage

# 3. Build frontend (static assets are packaged into the wheel)
cd frontend && npm install && npm run build && cd ..

# 4. Install the package
pip install .
```

## Configuration

### Environment Variables (~/.ilssage/env.json)

Created automatically on first run with default values. Edit as needed:

```json
{
  "ILSSAGE_TRAIN_EB_PATH": "/path/to/properties.pkl",
  "ILSSAGE_QM_FEATURE_PATH": "/path/to/dft_features.pkl",
  "ILSSAGE_MOLECULE_GEN_SCRIPT": "/path/to/generation_script.sh",
  "ILSSAGE_EB_PREDICT_SCRIPT": "/path/to/Eb_predict.py"
}
```

See [Environment Variables](#environment-variables) for the complete list.

### LLM Provider (~/.ilssage/config.json)

```bash
mkdir -p ~/.ilssage
cp config.example.json ~/.ilssage/config.json
# Edit ~/.ilssage/config.json to add your API keys
```

Config example:

```json
{
  "currentModel": "volcengine/deepseek-v3.2",
  "providers": {
    "volcengine": {
      "name": "Volcano Engine",
      "type": "openai-compatible",
      "options": {
        "baseURL": "https://ark.cn-beijing.volces.com/api/coding/v3",
        "apiKey": "${ENV:VOLC_API_KEY}"
      },
      "models": {
        "deepseek-v3.2": {
          "name": "DeepSeek V3.2",
          "limit": { "context": 128000, "output": 4096 }
        }
      }
    }
  },
  "mcp_servers": [],
  "server": { "host": "0.0.0.0", "port": 8789 }
}
```

**Key points:**
- `${ENV:VAR_NAME}` placeholders are resolved from environment variables at runtime
- You can add multiple providers and switch between them at runtime
- `currentModel` sets the default model on startup

## Usage

Once installed, the `ilssage` command is available from any directory:

### TUI Mode (default)

```bash
ilssage
```

### Web UI Mode

```bash
ilssage web
```

**Local access:** Open **http://localhost:8789** in your browser.

**Remote access (via SSH port forwarding):**

If the server is running on a remote machine, use SSH local port forwarding to access it from your local browser:

1. Set up SSH key authentication (one-time setup):
   ```bash
   # On your local machine, generate a key pair if you don't have one
   ssh-keygen -t ed25519

   # Copy the public key to the remote server
   ssh-copy-id your-user@your-server
   ```

2. Forward the remote port to your local machine:
   ```bash
   ssh -N -L 8789:localhost:8789 your-user@your-server
   ```

3. Open **http://localhost:8789** in your local browser.

### MCP Server Mode

Expose tools for other agents (Claude Code, etc.):

```bash
ilssage mcp --transport stdio                        # stdio (for Claude Code)
ilssage mcp --transport sse --port 50001             # SSE (network clients)
ilssage mcp --transport streamable-http --port 50001 # HTTP streaming
```

## Skills — Adding Your Own Custom Instructions

Skills let you teach the agent specialized domain knowledge. Each skill is a simple Markdown file — the agent loads them **on-demand** when it recognizes a matching task.

### Quick Start

Create a skill directory with a `SKILL.md` file:

```bash
mkdir -p ~/.ilssage/skills/my_skill
```

Write `~/.ilssage/skills/my_skill/SKILL.md`:

```markdown
---
name: my_skill
version: "1.0"
description: Describe what this skill does in one sentence
author: Your Name
tags: [tag1, tag2]
trigger_keywords: [keyword1, keyword2]
---

# My Skill Title

## When to Use
Explain when this skill should be applied.

## Workflow
1. Step one
2. Step two
3. Step three

## Guidelines
- Important rules or conventions to follow
- Output format requirements
```

That's it — the agent will discover the skill on next startup. You don't need to restart if the agent is already running; new sessions pick up skills automatically.

### How It Works

1. **Discovery** — On startup, the agent scans `~/.ilssage/skills/` for directories containing `SKILL.md`. Only the YAML front matter (name, description) is loaded — the full content stays on disk.

2. **On-Demand Loading** — When you ask a question, the agent decides if a skill is relevant. If so, it calls the `load_skill` tool, which loads the full `SKILL.md` content and injects it into the conversation. The skill's directory path is also returned, so the agent can read additional files from the skill directory if needed.

3. **Persistence** — Once loaded, the skill content stays in the conversation history. The agent won't reload it on subsequent turns.

### Large Skills: Split Into Multiple Files

For complex skills, avoid putting everything into one huge `SKILL.md`. Instead, keep `SKILL.md` concise and reference additional files that the agent can read on-demand:

```
~/.ilssage/skills/deep_skill/
├── SKILL.md            # Core instructions + index of additional files
├── advanced.md         # Advanced usage scenarios
├── examples.md         # Worked examples
└── reference.md        # API reference or lookup tables
```

In `SKILL.md`, guide the agent:

```markdown
# Deep Skill

## Basic Workflow
1. Follow the steps below.
2. For advanced scenarios, read `advanced.md` in this directory.
3. For worked examples, read `examples.md`.

## When to Read Additional Files
- If the user asks about edge cases → read `advanced.md`
- If the user wants concrete examples → read `examples.md`
- If the user asks about specific parameters → read `reference.md`
```

The agent receives the skill directory path when it loads the skill, so it can use the `read_file` tool to fetch additional files only when needed. This keeps the initial context lean while preserving access to deep detail.


## Environment Variables

All environment variables are managed via `~/.ilssage/env.json`:

| Variable | Purpose | Default | Required For |
|----------|---------|---------|--------------|
| `ILSSAGE_WEB_HOST` | Web server host | `0.0.0.0` | Web UI |
| `ILSSAGE_WEB_PORT` | Web server port | `8789` | Web UI |
| `ILSSAGE_MCP_TRANSPORT` | MCP server transport | `stdio` | MCP server |
| `ILSSAGE_MCP_HOST` | MCP server host | `localhost` | MCP server |
| `ILSSAGE_MCP_PORT` | MCP server port | `50001` | MCP server |
| `ILSSAGE_TRAIN_EB_PATH` | Properties dataset path | — | Property search |
| `ILSSAGE_QM_FEATURE_PATH` | DFT features dataset path | — | DFT feature search |
| `ILSSAGE_MOLECULE_GEN_SCRIPT` | Ion generation script path | — | Novel ion generation |
| `ILSSAGE_EB_PREDICT_SCRIPT` | Binding energy prediction script | See note | Binding energy prediction |

**Note:** `ILSSAGE_EB_PREDICT_SCRIPT` defaults to `/personal/test/dwl/ilssage-models/Model/Property_pred/Eb_predict.py`

## For Developers

See the `docs/` directory for developer documentation:

- **[docs/MCP_TOOLS.md](docs/MCP_TOOLS.md)** — How to add custom MCP tools
- **[docs/SKILLS.md](docs/SKILLS.md)** — Skills system architecture (on-demand loading design)
- **[docs/DESIGN.md](docs/DESIGN.md)** — Architecture and design decisions
- **[docs/STRUCTURE.md](docs/STRUCTURE.md)** — Codebase structure guide

## Dependencies

- Python >= 3.10
- fastapi + uvicorn (web server)
- openai (LLM client)
- mcp >= 1.9.0 (Model Context Protocol)
- ase (structure generation)
- openbabel + rdkit (SMILES conversion)
- Node.js >= 18 (frontend build only)
