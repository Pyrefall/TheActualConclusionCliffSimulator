from __future__ import annotations

import audioop
import json
import math
import random
import threading
import wave
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    import simpleaudio  # type: ignore
except Exception:  # pragma: no cover
    simpleaudio = None  # type: ignore

# Core configuration
RESOURCE_KEYS = [
    "mallets",
    "T1 cheese",
    "T2 cheese",
    "T3 cheese",
    "Thread",
    "Machinery",
    "Diamond",
]
CONSUMABLE_KEYS = ["CC", "hooks", "Gold", "ME"]
BASE_GENRES = ["Romance", "Adventure", "Comedy", "Tragedy", "Suspense"]
FANTASY_GENRE = "Fantasy"
CHAPTER_LENGTHS = [10, 20, 30]
TOTAL_CHAPTERS = 6
CHEESE_HUNT_RULES = {
    "T1": {
        "resource": "T1 cheese",
        "page_gain": 25,
        "chapter_enemy": "T1 mouse",
        "post_enemy": "Common Weaver - With T1 Cheese",
        "post_fantasy_enemy": "Ultimate MythWeaver - With T1 Cheese",
        "notoriety_gain": 25,
    },
    "T2": {
        "resource": "T2 cheese",
        "page_gain": 50,
        "chapter_enemy": "T2 mouse",
        "post_enemy": "Common Weaver - With T2 Cheese",
        "post_fantasy_enemy": "Ultimate MythWeaver - With T2 Cheese",
        "notoriety_gain": 50,
    },
    "T3": {
        "resource": "T3 cheese",
        "page_gain": 125,
        "chapter_enemy": "T3 mouse",
        "post_enemy": "Common Weaver - With T3 Cheese",
        "post_fantasy_enemy": "Ultimate MythWeaver - With T3 Cheese",
        "notoriety_gain": 125,
    },
}
SOUND_FILES = {
    "copy_message": "copy_message.wav",
    "import_success": "import_success.wav",
    "dialog_open": "dialog_open.wav",
    "button_click": "button_click.wav",
    "completion": "completion.wav",
}
SOUNDS_DIR = Path(__file__).resolve().parent / "sounds"
DEFAULT_ENEMY_DROPS = {
    "T1 mouse": {"Thread": 1.54, "Gold": 7500},
    "T2 mouse": {"Machinery": 2.43, "Gold": 16500},
    "T3 mouse": {"Gold": 25000},
    "Common Weaver - With T1 Cheese": {"Gold": 25000, "mallets": 1.5, "Thread": 1.54},
    "Common Weaver - With T2 Cheese": {
        "Gold": 25000,
        "mallets": 1.5,
        "Machinery": 2.43,
    },
    "Common Weaver - With T3 Cheese": {"Gold": 25000, "mallets": 1.5},
    "Ultimate MythWeaver - With T1 Cheese": {
        "Gold": 225000,
        "Diamond": 1,
        "mallets": 2.3,
        "Thread": 1.54,
    },
    "Ultimate MythWeaver - With T2 Cheese": {
        "Gold": 225000,
        "Diamond": 1,
        "mallets": 2.3,
        "Machinery": 2.43,
    },
    "Ultimate MythWeaver - With T3 Cheese": {
        "Gold": 225000,
        "Diamond": 1,
        "mallets": 2.3,
    },
}
ALL_MATERIAL_TYPES = sorted(set(RESOURCE_KEYS + CONSUMABLE_KEYS))

def _default_enemy_drops() -> dict:
    return {enemy: dict(drops) for enemy, drops in DEFAULT_ENEMY_DROPS.items()}


def _copy_enemy_drops(source: dict) -> dict:
    return {enemy: dict(drops) for enemy, drops in source.items()}


def _default_genre_pages() -> dict:
    genres = list(BASE_GENRES) + [FANTASY_GENRE]
    return {genre: 0 for genre in genres}


def _copy_genre_pages(source: dict) -> dict:
    pages = _default_genre_pages()
    for genre, value in source.items():
        if genre in pages:
            pages[genre] = int(value)
    return pages


def _copy_chapter_choices(choices: list[dict]) -> list[dict]:
    return [dict(choice) for choice in choices]


def _open_sound_path(name: str) -> Path:
    return SOUNDS_DIR / SOUND_FILES[name]


class AudioManager:
    def __init__(self) -> None:
        self._enabled = True
        self._volume = 0.7
        self._samples: dict[str, tuple[bytes, int, int, int]] = {}
        self._lock = threading.Lock()
        self._initialized = False
        self._available = False
        print(f"[SFX] AudioManager init (simpleaudio available: {simpleaudio is not None})")

    def configure(self, enabled: bool, volume: float) -> None:
        with self._lock:
            self._enabled = bool(enabled)
            self._volume = max(0.0, min(1.0, float(volume)))
        print(f"[SFX] configure -> enabled={self._enabled}, volume={self._volume:.2f}")

    def ensure_loaded(self) -> None:
        if simpleaudio is None:
            with self._lock:
                self._initialized = True
                self._available = False
            print('[SFX] simpleaudio not available; sounds disabled.')
            return
        with self._lock:
            if self._initialized:
                return
            try:
                for cue in SOUND_FILES:
                    path = _open_sound_path(cue)
                    with wave.open(str(path), "rb") as wf:
                        params = wf.getparams()
                        frames = wf.readframes(params.nframes)
                        self._samples[cue] = (
                            frames,
                            params.nchannels,
                            params.sampwidth,
                            params.framerate,
                        )
                self._available = True
                print(f"[SFX] Loaded {len(self._samples)} sound samples.")
            except Exception as exc:
                print(f'[SFX] Failed to load sounds: {exc}')
                self._samples.clear()
                self._available = False
            finally:
                self._initialized = True

    def play(self, cue: str) -> None:
        if not self._enabled:
            print(f"[SFX] Skipping '{cue}' (disabled).")
            return
        if simpleaudio is None:
            print(f"[SFX] Skipping '{cue}' (simpleaudio missing).")
            return
        with self._lock:
            if not self._initialized:
                self.ensure_loaded()
            if not self._available:
                print(f"[SFX] Skipping '{cue}' (audio unavailable).")
                return
            sample = self._samples.get(cue)
        if not sample:
            print(f"[SFX] Sample '{cue}' not found.")
            return
        data, channels, sample_width, frame_rate = sample
        try:
            payload = data if self._volume >= 0.999 else audioop.mul(data, sample_width, self._volume)
            simpleaudio.play_buffer(payload, channels, sample_width, frame_rate)
        except Exception as exc:
            print(f"[SFX] Playback error for '{cue}': {exc}")


audio_manager = AudioManager()
audio_manager.ensure_loaded()


RECIPES = [
    {
        "label": "6 hook + 2000 Gold → 1 T1 cheese",
        "outputs": {"T1 cheese": 1},
        "costs": {"hooks": 6, "Gold": 2000},
    },
    {
        "label": "6 hook + 16000 Gold → 2 T1 cheese",
        "outputs": {"T1 cheese": 2},
        "costs": {"hooks": 6, "Gold": 16000},
    },
    {
        "label": "12 T1 cheese + 24 Thread + 1 ME → 2 T2 cheese",
        "outputs": {"T2 cheese": 2},
        "costs": {"T1 cheese": 12, "Thread": 24, "ME": 1},
    },
    {
        "label": "48 T1 cheese + 60 Machinery + 1 ME → 2 T3 cheese",
        "outputs": {"T3 cheese": 2},
        "costs": {"T1 cheese": 48, "Machinery": 60, "ME": 1},
    },
    {
        "label": "30 Machinery → 1 Mallet",
        "outputs": {"mallets": 1},
        "costs": {"Machinery": 30},
    },
]


@dataclass
class GameState:
    resources: dict = field(default_factory=lambda: {key: 0 for key in RESOURCE_KEYS})
    consumables: dict = field(default_factory=lambda: {key: 0 for key in CONSUMABLE_KEYS})
    notoriety: dict = field(default_factory=lambda: {genre: 0 for genre in BASE_GENRES})
    enemy_drops: dict = field(default_factory=_default_enemy_drops)
    genre_pages: dict = field(default_factory=_default_genre_pages)
    total_hunts: int = 0
    current_run_hunts: int = 0
    chapter_position: int = 0
    current_chapter_length: int | None = None
    current_chapter_genre: str | None = None
    current_chapter_progress: int = 0
    postscript_length: int = 10
    pending_chapter_choices: list[dict] = field(default_factory=list)
    run_fantasy_available: bool = False
    postscript_extended: bool = False
    run_mallets_spent: int = 0
    total_mallets_spent: int = 0
    total_diamonds_gain: float = 0.0
    pending_choices_locked: bool = False

    def clone(self) -> "GameState":
        return GameState(
            resources=dict(self.resources),
            consumables=dict(self.consumables),
            notoriety=dict(self.notoriety),
            enemy_drops=_copy_enemy_drops(self.enemy_drops),
            genre_pages=_copy_genre_pages(self.genre_pages),
            total_hunts=self.total_hunts,
            current_run_hunts=self.current_run_hunts,
            chapter_position=self.chapter_position,
            current_chapter_length=self.current_chapter_length,
            current_chapter_genre=self.current_chapter_genre,
            current_chapter_progress=self.current_chapter_progress,
            postscript_length=self.postscript_length,
            pending_chapter_choices=_copy_chapter_choices(self.pending_chapter_choices),
            run_fantasy_available=self.run_fantasy_available,
            postscript_extended=self.postscript_extended,
            run_mallets_spent=self.run_mallets_spent,
            total_mallets_spent=self.total_mallets_spent,
            pending_choices_locked=self.pending_choices_locked,
            total_diamonds_gain=self.total_diamonds_gain,
        )

    def to_dict(self) -> dict:
        return {
            "resources": self.resources,
            "consumables": self.consumables,
            "notoriety": self.notoriety,
            "enemy_drops": self.enemy_drops,
            "genre_pages": self.genre_pages,
            "total_hunts": self.total_hunts,
            "current_run_hunts": self.current_run_hunts,
            "chapter_position": self.chapter_position,
            "current_chapter_length": self.current_chapter_length,
            "current_chapter_genre": self.current_chapter_genre,
            "current_chapter_progress": self.current_chapter_progress,
            "postscript_length": self.postscript_length,
            "pending_chapter_choices": self.pending_chapter_choices,
            "run_fantasy_available": self.run_fantasy_available,
            "postscript_extended": self.postscript_extended,
            "run_mallets_spent": self.run_mallets_spent,
            "total_mallets_spent": self.total_mallets_spent,
            "pending_choices_locked": self.pending_choices_locked,
            "total_diamonds_gain": self.total_diamonds_gain,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        state = cls()
        state.resources.update({key: float(data.get("resources", {}).get(key, 0)) for key in RESOURCE_KEYS})
        state.consumables.update({key: float(data.get("consumables", {}).get(key, 0)) for key in CONSUMABLE_KEYS})
        raw_notoriety = data.get("notoriety", {})
        for genre in BASE_GENRES:
            value = int(raw_notoriety.get(genre, 0))
            state.notoriety[genre] = max(0, min(200, value))
        raw_drops = data.get("enemy_drops", {})
        for enemy, drops in raw_drops.items():
            state.enemy_drops[enemy] = {material: float(amount) for material, amount in drops.items()}
        for enemy in DEFAULT_ENEMY_DROPS:
            state.enemy_drops.setdefault(enemy, dict(DEFAULT_ENEMY_DROPS[enemy]))
        state.genre_pages = _copy_genre_pages(data.get("genre_pages", {}))
        state.total_hunts = int(data.get("total_hunts", 0))
        state.current_run_hunts = int(data.get("current_run_hunts", 0))
        state.chapter_position = int(data.get("chapter_position", 0))
        stored_length = data.get("current_chapter_length")
        state.current_chapter_length = int(stored_length) if stored_length is not None else None
        state.current_chapter_genre = data.get("current_chapter_genre")
        state.current_chapter_progress = int(data.get("current_chapter_progress", 0))
        state.postscript_length = int(data.get("postscript_length", 10))
        state.pending_chapter_choices = _copy_chapter_choices(data.get("pending_chapter_choices", []))
        state.run_fantasy_available = bool(data.get("run_fantasy_available", False))
        state.postscript_extended = bool(data.get("postscript_extended", False))
        state.run_mallets_spent = int(data.get("run_mallets_spent", 0))
        state.total_mallets_spent = int(data.get("total_mallets_spent", 0))
        state.pending_choices_locked = bool(data.get("pending_choices_locked", False))
        state.total_diamonds_gain = float(data.get("total_diamonds_gain", 0.0))
        return state

    def fantasy_unlocked(self) -> bool:
        return all(value > 80 for value in self.notoriety.values())


class HistoryManager:
    def __init__(self, initial_state: GameState):
        self._current = initial_state
        self._undo = []
        self._redo = []

    @property
    def current(self) -> GameState:
        return self._current

    def commit(self, new_state: GameState):
        self._undo.append(self._current)
        self._current = new_state
        self._redo.clear()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> GameState | None:
        if not self._undo:
            return None
        self._redo.append(self._current)
        self._current = self._undo.pop()
        return self._current

    def redo(self) -> GameState | None:
        if not self._redo:
            return None
        self._undo.append(self._current)
        self._current = self._redo.pop()
        return self._current


class SimulatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Complete Coclusion Cliff Simulator")
        self.root.geometry("1500x895")
        self.history = HistoryManager(GameState())
        self.state = self.history.current

        self.resource_vars = {key: tk.StringVar(value="0") for key in RESOURCE_KEYS}
        self.consumable_vars = {key: tk.StringVar(value="0") for key in CONSUMABLE_KEYS}
        self.notoriety_vars = {genre: tk.StringVar(value="0") for genre in BASE_GENRES}
        self.quantity_var = tk.StringVar(value="1")
        self.fantasy_var = tk.StringVar(value=self._fantasy_text())
        self.drop_vars: dict[str, dict[str, tk.StringVar]] = {}
        self.drop_rows: dict[str, dict[str, tk.Widget]] = {}
        self.enemy_frames: dict[str, ttk.Frame] = {}
        self.add_buttons: dict[str, ttk.Button] = {}
        self.start_random_button: ttk.Button | None = None
        self.start_manual_button: ttk.Button | None = None
        self.extend_postscript_button: ttk.Button | None = None
        self.pending_choices_frame: ttk.LabelFrame | None = None
        self.pending_choices_container: ttk.Frame | None = None
        self.log_text: tk.Text | None = None
        self.cc_enabled = tk.BooleanVar(value=True)
        self.total_hunts_var = tk.StringVar(value="0")
        self.run_hunts_var = tk.StringVar(value="0")
        self.chapter_pos_var = tk.StringVar(value="0")
        self.chapter_length_var = tk.StringVar(value="—")
        self.chapter_genre_var = tk.StringVar(value="—")
        self.chapter_progress_var = tk.StringVar(value="0 / 0")
        self.genre_page_vars = {genre: tk.StringVar(value="0") for genre in BASE_GENRES + [FANTASY_GENRE]}
        self.page_label_widgets: dict[str, ttk.Label] = {}
        self.pages_pie_canvas: tk.Canvas | None = None
        self.run_mallets_var = tk.StringVar(value="0")
        self.total_mallets_var = tk.StringVar(value="0")
        self.hunts_per_diamond_var = tk.StringVar(value="N/A")
        self.sfx_enabled = tk.BooleanVar(value=True)
        self.sfx_volume = tk.DoubleVar(value=25.0)

        self._build_layout()
        self._refresh_view()
        self._update_sound_settings()

    def _build_layout(self):
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        notebook = ttk.Notebook(self.root)
        notebook.grid(row=0, column=0, sticky="nsew")

        craft_tab = ttk.Frame(notebook, padding=10)
        notebook.add(craft_tab, text="Simulation")
        drop_tab = ttk.Frame(notebook, padding=10)
        notebook.add(drop_tab, text="Drop Data")

        self._build_crafting_tab(craft_tab)
        self._build_drop_tab(drop_tab)

    def _build_crafting_tab(self, container: ttk.Frame):
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        left_panel = ttk.Frame(container)
        left_panel.grid(row=0, column=0, sticky="nsew")
        left_panel.columnconfigure(0, weight=1)
        left_panel.columnconfigure(1, weight=1)

        right_panel = ttk.Frame(container)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right_panel.columnconfigure(0, weight=1)

        resources_frame = ttk.LabelFrame(left_panel, text="Resources")
        resources_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._populate_entries(resources_frame, self.resource_vars, "resources", allow_float=True)

        consumables_frame = ttk.LabelFrame(left_panel, text="Consumables (can go negative)")
        consumables_frame.grid(row=0, column=1, sticky="nsew")
        self._populate_entries(consumables_frame, self.consumable_vars, "consumables", allow_float=True)
        cc_check = ttk.Checkbutton(consumables_frame, text="CC ON", variable=self.cc_enabled)
        cc_check.grid(row=len(self.consumable_vars) + 1, column=0, sticky="w", pady=(10, 0))

        stats_frame = ttk.Frame(left_panel)
        stats_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)

        notoriety_frame = ttk.LabelFrame(stats_frame, text="Genre Notoriety (0-200)")
        notoriety_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._build_notoriety_display(notoriety_frame)
        self.fantasy_label = ttk.Label(notoriety_frame, textvariable=self.fantasy_var, font=("Arial", 11, "bold"))
        self.fantasy_label.grid(row=1, column=0, columnspan=5, pady=(10, 0), sticky="w")

        pages_container = ttk.Frame(stats_frame)
        pages_container.grid(row=0, column=1, sticky="nsew")
        self._build_pages_section(pages_container)

        craft_frame = ttk.LabelFrame(left_panel, text="Crafting Simulator")
        craft_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        quantity_row = ttk.Frame(craft_frame)
        quantity_row.pack(fill="x", pady=4)
        ttk.Label(quantity_row, text="Craft quantity:").pack(side="left")
        qty_entry = ttk.Entry(quantity_row, textvariable=self.quantity_var, width=5)
        qty_entry.pack(side="left", padx=(5, 0))
        qty_entry.bind("<FocusOut>", lambda _event: self._sanitize_quantity())
        qty_entry.bind("<Return>", lambda _event: self._sanitize_quantity())

        for recipe in RECIPES:
            self._button(
                craft_frame,
                text=recipe["label"],
                command=lambda r=recipe: self._craft(r),
                sound="import_success",
            ).pack(fill="x", pady=2)

        snapshot_frame = ttk.Frame(left_panel)
        snapshot_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.undo_button = ttk.Button(snapshot_frame, text="Undo", command=self._undo)
        self.undo_button.pack(side="left", padx=(0, 5))
        self.redo_button = ttk.Button(snapshot_frame, text="Redo", command=self._redo)
        self.redo_button.pack(side="left", padx=(0, 5))
        ttk.Button(snapshot_frame, text="Save Snapshot…", command=self._save_snapshot).pack(side="left", padx=(0, 5))
        ttk.Button(snapshot_frame, text="Load Snapshot…", command=self._load_snapshot).pack(side="left")
        sfx_frame = ttk.Frame(snapshot_frame)
        sfx_frame.pack(side="right")
        ttk.Checkbutton(
            sfx_frame,
            text="SFX",
            variable=self.sfx_enabled,
            command=self._update_sound_settings,
        ).pack(side="left", padx=(0, 5))
        self.sfx_volume_label = ttk.Label(sfx_frame, width=4, anchor="e")
        sfx_slider = ttk.Scale(
            sfx_frame,
            from_=0,
            to=100,
            orient="horizontal",
            variable=self.sfx_volume,
            command=lambda _event: self._update_sound_settings(),
            length=120,
        )
        sfx_slider.pack(side="left")
        self.sfx_volume_label.pack(side="left", padx=(5, 0))
        snapshot_frame.columnconfigure(0, weight=1)
        self._build_hunt_section(right_panel)

    def _build_drop_tab(self, container: ttk.Frame):
        container.columnconfigure(0, weight=1)
        self.drop_tab_container = container
        self.next_enemy_row = 0
        for enemy in DEFAULT_ENEMY_DROPS.keys():
            self._create_enemy_section(enemy)

    def _create_enemy_section(self, enemy: str):
        if enemy in self.enemy_frames:
            return
        frame = ttk.LabelFrame(self.drop_tab_container, text=enemy)
        frame.grid(row=self.next_enemy_row, column=0, sticky="ew", pady=5)
        frame.columnconfigure(0, weight=1)
        rows_container = ttk.Frame(frame)
        rows_container.grid(row=0, column=0, sticky="ew")
        self.enemy_frames[enemy] = rows_container
        self.drop_vars[enemy] = {}
        self.drop_rows[enemy] = {}
        add_button = ttk.Button(
            frame,
            text="+",
            width=3,
            command=lambda e=enemy: self._show_add_drop_dialog(e),
        )
        add_button.grid(row=0, column=1, padx=5, sticky="n")
        self.add_buttons[enemy] = add_button
        self.next_enemy_row += 1

    def _populate_entries(
        self,
        container: ttk.LabelFrame,
        variables: dict,
        category: str,
        clamp: bool = False,
        allow_float: bool = False,
    ):
        for idx, (label, var) in enumerate(variables.items()):
            row = ttk.Frame(container)
            row.grid(row=idx, column=0, sticky="ew", pady=2)
            ttk.Label(row, text=label).pack(side="left")
            entry = ttk.Entry(row, textvariable=var, width=8)
            entry.pack(side="right")
            entry.bind(
                "<FocusOut>",
                lambda _event, key=label, cat=category, clamp_value=clamp, float_ok=allow_float: self._entry_changed(
                    cat, key, clamp_value, float_ok
                ),
            )
            entry.bind(
                "<Return>",
                lambda _event, key=label, cat=category, clamp_value=clamp, float_ok=allow_float: self._entry_changed(
                    cat, key, clamp_value, float_ok
                ),
            )

    def _entry_changed(self, category: str, key: str, clamp: bool, allow_float: bool = False):
        parser = self._parse_float if allow_float else self._parse_int
        value = parser(self._get_var(category, key).get())
        if value is None:
            number_type = "number" if allow_float else "integer"
            messagebox.showerror("Invalid number", f"Please enter a valid {number_type} for {key}.")
            self._refresh_view()
            return
        if clamp:
            value = max(0, min(200, value))
        current_dict = getattr(self.state, category)
        if current_dict.get(key) == value:
            self._refresh_view()
            return
        new_state = self.state.clone()
        getattr(new_state, category)[key] = value
        self._commit_state(new_state)

    def _build_notoriety_display(self, container: ttk.LabelFrame):
        colors = ["#d9534f", "#f0ad4e", "#5cb85c", "#0275d8", "#613d7c"]
        for idx, genre in enumerate(BASE_GENRES):
            column = ttk.Frame(container, padding=5)
            column.grid(row=0, column=idx, sticky="ns")
            ttk.Label(column, text=genre).pack()
            canvas = tk.Canvas(column, width=30, height=120, bg="#f0f0f0", highlightthickness=1, highlightbackground="#ccc")
            canvas.pack(pady=5)
            bar = canvas.create_rectangle(5, 5, 25, 115, fill="#ffffff")
            setattr(self, f"notoriety_canvas_{genre}", (canvas, bar, colors[idx]))
            entry = ttk.Entry(column, textvariable=self.notoriety_vars[genre], width=6, justify="center")
            entry.pack()
            entry.bind(
                "<FocusOut>",
                lambda _event, key=genre: self._entry_changed("notoriety", key, True),
            )
            entry.bind(
                "<Return>",
                lambda _event, key=genre: self._entry_changed("notoriety", key, True),
            )

    def _build_pages_section(self, container: ttk.Frame):
        pages_frame = ttk.LabelFrame(container, text="Current Pages")
        pages_frame.pack(fill="both", expand=True)
        pages_frame.columnconfigure(0, weight=1)
        pages_frame.columnconfigure(1, weight=1)
        pages_list = ttk.Frame(pages_frame)
        pages_list.grid(row=0, column=0, sticky="nw")
        for idx, genre in enumerate(self.genre_page_vars.keys()):
            row = ttk.Frame(pages_list)
            row.grid(row=idx, column=0, sticky="ew")
            label = ttk.Label(row, text=f"{genre} (0%)")
            label.pack(side="left")
            self.page_label_widgets[genre] = label
            ttk.Label(row, textvariable=self.genre_page_vars[genre]).pack(side="right")
        self.pages_pie_canvas = tk.Canvas(pages_frame, width=160, height=160, highlightthickness=0, bg=self.root.cget("bg"))
        self.pages_pie_canvas.grid(row=0, column=1, padx=10)

    def _build_hunt_section(self, container: ttk.Frame):
        hunt_frame = ttk.LabelFrame(container, text="Hunt Simulator")
        hunt_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        hunt_frame.columnconfigure(0, weight=1)
        hunt_frame.columnconfigure(1, weight=1)

        info_frame = ttk.Frame(hunt_frame)
        info_frame.grid(row=0, column=0, sticky="nw", padx=(0, 10))
        ttk.Label(info_frame, text="Chapter Position:").grid(row=0, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.chapter_pos_var).grid(row=0, column=1, sticky="w")
        ttk.Label(info_frame, text="Current Chapter Length:").grid(row=1, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.chapter_length_var).grid(row=1, column=1, sticky="w")
        ttk.Label(info_frame, text="Current Chapter Genre:").grid(row=2, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.chapter_genre_var).grid(row=2, column=1, sticky="w")
        ttk.Label(info_frame, text="Progress:").grid(row=3, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.chapter_progress_var).grid(row=3, column=1, sticky="w")
        ttk.Label(info_frame, text="Total hunts taken:").grid(row=4, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.total_hunts_var).grid(row=4, column=1, sticky="w")
        ttk.Label(info_frame, text="Current run - hunts taken:").grid(row=5, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.run_hunts_var).grid(row=5, column=1, sticky="w")
        ttk.Label(info_frame, text="Mallets spent this run:").grid(row=6, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.run_mallets_var).grid(row=6, column=1, sticky="w")
        ttk.Label(info_frame, text="Total Mallets spent:").grid(row=7, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.total_mallets_var).grid(row=7, column=1, sticky="w")
        ttk.Label(info_frame, text="Total hunts / total Diamonds gain:").grid(row=8, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.hunts_per_diamond_var).grid(row=8, column=1, sticky="w")

        controls_frame = ttk.Frame(hunt_frame)
        controls_frame.grid(row=0, column=1, sticky="ne")
        self.start_random_button = ttk.Button(
            controls_frame, text="Start run (random)", command=self._start_random_run
        )
        self.start_random_button.grid(row=0, column=0, sticky="ew", pady=2)
        self.start_manual_button = ttk.Button(
            controls_frame, text="Start run (manual, cost 30 Mallets)", command=self._start_manual_run
        )
        self.start_manual_button.grid(row=1, column=0, sticky="ew", pady=2)
        self.hunt_t1_button = self._button(
            controls_frame, text="Hunt (T1)", command=lambda: self._perform_hunt("T1"), sound="copy_message"
        )
        self.hunt_t1_button.grid(row=2, column=0, sticky="ew", pady=2)
        self.hunt_t2_button = self._button(
            controls_frame, text="Hunt (T2)", command=lambda: self._perform_hunt("T2"), sound="copy_message"
        )
        self.hunt_t2_button.grid(row=3, column=0, sticky="ew", pady=2)
        self.hunt_t3_button = self._button(
            controls_frame, text="Hunt (T3)", command=lambda: self._perform_hunt("T3"), sound="copy_message"
        )
        self.hunt_t3_button.grid(row=4, column=0, sticky="ew", pady=2)
        self.hunt10_t1_button = self._button(
            controls_frame, text="10-Hunt (T1)", command=lambda: self._batch_hunt("T1"), sound="copy_message"
        )
        self.hunt10_t1_button.grid(row=2, column=1, sticky="ew", pady=2, padx=(5, 0))
        self.hunt10_t2_button = self._button(
            controls_frame, text="10-Hunt (T2)", command=lambda: self._batch_hunt("T2"), sound="copy_message"
        )
        self.hunt10_t2_button.grid(row=3, column=1, sticky="ew", pady=2, padx=(5, 0))
        self.hunt10_t3_button = self._button(
            controls_frame, text="10-Hunt (T3)", command=lambda: self._batch_hunt("T3"), sound="copy_message"
        )
        self.hunt10_t3_button.grid(row=4, column=1, sticky="ew", pady=2, padx=(5, 0))
        self.extend_postscript_button = ttk.Button(
            controls_frame, text="Postscript +3 (cost 30 Mallets)", command=self._extend_postscript
        )
        self.extend_postscript_button.grid(row=5, column=0, sticky="ew", pady=2)

        self.pending_choices_frame = ttk.LabelFrame(hunt_frame, text="Select Next Chapter")
        self.pending_choices_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        reroll_frame = ttk.Frame(self.pending_choices_frame)
        reroll_frame.pack(fill="x", padx=5, pady=(5, 0))
        ttk.Button(
            reroll_frame,
            text="Spend 3 Mallets to reroll",
            command=self._reroll_chapter_choices,
        ).pack(side="right")
        self.pending_choices_container = ttk.Frame(self.pending_choices_frame)
        self.pending_choices_container.pack(fill="x", padx=5, pady=5)
        self.pending_choices_frame.grid_remove()
        log_frame = ttk.LabelFrame(hunt_frame, text="Log")
        log_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=29, state="disabled", wrap="word")
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.tag_configure("info_postscript", foreground="#d9534f")
        self.log_text.tag_configure("info_run_complete", foreground="#5cb85c")
        ttk.Button(log_frame, text="Export Log", command=self._export_log).grid(
            row=1, column=0, columnspan=2, sticky="e", pady=(5, 0)
        )
    def _get_var(self, category: str, key: str) -> tk.StringVar:
        mapping = {
            "resources": self.resource_vars,
            "consumables": self.consumable_vars,
            "notoriety": self.notoriety_vars,
        }
        return mapping[category][key]

    def _parse_int(self, raw: str) -> int | None:
        raw = raw.strip()
        raw = "0" if raw == "" else raw
        try:
            return int(raw)
        except ValueError:
            return None

    def _create_drop_row(self, enemy: str, material: str):
        container = self.enemy_frames[enemy]
        row = ttk.Frame(container)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=material).pack(side="left")
        var = tk.StringVar()
        entry = ttk.Entry(row, textvariable=var, width=10)
        entry.pack(side="right")
        entry.bind(
            "<FocusOut>",
            lambda _event, e=enemy, m=material: self._drop_value_changed(e, m),
        )
        entry.bind(
            "<Return>",
            lambda _event, e=enemy, m=material: self._drop_value_changed(e, m),
        )
        self.drop_vars[enemy][material] = var
        self.drop_rows[enemy][material] = row

    def _sanitize_quantity(self):
        quantity = self._parse_int(self.quantity_var.get())
        if quantity is None or quantity <= 0:
            quantity = 1
        self.quantity_var.set(str(quantity))

    def _craft(self, recipe: dict):
        quantity = self._parse_int(self.quantity_var.get())
        if quantity is None or quantity <= 0:
            messagebox.showerror("Invalid quantity", "Craft quantity must be a positive integer.")
            self.quantity_var.set("1")
            return
        new_state = self.state.clone()
        for key, amount in recipe["costs"].items():
            self._apply_delta(new_state, key, -amount * quantity)
        for key, amount in recipe["outputs"].items():
            self._apply_delta(new_state, key, amount * quantity)
        self._log(f"Crafted {quantity} × {recipe['label']}")
        self._commit_state(new_state)

    def _apply_delta(self, state: GameState, key: str, delta: int):
        if key in state.resources:
            state.resources[key] += delta
            return
        if key in state.consumables:
            state.consumables[key] += delta
            return
        raise KeyError(f"Unknown resource '{key}' in recipe definition.")

    def _apply_enemy_loot(self, state: GameState, enemy: str, multiplier: float = 1.0) -> list[tuple[str, float]]:
        drops = state.enemy_drops.get(enemy) or DEFAULT_ENEMY_DROPS.get(enemy)
        if not drops:
            return []
        results = []
        for material, amount in drops.items():
            value = float(amount)
            if material not in {"Gold", "Diamond"}:
                value *= multiplier
            if material == "Diamond":
                state.total_diamonds_gain += value
            self._apply_loot_amount(state, material, value)
            results.append((material, value))
        return results

    def _apply_loot_amount(self, state: GameState, material: str, amount: float):
        if material in state.resources:
            state.resources[material] = state.resources.get(material, 0) + amount
        elif material in state.consumables:
            state.consumables[material] = state.consumables.get(material, 0) + amount
        else:
            state.resources[material] = state.resources.get(material, 0) + amount

    def _page_gain_for_hunt(self, cheese_rule: dict | None) -> float:
        if cheese_rule:
            return float(cheese_rule.get("page_gain", 0))
        return 1.0

    def _handle_postscript_hunt(self, state: GameState, cheese_rule: dict, multiplier: float = 1.0):
        selected_genre = self._select_genre_by_pages(state)
        if selected_genre is None:
            return None
        if selected_genre == FANTASY_GENRE:
            drops = self._apply_enemy_loot(state, cheese_rule["post_fantasy_enemy"], multiplier)
            for genre in state.notoriety:
                state.notoriety[genre] = max(0, state.notoriety[genre] - 20)
            return selected_genre, cheese_rule["post_fantasy_enemy"], drops
        else:
            drops = self._apply_enemy_loot(state, cheese_rule["post_enemy"], multiplier)
            gain = cheese_rule.get("notoriety_gain", 0)
            self._adjust_notoriety(state, selected_genre, gain)
            return selected_genre, cheese_rule["post_enemy"], drops

    def _select_genre_by_pages(self, state: GameState) -> str | None:
        weights = []
        for genre in BASE_GENRES + [FANTASY_GENRE]:
            pages = max(0, state.genre_pages.get(genre, 0))
            if pages > 0:
                weights.append((genre, pages))
        if not weights:
            return random.choice(BASE_GENRES + [FANTASY_GENRE])
        total = sum(weight for _, weight in weights)
        pick = random.uniform(0, total)
        cumulative = 0.0
        for genre, weight in weights:
            cumulative += weight
            if pick <= cumulative:
                return genre
        return weights[-1][0]

    def _adjust_notoriety(self, state: GameState, selected_genre: str, increase: int):
        current = state.notoriety.get(selected_genre, 0)
        state.notoriety[selected_genre] = max(0, min(200, current + increase))
        for genre in state.notoriety.keys():
            if genre == selected_genre:
                continue
            if state.notoriety[genre] > 1:
                state.notoriety[genre] -= 1

    def _log_hunt(self, display_genre: str, enemy_name: str, cheese_type: str, drops: list[tuple[str, float]]):
        cheese_label = cheese_type if cheese_type else "Unknown"
        drops_text = ", ".join(f"{name} +{self._format_float(amount)}" for name, amount in drops if amount != 0)
        if not drops_text:
            drops_text = "none"
        message = f"[{display_genre}] - Get a [{enemy_name}] with [{cheese_label}]； drops: {drops_text}"
        self._log(message)

    def _log(self, message: str, tag: str | None = None):
        if not self.log_text:
            return
        self.log_text.configure(state="normal")
        if tag:
            self.log_text.insert("end", message + "\n", tag)
        else:
            self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _undo(self):
        state = self.history.undo()
        if state is None:
            messagebox.showinfo("Undo", "No previous snapshot.")
            return
        self.state = state
        self._refresh_view()

    def _redo(self):
        state = self.history.redo()
        if state is None:
            messagebox.showinfo("Redo", "No future snapshot.")
            return
        self.state = state
        self._refresh_view()

    def _commit_state(self, new_state: GameState):
        self.history.commit(new_state)
        self.state = new_state
        self._refresh_view()

    def _refresh_view(self):
        for key, value in self.state.resources.items():
            self.resource_vars[key].set(self._format_float(value))
        for key, value in self.state.consumables.items():
            self.consumable_vars[key].set(self._format_float(value))
        for genre, value in self.state.notoriety.items():
            self.notoriety_vars[genre].set(str(value))
            self._update_notoriety_bar(genre, value)
        self.fantasy_var.set(self._fantasy_text())
        self._update_history_buttons()
        self._refresh_drops()
        self._refresh_hunt_section()

    def _update_history_buttons(self):
        if hasattr(self, "undo_button"):
            self.undo_button.config(state="normal" if self.history.can_undo() else "disabled")
        if hasattr(self, "redo_button"):
            self.redo_button.config(state="normal" if self.history.can_redo() else "disabled")

    def _refresh_drops(self):
        for enemy, drops in self.state.enemy_drops.items():
            self._create_enemy_section(enemy)
            existing_rows = self.drop_rows.setdefault(enemy, {})
            existing_vars = self.drop_vars.setdefault(enemy, {})
            # Remove rows not present anymore
            for material in list(existing_rows.keys()):
                if material not in drops:
                    existing_rows[material].destroy()
                    del existing_rows[material]
                    del existing_vars[material]
            # Ensure rows exist and update values
            for material, amount in drops.items():
                if material not in existing_vars:
                    self._create_drop_row(enemy, material)
                existing_vars[material].set(self._format_float(amount))
        self._update_add_buttons()

    def _update_notoriety_bar(self, genre: str, value: int):
        clamp_value = max(0, min(200, value))
        canvas_info = getattr(self, f"notoriety_canvas_{genre}", None)
        if not canvas_info:
            return
        canvas, bar, color = canvas_info
        height = 110
        fill_height = int((clamp_value / 200) * height)
        y1 = 115 - fill_height
        canvas.coords(bar, 5, y1, 25, 115)
        canvas.itemconfig(bar, fill=color)

    def _update_add_buttons(self):
        for enemy, button in self.add_buttons.items():
            state = "normal" if self._available_drop_types(enemy) else "disabled"
            button.config(state=state)

    def _update_pages_display(self):
        total_pages = sum(self.state.genre_pages.get(g, 0) for g in BASE_GENRES + [FANTASY_GENRE])
        colors = {
            "Romance": "#d9534f",
            "Adventure": "#f0ad4e",
            "Comedy": "#5cb85c",
            "Tragedy": "#0275d8",
            "Suspense": "#613d7c",
            FANTASY_GENRE: "#ffffff",
        }
        for genre in self.genre_page_vars.keys():
            value = self.state.genre_pages.get(genre, 0)
            percent = (value / total_pages * 100) if total_pages > 0 else 0
            label = self.page_label_widgets.get(genre)
            if label:
                label.config(text=f"{genre} ({percent:.0f}%)")
        if self.pages_pie_canvas:
            self.pages_pie_canvas.delete("slice")
            start = 0
            if total_pages == 0:
                self.pages_pie_canvas.create_oval(10, 10, 150, 150, fill="#e0e0e0", outline="#c0c0c0", tags="slice")
            else:
                center_x, center_y = 80, 80
                radius_inner = 50
                for genre in BASE_GENRES + [FANTASY_GENRE]:
                    value = self.state.genre_pages.get(genre, 0)
                    if value <= 0:
                        continue
                    extent = value / total_pages * 360
                    self.pages_pie_canvas.create_arc(
                        10,
                        10,
                        150,
                        150,
                        start=start,
                        extent=extent,
                        fill=colors.get(genre, "#dddddd"),
                        outline="#ffffff",
                        tags="slice",
                    )
                    mid_angle = math.radians(start + extent / 2)
                    label_x = center_x + radius_inner * math.cos(mid_angle)
                    label_y = center_y - radius_inner * math.sin(mid_angle)
                    percent_text = f"{genre[0].upper()} ({(value / total_pages * 100):.0f}%)"
                    self.pages_pie_canvas.create_text(
                        label_x,
                        label_y,
                        text=percent_text,
                        fill="#000000",
                        font=("Arial", 8, "bold"),
                        tags="slice",
                    )
                    start += extent

    def _refresh_hunt_section(self):
        self.total_hunts_var.set(str(self.state.total_hunts))
        self.run_hunts_var.set(str(self.state.current_run_hunts))
        self.run_mallets_var.set(str(self.state.run_mallets_spent))
        self.total_mallets_var.set(str(self.state.total_mallets_spent))
        diamonds = self.state.total_diamonds_gain
        if diamonds > 0:
            ratio = self.state.total_hunts / diamonds if diamonds else 0
            self.hunts_per_diamond_var.set(f"{ratio:.2f}")
        else:
            self.hunts_per_diamond_var.set("N/A")
        self.chapter_pos_var.set(str(self.state.chapter_position))
        if self.state.chapter_position == 7:
            length_display = str(self.state.postscript_length)
            genre_display = "—"
            target_length = self.state.postscript_length
        elif self.state.chapter_position == 0:
            length_display = "—"
            genre_display = "—"
            target_length = 0
        else:
            if self.state.current_chapter_length:
                length_display = str(self.state.current_chapter_length)
                target_length = self.state.current_chapter_length
            else:
                length_display = "Awaiting choice"
                target_length = 0
            genre_display = self.state.current_chapter_genre or "Selecting"
        self.chapter_length_var.set(length_display)
        self.chapter_genre_var.set(genre_display)
        progress_value = self.state.current_chapter_progress
        self.chapter_progress_var.set(f"{progress_value} / {target_length}")
        for genre, var in self.genre_page_vars.items():
            var.set(str(self.state.genre_pages.get(genre, 0)))
        self._update_pages_display()

        if self.start_random_button is not None:
            can_start = self.state.chapter_position == 0
            self.start_random_button.config(state="normal" if can_start else "disabled")
        if self.start_manual_button is not None:
            can_manual = self.state.chapter_position == 0 and self.state.resources.get("mallets", 0) >= 30
            self.start_manual_button.config(state="normal" if can_manual else "disabled")
        if self.extend_postscript_button is not None:
            extend_state = (
                self.state.chapter_position == 7
                and self.state.resources.get("mallets", 0) >= 30
                and not self.state.postscript_extended
            )
            self.extend_postscript_button.config(state="normal" if extend_state else "disabled")
        selection_blocked = (
            self.state.pending_chapter_choices
            and not self.state.pending_choices_locked
            and self.state.chapter_position <= TOTAL_CHAPTERS
        )
        cheese_allowed = (
            (1 <= self.state.chapter_position <= TOTAL_CHAPTERS or self.state.chapter_position == 7)
            and not selection_blocked
            and (target_length or 0) > 0
        )
        for cheese_type, button in [
            ("T1", getattr(self, "hunt_t1_button", None)),
            ("T2", getattr(self, "hunt_t2_button", None)),
            ("T3", getattr(self, "hunt_t3_button", None)),
        ]:
            if button is None:
                continue
            rule = CHEESE_HUNT_RULES[cheese_type]
            available = self.state.resources.get(rule["resource"], 0)
            button_state = "normal" if (cheese_allowed and available > 0) else "disabled"
            button.config(state=button_state)
        batch_buttons = [
            ("T1", getattr(self, "hunt10_t1_button", None)),
            ("T2", getattr(self, "hunt10_t2_button", None)),
            ("T3", getattr(self, "hunt10_t3_button", None)),
        ]
        for cheese_type, button in batch_buttons:
            if button is None:
                continue
            rule = CHEESE_HUNT_RULES[cheese_type]
            available = self.state.resources.get(rule["resource"], 0)
            remaining = (target_length or 0) - self.state.current_chapter_progress
            enabled = cheese_allowed and available >= 10 and remaining >= 10
            button.config(state="normal" if enabled else "disabled")

        if self.pending_choices_frame is not None and self.pending_choices_container is not None:
            for child in self.pending_choices_container.winfo_children():
                child.destroy()
            if self.state.pending_chapter_choices:
                self.pending_choices_frame.grid()
                locked = self.state.pending_choices_locked
                for choice in self.state.pending_chapter_choices:
                    choice_text = f"Length {choice['length']} - Genre {choice['genre']}"
                    ttk.Button(
                        self.pending_choices_container,
                        text=choice_text,
                        command=lambda c=choice: self._choose_next_chapter(c),
                        state="disabled" if locked else "normal",
                    ).pack(fill="x", pady=2)
                if locked:
                    ttk.Label(
                        self.pending_choices_container,
                        text="Complete the current chapter before selecting.",
                        foreground="#666",
                    ).pack(fill="x", pady=(4, 0))
            else:
                self.pending_choices_frame.grid_remove()

    def _fantasy_text(self) -> str:
        unlocked = self.state.fantasy_unlocked()
        status = "available" if unlocked else "locked"
        explanation = (
            "All five base genres have notoriety > 80."
            if unlocked
            else "Needs every base genre notoriety to exceed 80."
        )
        return f"Fantasy genre is {status}. {explanation}"

    def _save_snapshot(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON file", "*.json"), ("All files", "*.*")],
            title="Save Snapshot",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.state.to_dict(), fh, indent=2)
            messagebox.showinfo("Snapshot saved", f"Snapshot saved to {path}.")
        except OSError as exc:
            messagebox.showerror("Save failed", f"Failed to save snapshot:\n{exc}")

    def _load_snapshot(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON file", "*.json"), ("All files", "*.*")],
            title="Load Snapshot",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror("Load failed", f"Failed to load snapshot:\n{exc}")
            return
        new_state = GameState.from_dict(raw)
        self._commit_state(new_state)

    def _parse_float(self, raw: str) -> float | None:
        raw = raw.strip()
        raw = "0" if raw == "" else raw
        try:
            return float(raw)
        except ValueError:
            return None

    def _format_float(self, value: float) -> str:
        if abs(value - int(value)) < 1e-9:
            return str(int(value))
        text = f"{value:.4f}".rstrip("0").rstrip(".")
        return text if text else "0"

    def _drop_value_changed(self, enemy: str, material: str):
        raw = self.drop_vars[enemy][material].get()
        value = self._parse_float(raw)
        if value is None:
            messagebox.showerror("Invalid number", f"Please enter a number for {enemy} - {material}.")
            self._refresh_view()
            return
        current_value = self.state.enemy_drops.get(enemy, {}).get(material, 0.0)
        if current_value == value:
            self._refresh_view()
            return
        new_state = self.state.clone()
        new_state.enemy_drops.setdefault(enemy, {})[material] = value
        self._commit_state(new_state)

    def _available_drop_types(self, enemy: str) -> list[str]:
        used = set(self.state.enemy_drops.get(enemy, {}).keys())
        return [item for item in ALL_MATERIAL_TYPES if item not in used]

    def _show_add_drop_dialog(self, enemy: str):
        options = self._available_drop_types(enemy)
        if not options:
            messagebox.showinfo("No options", "All material types already exist for this enemy.")
            return
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Add drop - {enemy}")
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Select drop type:").pack(padx=10, pady=(10, 0))
        selection = tk.StringVar(value=options[0])
        combo = ttk.Combobox(dialog, textvariable=selection, values=options, state="readonly")
        combo.pack(padx=10, pady=5)
        combo.focus_set()

        def confirm():
            dialog.grab_release()
            dialog.destroy()
            self._add_drop_to_enemy(enemy, selection.get())

        ttk.Button(dialog, text="Add", command=confirm).pack(pady=(0, 10))
        dialog.bind("<Return>", lambda _event: confirm())

    def _add_drop_to_enemy(self, enemy: str, material: str):
        new_state = self.state.clone()
        drops = new_state.enemy_drops.setdefault(enemy, {})
        if material in drops:
            return
        drops[material] = 0.0
        self._commit_state(new_state)

    def _start_random_run(self):
        if not self._ensure_can_start_run():
            return
        fantasy_available = self.state.fantasy_unlocked()
        available_genres = self._genres_for_selection(fantasy_available)
        if not available_genres:
            messagebox.showerror("Cannot start", "No genres are available right now.")
            return
        length = random.choice(CHAPTER_LENGTHS)
        genre = random.choice(available_genres)
        new_state = self.state.clone()
        self._initialize_new_run_state(new_state, fantasy_available)
        self._begin_chapter(new_state, 1, length, genre)
        self._log(f"Run started with random selection: length {length}, genre {genre}")
        self._commit_state(new_state)

    def _start_manual_run(self):
        if not self._ensure_can_start_run():
            return
        if self.state.resources.get("mallets", 0) < 30:
            self._play_sound("dialog_open")
            messagebox.showerror("Not enough Mallets", "You need at least 30 Mallets to pick manually.")
            return
        fantasy_available = self.state.fantasy_unlocked()
        available_genres = self._genres_for_selection(fantasy_available)
        if not available_genres:
            messagebox.showerror("Cannot start", "No genres are available right now.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Manual Chapter Selection")
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Choose chapter length:").pack(padx=10, pady=(10, 0))
        length_var = tk.StringVar(value=str(CHAPTER_LENGTHS[0]))
        length_combo = ttk.Combobox(
            dialog, textvariable=length_var, values=[str(length) for length in CHAPTER_LENGTHS], state="readonly"
        )
        length_combo.pack(padx=10, pady=5)
        ttk.Label(dialog, text="Choose chapter genre:").pack(padx=10, pady=(10, 0))
        genre_var = tk.StringVar(value=available_genres[0])
        genre_combo = ttk.Combobox(dialog, textvariable=genre_var, values=available_genres, state="readonly")
        genre_combo.pack(padx=10, pady=5)
        length_combo.focus_set()

        def confirm():
            dialog.grab_release()
            dialog.destroy()
            try:
                chosen_length = int(length_var.get())
            except ValueError:
                messagebox.showerror("Invalid length", "The selected length is invalid.")
                return
            chosen_genre = genre_var.get()
            self._confirm_manual_start(chosen_length, chosen_genre)

        ttk.Button(dialog, text="Confirm", command=confirm).pack(pady=(0, 10))
        dialog.bind("<Return>", lambda _event: confirm())

    def _confirm_manual_start(self, length: int, genre: str):
        new_state = self.state.clone()
        if new_state.resources.get("mallets", 0) < 30:
            messagebox.showerror("Not enough Mallets", "You need at least 30 Mallets to pick manually.")
            return
        new_state.resources["mallets"] -= 30
        fantasy_available = new_state.fantasy_unlocked()
        if genre == FANTASY_GENRE and not fantasy_available:
            self._play_sound("dialog_open")
            messagebox.showerror("Fantasy locked", "Fantasy is not unlocked for this run.")
            return
        self._initialize_new_run_state(new_state, fantasy_available)
        self._record_mallet_spend(new_state, 30)
        self._begin_chapter(new_state, 1, length, genre)
        self._log(f"Run started manually: length {length}, genre {genre}")
        self._commit_state(new_state)

    def _ensure_can_start_run(self) -> bool:
        if self.state.chapter_position != 0:
            messagebox.showinfo("Run in progress", "Finish the current run before starting a new one.")
            return False
        return True

    def _initialize_new_run_state(self, state: GameState, fantasy_available: bool):
        state.genre_pages = _default_genre_pages()
        state.current_run_hunts = 0
        state.chapter_position = 0
        state.current_chapter_length = None
        state.current_chapter_genre = None
        state.current_chapter_progress = 0
        state.postscript_length = 10
        state.pending_chapter_choices = []
        state.run_fantasy_available = fantasy_available
        state.postscript_extended = False
        state.run_mallets_spent = 0
        state.pending_choices_locked = False

    def _begin_chapter(self, state: GameState, chapter_number: int, length: int, genre: str):
        state.chapter_position = chapter_number
        state.current_chapter_length = length
        state.current_chapter_genre = genre
        state.current_chapter_progress = 0
        if chapter_number <= TOTAL_CHAPTERS - 1:
            state.pending_chapter_choices = self._generate_next_chapter_choices(state)
            state.pending_choices_locked = True
        else:
            state.pending_chapter_choices = []
            state.pending_choices_locked = False
        if chapter_number == 7:
            self._log(f"Entered Postscript with length {state.postscript_length}")
        else:
            self._log(f"Entered Chapter {chapter_number}: length {length}, genre {genre}")

    def _genres_for_selection(self, fantasy_available: bool | None = None) -> list[str]:
        if fantasy_available is None:
            fantasy_available = self.state.run_fantasy_available
        genres = list(BASE_GENRES)
        if fantasy_available:
            genres.append(FANTASY_GENRE)
        return genres

    def _perform_hunt(self, cheese_type: str | None = None):
        if self.state.chapter_position == 0:
            messagebox.showinfo("Not started", "Enter the first chapter before hunting.")
            return
        if (
            self.state.pending_chapter_choices
            and not self.state.pending_choices_locked
            and self.state.chapter_position <= TOTAL_CHAPTERS
        ):
            messagebox.showinfo("Select chapter", "Choose the next chapter before continuing.")
            return
        if cheese_type is None:
            messagebox.showinfo("Select cheese", "Choose a cheese to hunt with.")
            return
        if not (1 <= self.state.chapter_position <= TOTAL_CHAPTERS or self.state.chapter_position == 7):
            messagebox.showinfo("Cannot use cheese", "You cannot hunt with cheese in this phase.")
            return
        target_length = (
            self.state.postscript_length if self.state.chapter_position == 7 else self.state.current_chapter_length
        )
        if not target_length:
            messagebox.showerror("Invalid chapter", "There is no active chapter to progress.")
            return
        cheese_rule = CHEESE_HUNT_RULES.get(cheese_type) if cheese_type else None
        if cheese_rule:
            available = self.state.resources.get(cheese_rule["resource"], 0)
            if available <= 0:
                messagebox.showerror("Not enough cheese", f"You need at least 1 {cheese_rule['resource']}.")
                return
        new_state = self.state.clone()
        if cheese_rule:
            new_state.resources[cheese_rule["resource"]] = new_state.resources.get(cheese_rule["resource"], 0) - 1
        new_state.current_chapter_progress += 1
        new_state.total_hunts += 1
        new_state.current_run_hunts += 1
        if cheese_rule:
            log_genre = None
            log_enemy = None
            log_drops = []
            loot_multiplier = self._cc_multiplier() if self.cc_enabled.get() else 1.0
            if self.cc_enabled.get():
                new_state.consumables["CC"] = new_state.consumables.get("CC", 0) - 1
            if new_state.chapter_position == 7:
                result = self._handle_postscript_hunt(new_state, cheese_rule, loot_multiplier)
                if result:
                    log_genre, log_enemy, log_drops = result
            elif new_state.current_chapter_genre:
                gain = self._page_gain_for_hunt(cheese_rule)
                current_pages = new_state.genre_pages.get(new_state.current_chapter_genre, 0)
                new_state.genre_pages[new_state.current_chapter_genre] = current_pages + gain
                log_genre = new_state.current_chapter_genre
                log_enemy = cheese_rule["chapter_enemy"]
                log_drops = self._apply_enemy_loot(new_state, log_enemy, loot_multiplier)
            if log_genre and log_enemy is not None:
                self._log_hunt(log_genre, log_enemy, cheese_type, log_drops)
        if new_state.current_chapter_progress >= target_length:
            if new_state.chapter_position == 7:
                self._finish_postscript(new_state)
            else:
                self._handle_chapter_completion(new_state)
        self._commit_state(new_state)

    def _handle_chapter_completion(self, state: GameState):
        if state.chapter_position >= TOTAL_CHAPTERS:
            self._enter_postscript(state)
            return
        state.current_chapter_length = None
        state.current_chapter_genre = None
        state.current_chapter_progress = 0
        state.pending_choices_locked = False
        if not state.pending_chapter_choices:
            state.pending_chapter_choices = self._generate_next_chapter_choices(state)
        self._log_chapter_choices("Available next chapters", state.pending_chapter_choices)

    def _generate_next_chapter_choices(self, state: GameState) -> list[dict]:
        genres = self._genres_for_selection(state.run_fantasy_available)
        choices = []
        available_genres = genres.copy()
        random.shuffle(available_genres)
        for length in CHAPTER_LENGTHS:
            if not available_genres:
                available_genres = genres.copy()
                random.shuffle(available_genres)
            genre = available_genres.pop()
            choices.append({"length": length, "genre": genre})
        return choices

    def _choose_next_chapter(self, choice: dict):
        if not choice or not choice.get("length"):
            return
        new_state = self.state.clone()
        if not new_state.pending_chapter_choices:
            return
        if new_state.pending_choices_locked:
            messagebox.showinfo("Chapter in progress", "Finish the current chapter before selecting the next one.")
            return
        next_chapter_number = min(new_state.chapter_position + 1, TOTAL_CHAPTERS)
        # If chapter_position was 0 (should not happen), start at 1
        if next_chapter_number <= new_state.chapter_position:
            next_chapter_number = new_state.chapter_position + 1
        self._begin_chapter(new_state, next_chapter_number, int(choice["length"]), choice["genre"])
        self._log(f"Selected next chapter: length {choice['length']}, genre {choice['genre']}")
        self._commit_state(new_state)

    def _enter_postscript(self, state: GameState):
        state.chapter_position = 7
        state.current_chapter_length = None
        state.current_chapter_genre = None
        state.current_chapter_progress = 0
        state.pending_chapter_choices = []
        state.postscript_extended = False
        state.pending_choices_locked = False
        self._play_sound("completion")
        self._log("Postscript started.", tag="info_postscript")

    def _finish_postscript(self, state: GameState):
        state.chapter_position = 0
        state.current_chapter_length = None
        state.current_chapter_genre = None
        state.current_chapter_progress = 0
        state.postscript_length = 10
        state.pending_chapter_choices = []
        state.run_fantasy_available = False
        state.current_run_hunts = 0
        state.genre_pages = _default_genre_pages()
        state.run_mallets_spent = 0
        self._log("Run completed. Returned to start.", tag="info_run_complete")

    def _extend_postscript(self):
        if self.state.chapter_position != 7:
            messagebox.showinfo("Not in Postscript", "You can only extend during Postscript.")
            return
        if self.state.resources.get("mallets", 0) < 30:
            self._play_sound("dialog_open")
            messagebox.showerror("Not enough Mallets", "You need at least 30 Mallets to extend Postscript.")
            return
        new_state = self.state.clone()
        if new_state.resources.get("mallets", 0) < 30:
            self._play_sound("dialog_open")
            messagebox.showerror("Not enough Mallets", "You need at least 30 Mallets to extend Postscript.")
            return
        new_state.resources["mallets"] -= 30
        new_state.postscript_length += 3
        new_state.postscript_extended = True
        self._record_mallet_spend(new_state, 30)
        self._log("Postscript extended by +3 length (cost 30 Mallets).")
        self._commit_state(new_state)

    def _reroll_chapter_choices(self):
        if not self.state.pending_chapter_choices:
            messagebox.showinfo("Nothing to reroll", "There are no pending chapters to reroll.")
            return
        if self.state.resources.get("mallets", 0) < 3:
            self._play_sound("dialog_open")
            messagebox.showerror("Not enough Mallets", "You need at least 3 Mallets to reroll.")
            return
        new_state = self.state.clone()
        if new_state.resources.get("mallets", 0) < 3:
            self._play_sound("dialog_open")
            messagebox.showerror("Not enough Mallets", "You need at least 3 Mallets to reroll.")
            return
        new_state.resources["mallets"] -= 3
        new_state.pending_chapter_choices = self._generate_next_chapter_choices(new_state)
        self._record_mallet_spend(new_state, 3)
        self._log_chapter_choices("Rerolled chapter options", new_state.pending_chapter_choices)
        self._commit_state(new_state)

    def _log_chapter_choices(self, prefix: str, choices: list[dict]):
        formatted = ", ".join(f"{item['length']}-{item['genre']}" for item in choices)
        self._log(f"{prefix}: {formatted}")

    def _batch_hunt(self, cheese_type: str):
        cheese_rule = CHEESE_HUNT_RULES.get(cheese_type)
        if not cheese_rule:
            return
        available = self.state.resources.get(cheese_rule["resource"], 0)
        if available < 10:
            messagebox.showerror("Not enough cheese", f"You need at least 10 {cheese_rule['resource']}.")
            return
        target_length = (
            self.state.postscript_length if self.state.chapter_position == 7 else self.state.current_chapter_length
        )
        remaining = (target_length or 0) - self.state.current_chapter_progress
        if remaining < 10:
            messagebox.showinfo("Not enough progress", "Less than 10 hunts remain in this chapter.")
            return
        for _ in range(10):
            self._perform_hunt(cheese_type)

    def _record_mallet_spend(self, state: GameState, amount: int):
        state.run_mallets_spent += amount
        state.total_mallets_spent += amount
        self._play_sound("button_click")

    def _update_sound_settings(self):
        volume = max(0.0, min(100.0, float(self.sfx_volume.get())))
        self.sfx_volume.set(volume)
        if hasattr(self, "sfx_volume_label"):
            self.sfx_volume_label.config(text=f"{int(volume)}%")
        enabled = bool(self.sfx_enabled.get())
        audio_manager.configure(enabled, volume / 100.0)

    def _play_sound(self, cue: str):
        if not self.sfx_enabled.get():
            return
        audio_manager.play(cue)

    def _button(self, parent: tk.Widget, *, text: str, command, sound: str | None = None, **kwargs) -> ttk.Button:
        def wrapped():
            if sound:
                self._play_sound(sound)
            command()

        return ttk.Button(parent, text=text, command=wrapped, **kwargs)

    def _export_log(self):
        if not self.log_text:
            return
        content = self.log_text.get("1.0", "end-1c")
        path = filedialog.asksaveasfilename(
            title="Export Log",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            messagebox.showinfo("Export Log", f"Log exported to {path}")
        except OSError as exc:
            messagebox.showerror("Export Log", f"Failed to export log:\n{exc}")

    def _cc_multiplier(self) -> float:
        return 2.0


def main():
    root = tk.Tk()
    SimulatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
