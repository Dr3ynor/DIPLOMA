# Palety a QSS šablony pro přepínání tmavého / světlého vzhledu.

PALETTES = {
    "dark": {
        "bg":           "#0f1117",
        "surface":      "#1a1d2e",
        "surface2":     "#252841",
        "border":       "#2d3148",
        "primary":      "#6366f1",
        "primary_h":    "#818cf8",
        "primary_d":    "#4f46e5",
        "success":      "#10b981",
        "success_d":    "#059669",
        "danger":       "#ef4444",
        "danger_d":     "#dc2626",
        "text":         "#f1f5f9",
        "text_dim":     "#94a3b8",
        "text_faint":   "#475569",
        "accent":       "#6366f1",
    },
    "light": {
        "bg":           "#f1f5f9",
        "surface":      "#ffffff",
        "surface2":     "#e2e8f0",
        "border":       "#cbd5e1",
        "primary":      "#4f46e5",
        "primary_h":    "#6366f1",
        "primary_d":    "#4338ca",
        "success":      "#059669",
        "success_d":    "#047857",
        "danger":       "#dc2626",
        "danger_d":     "#b91c1c",
        "text":         "#0f172a",
        "text_dim":     "#475569",
        "text_faint":   "#64748b",
        "accent":       "#4f46e5",
    },
}


def combo_box_qss(P: dict) -> str:
    """Stejné QComboBox styly jako ve sidebaru (solver, metrika, …)."""
    return f"""
QComboBox {{
    background-color: {P['surface2']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    min-height: 38px;
    min-width: 0;
    selection-background-color: {P['primary']};
}}
QComboBox:hover {{
    border-color: {P['primary']};
}}
QComboBox:focus {{
    border-color: {P['primary']};
    outline: none;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {P['text_dim']};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {P['surface2']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 6px;
    padding: 4px;
    selection-background-color: {P['primary']};
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    min-height: 30px;
    padding: 4px 8px;
    border-radius: 4px;
}}
"""


def secondary_button_qss(P: dict) -> str:
    """Sekundární tlačítko jako ve sidebaru (Export / Import)."""
    return f"""
QPushButton#SecondaryBtn {{
    background-color: {P['surface2']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 13px;
    min-height: 38px;
    min-width: 0;
}}
QPushButton#SecondaryBtn:hover {{
    background-color: {P['border']};
    border-color: {P['primary']};
    color: {P['text']};
}}
QPushButton#SecondaryBtn:pressed {{
    background-color: {P['surface']};
}}
"""


def build_sidebar_stylesheet(P: dict) -> str:
    return f"""
QWidget#Sidebar {{
    background-color: {P['bg']};
}}
QScrollArea {{
    border: none;
    background-color: {P['bg']};
}}
QWidget#ScrollContent {{
    background-color: {P['bg']};
}}

QLabel#SectionLabel {{
    color: {P['text_dim']};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
}}

QPushButton#SectionToggleBtn {{
    background-color: transparent;
    color: {P['text_dim']};
    border: none;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-align: left;
    padding: 8px 6px 6px 4px;
    margin: 0;
}}
QPushButton#SectionToggleBtn:hover {{
    color: {P['text']};
    background-color: {P['surface2']};
}}
QPushButton#SectionToggleBtn:pressed {{
    color: {P['primary']};
}}

QLabel#DistanceLabel {{
    color: {P['primary']};
    font-size: 14px;
    font-weight: 700;
    background-color: {P['surface']};
    border: 1px solid {P['border']};
    border-radius: 8px;
    padding: 10px 14px;
}}
{combo_box_qss(P)}
QLineEdit {{
    background-color: {P['surface2']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    min-height: 38px;
    selection-background-color: {P['primary']};
}}
QLineEdit:focus {{
    border-color: {P['primary']};
}}
QLineEdit::placeholder {{
    color: {P['text_faint']};
}}

QPushButton#PrimaryBtn {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #7c7ff5, stop:1 #4f52e0);
    color: white;
    border: 2px solid #818cf8;
    border-bottom: 3px solid #3730a3;
    border-radius: 10px;
    padding: 11px 12px;
    font-size: 14px;
    font-weight: 800;
    min-height: 48px;
    min-width: 0;
    letter-spacing: 0.5px;
}}
QPushButton#PrimaryBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #818cf8, stop:1 #6366f1);
    border-color: #a5b4fc;
    border-bottom-color: #4338ca;
}}
QPushButton#PrimaryBtn:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4f46e5, stop:1 #4338ca);
    border-color: #6366f1;
    border-bottom-width: 2px;
    padding-top: 12px;
    padding-bottom: 11px;
}}
QPushButton#PrimaryBtn:disabled {{
    background: {P['border']};
    color: {P['text_faint']};
    border-color: {P['border']};
}}
{secondary_button_qss(P)}
QPushButton#DangerBtn {{
    background-color: transparent;
    color: {P['danger']};
    border: 1px solid {P['danger']};
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 13px;
    min-height: 38px;
    min-width: 0;
}}
QPushButton#DangerBtn:hover {{
    background-color: {P['danger']};
    color: white;
}}
QPushButton#DangerBtn:pressed {{
    background-color: {P['danger_d']};
    color: white;
}}

QPushButton#SuccessBtn {{
    background-color: {P['success']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    min-height: 38px;
}}
QPushButton#SuccessBtn:hover {{
    background-color: {P['success_d']};
}}

QPushButton#ErrorBtn {{
    background-color: {P['danger']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    min-height: 38px;
}}

QListWidget {{
    background-color: {P['surface']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 10px;
    padding: 6px;
    font-size: 12px;
    outline: none;
}}
QListWidget::item {{
    padding: 6px 10px;
    border-radius: 6px;
    color: {P['text']};
    min-height: 24px;
}}
QListWidget::item:hover {{
    background-color: {P['surface2']};
}}
QListWidget::item:selected {{
    background-color: {P['primary']};
    color: white;
}}

QScrollBar:vertical {{
    background: {P['bg']};
    width: 6px;
    margin: 0;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {P['border']};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {P['text_faint']};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
}}
"""


def build_settings_dialog_stylesheet(P: dict) -> str:
    return (
        f"""
QDialog {{
    background-color: {P['surface']};
    color: {P['text']};
}}
QLabel {{
    color: {P['text_dim']};
    font-size: 13px;
}}
QCheckBox {{
    color: {P['text']};
    font-size: 13px;
    spacing: 10px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {P['border']};
    background-color: {P['surface2']};
}}
QCheckBox::indicator:hover {{
    border-color: {P['primary']};
}}
QCheckBox::indicator:checked {{
    background-color: {P['primary']};
    border-color: {P['primary']};
}}
"""
        + combo_box_qss(P)
        + secondary_button_qss(P)
    )


def build_map_settings_button_style(P: dict) -> str:
    return f"""
QPushButton#MapSettingsBtn {{
    background-color: {P['surface']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 20px;
    text-align: center;
    padding: 0;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
}}
QPushButton#MapSettingsBtn:hover {{
    background-color: {P['surface2']};
    border-color: {P['primary']};
    color: {P['primary']};
}}
"""


def build_api_status_panel_style(P: dict) -> str:
    """Stejné materiály jako MapSettingsBtn / combobox (surface, border, radius 8)."""
    return f"""
QWidget#ApiStatusPanel {{
    background-color: {P['surface']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 8px;
}}
QWidget#ApiStatusRow {{
    background-color: transparent;
}}
QLabel#ApiStatusLabel {{
    color: {P['text']};
    font-size: 12px;
    font-weight: 600;
}}
"""


def build_routing_profile_bar_style(P: dict) -> str:
    return f"""
QFrame#RoutingProfileBar {{
    background-color: {P['surface']};
    border: 1px solid {P['border']};
    border-radius: 8px;
}}
QWidget#RoutingProfileTrack {{
    background-color: {P['surface2']};
    border-radius: 8px;
    border: none;
}}
QFrame#RoutingProfileIndicator {{
    background-color: {P['primary']};
    border-radius: 7px;
    border: none;
}}
QToolButton#RoutingProfileBtn {{
    background-color: transparent;
    color: {P['text']};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 0;
    margin: 0;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
}}
QToolButton#RoutingProfileBtn:hover {{
    border-color: {P['primary']};
    color: {P['primary']};
}}
QToolButton#RoutingProfileBtn:checked {{
    background-color: transparent;
    color: {P['text']};
    border-color: transparent;
}}
QToolButton#RoutingProfileBtn:checked:hover {{
    background-color: transparent;
    border-color: transparent;
    color: {P['text']};
}}
QToolButton#RoutingProfileBtn:disabled {{
    color: {P['text_faint']};
    background-color: transparent;
}}
"""


def build_avoid_features_panel_style(P: dict) -> str:
    return f"""
QFrame#AvoidFeaturesPanel {{
    background-color: {P['surface']};
    border: 1px solid {P['border']};
    border-radius: 8px;
}}
QWidget#AvoidFeaturesTrack {{
    background-color: {P['surface2']};
    border-radius: 8px;
    border: none;
}}
QToolButton#AvoidFeatureBtn {{
    background-color: transparent;
    color: {P['text']};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 0;
    margin: 0;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
}}
QToolButton#AvoidFeatureBtn:hover {{
    border-color: {P['primary']};
}}
QToolButton#AvoidFeatureBtn:checked {{
    background-color: {P['danger']};
    border: 1px solid {P['danger_d']};
}}
QToolButton#AvoidFeatureBtn:checked:hover {{
    background-color: {P['danger_d']};
    border-color: {P['danger_d']};
}}
QToolButton#AvoidFeatureBtn:disabled {{
    color: {P['text_faint']};
    background-color: transparent;
    border-color: transparent;
}}
"""


def build_map_search_bar_style(P: dict) -> str:
    return f"""
QFrame#MapSearchBar {{
    background-color: {P['surface']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 8px;
}}
QFrame#MapSearchPopup {{
    background-color: {P['surface']};
    border: 1px solid {P['border']};
    border-radius: 8px;
}}
QLineEdit#MapSearchLineEdit {{
    background-color: {P['surface2']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 6px;
    padding: 0 26px 0 12px;
    margin: 0;
    font-size: 14px;
    selection-background-color: {P['primary']};
}}
QLineEdit#MapSearchLineEdit:focus {{
    border-color: {P['primary']};
}}
QLineEdit#MapSearchLineEdit:disabled {{
    color: {P['text_faint']};
    background-color: {P['surface']};
}}
QListWidget#MapSearchList {{
    background-color: {P['surface2']};
    color: {P['text']};
    border: none;
    border-radius: 4px;
    padding: 2px;
    font-size: 13px;
    outline: none;
}}
QListWidget#MapSearchList::item {{
    padding: 8px 10px;
    border-radius: 4px;
    min-height: 28px;
}}
QListWidget#MapSearchList::item:hover {{
    background-color: {P['border']};
}}
QListWidget#MapSearchList::item:selected {{
    background-color: {P['primary']};
    color: {P['text']};
}}
"""


def central_widget_bg_style(P: dict) -> str:
    return f"background-color: {P['bg']};"


def build_right_route_panel_stylesheet(P: dict) -> str:
    """Pravý panel tras – stejné materiály jako sidebar."""
    return f"""
QWidget#RightRoutePanel {{
    background-color: {P['bg']};
}}
QScrollArea#RightRouteScroll {{
    border: none;
    background-color: {P['bg']};
}}
QWidget#RightRouteScrollContent {{
    background-color: {P['bg']};
}}
QLabel#RightRouteEmpty {{
    color: {P['text_dim']};
    font-size: 13px;
    padding: 12px 8px;
}}
QLabel#RightRouteHint {{
    color: {P['text_faint']};
    font-size: 11px;
    padding: 4px 8px 8px 8px;
}}
QToolButton#RightRouteToggle {{
    background-color: {P['surface']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 8px;
    font-size: 18px;
    font-weight: 700;
    padding: 4px;
    margin: 4px;
    min-width: 32px;
    max-width: 36px;
}}
QToolButton#RightRouteToggle:hover {{
    border-color: {P['primary']};
    color: {P['primary']};
}}
QToolButton#RightRouteFuelHeader {{
    background-color: {P['surface2']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
    padding: 10px 12px;
    text-align: left;
}}
QToolButton#RightRouteFuelHeader:hover {{
    border-color: {P['primary']};
}}
QToolButton#RightRouteFuelHeader:checked {{
    border-color: {P['primary']};
}}
{secondary_button_qss(P)}
QDoubleSpinBox#RightRouteSpin {{
    background-color: {P['surface2']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 8px;
    padding: 6px 8px;
    font-size: 13px;
    min-height: 34px;
    min-width: 0;
}}
QLabel#RightRouteFuelResult {{
    color: {P['primary']};
    font-size: 14px;
    font-weight: 700;
    padding: 4px 2px 4px 0;
}}
"""


def build_right_route_panel_collapsed_stylesheet(P: dict) -> str:
    """Jen šipka nad mapou – panel bez pozadí, tlačítko zůstane čitelné."""
    return f"""
QWidget#RightRoutePanel {{
    background: transparent;
    border: none;
}}
QScrollArea#RightRouteScroll,
QWidget#RightRouteScrollContent {{
    background: transparent;
    border: none;
}}
QToolButton#RightRouteToggle {{
    background-color: {P['surface']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 8px;
    font-size: 18px;
    font-weight: 700;
    padding: 4px;
    margin: 2px 4px 2px 2px;
    min-width: 32px;
    max-width: 36px;
}}
QToolButton#RightRouteToggle:hover {{
    border-color: {P['primary']};
    color: {P['primary']};
}}
"""
