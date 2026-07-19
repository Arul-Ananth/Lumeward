from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage


class SignalBus(QObject):
    status_message = Signal(str)
    log_message = Signal(str)
    progress_update = Signal(int)
    result_ready = Signal(str)
    ocr_requested = Signal(QImage)
    ocr_result = Signal(str)
    ocr_error = Signal(str)
    snip_requested = Signal()


_signal_bus = None


def get_signal_bus() -> SignalBus:
    global _signal_bus
    if _signal_bus is None:
        _signal_bus = SignalBus()
    return _signal_bus
