import os
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class SensorViewerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Sensor Data Viewer")
        self.root.geometry("1200x900")

        self.db_path_var = tk.StringVar()
        self.start_var = tk.StringVar()
        self.end_var = tk.StringVar()
        self.tank_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready.")

        self.sensor_id_list: list[int] = []  # 하위 호환용 (단일 sensor_id 선택 시)
        self.tank_sensor_list: list[tuple[str, int]] = []  # (tank_id, sensor_id) 목록 — DB의 실제 시계열 개수 반영
        self.table_data: list[tuple] = []
        self.filtered_data: list[tuple] = []  # 필터된 데이터 (현재 테이블에 표시된 데이터)

        self._build_ui()

    def _build_ui(self) -> None:
        top_frame = ttk.Frame(self.root, padding=8)
        top_frame.pack(fill="x")

        ttk.Label(top_frame, text="Database").pack(side="left")
        ttk.Entry(top_frame, textvariable=self.db_path_var, width=80).pack(
            side="left", padx=6
        )
        ttk.Button(top_frame, text="Select DB", command=self.select_db).pack(
            side="left"
        )
        ttk.Button(top_frame, text="Load Info", command=self.load_metadata).pack(
            side="left", padx=6
        )

        info_frame = ttk.LabelFrame(self.root, text="DB Info", padding=8)
        info_frame.pack(fill="x", padx=8, pady=6)

        self.time_range_label = ttk.Label(info_frame, text="Time range: -")
        self.time_range_label.pack(side="left")

        self.sensor_count_label = ttk.Label(info_frame, text="Sensors: -")
        self.sensor_count_label.pack(side="left", padx=16)

        selection_frame = ttk.LabelFrame(self.root, text="Selection", padding=8)
        selection_frame.pack(fill="x", padx=8, pady=6)

        ttk.Label(selection_frame, text="Start").grid(row=0, column=0, sticky="w")
        ttk.Entry(selection_frame, textvariable=self.start_var, width=22).grid(
            row=0, column=1, padx=6
        )
        ttk.Button(selection_frame, text="Use Min", command=self.use_min_time).grid(
            row=0, column=2, padx=6
        )

        ttk.Label(selection_frame, text="End").grid(row=0, column=3, sticky="w")
        ttk.Entry(selection_frame, textvariable=self.end_var, width=22).grid(
            row=0, column=4, padx=6
        )
        ttk.Button(selection_frame, text="Use Max", command=self.use_max_time).grid(
            row=0, column=5, padx=6
        )

        ttk.Label(selection_frame, text="Tank ID (optional)").grid(
            row=1, column=0, sticky="w", pady=6
        )
        ttk.Entry(selection_frame, textvariable=self.tank_var, width=22).grid(
            row=1, column=1, padx=6, pady=6
        )

        ttk.Label(selection_frame, text="Sensors").grid(
            row=2, column=0, sticky="nw"
        )
        self.sensor_listbox = tk.Listbox(
            selection_frame, selectmode="extended", height=5, width=30
        )
        self.sensor_listbox.grid(row=2, column=1, columnspan=2, sticky="w")

        button_frame = ttk.Frame(selection_frame)
        button_frame.grid(row=2, column=3, columnspan=3, sticky="w")
        ttk.Button(button_frame, text="Load Data", command=self.load_data_table).pack(
            fill="x", pady=2
        )
        ttk.Button(button_frame, text="Plot", command=self.plot_selected).pack(
            fill="x", pady=2
        )
        ttk.Button(button_frame, text="Export CSV", command=self.export_csv).pack(
            fill="x", pady=2
        )

        # 데이터 테이블 프레임 (DB Browser 스타일)
        table_frame = ttk.LabelFrame(self.root, text="Data Table", padding=8)
        table_frame.pack(fill="both", expand=True, padx=8, pady=6)

        # 필터 행
        filter_frame = ttk.Frame(table_frame)
        filter_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        columns = ("id", "packet_id", "tank_id", "sensor_id", "value")
        self.filter_vars: dict[str, tk.StringVar] = {}
        for i, col in enumerate(columns):
            ttk.Label(filter_frame, text=col, width=12, anchor="center").grid(row=0, column=i, padx=2)
            var = tk.StringVar()
            self.filter_vars[col] = var
            entry = ttk.Entry(filter_frame, textvariable=var, width=12)
            entry.grid(row=1, column=i, padx=2)
            entry.bind("<Return>", lambda e: self.apply_filter())

        ttk.Button(filter_frame, text="Filter", command=self.apply_filter).grid(row=1, column=len(columns), padx=6)
        ttk.Button(filter_frame, text="Clear", command=self.clear_filter).grid(row=1, column=len(columns)+1, padx=2)

        # Treeview 테이블
        self.data_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        for col in columns:
            self.data_tree.heading(col, text=col)
            self.data_tree.column(col, width=100, anchor="center")
        
        # 스크롤바
        tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.data_tree.yview)
        tree_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        self.data_tree.grid(row=1, column=0, sticky="nsew")
        tree_scroll_y.grid(row=1, column=1, sticky="ns")
        tree_scroll_x.grid(row=2, column=0, sticky="ew")
        table_frame.grid_rowconfigure(1, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        chart_frame = ttk.LabelFrame(self.root, text="Chart", padding=8)
        chart_frame.pack(fill="both", expand=True, padx=8, pady=6)

        self.figure = Figure(figsize=(8, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief="sunken", anchor="w"
        )
        status_bar.pack(fill="x", side="bottom")

    def select_db(self) -> None:
        initial_dir = os.path.abspath(os.path.join(os.getcwd(), "backend"))
        path = filedialog.askopenfilename(
            title="Select sensor_data.db",
            initialdir=initial_dir if os.path.isdir(initial_dir) else os.getcwd(),
            filetypes=[("SQLite DB", "*.db"), ("All Files", "*.*")],
        )
        if path:
            self.db_path_var.set(path)
            self.load_metadata()

    def load_metadata(self) -> None:
        db_path = self.db_path_var.get().strip()
        if not db_path:
            messagebox.showwarning("Missing DB", "Please select a database file.")
            return
        if not os.path.isfile(db_path):
            messagebox.showerror("Not Found", f"DB not found:\n{db_path}")
            return

        try:
            with sqlite3.connect(db_path) as conn:
                if not self._has_required_tables(conn):
                    messagebox.showerror(
                        "Invalid DB",
                        "Required tables not found. Expecting 'packets' and 'readings'.",
                    )
                    return

                min_time, max_time = self._fetch_time_range(conn)
                sensor_counts = self._fetch_sensor_counts(conn)
                total_readings = self._fetch_total_readings(conn)

            self._update_info(min_time, max_time, sensor_counts, total_readings)
            self.status_var.set("DB info loaded.")
        except sqlite3.Error as exc:
            messagebox.showerror("DB Error", str(exc))

    def _has_required_tables(self, conn: sqlite3.Connection) -> bool:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        tables = {row[0] for row in rows}
        return "packets" in tables and "readings" in tables

    def _fetch_time_range(self, conn: sqlite3.Connection) -> tuple[str | None, str | None]:
        row = conn.execute(
            "SELECT MIN(created_at), MAX(created_at) FROM packets"
        ).fetchone()
        if not row:
            return None, None
        return row[0], row[1]

    def _fetch_total_readings(self, conn: sqlite3.Connection) -> int:
        """readings 테이블 전체 행 수 (검증용)."""
        row = conn.execute("SELECT COUNT(*) FROM readings").fetchone()
        return int(row[0]) if row else 0

    def _fetch_sensor_counts(self, conn: sqlite3.Connection) -> list[tuple[str, int, int]]:
        """(tank_id, sensor_id) 조합별 행 개수 조회. 동일 sensor_id가 여러 탱크에 있으면 각각 별도 시계열로 센다."""
        rows = conn.execute(
            """SELECT tank_id, sensor_id, COUNT(*)
               FROM readings
               GROUP BY tank_id, sensor_id
               ORDER BY tank_id, sensor_id"""
        ).fetchall()
        return [(str(tank_id), int(sensor_id), int(count)) for tank_id, sensor_id, count in rows]

    def _update_info(
        self,
        min_time: str | None,
        max_time: str | None,
        sensor_counts: list[tuple[str, int, int]],
        total_readings: int = 0,
    ) -> None:
        if min_time and max_time:
            self.time_range_label.config(
                text=f"Time range: {min_time} ~ {max_time}"
            )
            self.start_var.set(min_time)
            self.end_var.set(max_time)
        else:
            self.time_range_label.config(text="Time range: -")

        self.sensor_listbox.delete(0, tk.END)
        self.sensor_id_list = []
        self.tank_sensor_list = []
        for tank_id, sensor_id, count in sensor_counts:
            self.tank_sensor_list.append((tank_id, sensor_id))
            self.sensor_id_list.append(sensor_id)  # 리스트박스 인덱스와 동일 순서 유지
            self.sensor_listbox.insert(tk.END, f"{tank_id}-{sensor_id} ({count})")
        self.sensor_count_label.config(
            text=f"Sensors: {len(sensor_counts)} (tank×sensor) | Total rows: {total_readings}"
        )

    def use_min_time(self) -> None:
        label = self.time_range_label.cget("text")
        if "~" in label:
            self.start_var.set(label.split("~")[0].replace("Time range:", "").strip())

    def use_max_time(self) -> None:
        label = self.time_range_label.cget("text")
        if "~" in label:
            self.end_var.set(label.split("~")[1].strip())

    def _fetch_readings_by_criteria(self, limit: int | None = None) -> list[tuple]:
        """날짜·탱크·센서 조건에 맞는 readings 조회. limit=None이면 전체, 정수면 해당 개수만."""
        db_path = self.db_path_var.get().strip()
        if not db_path:
            return []
        start_text = self.start_var.get().strip()
        end_text = self.end_var.get().strip()
        if not start_text or not end_text:
            return []
        selected_pairs = self._get_selected_tank_sensor_pairs()
        tank_filter = self.tank_var.get().strip()

        query = """
            SELECT r.id, r.packet_id, r.tank_id, r.sensor_id, r.value
            FROM readings r
            JOIN packets p ON r.packet_id = p.id
            WHERE p.created_at BETWEEN ? AND ?
        """
        params: list = [start_text, end_text]
        if selected_pairs:
            conds = " OR ".join(
                "(r.tank_id = ? AND r.sensor_id = ?)" for _ in selected_pairs
            )
            query += f" AND ({conds})"
            for t_id, s_id in selected_pairs:
                params.append(t_id)
                params.append(s_id)
        if tank_filter:
            query += " AND r.tank_id = ?"
            params.append(tank_filter)
        query += " ORDER BY r.id ASC"
        if limit is not None:
            query += f" LIMIT {limit}"

        try:
            with sqlite3.connect(db_path) as conn:
                return conn.execute(query, params).fetchall()
        except sqlite3.Error:
            return []

    def load_data_table(self) -> None:
        """DB Browser처럼 readings 테이블 데이터를 테이블에 표시 (최대 5000행)."""
        db_path = self.db_path_var.get().strip()
        if not db_path:
            messagebox.showwarning("Missing DB", "Please select a database file.")
            return
        start_text = self.start_var.get().strip()
        end_text = self.end_var.get().strip()
        if not start_text or not end_text:
            messagebox.showwarning("Missing Range", "Please enter start and end time.")
            return

        try:
            rows = self._fetch_readings_by_criteria(limit=5000)
            self.table_data = rows
            self.clear_filter()
            self.status_var.set(f"Loaded {len(rows)} rows (max 5000 for table).")
        except sqlite3.Error as exc:
            messagebox.showerror("DB Error", str(exc))

    def apply_filter(self) -> None:
        """필터 조건에 맞는 데이터만 표시"""
        columns = ("id", "packet_id", "tank_id", "sensor_id", "value")
        
        # 필터 조건 가져오기
        filters = {col: self.filter_vars[col].get().strip() for col in columns}

        # 기존 데이터 삭제
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)

        # 필터링된 데이터 저장 및 삽입
        self.filtered_data = []
        for row in self.table_data:
            match = True
            for i, col in enumerate(columns):
                filter_val = filters[col]
                if filter_val:
                    # 문자열 포함 비교 (대소문자 무시)
                    if filter_val.lower() not in str(row[i]).lower():
                        match = False
                        break
            if match:
                self.filtered_data.append(row)
                self.data_tree.insert("", "end", values=row)

        self.status_var.set(f"Showing {len(self.filtered_data)} of {len(self.table_data)} rows.")

    def clear_filter(self) -> None:
        """필터 초기화 및 전체 데이터 표시"""
        # 필터 입력 초기화
        for var in self.filter_vars.values():
            var.set("")

        # 기존 데이터 삭제
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)

        # 전체 데이터 삽입 및 필터 데이터 초기화
        self.filtered_data = list(self.table_data)
        for row in self.table_data:
            self.data_tree.insert("", "end", values=row)

        self.status_var.set(f"Showing {len(self.table_data)} rows.")

    def plot_selected(self) -> None:
        """날짜·선택 조건에 맞는 전체 데이터를 그래프로 표시 (제한 없음)."""
        db_path = self.db_path_var.get().strip()
        if not db_path:
            messagebox.showwarning("Missing DB", "Please select a database file.")
            return
        start_text = self.start_var.get().strip()
        end_text = self.end_var.get().strip()
        if not start_text or not end_text:
            messagebox.showwarning("Missing Range", "Please enter start and end time.")
            return

        rows = self._fetch_readings_by_criteria(limit=None)
        if not rows:
            messagebox.showwarning("No Data", "No data in the selected date range and filters.")
            self._clear_plot()
            return

        df = pd.DataFrame(
            rows,
            columns=["id", "packet_id", "tank_id", "sensor_id", "value"]
        )
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"])

        if df.empty:
            messagebox.showinfo("No Data", "No valid data to plot.")
            self._clear_plot()
            return

        df["tank_sensor"] = df["tank_id"].astype(str) + "-" + df["sensor_id"].astype(str)
        self.ax.clear()
        for label in df["tank_sensor"].unique():
            subset = df[df["tank_sensor"] == label]
            self.ax.plot(range(len(subset)), subset["value"].values, label=label)
        self.ax.set_title("Sensor Data (Full by date/filter)")
        self.ax.set_xlabel("Index")
        self.ax.set_ylabel("Value")
        self.ax.grid(True, linestyle="--", alpha=0.3)
        self.ax.legend(loc="upper right")
        self.canvas.draw()

        self.status_var.set(f"Plotted {len(df)} data points (full).")

    def _get_selected_sensor_ids(self) -> list[int]:
        indices = self.sensor_listbox.curselection()
        return [self.sensor_id_list[i] for i in indices]

    def _get_selected_tank_sensor_pairs(self) -> list[tuple[str, int]]:
        indices = self.sensor_listbox.curselection()
        return [self.tank_sensor_list[i] for i in indices]

    def _clear_plot(self) -> None:
        self.ax.clear()
        self.ax.set_title("Sensor Data")
        self.canvas.draw()

    def export_csv(self) -> None:
        """날짜·선택 조건에 맞는 전체 데이터를 CSV로 내보내기 (제한 없음)."""
        db_path = self.db_path_var.get().strip()
        if not db_path:
            messagebox.showwarning("Missing DB", "Please select a database file.")
            return
        start_text = self.start_var.get().strip()
        end_text = self.end_var.get().strip()
        if not start_text or not end_text:
            messagebox.showwarning("Missing Range", "Please enter start and end time.")
            return

        rows = self._fetch_readings_by_criteria(limit=None)
        if not rows:
            messagebox.showwarning("No Data", "No data in the selected date range and filters.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not save_path:
            return

        try:
            df = pd.DataFrame(
                rows,
                columns=["id", "packet_id", "tank_id", "sensor_id", "value"]
            )
            df.to_csv(save_path, index=False, encoding="utf-8-sig")
            self.status_var.set(f"CSV saved: {save_path} ({len(df)} rows, full).")
        except OSError as e:
            messagebox.showerror(
                "Save Error",
                f"Cannot write file.\n\n{e}",
            )
            self.status_var.set("CSV save failed (file/path error).")
        except Exception as e:
            messagebox.showerror(
                "CSV Export Error",
                f"Export failed.\n\n{e}",
            )
            self.status_var.set("CSV export failed.")


def main() -> None:
    root = tk.Tk()
    app = SensorViewerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
