from PyQt6 import QtCore

import queue
import typing


class QueueListModel(QtCore.QAbstractListModel):

    def __init__(self, q: queue.Queue, **kwargs):
        parent = kwargs.get('parent', None)
        super().__init__(parent=parent)
        if isinstance(q, queue.PriorityQueue):
            self._priority_flag = True
        else:
            self._priority_flag = False

        self.queue = q

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return self.queue.qsize()

    def data(self, index: QtCore.QModelIndex, role: QtCore.Qt.ItemDataRole = QtCore.Qt.ItemDataRole.DisplayRole) -> typing.Any:
        if not index.isValid():
            return None
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if self._priority_flag:
                try:
                    _, action = self.queue.queue[index.row()]
                except IndexError:
                    return None
            else:
                try:
                    action = self.queue.queue[index.row()]
                except IndexError:
                    return None
            if action is None:
                return 'Shutdown Action'
            return action.short_description

        return None

    @QtCore.pyqtSlot()
    def on_queue_content_change(self):
        self.beginResetModel()
        self.endResetModel()
