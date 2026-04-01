import flet as ft
import os
from app_state import state
from tspmanager import tsp_manager

class Sidebar(ft.Container):
    def __init__(self):
        super().__init__(
            width=350, 
            bgcolor=ft.Colors.GREY_400, 
            padding=20,
            border=ft.border.only(right=ft.BorderSide(1, ft.Colors.GREY_500)),
            expand=True
        )

        self.dynamic_params_container = ft.Column(spacing=5)
        self.current_param_controls = {}

        self.map_sources = {
            "OpenStreetMap (DE)": "https://tile.openstreetmap.de/{z}/{x}/{y}.png",
            "CartoDB (Light)": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
            "CartoDB (Dark)": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
            "OpenTopoMap": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        }

        self.map_selector = ft.Dropdown(
            label="Mapový podklad",
            value=state.get_map_url(),
            options=[ft.dropdown.Option(key=url, text=name) for name, url in self.map_sources.items()],
            border_color=ft.Colors.WHITE,
            focused_border_color=ft.Colors.WHITE,
            color=ft.Colors.BLACK,
        )

        self.apply_map_btn = ft.ElevatedButton("Změnit mapu", on_click=self._on_apply_map_click, style=ft.ButtonStyle(color=ft.Colors.BLACK))
        self.file_name_input = ft.TextField(label="Název souboru", value="moje_instance", bgcolor=ft.Colors.WHITE, color=ft.Colors.BLACK, dense=True)

        self.export_dropdown = ft.Dropdown(
            label="Formát exportu",
            options=[ft.dropdown.Option(fmt) for fmt in tsp_manager.get_export_formats()],
            value=tsp_manager.get_export_formats()[0] if tsp_manager.get_export_formats() else None,
            border_color=ft.Colors.WHITE,
            color=ft.Colors.BLACK,
        )

        self.export_btn = ft.ElevatedButton("Uložit do složky instances", on_click=self._on_export_click, style=ft.ButtonStyle(color=ft.Colors.BLACK))
        self.import_btn = ft.ElevatedButton("Načíst z instance", on_click=self._on_import_click, style=ft.ButtonStyle(color=ft.Colors.BLACK))

        # --- GIGANTICKÁ OPRAVA: TLAČÍTKO MÍSTO ON_CHANGE ---
        self.solver_dropdown = ft.Dropdown(
            label="Algoritmus (Solver)",
            options=[ft.dropdown.Option(key=k, text=v) for k, v in tsp_manager.get_supported_solvers()],
            value="NN",
            border_color=ft.Colors.WHITE,
            color=ft.Colors.BLACK,
            expand=True # Aby roletka vyplnila volné místo vedle tlačítka
        )
        
        # Přidáme tlačítko s ikonou pro potvrzení výběru a načtení parametrů
        self.load_params_btn = ft.IconButton(
            icon=ft.Icons.SETTINGS,
            tooltip="Načíst parametry",
            on_click=self._on_solver_change,
            icon_color=ft.Colors.BLUE_900,
            icon_size=30
        )
        
        # Dáme je vedle sebe do jednoho řádku
        self.solver_row = ft.Row([self.solver_dropdown, self.load_params_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        # ---------------------------------------------------

        self.metric_dropdown = ft.Dropdown(
            label="Metrika vzdálenosti",
            options=[
                ft.dropdown.Option("haversine", text="Letecká (Haversine)"),
                ft.dropdown.Option("routing_dist", text="Silniční vzdálenost (OSRM)"),
                ft.dropdown.Option("routing_time", text="Silniční čas (OSRM)"),
            ],
            value="haversine",
            border_color=ft.Colors.WHITE,
            color=ft.Colors.BLACK,
        )

        self.solve_btn = ft.FilledButton("SPOČÍTAT TRASU", width=float("inf"), on_click=self._on_solve_click)
        self.distance_text = ft.Text("Celkem: -- km", size=16, weight="bold", color=ft.Colors.BLUE_700)
        self.points_list = ft.ListView(expand=True, spacing=5, padding=10)

        self.content = ft.Column([
            ft.Text("TSP Konfigurátor", size=22, weight="bold", color=ft.Colors.BLACK87),
            ft.Divider(color=ft.Colors.GREY_600),
            ft.Text("Nastavení mapy:", size=14, weight="bold", color=ft.Colors.BLACK54),
            self.map_selector,
            self.apply_map_btn,
            ft.Divider(color=ft.Colors.GREY_600),
            ft.Text("Správa instancí:", size=14, weight="bold", color=ft.Colors.BLACK54),
            self.file_name_input,
            self.export_dropdown,
            ft.Row([
                ft.ElevatedButton("Export", on_click=self._on_export_click, expand=True, style=ft.ButtonStyle(color=ft.Colors.BLACK)),
                ft.ElevatedButton("Import", on_click=self._on_import_click, expand=True, style=ft.ButtonStyle(color=ft.Colors.BLACK)),
            ], spacing=10),
            ft.Divider(color=ft.Colors.GREY_600),
            
            ft.Text("Výpočet trasy:", size=14, weight="bold", color=ft.Colors.BLACK54),
            self.solver_row, # <-- TADY JE NYNÍ ŘÁDEK S TLAČÍTKEM
            self.dynamic_params_container,
            self.metric_dropdown,
            self.solve_btn,
            self.distance_text,
            
            ft.Divider(color=ft.Colors.GREY_600),
            ft.TextButton("Vymazat vše", width=float("inf"), style=ft.ButtonStyle(color=ft.Colors.RED_700), on_click=lambda _: state.clear_all())
        ], tight=False, scroll=ft.ScrollMode.ADAPTIVE)

        state.attach(self.update_ui)
        self._build_params("NN") # Inicializace v paměti

    def _build_params(self, val):
        self.dynamic_params_container.controls.clear()
        self.current_param_controls.clear()
        
        params_def = tsp_manager.engine.get_solver_params(val)
        
        if params_def:
            self.dynamic_params_container.controls.append(
                ft.Text(f"Parametry ({val}):", size=12, weight="bold", color=ft.Colors.BLACK87)
            )
            for p in params_def:
                default_val_str = str(p["default"]) if p["default"] is not None else ""
                ctrl = ft.TextField(
                    label=p["label"], 
                    value=default_val_str, 
                    dense=True, 
                    text_size=12,
                    bgcolor=ft.Colors.WHITE,
                    color=ft.Colors.BLACK
                )
                self.dynamic_params_container.controls.append(ctrl)
                self.current_param_controls[p["id"]] = (ctrl, p["type"])

    def _on_solver_change(self, e):
        """Vyvolá se kliknutím na tlačítko ozubeného kolečka."""
        val = self.solver_dropdown.value
        self._build_params(val)
        
        if self.page:
            self.dynamic_params_container.update()
            self.update()

    def _on_apply_map_click(self, e):
        if self.map_selector.value: state.set_map_url(self.map_selector.value)

    def update_ui(self, data):
        if isinstance(data, tuple) and data[0] in ["center_map", "delete"]: return
        if isinstance(data, tuple) and data[0] == "route_update":
            if not data[1]: self.distance_text.value = "Celková vzdálenost: -- km"; self.update()
            return
        self.update()

    def _on_export_click(self, e):
        try:
            if not os.path.exists("instances"): os.makedirs("instances")
            filename = f"{self.file_name_input.value}.tsp"
            filepath = os.path.join("instances", filename)
            points = state.get_points()
            fmt = self.export_dropdown.value
            if not points: return
            tsp_manager.export_instance(filepath, points, fmt)
            self.export_btn.text = "ULOŽENO!"
            self.export_btn.bgcolor = ft.Colors.GREEN_200
            self.update()
        except Exception as ex:
            print(f"ERROR: {ex}")

    def _on_import_click(self, e):
        filename = f"{self.file_name_input.value}.tsp"
        filepath = os.path.join("instances", filename)
        if not os.path.exists(filepath):
            self.import_btn.text = "SOUBOR NENALEZEN"
            self.import_btn.bgcolor = ft.Colors.RED_200
            self.update()
            return

        try:
            is_geo = False
            with open(filepath, "r", encoding="utf-8") as f:
                for _ in range(20):
                    line = f.readline()
                    if not line: break
                    if "EDGE_WEIGHT_TYPE" in line and "GEO" in line:
                        is_geo = True
                        break

            new_points = tsp_manager.load_instance(filepath)
            if new_points:
                state.clear_all()
                state.set_points(new_points, is_geographic=is_geo)
                state.notify(("center_map", new_points[0]))
                self.import_btn.text = "NAČTENO"
                self.import_btn.bgcolor = ft.Colors.GREEN_200
                self.update()
        except Exception as ex:
            print(f"ERROR: {ex}")

    def _on_solve_click(self, e):
        algo_kwargs = {}
        for param_id, (ctrl, param_type) in self.current_param_controls.items():
            val_str = ctrl.value.strip()
            if not val_str or val_str.lower() == "none":
                if param_type == "int_or_none": algo_kwargs[param_id] = None
                continue
            try:
                if param_type == "int": algo_kwargs[param_id] = int(val_str)
                elif param_type == "float": algo_kwargs[param_id] = float(val_str)
                elif param_type == "int_or_none": algo_kwargs[param_id] = int(val_str)
            except ValueError:
                print(f"Ignoruji špatnou hodnotu u {param_id}")
        
        points = state.get_points()
        if len(points) < 2: return

        try:
            ordered_cities, visual_route, total_dist = tsp_manager.solve(
                points=points, solver_type=self.solver_dropdown.value,
                distance_metric=self.metric_dropdown.value, algo_params=algo_kwargs
            )
            state.update_route(visual_route)
            
            if self.metric_dropdown.value == "routing_time":
                if total_dist >= 120:
                    self.distance_text.value = f"Celkem: {total_dist:.1f} min ({total_dist/60:.1f} hod)"
                else:
                    self.distance_text.value = f"Celkem: {total_dist:.1f} minut"
            else:
                self.distance_text.value = f"Celkem: {total_dist:.2f} km"
            
            self.update()
        except Exception as ex:
            print(f"ERROR: {ex}")