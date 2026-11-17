from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk

from .plugins import SkillCatalogPlugin, WorkflowBriefPlugin


class GameDevHubApp(tk.Tk):
    """Search and assemble practical knowledge from the non-Bevy, non-3D skills."""

    def __init__(self, skills_dir: str | Path | None = None):
        super().__init__()
        self.title("Game Dev Skills Hub")
        self.geometry("1180x760")
        self.minsize(860, 560)

        repository_root = Path(__file__).resolve().parents[2]
        self.skills_dir = Path(skills_dir) if skills_dir else repository_root / "skills"
        self.status_var = tk.StringVar(value="Loading skills…")
        self.plugins = {
            "catalog": SkillCatalogPlugin(self),
            "brief": WorkflowBriefPlugin(self),
        }

        self._build_shell()
        for plugin in self.plugins.values():
            plugin.attach(self.workspace)
        self.plugins["catalog"].refresh()

    def _build_shell(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        self.workspace = ttk.Notebook(self)
        self.workspace.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 4))
        ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(10, 3)).grid(
            row=1, column=0, sticky="ew"
        )

    def set_status(self, message: str) -> None:
        self.status_var.set(message)
