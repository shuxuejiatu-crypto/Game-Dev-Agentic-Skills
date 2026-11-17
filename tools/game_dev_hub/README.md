# Game Dev Skills Hub

A small desktop game-development reference and workflow tool built with Python's standard-library Tkinter. It reads `SKILL.md` files **only** from this repository's `skills/` directory; it does not depend on the generated index or other repository folders.

## Features

- Search skill names, descriptions, and skill content.
- Filter by skill category.
- Read each eligible `SKILL.md` in the app.
- Collect multiple skills into a workflow brief and export the combined source material to Markdown.
- Exclude skill folders/names marked Bevy, 3D, or VR.
- Use a small plugin structure: the catalog and workflow brief are separate tabs/plugins.

## Run

From the repository root:

```bash
python -m tools.game_dev_hub
```

Tkinter is included with most Python distributions. On some Linux distributions it is packaged separately (often as `python3-tk`).

## Scope

The catalog scans immediate child folders of `skills/` and loads each folder's `SKILL.md`. It does not modify the original skills. Skills whose folder/name contains `bevy`, `3d`, `vr`, or `virtual-reality` are excluded. Other skill text is shown as authored, so a general skill may still mention 3D as an incidental comparison; dedicated Bevy/3D/VR skill entries are omitted.
