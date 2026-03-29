import flet as ft
from map_viewer import MapViewer
from sidebar import Sidebar

def main(page: ft.Page):
    page.title = "TSP Solver"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.add(ft.Row(controls=[Sidebar(), MapViewer()], expand=True, spacing=0))

if __name__ == "__main__":
    ft.app(target=main)
