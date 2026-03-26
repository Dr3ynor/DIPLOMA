import flet as ft
from app_state import state

class TspSidebar(ft.Container):
    def __init__(self):
        super().__init__(
            width=350, 
            bgcolor=ft.Colors.GREY_400, 
            padding=20,
            border=ft.border.only(right=ft.BorderSide(1, ft.Colors.GREY_500)),
            expand=True
        )

        # 1. definice mapových zdrojů
        self.map_sources = {
            "OpenStreetMap (DE)": "https://tile.openstreetmap.de/{z}/{x}/{y}.png",
            # "OpenStreetMap (Standard)": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "CartoDB (Light)": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
            "CartoDB (Dark)": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
            "OpenTopoMap": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        }

        # 2. dropdown menu
        self.map_selector = ft.Dropdown(
            label="Mapový podklad",
            value=state.get_map_url(),
            options=[ft.dropdown.Option(key=url, text=name) for name, url in self.map_sources.items()],
            border_color=ft.Colors.WHITE,
            focused_border_color=ft.Colors.WHITE,
            color=ft.Colors.BLACK,
        )

        # 3. tlačítko pro potvrzení změny mapy
        self.apply_map_btn = ft.ElevatedButton(
            "Změnit mapu",
            on_click=self._on_apply_map_click,
            style=ft.ButtonStyle(color=ft.Colors.BLACK)
        )

        # 4. seznam bodů
        self.points_list = ft.ListView(
            expand=True,
            spacing=5,
            padding=10
        )

        # 5. kontejner pro seznam bodů
        self.list_container = ft.Container(
            content=self.points_list,
            height=300,
            bgcolor=ft.Colors.WHITE,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.GREY_300),
            expand=True
        )
        
        # 6. sestavení celého obsahu sidebaru
        self.content = ft.Column([
            ft.Text("TSP Konfigurátor", size=22, weight="bold", color=ft.Colors.BLACK87),
            ft.Divider(color=ft.Colors.GREY_600),
            
            # nastavení mapy
            ft.Text("Nastavení mapy:", size=14, weight="bold", color=ft.Colors.BLACK54),
            self.map_selector,
            self.apply_map_btn,

            ft.Divider(color=ft.Colors.GREY_600),

            # seznamu bodů
            ft.Text("Vybrané lokality:", weight="bold", color=ft.Colors.BLACK54),
            self.list_container,
            
            ft.Divider(color=ft.Colors.GREY_600),
            
            # tlačítka
            ft.FilledButton(
                "SPOČÍTAT TRASU", 
                width=float("inf"),
                on_click=lambda _: print(f"DEBUG: Počítám trasu pro {len(state.get_points())} bodů.")
            ),
            ft.TextButton(
                "Vymazat vše", 
                width=float("inf"),
                style=ft.ButtonStyle(color=ft.Colors.RED_700),
                on_click=lambda _: state.clear_all()
            )
        ], tight=False)

        state.attach(self.update_ui)

    def _on_apply_map_click(self, e):
        """Zpracuje kliknutí na tlačítko a aktualizuje stav mapy."""
        if self.map_selector.value:
            print(f"DEBUG: Sidebar posílá novou URL: {self.map_selector.value}")
            state.set_map_url(self.map_selector.value)

    def update_ui(self, points):
        """Zavolá se při každé změně stavu (přidání bodu, smazání, změna mapy)."""
        self.points_list.controls.clear()
        for i, (lat, lon) in enumerate(points):
            self.points_list.controls.append(
                ft.Text(f"{i+1}. {lat:.4f}, {lon:.4f}", size=12, color=ft.Colors.BLACK)
            )
        self.update()