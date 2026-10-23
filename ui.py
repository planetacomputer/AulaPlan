import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from model import AulaPlanModel
from storage import AulaPlanStorage


class AulaPlanGUI(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("AulaPlan — Distribució de la Classe")
        self.geometry("1350x800")

        self.model = AulaPlanModel()

        self.drag_data = {"source": None, "student": None}
        self.drag_label = None
        self.highlighted_student = None
        self._highlight_timer = None

        self._build_ui()

        default_file = "config_default.json"
        if AulaPlanStorage.load_default_json(default_file, self.model):
            self.spin_rows.set(self.model.rows)
            self.spin_cols.set(self.model.cols)
            self.aisle_var.set(self.model.vertical_aisle_after > 0)
            self.refresh_ui()

    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(toolbar, text="↩ Desfer", command=self.undo).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(toolbar, text="↪ Refer", command=self.redo).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=5
        )

        ttk.Label(toolbar, text="Files:").pack(side=tk.LEFT, padx=2)
        self.spin_rows = ttk.Spinbox(
            toolbar, from_=1, to=10, width=3, command=self.update_grid_config
        )
        self.spin_rows.set(self.model.rows)
        self.spin_rows.pack(side=tk.LEFT, padx=2)

        ttk.Label(toolbar, text="Cols:").pack(side=tk.LEFT, padx=2)
        self.spin_cols = ttk.Spinbox(
            toolbar, from_=1, to=10, width=3, command=self.update_grid_config
        )
        self.spin_cols.set(self.model.cols)
        self.spin_cols.pack(side=tk.LEFT, padx=2)

        self.aisle_var = tk.BooleanVar(
            value=(self.model.vertical_aisle_after > 0)
        )
        self.chk_aisle = ttk.Checkbutton(
            toolbar,
            text="Passadís Vertical",
            variable=self.aisle_var,
            command=self.update_grid_config,
        )
        self.chk_aisle.pack(side=tk.LEFT, padx=8)

        ttk.Button(
            toolbar, text="📂 Importar CSV", command=self.import_csv
        ).pack(side=tk.RIGHT, padx=2)
        ttk.Button(
            toolbar, text="🌐 Exportar HTML", command=self.export_html
        ).pack(side=tk.RIGHT, padx=2)
        ttk.Button(toolbar, text="🎨 Exportar SVG", command=self.export_svg).pack(
            side=tk.RIGHT, padx=2
        )
        ttk.Button(
            toolbar, text="💾 Desar JSON", command=self.save_json
        ).pack(side=tk.RIGHT, padx=2)
        ttk.Button(
            toolbar, text="📖 Carregar JSON", command=self.load_json
        ).pack(side=tk.RIGHT, padx=2)

        main_panel = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_panel.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # PANELL ESQUERRA: ALUMNES (Amb selecció múltiple EXTENDED)
        self.left_frame = ttk.LabelFrame(
            main_panel, text=" Llista d'Alumnes ", padding=10
        )
        main_panel.add(self.left_frame, weight=1)

        entry_frame = ttk.Frame(self.left_frame)
        entry_frame.pack(fill=tk.X, pady=(0, 5))

        self.entry_student = ttk.Entry(entry_frame, font=("Arial", 13))
        self.entry_student.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entry_student.bind("<KeyRelease>", self.filter_students)

        ttk.Button(entry_frame, text="+", width=3, command=self.add_student).pack(
            side=tk.RIGHT
        )

        self.listbox_students = tk.Listbox(
            self.left_frame, selectmode=tk.EXTENDED, font=("Arial", 13, "bold")
        )
        self.listbox_students.pack(fill=tk.BOTH, expand=True, pady=5)

        self.listbox_students.bind("<Button-1>", self.on_listbox_click)
        self.listbox_students.bind("<B1-Motion>", self.on_drag_motion)
        self.listbox_students.bind("<ButtonRelease-1>", self.on_drag_release)

        ttk.Button(
            self.left_frame,
            text="Eliminar Seleccionats",
            command=self.remove_student,
        ).pack(fill=tk.X)

        # PANELL DRETA: GRAELLA AULA
        right_outer_frame = ttk.LabelFrame(
            main_panel, text=" Vista de l'Aula (Pissarra a dalt) ", padding=5
        )
        main_panel.add(right_outer_frame, weight=3)

        board_label = tk.Label(
            right_outer_frame,
            text="[ PISSARRA ]",
            bg="#333",
            fg="#fff",
            font=("Arial", 12, "bold"),
        )
        board_label.pack(fill=tk.X, pady=(0, 5))

        self.canvas = tk.Canvas(right_outer_frame, bg="#ffffff")
        self.scrollbar_y = ttk.Scrollbar(
            right_outer_frame, orient="vertical", command=self.canvas.yview
        )
        self.scrollbar_x = ttk.Scrollbar(
            right_outer_frame, orient="horizontal", command=self.canvas.xview
        )

        self.grid_container = ttk.Frame(self.canvas)
        self.grid_container.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )

        self.canvas.create_window((0, 0), window=self.grid_container, anchor="nw")
        self.canvas.configure(
            yscrollcommand=self.scrollbar_y.set,
            xscrollcommand=self.scrollbar_x.set,
        )

        self.scrollbar_y.pack(side="right", fill="y")
        self.scrollbar_x.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.refresh_ui()

    def trigger_highlight(self, student_name):
        self.highlighted_student = student_name
        if self._highlight_timer:
            self.after_cancel(self._highlight_timer)
        self._highlight_timer = self.after(1000, self.clear_highlight)
        self.refresh_ui()

    def clear_highlight(self):
        self.highlighted_student = None
        self._highlight_timer = None
        self.refresh_ui()

    def refresh_ui(self):
        self.filter_students()

        for widget in self.grid_container.winfo_children():
            widget.destroy()

        aisle_col = (
            self.model.vertical_aisle_after if self.aisle_var.get() else 0
        )

        for r in range(self.model.rows):
            self.grid_container.rowconfigure(r, weight=0)
            for c in range(self.model.cols):
                visual_c = c
                if aisle_col > 0 and c >= aisle_col:
                    visual_c = c + 1

                student_name = self.model.grid.get((r, c), "")
                is_highlighted = (student_name and student_name == self.highlighted_student)

                if is_highlighted:
                    bg_color = "#2196f3"  # Blau intens
                    border_color = "#0d47a1"
                    text_color = "#ffffff"
                else:
                    bg_color = "#e1f5fe" if student_name else "#f5f5f5"
                    border_color = "#90caf9" if student_name else "#cccccc"
                    text_color = "#0d47a1" if student_name else "#bbb"

                cell = tk.Frame(
                    self.grid_container,
                    bg=bg_color,
                    highlightbackground=border_color,
                    highlightthickness=2,
                    width=220,
                    height=110,
                )
                cell.grid_propagate(False)
                cell.grid(row=r, column=visual_c, sticky="nw", padx=8, pady=8)

                label_pos = tk.Label(
                    cell,
                    text=f"F{r+1}-C{c+1}",
                    font=("Arial", 10, "bold"),
                    bg=bg_color,
                    fg="#ffffff" if is_highlighted else "#777",
                )
                label_pos.pack(anchor="nw", padx=6, pady=4)

                label_name = tk.Label(
                    cell,
                    text=student_name if student_name else "[ Buit ]",
                    font=("Arial", 14, "bold" if student_name else "normal"),
                    bg=bg_color,
                    fg=text_color,
                    wraplength=200,
                )
                label_name.pack(expand=True)

                cell.seat_pos = (r, c)
                label_name.seat_pos = (r, c)

                if student_name:
                    for w in (cell, label_name):
                        w.bind(
                            "<Button-1>",
                            lambda e, pos=(r, c), name=student_name: self.on_seat_click(
                                e, pos, name
                            ),
                        )
                        w.bind("<B1-Motion>", self.on_drag_motion)
                        w.bind("<ButtonRelease-1>", self.on_drag_release)

        if aisle_col > 0:
            for r in range(self.model.rows):
                aisle_cell = tk.Frame(
                    self.grid_container,
                    bg="#fafafa",
                    cursor="arrow",
                    width=50,
                    height=110,
                )
                aisle_cell.grid_propagate(False)
                aisle_cell.grid(
                    row=r, column=aisle_col, sticky="nw", padx=2, pady=8
                )
                tk.Label(
                    aisle_cell, text="│", font=("Arial", 14), fg="#ccc", bg="#fafafa"
                ).pack(expand=True)

    def filter_students(self, event=None):
        query = self.entry_student.get().lower()
        self.listbox_students.delete(0, tk.END)
        seated_students = set(self.model.grid.values())

        for name in self.model.students:
            if query in name.lower():
                status = " (Assegut)" if name in seated_students else ""
                idx = self.listbox_students.size()
                self.listbox_students.insert(tk.END, f"{name}{status}")
                if name == self.highlighted_student:
                    self.listbox_students.itemconfig(
                        idx, bg="#2196f3", fg="#ffffff"
                    )

    def on_listbox_click(self, event):
        sel = self.listbox_students.curselection()
        if sel:
            full_text = self.listbox_students.get(sel[0])
            name = full_text.split(" (")[0]
            self.drag_data["source"] = "list"
            self.drag_data["student"] = name
            self._create_drag_label(name, event)

    def on_seat_click(self, event, pos, name):
        self.drag_data["source"] = pos
        self.drag_data["student"] = name
        self._create_drag_label(name, event)

    def _create_drag_label(self, name, event):
        self.drag_label = tk.Label(
            self,
            text=name,
            bg="#fff59d",
            font=("Arial", 13, "bold"),
            relief="solid",
            bd=1,
            padx=8,
            pady=5,
        )
        self.drag_label.place(
            x=event.x_root - self.winfo_rootx(),
            y=event.y_root - self.winfo_rooty(),
        )

    def on_drag_motion(self, event):
        if self.drag_label:
            x = event.x_root - self.winfo_rootx() + 10
            y = event.y_root - self.winfo_rooty() + 10
            self.drag_label.place(x=x, y=y)

    def on_drag_release(self, event):
        if self.drag_label:
            self.drag_label.destroy()
            self.drag_label = None

        target_widget = self.winfo_containing(event.x_root, event.y_root)
        src = self.drag_data["source"]

        is_over_left_panel = False
        curr = target_widget
        while curr:
            if curr == self.left_frame:
                is_over_left_panel = True
                break
            curr = curr.master

        if is_over_left_panel:
            if isinstance(src, tuple):
                self.model.unseat_student(src)
                self.refresh_ui()
        else:
            dst_pos = None
            curr = target_widget
            while curr:
                if hasattr(curr, "seat_pos"):
                    dst_pos = curr.seat_pos
                    break
                curr = curr.master

            if dst_pos is not None:
                student = self.drag_data["student"]
                if src == "list":
                    self.model.assign_unseated(student, dst_pos)
                elif isinstance(src, tuple):
                    self.model.move_or_swap(src, dst_pos)

                self.trigger_highlight(student)

        self.drag_data = {"source": None, "student": None}

    def add_student(self):
        name = self.entry_student.get().strip()
        if name:
            if self.model.add_student(name):
                self.entry_student.delete(0, tk.END)
                self.refresh_ui()

    def remove_student(self):
        selections = self.listbox_students.curselection()
        if selections:
            names_to_remove = []
            for idx in selections:
                full_text = self.listbox_students.get(idx)
                name = full_text.split(" (")[0]
                names_to_remove.append(name)

            msg = f"Segur que vols eliminar {'aquests alumnes' if len(names_to_remove) > 1 else 'aquest alumne'}: {', '.join(names_to_remove)}?"
            if messagebox.askyesno("Confirmar eliminació", msg):
                for name in names_to_remove:
                    self.model.remove_student(name)
                self.refresh_ui()

    def update_grid_config(self):
        try:
            r = int(self.spin_rows.get())
            c = int(self.spin_cols.get())
            aisle_active = self.aisle_var.get()

            if aisle_active:
                if self.model.vertical_aisle_after <= 0:
                    self.model.vertical_aisle_after = c // 2 if c > 1 else 1
            else:
                self.model.vertical_aisle_after = 0

            self.model.set_grid_size(r, c, self.model.vertical_aisle_after)
            self.refresh_ui()
        except ValueError:
            pass

    def undo(self):
        if self.model.undo():
            self.spin_rows.set(self.model.rows)
            self.spin_cols.set(self.model.cols)
            self.aisle_var.set(self.model.vertical_aisle_after > 0)
            self.refresh_ui()

    def redo(self):
        if self.model.redo():
            self.spin_rows.set(self.model.rows)
            self.spin_cols.set(self.model.cols)
            self.aisle_var.set(self.model.vertical_aisle_after > 0)
            self.refresh_ui()

    def import_csv(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Fitxers CSV", "*.csv")]
        )
        if filepath:
            AulaPlanStorage.import_csv(filepath, self.model)
            self.refresh_ui()

    def export_svg(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".svg", filetypes=[("Fitxers SVG", "*.svg")]
        )
        if filepath:
            AulaPlanStorage.export_svg(filepath, self.model)
            messagebox.showinfo("Exportar", "Fitxer SVG exportat correctament!")

    def export_html(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".html", filetypes=[("Fitxers HTML", "*.html")]
        )
        if filepath:
            AulaPlanStorage.export_html(filepath, self.model)
            messagebox.showinfo(
                "Exportar", "Fitxer HTML exportat correctament!"
            )

    def save_json(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("Fitxers JSON", "*.json")]
        )
        if filepath:
            AulaPlanStorage.save_json(filepath, self.model)

    def load_json(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Fitxers JSON", "*.json")]
        )
        if filepath:
            AulaPlanStorage.load_json(filepath, self.model)
            self.spin_rows.set(self.model.rows)
            self.spin_cols.set(self.model.cols)
            self.aisle_var.set(self.model.vertical_aisle_after > 0)
            self.refresh_ui()