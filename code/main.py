import flet as ft
from map_viewer import TspMapViewer
from sidebar import TspSidebar

def main(page: ft.Page):
    page.title = "TSP Solver - Observer Pattern"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.add(ft.Row(controls=[TspSidebar(), TspMapViewer()], expand=True, spacing=0))

if __name__ == "__main__":
    ft.app(target=main)
