# Zero-to-One Product

`zero-to-one-product` is a skills-only Codex router that combines selected workflows from [Matt Pocock's skills](https://github.com/mattpocock/skills) and [Superpowers](https://github.com/obra/superpowers) into a fixed path from product idea to first usable version.

The plugin does not bundle either upstream project. Install and update those dependencies separately before installing this marketplace.

## Prerequisites

- Codex App or Codex CLI with Plugins support.
- Node.js and `npx`, required by the Matt Pocock skills installer.
- Network access to GitHub and the Codex Plugins marketplace.

## Install dependencies

### 1. Matt Pocock skills

Run the current upstream installer:

```bash
npx skills@latest add mattpocock/skills
```

Select the required skills listed below, plus `setup-matt-pocock-skills`. Then open the project where you will use the router and complete the installed `setup-matt-pocock-skills` workflow in that project.

That upstream setup first explores the project, presents its findings and proposed changes, and asks you to confirm. After confirmation, it edits an existing project-level `CLAUDE.md` or `AGENTS.md`; if neither exists, it asks which one to create. It also writes `docs/agents/issue-tracker.md` and `docs/agents/domain.md`, plus the optional `docs/agents/triage-labels.md` when the `triage` skill is installed. These are explicit project-level writes made by the upstream setup, not silent global `AGENTS.md` changes made by this router.

### 2. Superpowers

- In Codex App, open the official Plugins marketplace, search for **Superpowers**, and install it.
- In Codex CLI, enter `/plugins`, search for **Superpowers**, and choose **Install Plugin**.

## Install this plugin

Add the marketplace and install its plugin:

```bash
codex plugin marketplace add nuts-and-bytes/zero-to-one-product
codex plugin add zero-to-one-product@zero-to-one-product
```

Open a new conversation so Codex refreshes its skill catalog.

## Use

Explicit invocation is the reliable entry point:

```text
$zero-to-one-product <your product idea or current 0-to-1 goal>
```

Implicit invocation may also work, but another installation's `AGENTS.md` can contain conflicting catch-all workflow rules. This plugin never silently changes a global `AGENTS.md`.

## Required external skills

Matt Pocock skills:

- `grill-me`
- `grill-with-docs`
- `wayfinder`
- `research`
- `prototype`
- `to-spec`
- `to-tickets`
- `diagnosing-bugs`
- `code-review`
- `handoff`

Superpowers skills:

- `using-git-worktrees`
- `writing-plans`
- `test-driven-development`
- `systematic-debugging`
- `requesting-code-review`
- `verification-before-completion`
- `finishing-a-development-branch`

See [`dependencies.md`](plugins/zero-to-one-product/skills/zero-to-one-product/references/dependencies.md) for the canonical dependency list and upstream links.

## Update

Refresh the marketplace snapshot:

```bash
codex plugin marketplace upgrade zero-to-one-product
```

Then use the Codex Plugins interface to update or reinstall **Zero-to-One Product**. Update Matt Pocock skills and Superpowers separately through their current upstream installation interfaces, and open a new conversation afterward.

## Uninstall

```bash
codex plugin remove zero-to-one-product@zero-to-one-product
```

This removes the router plugin. It does not remove the independently installed Matt Pocock or Superpowers skills.

## Troubleshooting

If the router reports a missing dependency:

1. Note the exact skill name and whether it belongs to Matt Pocock skills or Superpowers.
2. Install or update that upstream project using the instructions above.
3. For Matt Pocock skills, complete `setup-matt-pocock-skills` inside the current project.
4. Open a new conversation and invoke `$zero-to-one-product` explicitly.

If the router reports an ambiguous dependency, remove or disable stale duplicate installations so exactly one trusted copy of that skill is discoverable, then open a new conversation. Do not patch the router with a machine-specific skill path.

## Security

This distribution contains no MCP server, hook, runtime script, credential, or private data. It bundles only the router skill and its documentation. The repository-local distribution validator is a maintainer check and is not required at runtime.
