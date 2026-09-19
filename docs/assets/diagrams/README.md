# Diagram assets

This directory holds exported diagram images for the documentation site. It is
currently empty.

The architecture diagrams exist only as Excalidraw **source** at
`legacy/documentation/diagrams/`:

| File | Subject |
| --- | --- |
| `pipeline-architecture.excalidraw` | The end-to-end pipeline |
| `screening-schema.excalidraw` | The structured screening record |
| `paper-discovery-module.excalidraw` | The discovery module |

`legacy/documentation/diagrams/generate.py` regenerates those `.excalidraw`
files; share links are listed in `legacy/EXCALIDRAW.md`.

## To use one on the site

1. Open the `.excalidraw` file at <https://excalidraw.com>.
2. Export as **SVG** with a transparent background, so it works in both the
   light and dark themes.
3. Save it here and reference it with `![Alt text](../assets/diagrams/name.svg)`.

Prefer a Mermaid fence over an exported image where the diagram is simple
enough — Mermaid diagrams are searchable, themable and diffable, and
`pymdownx.superfences` is already configured for them. Reserve exported SVGs
for diagrams whose layout carries meaning that Mermaid cannot express.
