class _MapBridge(QObject):

    def __init__(self, on_click, on_remove):
        super().__init__()
        self._on_click = on_click
        self._on_remove = on_remove

    @pyqtSlot(float, float)
    def onMapClick(self, lat: float, lon: float):
        self._on_click(lat, lon)

    @pyqtSlot(int)
    def onMarkerRightClick(self, index: int):
        self._on_remove(index)

def _setup_map_view_excerpt(self, layout):
    self.view = QWebEngineView()
    layout.addWidget(self.view)
    self._channel = QWebChannel()
    self._bridge = _MapBridge(
        on_click=self._handle_click,
        on_remove=self._handle_remove,
    )
    self._channel.registerObject("bridge", self._bridge)
    self.view.page().setWebChannel(self._channel)
    self.view.setHtml(MAP_HTML, QUrl("https://localhost/"))
