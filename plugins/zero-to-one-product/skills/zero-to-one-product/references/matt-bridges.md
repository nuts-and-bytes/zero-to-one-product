# Matt Bridges

## Purpose

The mapped Matt skills have two invocation and resolution types. Six are user-invoked and may declare `disable-model-invocation: true`; four are catalog-visible. The router follows both types through this bridge. Do not edit, remove, or work around third-party invocation metadata.

`zero-to-one-product` remains the single outer process owner. A bridged Matt skill supplies the selected phase procedure; it does not become an additional outer owner.

## Exact skill map

The map records names only. It never records or assumes an installation path.

| Routed purpose | Exact skill name | Invocation and resolution type |
|---|---|---|
| Product discovery without a codebase | `grill-me` | User-invoked; catalog first, trusted-root fallback only when catalog-missing |
| Product discovery with a workspace | `grill-with-docs` | User-invoked; catalog first, trusted-root fallback only when catalog-missing |
| Large unknown effort | `wayfinder` | User-invoked; catalog first, trusted-root fallback only when catalog-missing |
| External fact finding | `research` | Catalog-visible; catalog only, no filesystem fallback |
| Runnable design validation | `prototype` | Catalog-visible; catalog only, no filesystem fallback |
| Specification | `to-spec` | User-invoked; catalog first, trusted-root fallback only when catalog-missing |
| Product slicing | `to-tickets` | User-invoked; catalog first, trusted-root fallback only when catalog-missing |
| Difficult debugging | `diagnosing-bugs` | Catalog-visible; catalog only, no filesystem fallback |
| Whole-ticket review | `code-review` | Catalog-visible; catalog only, no filesystem fallback |
| Actual context or session transition | `handoff` | User-invoked; catalog first, trusted-root fallback only when catalog-missing |

## Bridge protocol

For the selected Matt phase:

1. Resolve the exact skill name with the Portable dependency gate in `../SKILL.md`. First use only the host-provided current-session catalog. One readable exact-name catalog path wins; an unreadable sole path or multiple exact-name catalog paths require a stop. Fallback is allowed only when the exact name is absent from the catalog.
2. Only when one of `grill-me`, `grill-with-docs`, `wayfinder`, `to-spec`, `to-tickets`, or `handoff` is absent from the catalog, build the POSIX or Windows trusted user/admin roots defined by the gate. `research`, `prototype`, `diagnosing-bugs`, and `code-review` are catalog-only and must stop with `dependencies.md` guidance when absent. Never search the current project, repository ancestors, project-local skill folders, or any directory recursively.
3. For each canonical trusted root, construct only `<canonical-root>/<exact-skill-name>/SKILL.md`. Canonicalize the candidate, reject it unless a path-component-aware check proves it remains contained in the root, normalize and deduplicate it, and count only readable candidates. If more than one remains, stop and report all candidates. If none remains, read `dependencies.md`, report the missing exact name and upstream installation guidance, and stop.
4. Read the selected `SKILL.md` completely before any phase action; continue through every chunk until EOF.
5. Follow the source procedure within the router's current scope, safety rules, phase entry condition, and phase exit gate.
6. Keep `zero-to-one-product` as the outer owner and keep `Other process skills selected now` as `none`.
7. Preserve every authorization and external-write gate. The bridge never grants permission.
8. On the phase exit gate, update state pointers and return control to the router for reclassification.

Never substitute a remembered, cached, copied, or reconstructed implementation, and never copy or edit the third-party source.

Use bridged `handoff` only for an actual context or session transition. It does not replace project state and cannot advance the product phase by itself.
