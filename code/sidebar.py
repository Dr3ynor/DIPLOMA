import flet as ft
from app_state import state

class TspSidebar(ft.Container):
    def __init__(self):
        super().__init__(
            width=350, 
            bgcolor=ft.Colors.GREY,
            padding=20,
            border=ft.border.only(right=ft.BorderSide(1, ft.Colors.GREY_400))
        )
        
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
        
        self.content = ft.Column([
            ft.Text("TSP Konfigurátor", size=22, weight="bold", color=ft.Colors.BLACK87),
            ft.Divider(color=ft.Colors.GREY_400),
            
            ft.Text("Vybrané lokality:", weight="bold", color=ft.Colors.BLACK54),
            
            self.list_container,
            
            ft.Divider(color=ft.Colors.GREY_400),
            
            ft.FilledButton(
                "SPOČÍTAT TRASU", 
                expand=False, 
                on_click=lambda _: print(f"Processing... {len(state.get_points())} points \n{state.get_points()}")
            ),
            ft.TextButton(
                "Vymazat vše", 
                on_click=lambda _: state.clear_all()
            )
        ], tight=False)

        state.attach(self.update_ui)

    def update_ui(self, points):
        self.points_list.controls.clear()
        for i, (lat, lon) in enumerate(points):
            self.points_list.controls.append(
                ft.Text(f"{i+1}. {lat:.4f}, {lon:.4f}", size=12)
            )
        self.update()
