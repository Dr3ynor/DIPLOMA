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

        # 1. Definice mapových zdrojů
        self.map_sources = {
            "OpenStreetMap (DE)": "https://tile.openstreetmap.de/{z}/{x}/{y}.png",
            "CartoDB (Light)": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
            "CartoDB (Dark)": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
            "OpenTopoMap": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        }

        # 2. Dropdown pro mapu
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

        # 3. EXPORT SEKCE (Nový přístup bez FilePickeru)
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
                ft.dropdown.Option("routing", text="Silniční (OSRM)"),
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
        # ----------------------------------------

        # 4. Seznam bodů
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
        
        # 5. Sestavení obsahu
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

            ft.Divider(color=ft.Colors.GREY_600),

            ft.Text("Vybrané lokality:", weight="bold", color=ft.Colors.BLACK54),
            self.list_container,
            
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
        if isinstance(data, tuple) and data[0] == "route_update":
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


# --- PŘIDÁNO: Automatický přepočet trasy ---
                # Pokud už nějaká trasa existuje, chceme ji po smazání bodu hned přepočítat
                if state.get_route(): 
                    if len(state.get_points()) >= 2:
                        print("DEBUG: Automatický přepočet po smazání bodu...")
                        self._on_solve_click(None) # Virtuální kliknutí na tlačítko výpočtu
                    else:
                        # Pokud zbyl jen 1 bod (nebo nula), trasa už nedává smysl, tak ji smažeme
                        state.set_route([])
                # -------------------------------------------




            return

        points = data # V tomhle případě je data seznam bodů
        current_count = len(self.points_list.controls)
        new_count = len(points)

        if new_count == current_count + 1:
            # 1. Bod se přidá do textového seznamu v Sidebaru
            lat, lon = points[-1]
            self.points_list.controls.append(
                ft.Text(f"{new_count}. {lat:.4f}, {lon:.4f}", size=12, color="black")
            )
            
            # --- PŘIDÁNO: Automatický přepočet trasy při přidání ---
            # Pokud už nějaká trasa na mapě existuje, hned ji přepočítáme
            if state.get_route() and new_count >= 2:
                print("DEBUG: Automatický přepočet po přidání bodu...")
                self._on_solve_click(None) # Virtuální kliknutí na tlačítko
            # -------------------------------------------------------
            
        else:
            # Import celé instance (zde nepřepočítáváme automaticky, 
            # necháme uživatele, ať si klikne na tlačítko sám)
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
            print(f"DEBUG: Soubor uložen do {filepath}")
            
        except Exception as ex:
            print(f"CHYBA EXPORTU: {ex}")

    def _on_import_click(self, e):
        filename = f"{self.file_name_input.value}.tsp"
        filepath = os.path.join("instances", filename)
        
        if not os.path.exists(filepath):
            print(f"CHYBA: Soubor {filepath} nebyl nalezen!")
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
                print(f"Chyba při čtení hlavičky: {e}")

            new_points = tsp_manager.load_instance(filepath)
            
            if new_points:
                state.clear_all()
                state.set_points(new_points, is_geographic=is_geo)
                
                self.import_btn.text = "NAČTENO"
                self.import_btn.bgcolor = ft.Colors.GREEN_200
                self.update()
            else:
                print("VAROVÁNÍ: Soubor byl prázdný nebo chybně formátovaný.")
                
        except Exception as ex:
            print(f"KRITICKÁ CHYBA PŘI IMPORTU: {ex}")
            self.import_btn.text = "CHYBA IMPORTU"
            self.import_btn.bgcolor = ft.Colors.RED_200
            self.update()

    def _on_solve_click(self, e):
        points = state.get_points()
        if len(points) < 2:
            return

        try:
            res = tsp_manager.solve(
                points=points,
                solver_type=self.solver_dropdown.value,
                distance_metric=self.metric_dropdown.value
            )
            
            # DEBUG: Tohle nám v konzoli konečně řekne pravdu!
            print(f"DEBUG: Skutečný obsah 'res' je: {res}")
            
            # Defenzivní rozbalení: vezmeme první dva prvky, ať už jich přišlo kolikkoliv
            ordered_route = res[0]
            total_dist = res[1]

            state.set_route(ordered_route)
            print(f"Trasa nalezena! Délka: {total_dist:.2f} km")
            
        except Exception as ex:
            print(f"CHYBA PŘI VÝPOČTU: {ex}")
            # Pokud to spadne i tady, vypiš celou chybu:
            import traceback
            traceback.print_exc()