---
name: find-skills
description: Helps users discover and install agent skills when they ask questions like "how do I do X", "find a skill for X", "is there a skill that can...", or express interest in extending capabilities. This skill should be used when the user is looking for functionality that might exist as an installable skill.
---

# Find Skills

This skill helps you discover and install skills from the open agent skills ecosystem (skills.sh / GitHub / Antigravity).

## When to Use This Skill

Use this skill when the user:

- Asks "how do I do X" where X might be a common task with an existing skill
- Says "find a skill for X" or "is there a skill for X"
- Asks "can you do X" where X is a specialized capability
- Expresses interest in extending agent capabilities
- Wants to search for tools, templates, or workflows
- Mentions they wish they had help with a specific domain (design, testing, deployment, etc.)

## What is the Skills CLI?

The Skills CLI (`npx skills`) is the package manager for the open agent skills ecosystem. Skills are modular packages that extend agent capabilities with specialized knowledge, workflows, and tools.

**Key commands:**

- `npx skills find [query] [--owner <owner>]` - Search for skills interactively or by keyword, optionally scoped to a GitHub owner
- `npx skills add <package>` - Install a skill from GitHub or other sources
- `npx skills update` - Update all installed skills

**Browse skills at:** https://skills.sh/

## How Skills Work in Antigravity

In Antigravity, skills can be installed in:
1. **Workspace level**: `.agents/skills/<skill-name>/SKILL.md` (active for the current project)
2. **Global level**: `~/.gemini/config/skills/<skill-name>/SKILL.md` (active for all projects)
3. **Plugins**: In `~/.gemini/config/plugins/` with `plugin.json` containing bundled skills, rules, and MCP servers.

## How to Help Users Find and Install Skills

### Step 1: Understand What They Need
1. The domain (e.g., React, testing, scientific research, documentation, devops)
2. The specific task
3. Check existing installed skills first (e.g. built-ins and plugins like `science`, `chrome-devtools`, `gemini-api`)

### Step 2: Search for Skills
- Search `skills.sh` or query GitHub repositories for `SKILL.md` specifications.
- If Node.js/npx is available:
  ```bash
  npx skills find [query]
  ```

### Step 3: Install the Skill
- To install a skill in the current workspace:
  Save the `SKILL.md` (and any associated `scripts/` or `references/`) to `.agents/skills/<skill-name>/SKILL.md`.
- To install globally:
  Save to `~/.gemini/config/skills/<skill-name>/SKILL.md`.
