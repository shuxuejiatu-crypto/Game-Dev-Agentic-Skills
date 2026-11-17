from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import tkinter as tk
from tkinter import ttk


@dataclass(frozen=True)
class Skill:
    name: str
    folder: str
    description: str
    path: Path
    content: str

    @property
    def category(self) -> str:
        parts = self.name.split("-")
        if len(parts) > 2 and parts[0] == "godot":
            return parts[1].replace("_", " ").title()
        return "General"


class Plugin:
    """Small interface used by tabs that extend the main app."""

    tab_title = "Plugin"

    def __init__(self, app):
        self.app = app

    def attach(self, notebook: ttk.Notebook) -> None:
        raise NotImplementedError


class SkillCatalogPlugin(Plugin):
    """Loads, filters, and displays SKILL.md files under the skills directory."""

    tab_title = "Skill Catalog"
    _excluded_tokens = ("bevy", "3d", "vr", "virtual-reality")

    def __init__(self, app):
        super().__init__(app)
        self.skills: list[Skill] = []
        self.visible_skills: list[Skill] = []

    @staticmethod
    def _frontmatter(content: str) -> dict[str, str]:
        match = re.match(r"\A\ufeff?---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|\Z)", content, re.DOTALL)
        if not match:
            return {}
        values: dict[str, str] = {}
        for line in match.group(1).splitlines():
            key, separator, value = line.partition(":")
            if separator:
                values[key.strip()] = value.strip().strip("\\\"'")
        return values

    @classmethod
    def _is_excluded(cls, folder: str, name: str, description: str) -> bool:
        identifier = f"{folder} {name}".casefold().replace("_", "-")
        return any(token in identifier for token in cls._excluded_tokens)

    def load(self) -> tuple[int, int]:
        self.skills = []
        root = self.app.skills_dir
        if not root.is_dir():
            return 0, 0

        excluded = 0
        for folder in sorted(root.iterdir(), key=lambda path: path.name.casefold()):
            if not folder.is_dir() or folder.name.startswith("."):
                continue
            skill_file = folder / "SKILL.md"
            if not skill_file.is_file():
                continue
            try:
                content = skill_file.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError):
                continue

            metadata = self._frontmatter(content)
            name = metadata.get("name", folder.name)
            description = metadata.get("description", "")
            if self._is_excluded(folder.name, name, description):
                excluded += 1
                continue
            self.skills.append(Skill(name, folder.name, description, skill_file, content))
        self.skills.sort(key=lambda skill: skill.name.casefold())
        return len(self.skills), excluded

    def attach(self, notebook: ttk.Notebook) -> None:
        self.frame = ttk.Frame(notebook, padding=8)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)
        notebook.add(self.frame, text=self.tab_title)

        toolbar = ttk.Frame(self.frame)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.columnconfigure(1, weight=1)
        ttk.Label(toolbar, text="Search").grid(row=0, column=0, padx=(0, 6))
        self.search_var = tk.StringVar()
        search = ttk.Entry(toolbar, textvariable=self.search_var)
        search.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.search_var.trace_add("write", lambda *_: self._apply_filter())

        ttk.Label(toolbar, text="Category").grid(row=0, column=2, padx=(0, 6))
        self.category_var = tk.StringVar(value="All")
        self.category_box = ttk.Combobox(
            toolbar, textvariable=self.category_var, state="readonly", width=18
        )
        self.category_box.grid(row=0, column=3, padx=(0, 10))
        self.category_box.bind("<<ComboboxSelected>>", lambda _event: self._apply_filter())
        ttk.Button(toolbar, text="Refresh", command=self.refresh).grid(row=0, column=4)

        body = ttk.Panedwindow(self.frame, orient="horizontal")
        body.grid(row=1, column=0, sticky="nsew")
        left = ttk.Frame(body, padding=(0, 0, 8, 0))
        right = ttk.Frame(body)
        body.add(left, weight=1)
        body.add(right, weight=3)
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        self.listbox = tk.Listbox(left, exportselection=False)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(left, orient="vertical", command=self.listbox.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=yscroll.set)
        self.listbox.bind("<<ListboxSelect>>", self._show_selected)
        ttk.Button(left, text="Add to workflow brief", command=self._add_selected).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )

        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        self.title_var = tk.StringVar(value="Choose a skill")
        ttk.Label(right, textvariable=self.title_var, font=("TkDefaultFont", 13, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        content_frame = ttk.Frame(right)
        content_frame.grid(row=1, column=0, sticky="nsew")
        content_frame.rowconfigure(0, weight=1)
        content_frame.columnconfigure(0, weight=1)
        self.content_view = tk.Text(content_frame, wrap="word", undo=False, padx=10, pady=8)
        self.content_view.grid(row=0, column=0, sticky="nsew")
        content_scroll = ttk.Scrollbar(content_frame, orient="vertical", command=self.content_view.yview)
        content_scroll.grid(row=0, column=1, sticky="ns")
        self.content_view.configure(yscrollcommand=content_scroll.set)
        self.content_view.configure(state="disabled")

    def refresh(self) -> None:
        count, excluded = self.load()
        categories = ["All", *sorted({skill.category for skill in self.skills})]
        self.category_box.configure(values=categories)
        if self.category_var.get() not in categories:
            self.category_var.set("All")
        self._apply_filter()
        self.app.set_status(
            f"Loaded {count} skills from {self.app.skills_dir}; excluded {excluded} Bevy/3D/VR folders."
        )

    def _apply_filter(self) -> None:
        if not hasattr(self, "listbox"):
            return
        query = self.search_var.get().strip().casefold()
        category = self.category_var.get()
        self.visible_skills = [
            skill for skill in self.skills
            if (category == "All" or skill.category == category)
            and (not query or query in skill.name.casefold()
                 or query in skill.description.casefold()
                 or query in skill.content.casefold())
        ]
        self.listbox.delete(0, tk.END)
        for skill in self.visible_skills:
            self.listbox.insert(tk.END, skill.name)
        if self.visible_skills:
            self.listbox.selection_set(0)
            self.listbox.event_generate("<<ListboxSelect>>")
        else:
            self.title_var.set("No matching skills")
            self._set_content("Change the search text or category to see matching skills.")
        self.app.set_status(f"Showing {len(self.visible_skills)} of {len(self.skills)} eligible skills.")

    def _selected_skill(self) -> Skill | None:
        selection = self.listbox.curselection()
        return self.visible_skills[selection[0]] if selection else None

    def _show_selected(self, _event=None) -> None:
        skill = self._selected_skill()
        if skill is None:
            return
        self.title_var.set(skill.name)
        self._set_content(skill.content)

    def _set_content(self, content: str) -> None:
        self.content_view.configure(state="normal")
        self.content_view.delete("1.0", tk.END)
        self.content_view.insert("1.0", content)
        self.content_view.configure(state="disabled")
        self.content_view.yview_moveto(0)

    def _add_selected(self) -> None:
        skill = self._selected_skill()
        if skill is None:
            return
        self.app.plugins["brief"].add_skill(skill)
        self.app.set_status(f"Added {skill.name} to the workflow brief.")


class WorkflowBriefPlugin(Plugin):
    """Collects selected skills into a portable Markdown brief for a game-dev task."""

    tab_title = "Workflow Brief"

    def __init__(self, app):
        super().__init__(app)
        self.selected: list[Skill] = []

    def attach(self, notebook: ttk.Notebook) -> None:
        self.frame = ttk.Frame(notebook, padding=10)
        self.frame.rowconfigure(1, weight=1)
        self.frame.columnconfigure(0, weight=1)
        notebook.add(self.frame, text=self.tab_title)

        header = ttk.Frame(self.frame)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Selected skill modules", font=("TkDefaultFont", 12, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(header, text="Remove selected", command=self.remove_selected).grid(row=0, column=1, padx=4)
        ttk.Button(header, text="Clear", command=self.clear).grid(row=0, column=2, padx=4)
        ttk.Button(header, text="Export Markdown…", command=self.export).grid(row=0, column=3, padx=(4, 0))

        body = ttk.Panedwindow(self.frame, orient="horizontal")
        body.grid(row=1, column=0, sticky="nsew")
        left = ttk.Frame(body, padding=(0, 0, 8, 0))
        right = ttk.Frame(body)
        body.add(left, weight=1)
        body.add(right, weight=3)
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        self.items = tk.Listbox(left, exportselection=False)
        self.items.grid(row=0, column=0, sticky="nsew")
        self.items.bind("<<ListboxSelect>>", self._preview_selected)

        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)
        self.preview = tk.Text(right, wrap="word", padx=10, pady=8, state="disabled")
        self.preview.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(right, orient="vertical", command=self.preview.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=scroll.set)

    def add_skill(self, skill: Skill) -> None:
        if all(existing.path != skill.path for existing in self.selected):
            self.selected.append(skill)
            self._refresh_items()
        self.app.workspace.select(self.frame)

    def _refresh_items(self) -> None:
        self.items.delete(0, tk.END)
        for skill in self.selected:
            self.items.insert(tk.END, skill.name)
        if self.selected:
            self.items.selection_set(0)
            self._preview_selected()
        else:
            self._set_preview("Add skills from the Skill Catalog tab to assemble a reusable workflow brief.")

    def _preview_selected(self, _event=None) -> None:
        selection = self.items.curselection()
        if selection:
            self._set_preview(self.selected[selection[0]].content)

    def _set_preview(self, text: str) -> None:
        self.preview.configure(state="normal")
        self.preview.delete("1.0", tk.END)
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")
        self.preview.yview_moveto(0)

    def remove_selected(self) -> None:
        selection = self.items.curselection()
        if selection:
            del self.selected[selection[0]]
            self._refresh_items()
            self.app.set_status("Removed a skill from the workflow brief.")

    def clear(self) -> None:
        self.selected.clear()
        self._refresh_items()
        self.app.set_status("Workflow brief cleared.")

    def export(self) -> None:
        from tkinter import filedialog, messagebox

        if not self.selected:
            messagebox.showinfo("Nothing to export", "Add at least one skill to the workflow brief first.", parent=self.app)
            return
        target = filedialog.asksaveasfilename(
            parent=self.app,
            title="Export workflow brief",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("All files", "*.*")],
            initialfile="game-dev-workflow-brief.md",
        )
        if not target:
            return
        chunks = [
            "# Game Development Workflow Brief",
            "",
            "Combined from selected, non-Bevy / non-3D skills in the repository `skills/` folder.",
            "",
        ]
        for skill in self.selected:
            chunks.extend((f"## {skill.name}", "", f"Source skill: `{skill.path.as_posix()}`", ""))
            chunks.append(skill.content.rstrip())
            chunks.extend(("", "---", ""))
        try:
            Path(target).write_text("\n".join(chunks).rstrip() + "\n", encoding="utf-8")
        except OSError as error:
            messagebox.showerror("Export failed", str(error), parent=self.app)
            return
        self.app.set_status(f"Exported workflow brief to {target}.")
        messagebox.showinfo("Export complete", f"Saved workflow brief:\n{target}", parent=self.app)
