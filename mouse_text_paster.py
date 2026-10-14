"""Pegador de textos mediante botones del mouse.

Requisitos:
    pip install -r requirements.txt

La aplicación usa pynput para detectar los botones del mouse globalmente y
pyperclip para colocar el texto en el portapapeles antes de enviar Ctrl+V.
"""

from __future__ import annotations

import json
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Dict, Optional

import pyperclip
from pynput import keyboard, mouse


APP_TITLE = "Pegador de textos - botones del mouse"


def config_path() -> Path:
    """Ubica la configuración junto al script o junto al .exe generado."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().with_name("mouse_text_paster_config.json")
    return Path(__file__).resolve().with_name("mouse_text_paster_config.json")


CONFIG_FILE = config_path()


def available_mouse_buttons() -> Dict[str, mouse.Button]:
    """Devuelve los botones que se pueden asignar desde la interfaz."""

    buttons: Dict[str, mouse.Button] = {
        "X1 (lateral atrás)": mouse.Button.x1,
        "X2 (lateral adelante)": mouse.Button.x2,
        "Botón central": mouse.Button.middle,
        "Botón derecho": mouse.Button.right,
        "Botón izquierdo": mouse.Button.left,
    }
    return buttons


MOUSE_BUTTONS = available_mouse_buttons()
MOUSE_BUTTON_NAMES = list(MOUSE_BUTTONS.keys())
BUTTON_NAME_BY_OBJECT = {value: key for key, value in MOUSE_BUTTONS.items()}


class BindingDialog(tk.Toplevel):
    """Ventana para crear o editar una asignación."""

    def __init__(self, parent: tk.Misc, binding: Optional[dict] = None):
        super().__init__(parent)
        self.result: Optional[dict] = None
        self.title("Editar texto" if binding else "Nuevo texto")
        self.resizable(True, True)
        self.minsize(540, 360)
        self.transient(parent)
        self.grab_set()

        binding = binding or {
            "name": "Nuevo texto",
            "text": "",
            "button": MOUSE_BUTTON_NAMES[0],
            "enabled": True,
        }

        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)

        ttk.Label(frame, text="Nombre:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        self.name_var = tk.StringVar(value=binding.get("name", "Nuevo texto"))
        ttk.Entry(frame, textvariable=self.name_var).grid(row=0, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="Botón:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        self.button_var = tk.StringVar(value=binding.get("button", MOUSE_BUTTON_NAMES[0]))
        ttk.Combobox(
            frame,
            textvariable=self.button_var,
            values=MOUSE_BUTTON_NAMES,
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="Texto a pegar:").grid(row=2, column=0, sticky="nw", padx=(0, 10), pady=5)
        text_frame = ttk.Frame(frame)
        text_frame.grid(row=2, column=1, sticky="nsew", pady=5)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        self.text_widget = tk.Text(text_frame, wrap="word", undo=True, height=10)
        self.text_widget.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.text_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        self.text_widget.insert("1.0", binding.get("text", ""))

        self.enabled_var = tk.BooleanVar(value=binding.get("enabled", True))
        ttk.Checkbutton(frame, text="Asignación activa", variable=self.enabled_var).grid(
            row=3, column=1, sticky="w", pady=(4, 12)
        )

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Guardar", command=self._save).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.name_var.set(binding.get("name", "Nuevo texto"))
        self.text_widget.focus_set()

    def _save(self) -> None:
        name = self.name_var.get().strip()
        text = self.text_widget.get("1.0", "end-1c")
        button = self.button_var.get().strip()

        if not name:
            messagebox.showwarning("Falta el nombre", "Escribe un nombre para esta asignación.", parent=self)
            return
        if not text:
            messagebox.showwarning("Falta el texto", "Escribe el texto que se pegará.", parent=self)
            return
        if button not in MOUSE_BUTTONS:
            messagebox.showwarning("Botón inválido", "Selecciona un botón del mouse.", parent=self)
            return

        self.result = {
            "name": name,
            "text": text,
            "button": button,
            "enabled": self.enabled_var.get(),
        }
        self.destroy()


class MouseTextPaster(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("860x520")
        self.minsize(700, 420)

        self.bindings = []
        self.listener: Optional[mouse.Listener] = None
        self.listener_active = False
        self.state_lock = threading.Lock()
        self.paste_lock = threading.Lock()
        self.restore_clipboard = False
        self.restore_clipboard_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Iniciando escucha...")

        self._build_menu()
        self._build_ui()
        self._load_config()
        self._start_listener()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_menu(self) -> None:
        menu = tk.Menu(self)

        config_menu = tk.Menu(menu, tearoff=False)
        config_menu.add_command(label="Nuevo texto", command=self._new_binding)
        config_menu.add_command(label="Guardar ahora", command=self._save_config)
        config_menu.add_separator()
        config_menu.add_command(label="Salir", command=self._close)
        menu.add_cascade(label="Configuración", menu=config_menu)

        listener_menu = tk.Menu(menu, tearoff=False)
        listener_menu.add_command(label="Activar escucha", command=self._start_listener)
        listener_menu.add_command(label="Pausar escucha", command=self._stop_listener)
        menu.add_cascade(label="Escucha", menu=listener_menu)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="Cómo usarlo", command=self._show_help)
        menu.add_cascade(label="Ayuda", menu=help_menu)
        self.config(menu=menu)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)
        root.rowconfigure(2, weight=1)
        root.columnconfigure(0, weight=1)

        ttk.Label(root, text="Textos rápidos", font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            root,
            text="Pulsa un botón lateral del mouse en cualquier aplicación para pegar el texto asignado.",
        ).grid(row=1, column=0, sticky="w", pady=(2, 12))

        table_frame = ttk.Frame(root)
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        columns = ("name", "button", "preview", "enabled")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("name", text="Nombre")
        self.tree.heading("button", text="Botón asignado")
        self.tree.heading("preview", text="Vista previa del texto")
        self.tree.heading("enabled", text="Estado")
        self.tree.column("name", width=170, anchor="w")
        self.tree.column("button", width=190, anchor="w")
        self.tree.column("preview", width=360, anchor="w")
        self.tree.column("enabled", width=90, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", lambda _event: self._edit_selected())
        tree_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        tree_scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scrollbar.set)

        actions = ttk.Frame(root)
        actions.grid(row=3, column=0, sticky="ew", pady=(12, 8))
        ttk.Button(actions, text="Nuevo", command=self._new_binding).pack(side="left")
        ttk.Button(actions, text="Editar", command=self._edit_selected).pack(side="left", padx=6)
        ttk.Button(actions, text="Eliminar", command=self._delete_selected).pack(side="left")
        ttk.Button(actions, text="Activar escucha", command=self._start_listener).pack(side="right")
        ttk.Button(actions, text="Pausar escucha", command=self._stop_listener).pack(side="right", padx=6)

        options = ttk.Frame(root)
        options.grid(row=4, column=0, sticky="ew")
        ttk.Checkbutton(
            options,
            text="Restaurar el portapapeles después de pegar",
            variable=self.restore_clipboard_var,
            command=self._update_restore_clipboard,
        ).pack(side="left")
        ttk.Label(options, textvariable=self.status_var).pack(side="right")

    def _load_config(self) -> None:
        if not CONFIG_FILE.exists():
            self._refresh_tree()
            return
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            loaded = data.get("bindings", [])
            if isinstance(loaded, list):
                self.bindings = [
                    item
                    for item in loaded
                    if isinstance(item, dict)
                    and item.get("name")
                    and item.get("text")
                    and item.get("button") in MOUSE_BUTTONS
                ]
            self.restore_clipboard_var.set(bool(data.get("restore_clipboard", False)))
            self.restore_clipboard = self.restore_clipboard_var.get()
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            messagebox.showwarning(
                "No se pudo cargar la configuración",
                f"Se iniciará con una configuración vacía.\n\nDetalle: {exc}",
                parent=self,
            )
        self._refresh_tree()

    def _save_config(self) -> None:
        data = {
            "bindings": self.bindings,
            "restore_clipboard": self.restore_clipboard_var.get(),
        }
        try:
            CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self.status_var.set("Configuración guardada")
        except OSError as exc:
            messagebox.showerror("No se pudo guardar", str(exc), parent=self)

    def _update_restore_clipboard(self) -> None:
        self.restore_clipboard = self.restore_clipboard_var.get()
        self._save_config()

    def _refresh_tree(self) -> None:
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)
        for index, binding in enumerate(self.bindings):
            preview = " ".join(str(binding["text"]).split())
            if len(preview) > 70:
                preview = preview[:67] + "..."
            state = "Activa" if binding.get("enabled", True) else "Pausada"
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(binding["name"], binding["button"], preview, state),
            )

    def _selected_index(self) -> Optional[int]:
        selection = self.tree.selection()
        if not selection:
            return None
        return int(selection[0])

    def _new_binding(self) -> None:
        dialog = BindingDialog(self)
        self.wait_window(dialog)
        if dialog.result is not None:
            self._add_or_update_binding(dialog.result)

    def _edit_selected(self) -> None:
        index = self._selected_index()
        if index is None:
            messagebox.showinfo("Selecciona un texto", "Selecciona una fila para editarla.", parent=self)
            return
        dialog = BindingDialog(self, self.bindings[index])
        self.wait_window(dialog)
        if dialog.result is not None:
            self._add_or_update_binding(dialog.result, index)

    def _add_or_update_binding(self, binding: dict, editing_index: Optional[int] = None) -> None:
        duplicate_index = next(
            (i for i, item in enumerate(self.bindings) if item.get("button") == binding["button"] and i != editing_index),
            None,
        )
        if duplicate_index is not None:
            duplicate = self.bindings[duplicate_index]["name"]
            replace = messagebox.askyesno(
                "Botón ya asignado",
                f"El botón ya está asignado a «{duplicate}». ¿Quieres reemplazar esa asignación?",
                parent=self,
            )
            if not replace:
                return
            del self.bindings[duplicate_index]
            if editing_index is not None and duplicate_index < editing_index:
                editing_index -= 1

        if editing_index is None:
            with self.state_lock:
                self.bindings.append(binding)
        else:
            with self.state_lock:
                self.bindings[editing_index] = binding
        self._refresh_tree()
        self._save_config()

    def _delete_selected(self) -> None:
        index = self._selected_index()
        if index is None:
            messagebox.showinfo("Selecciona un texto", "Selecciona una fila para eliminarla.", parent=self)
            return
        name = self.bindings[index]["name"]
        if messagebox.askyesno("Eliminar texto", f"¿Eliminar «{name}»?", parent=self):
            with self.state_lock:
                del self.bindings[index]
            self._refresh_tree()
            self._save_config()

    def _start_listener(self) -> None:
        if self.listener_active:
            self.status_var.set("Escucha activa")
            return
        try:
            self.listener = mouse.Listener(on_click=self._on_mouse_click)
            self.listener.start()
            self.listener_active = True
            self.status_var.set("Escucha activa")
        except Exception as exc:
            self.listener = None
            self.listener_active = False
            self.status_var.set("No se pudo iniciar la escucha")
            messagebox.showerror(
                "Error al escuchar el mouse",
                f"No se pudo iniciar la detección global de botones.\n\nDetalle: {exc}",
                parent=self,
            )

    def _stop_listener(self) -> None:
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
        self.listener_active = False
        self.status_var.set("Escucha pausada")

    def _on_mouse_click(self, _x: int, _y: int, button: mouse.Button, pressed: bool) -> None:
        if not pressed or not self.listener_active:
            return
        button_name = BUTTON_NAME_BY_OBJECT.get(button)
        if button_name is None:
            return

        with self.state_lock:
            binding = next(
                (item.copy() for item in self.bindings if item.get("button") == button_name and item.get("enabled", True)),
                None,
            )
        if binding is not None:
            self._paste_text(binding["text"])

    def _paste_text(self, text: str) -> None:
        # Evita que dos pulsaciones simultáneas mezclen sus contenidos.
        with self.paste_lock:
            old_clipboard = None
            if self.restore_clipboard:
                try:
                    old_clipboard = pyperclip.paste()
                except pyperclip.PyperclipException:
                    old_clipboard = None

            try:
                pyperclip.copy(text)
                controller = keyboard.Controller()
                with controller.pressed(keyboard.Key.ctrl):
                    controller.press("v")
                if old_clipboard is not None:
                    # Se espera un instante para que la aplicación destino procese Ctrl+V.
                    timer = threading.Timer(0.35, self._restore_clipboard, args=(old_clipboard,))
                    timer.daemon = True
                    timer.start()
            except pyperclip.PyperclipException:
                self.after(0, lambda: self.status_var.set("No se pudo acceder al portapapeles"))
            except Exception:
                self.after(0, lambda: self.status_var.set("No se pudo pegar el texto"))

    @staticmethod
    def _restore_clipboard(text: str) -> None:
        try:
            pyperclip.copy(text)
        except pyperclip.PyperclipException:
            pass

    def _show_help(self) -> None:
        messagebox.showinfo(
            "Cómo usarlo",
            "1. Pulsa «Nuevo» y escribe un texto.\n"
            "2. Selecciona X1 o X2 (los botones laterales del mouse).\n"
            "3. Deja «Escucha activa».\n"
            "4. Coloca el cursor en cualquier campo de texto y pulsa el botón asignado.\n\n"
            "La configuración se guarda automáticamente. También puedes pausar la escucha desde el menú «Escucha».",
            parent=self,
        )

    def _close(self) -> None:
        self._save_config()
        self._stop_listener()
        self.destroy()


if __name__ == "__main__":
    app = MouseTextPaster()
    app.mainloop()
