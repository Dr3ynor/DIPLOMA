from PyQt6.QtCore import QObject, QThread


def start_worker_in_qthread(
    thread: QThread,
    worker: QObject,
    *,
    on_finished,
    on_failed,
) -> None:
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(on_finished)
    worker.failed.connect(on_failed)
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.start()
