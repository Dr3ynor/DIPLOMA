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
            "Uložit do složky exports",
            on_click=self._on_export_click,
            style=ft.ButtonStyle(color=ft.Colors.BLACK)
        )

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

            ft.Text("Export dat (do projektu):", size=14, weight="bold", color=ft.Colors.BLACK54),
            self.file_name_input,
            self.export_dropdown,
            self.export_btn,

            ft.Divider(color=ft.Colors.GREY_600),

            ft.Text("Vybrané lokality:", weight="bold", color=ft.Colors.BLACK54),
            self.list_container,
            
            ft.Divider(color=ft.Colors.GREY_600),
            
            ft.FilledButton(
                "SPOČÍTAT TRASU", 
                width=float("inf"),
                on_click=lambda _: print(f"Calculating for {len(state.get_points())} points.")
            ),
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

    def update_ui(self, points):
        self.points_list.controls.clear()
        for i, (lat, lon) in enumerate(points):
            self.points_list.controls.append(
                ft.Text(f"{i+1}. {lat:.4f}, {lon:.4f}", size=12, color=ft.Colors.BLACK)
            )
        # Reset textu tlačítka při změně bodů
        self.export_btn.text = "Uložit do složky exports"
        self.export_btn.bgcolor = None
        self.update()
    
    def _on_export_click(self, e):
        # Synchronní zápis do složky exports
        try:
            if not os.path.exists("exports"):
                os.makedirs("exports")
            
            filename = f"{self.file_name_input.value}.tsp"
            filepath = os.path.join("exports", filename)
            
            points = state.get_points()
            fmt = self.export_dropdown.value
            
            if not points:
                print("Chyba: Seznam bodů je prázdný!")
                return

            tsp_manager.export_instance(filepath, points, fmt)
            
            # Vizuální potvrzení na tlačítku
            self.export_btn.text = "ULOŽENO!"
            self.export_btn.bgcolor = ft.Colors.GREEN_200
            self.update()
            print(f"DEBUG: Soubor uložen do {filepath}")
            
        except Exception as ex:
            print(f"CHYBA EXPORTU: {ex}")