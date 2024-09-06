from PyQt6 import QtCore, QtWidgets, QtGui
import typing
from dispatcher import base_action
from dispatcher import dispatcher_consts


class ThreadStatusModel(QtCore.QAbstractTableModel):

    def __init__(
        self,
        thread_status_dict: dict[int, dispatcher_consts.ThreadStatus],
        thread_action_dict: dict[int, base_action.BaseAction],
        **kwargs
    ):
        parent = kwargs.get("parent", None)
        super().__init__(parent=parent)
        self.thread_status_dict = thread_status_dict
        self.thread_action_dict = thread_action_dict
        self._has_series_thread = kwargs.get("has_series_thread", True)

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self.thread_status_dict)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 3

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> typing.Any:
        if section < 0 or section >= len(self.thread_status_dict):
            return None
        if orientation != QtCore.Qt.Orientation.Horizontal:
            return None
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if section == 0:
                return "Worker ID"
            if section == 1:
                return "Status"
            if section == 2:
                return "Current Action"
        if role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            return QtCore.Qt.AlignmentFlag.AlignCenter

        return None

    def data(
        self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> typing.Any:
        if not index.isValid():
            return None

        worker_id = list(self.thread_status_dict.keys())[index.row()]

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return worker_id
            elif index.column() == 1:
                return self.thread_status_dict.get(worker_id, None)
            elif index.column() == 2:
                action = self.thread_action_dict.get(worker_id, None)
                if not action:
                    return ""
                return action.short_description
            return None

        elif role == dispatcher_consts.THREAD_STATUS_ROLE and index.column() == 1:
            return self.thread_status_dict.get(worker_id, None)

        elif role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            return QtCore.Qt.AlignmentFlag.AlignCenter

        return None

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
        if not index.isValid():
            return QtCore.Qt.ItemFlag.NoItemFlags

        return QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable

    @QtCore.pyqtSlot(int)
    def on_thread_status_update(self, worker_id: int):
        try:
            dict_idx = list(self.thread_status_dict.keys()).index(worker_id)
        except ValueError:
            return
        mdl_idx = self.createIndex(dict_idx, 1)
        self.dataChanged.emit(mdl_idx, mdl_idx)

    @QtCore.pyqtSlot(int)
    def on_thread_action_update(self, worker_id: int):
        try:
            dict_idx = list(self.thread_action_dict.keys()).index(worker_id)
        except ValueError:
            return
        mdl_idx = self.createIndex(dict_idx, 2)
        self.dataChanged.emit(mdl_idx, mdl_idx)


class ThreadStatusDelegate(QtWidgets.QStyledItemDelegate):

    CIRCLE_SIZE = 6

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def paint(self, painter, option, index):
        if not index.isValid():
            return
        # get the correct color from the 'status role'
        painter.save()
        status = index.data(role=dispatcher_consts.THREAD_STATUS_ROLE)
        if status is not None:
            color = dispatcher_consts.THREAD_STATUS_COLORS.get(
                status, QtGui.QColor("#ff3838")
            )
            painter.setBrush(color)
            painter.drawEllipse(
                option.rect.center(), self.CIRCLE_SIZE, self.CIRCLE_SIZE
            )

        painter.restore()


class CircleStatusWidget(QtWidgets.QWidget):

    BUFFER_SPACE = 10
    MAX_RADIUS = 10

    def __init__(self, num_threads, parent=None):
        super().__init__(parent)
        # self.resize(293, 20)
        self.num_threads = num_threads
        self.status = [
            dispatcher_consts.THREAD_STATUS_COLORS[
                dispatcher_consts.ThreadStatus.UNINIT
            ]
            for _ in range(num_threads)
        ]

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        radius = min(
            (self.width() - ((self.num_threads - 1) * self.BUFFER_SPACE))
            // (2 * self.num_threads),
            self.height() // 2,
        )
        if radius > self.MAX_RADIUS:
            radius = self.MAX_RADIUS
        for i in range(self.num_threads):
            color = self.status[i]
            painter.setBrush(QtGui.QColor(color))
            x = ((2 * i + 1) * radius) + (self.BUFFER_SPACE * i)
            y = self.height() // 2
            painter.drawEllipse(x - radius, y - radius, 2 * radius, 2 * radius)

        # print(radius)

    def minimumSizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(
            (self.MAX_RADIUS * 2 * self.num_threads)
            + (self.BUFFER_SPACE * self.num_threads),
            30,
        )

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(
            (self.MAX_RADIUS * 2 * self.num_threads)
            + (self.BUFFER_SPACE * self.num_threads),
            30,
        )

    def set_status(self, thread_num, color):
        self.status[thread_num] = color
        self.update()


class ThreadStatusWidget(QtWidgets.QWidget):

    def __init__(
        self,
        num_parallel_threads: int,
        thread_status_dict: dict[int, dispatcher_consts.ThreadStatus],
        **kwargs
    ):
        parent = kwargs.get("parent", None)
        super().__init__(parent=parent)
        self.flag_series_thread_enabled = kwargs.get("series_thread_enabled", True)
        self.parallel_status_widget = CircleStatusWidget(
            num_parallel_threads, parent=self
        )
        self.series_status_widget = CircleStatusWidget(1, parent=self)
        self.lbl_status = QtWidgets.QLabel("Thread Status: ", self)
        self.thread_status_dict = thread_status_dict
        self.btn_thread_view = QtWidgets.QPushButton("Open View", self)
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setSpacing(5)
        main_layout.addWidget(self.lbl_status, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(
            self.parallel_status_widget, 0, QtCore.Qt.AlignmentFlag.AlignCenter
        )
        if self.flag_series_thread_enabled:
            line_seperator = QtWidgets.QFrame(self)
            line_seperator.setFrameShape(QtWidgets.QFrame.Shape.VLine)
            line_seperator.setFrameShadow(QtWidgets.QFrame.Shadow.Plain)
            main_layout.addWidget(line_seperator, 0)
            main_layout.addWidget(
                self.series_status_widget, 0, QtCore.Qt.AlignmentFlag.AlignCenter
            )
        main_layout.addWidget(
            self.btn_thread_view, 0, QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.setLayout(main_layout)

    @QtCore.pyqtSlot(int)
    def set_status(self, thread_id: int):
        if thread_id not in self.thread_status_dict:
            return
        thread_dict_idx = list(self.thread_status_dict.keys()).index(thread_id)
        status = self.thread_status_dict[thread_id]
        color = dispatcher_consts.THREAD_STATUS_COLORS[status]
        if (
            self.flag_series_thread_enabled
            and thread_dict_idx == len(self.thread_status_dict) - 1
        ):
            self.series_status_widget.set_status(0, color)
        else:
            self.parallel_status_widget.set_status(thread_dict_idx, color)

    def sizeHint(self) -> QtCore.QSize:

        return QtCore.QSize(350, 25)
