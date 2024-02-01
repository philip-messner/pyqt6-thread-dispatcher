from PyQt6 import QtCore
from dispatcher.base_action import BaseAction


class WorkerSignals(QtCore.QObject):

    worker_started = QtCore.pyqtSignal(int)
    worker_shutdown = QtCore.pyqtSignal(int)
    worker_paused = QtCore.pyqtSignal(int)
    worker_resumed = QtCore.pyqtSignal(int)
    worker_starting_action = QtCore.pyqtSignal(int, BaseAction)
    worker_done_with_action = QtCore.pyqtSignal(int, BaseAction)
