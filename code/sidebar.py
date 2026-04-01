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

        # Definice mapových zdrojů
        self.map_sources = {
            "OpenStreetMap (DE)": "https://tile.openstreetmap.de/{z}/{x}/{y}.png",
            "CartoDB (Light)": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
            "CartoDB (Dark)": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
            "OpenTopoMap": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        }

        # Dropdown pro mapu
        self.map_selector = ft.Dropdown(
            label="Mapový podklad",
            value=state.get_map_url(),
            options=[ft.dropdown.Option(key=url, text=name) for name, url in self.map_sources.items()],
            border_color=ft.Colors.WHITE,
            focused_border_color=ft.Colors.WHITE,
            color=ft.Colors.BLACK,
        )

        self.apply_map_btn = ft.ElevatedButton(
            "Změnit mapu",
            on_click=self._on_apply_map_click,
            style=ft.ButtonStyle(color=ft.Colors.BLACK)
        )

        # EXPORT SEKCE
        self.file_name_input = ft.TextField(
            label="Název souboru",
            value="moje_instance",
            bgcolor=ft.Colors.WHITE,
            color=ft.Colors.BLACK,
            dense=True
        )

        self.export_dropdown = ft.Dropdown(
            label="Formát exportu",
            options=[ft.dropdown.Option(fmt) for fmt in tsp_manager.get_export_formats()],
            value=tsp_manager.get_export_formats()[0] if tsp_manager.get_export_formats() else None,
            border_color=ft.Colors.WHITE,
            color=ft.Colors.BLACK,
        )

        self.export_btn = ft.ElevatedButton(
            "Uložit do složky instances",
            on_click=self._on_export_click,
            style=ft.ButtonStyle(color=ft.Colors.BLACK)
        )

        self.import_btn = ft.ElevatedButton(
            "Načíst z instance",
            on_click=self._on_import_click,
            style=ft.ButtonStyle(color=ft.Colors.BLACK)
        )

        # --- NOVÁ SEKCE: KONFIGURACE SOLVERU ---
        self.solver_dropdown = ft.Dropdown(
            label="Algoritmus (Solver)",
            options=[
                ft.dropdown.Option(key=k, text=v) 
                for k, v in tsp_manager.get_supported_solvers()
            ],
            value="NN", # Výchozí hodnota
            border_color=ft.Colors.WHITE,
            color=ft.Colors.BLACK,
        )

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

        self.solve_btn = ft.FilledButton(
            "SPOČÍTAT TRASU", 
            width=float("inf"),
            on_click=self._on_solve_click,
        )
        # --- NOVÝ PRVEK PRO ZOBRAZENÍ VZDÁLENOSTI ---
        self.distance_text = ft.Text(
            "Celkem: -- km", 
            size=16, 
            weight="bold", 
            color=ft.Colors.BLUE_700
        )
        # ----------------------------------------

        # seznam bodů
        self.points_list = ft.ListView(
            expand=True,
            spacing=5,
            padding=10
        )

        self.list_container = ft.Container(
            content=self.points_list,
            height=300,
            bgcolor=ft.Colors.WHITE,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.GREY_300),
            expand=True
        )
        
        # sestavení obsahu
        self.content = ft.Column([
            ft.Text("TSP Konfigurátor", size=22, weight="bold", color=ft.Colors.BLACK87),
            ft.Divider(color=ft.Colors.GREY_600),
            
            ft.Text("Nastavení mapy:", size=14, weight="bold", color=ft.Colors.BLACK54),
            self.map_selector,
            self.apply_map_btn,

            ft.Divider(color=ft.Colors.GREY_600),

            ft.Text("Správa instancí (v složce exports):", size=14, weight="bold", color=ft.Colors.BLACK54),
            self.file_name_input,
            self.export_dropdown,
            
            ft.Row([
                ft.ElevatedButton(
                    "Export", 
                    on_click=self._on_export_click, 
                    expand=True,
                    style=ft.ButtonStyle(color=ft.Colors.BLACK)
                ),
                ft.ElevatedButton(
                    "Import", 
                    on_click=self._on_import_click, 
                    expand=True,
                    style=ft.ButtonStyle(color=ft.Colors.BLACK)
                ),
            ], spacing=10),

            ft.Divider(color=ft.Colors.GREY_600),

            # SEKCE VÝPOČTU
            ft.Text("Výpočet trasy:", size=14, weight="bold", color=ft.Colors.BLACK54),
            self.solver_dropdown,
            self.metric_dropdown,
            self.solve_btn,
            self.distance_text, # Zobrazí vzdálenost trasy

            ft.Divider(color=ft.Colors.GREY_600),

            # ft.Text("Vybrané lokality:", weight="bold", color=ft.Colors.BLACK54),
            #self.list_container,
            
            ft.Divider(color=ft.Colors.GREY_600),
            
            ft.TextButton(
                "Vymazat vše", 
                width=float("inf"),
                style=ft.ButtonStyle(color=ft.Colors.RED_700),
                on_click=lambda _: state.clear_all()
            )
        ], tight=False, scroll=ft.ScrollMode.ADAPTIVE)

        state.attach(self.update_ui)

    def _on_apply_map_click(self, e):
        if self.map_selector.value:
            state.set_map_url(self.map_selector.value)

    def update_ui(self, data):

        if isinstance(data, tuple) and data[0] == "center_map":
            return

        # OCHRANA PRO TRASU A VYNULOVÁNÍ KILOMETRŮ
        if isinstance(data, tuple) and data[0] == "route_update":
            route_points = data[1]
            
            # Pokud přijde prázdná trasa (kliknuto na Vymazat vše, nebo zbylo málo bodů)
            if not route_points:
                self.distance_text.value = "Celková vzdálenost: -- km"
                self.update()
                
            return


        if isinstance(data, tuple) and data[0] == "delete":
            index = data[1]
            if 0 <= index < len(self.points_list.controls):
                self.points_list.controls.pop(index)
                for i in range(index, len(self.points_list.controls)):
                    old_text = self.points_list.controls[i].value
                    coords = old_text.split(". ")[1]
                    self.points_list.controls[i].value = f"{i+1}. {coords}"
                self.update()


                # --- PŘIDÁNO: Automatický přepočet trasy --- (!!! NEFUNGUJE !!!)
                # Pokud už nějaká trasa existuje, chceme ji po smazání bodu hned přepočítat
                if state.get_route(): 
                    if len(state.get_points()) >= 2:
                        print("DEBUG: Automatický přepočet po smazání bodu...")
                        self._on_solve_click(None)
                    else:
                        state.set_route([])
                # -------------------------------------------




            return

        points = data
        current_count = len(self.points_list.controls)
        new_count = len(points)

        if new_count == current_count + 1:
            lat, lon = points[-1]
            self.points_list.controls.append(
                ft.Text(f"{new_count}. {lat:.4f}, {lon:.4f}", size=12, color="black")
            )
            
            if state.get_route() and new_count >= 2:
                print("DEBUG: Automatický přepočet po přidání bodu...")
                self._on_solve_click(None)
            
        else:
            self.points_list.controls.clear()
            for i, (lat, lon) in enumerate(points):
                self.points_list.controls.append(
                    ft.Text(f"{i+1}. {lat:.4f}, {lon:.4f}", size=12, color="black")
                )
        
        self.export_btn.text = "Uložit do složky instances"
        self.export_btn.bgcolor = None
        self.update()
    
    def _on_export_click(self, e):
        try:
            if not os.path.exists("instances"):
                os.makedirs("instances")
            
            filename = f"{self.file_name_input.value}.tsp"
            filepath = os.path.join("instances", filename)
            
            points = state.get_points()
            fmt = self.export_dropdown.value
            
            if not points:
                print("Chyba: Seznam bodů je prázdný!")
                return

            tsp_manager.export_instance(filepath, points, fmt)
            
            self.export_btn.text = "ULOŽENO!"
            self.export_btn.bgcolor = ft.Colors.GREEN_200
            self.update()
            print(f"DEBUG: File saved to {filepath}")
            
        except Exception as ex:
            print(f"ERROR WITH EXPORT: {ex}")

    def _on_import_click(self, e):
        filename = f"{self.file_name_input.value}.tsp"
        filepath = os.path.join("instances", filename)
        
        if not os.path.exists(filepath):
            print(f"ERROR: File {filepath} not found!")
            self.import_btn.text = "SOUBOR NENALEZEN"
            self.import_btn.bgcolor = ft.Colors.RED_200
            self.update()
            return

        try:
            is_geo = False
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for _ in range(20):
                        line = f.readline()
                        if not line: break
                        if "EDGE_WEIGHT_TYPE" in line and "GEO" in line:
                            is_geo = True
                            break
            except Exception as e:
                print(f"Error reading the header: {e}")

            new_points = tsp_manager.load_instance(filepath)
            
            if new_points:
                state.clear_all()
                state.set_points(new_points, is_geographic=is_geo)
                state.notify(("center_map", new_points[0]))
                self.import_btn.text = "NAČTENO"
                self.import_btn.bgcolor = ft.Colors.GREEN_200
                self.update()
            else:
                print("WARNING: No points loaded from file.")
                
        except Exception as ex:
            print(f"ERROR WITH IMPORT: {ex}")
            self.import_btn.text = "CHYBA IMPORTU"
            self.import_btn.bgcolor = ft.Colors.RED_200
            self.update()

    def _on_solve_click(self, e):
        points = state.get_points()
        if len(points) < 2:
            return

        try:
            # 1. ordered_cities: seznam zastávek (města)
            # 2. visual_route: detailní body pro čáru (silnice)
            # 3. total_dist: délka v km/min
            ordered_cities, visual_route, total_dist = tsp_manager.solve(
                points=points,
                solver_type=self.solver_dropdown.value,
                distance_metric=self.metric_dropdown.value
            )
            
            # --- AKTUALIZACE MAPY ---
            state.update_route(visual_route)

            # --- AKTUALIZACE UI ---
            print(f"Route found!: {total_dist:.2f}")
            
            if self.metric_dropdown.value == "routing_time":
                # Pokud je to víc než 120 minut (2 hodiny), přidáme závorku s hodinama
                if total_dist >= 120:
                    hours = total_dist / 60
                    self.distance_text.value = f"Celkem: {total_dist:.1f} min ({hours:.1f} hod)"
                else:
                    self.distance_text.value = f"Celkem: {total_dist:.1f} minut"
            else:
                # Standardní zobrazení pro kilometry (Haversine nebo OSRM Dist)
                self.distance_text.value = f"Celkem: {total_dist:.2f} km"
            
            # opt: Pokud v state držet i seznam měst v pořadí (např. pro tabulku)
            # state.set_route(ordered_cities) 

            self.update()
            
        except Exception as ex:
            print(f"ERROR WHILE SOLVING: {ex}")
            import traceback
            traceback.print_exc()