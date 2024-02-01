from PyQt6 import QtCore, QtWidgets, QtGui

from dispatcher import base_action
from dispatcher import dispatcher_consts

class ActionStatusModel(QtCore.QAbstractItemModel):

    def __init__(self, *args, **kwargs):
        parent = kwargs.get('parent', None)
        super().__init__(parent=parent)
        base_action_list: list[base_action.BaseAction] = kwargs.get('action_list', None)
        if base_action_list is None:
            base_action_list = []
        self.root_actions: list[base_action.BaseAction] = base_action_list

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            parentActions = self.root_actions
        else:
            parent_action = self.get_action_from_index(parent)
            parentActions = parent_action.child_actions
        if row >= len(parentActions):
            return QtCore.QModelIndex()
        childAction = parentActions[row]
        if childAction:
            return self.createIndex(row, column, childAction)
        else:
            return QtCore.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        action = self.get_action_from_index(index)
        parent_action = action.parent_action
        if parent_action:
            grandparent_action = parent_action.parent_action
            if grandparent_action:
                return self.createIndex(grandparent_action.child_actions.index(parent_action), 0, parent_action)
            else:
                return self.createIndex(self.root_actions.index(parent_action), 0, parent_action)

        else:
            return QtCore.QModelIndex()
        # for root_action in self.root_actions:
        #     if action in root_action.child_actions:
        #         return self.createIndex(self.root_actions.index(root_action), 0, root_action)
        #     for child_action in root_action.child_actions:
        #         if action in child_action.child_actions:
        #             return self.createIndex(root_action.index(child_action), 0, child_action)

    def get_action_from_index(self, index: QtCore.QModelIndex):
        return index.internalPointer() if index.isValid() else None

    def rowCount(self, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            parent_actions = self.root_actions
        else:
            parent_actions = parent.internalPointer().child_actions
        return len(parent_actions)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 5

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        action: base_action.BaseAction = index.internalPointer()
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return action.short_description
            elif index.column() == 1:
                return action.current_process
            elif index.column() == 3:
                return action.pct_complete
            elif index.column() == 4:
                return action.duration_in_seconds
            return None
        elif role == dispatcher_consts.ACTION_STATUS_ROLE and (index.column() == 2 or index.column() == 3):
            return action.action_status
        elif role == dispatcher_consts.ACTION_PROGRESS_ROLE and index.column() == 3:
            return action.pct_complete
        elif role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            return QtCore.Qt.AlignmentFlag.AlignCenter
        else:
            return None

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemFlag.NoItemFlags
        else:
            return QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable

    def headerData(self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if orientation == QtCore.Qt.Orientation.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            if section == 0:
                return "Action"
            elif section == 1:
                return "Task"
            elif section == 2:
                return "Status"
            elif section == 3:
                return "Progress"
            elif section == 4:
                return 'Execution Time'
        else:
            return None

    def get_index(self, action: base_action.BaseAction):
        for rootIndex, rootNode in enumerate(self.root_actions):
            if rootNode is action:
                return self.createIndex(rootIndex, 0, rootNode)
            for childIndex, childNode in enumerate(rootNode.child_actions):
                if childNode is action:
                    return self.createIndex(childIndex, 0, childNode)
        return QtCore.QModelIndex()

    @QtCore.pyqtSlot(base_action.BaseAction)
    def add_action(self, action: base_action.BaseAction):
        parent = action.parent_action
        if not parent:
            # action is a root action
            self.beginInsertRows(QtCore.QModelIndex(), len(self.root_actions), len(self.root_actions))
            self.root_actions.append(action)
            self.endInsertRows()
        else:
            parent_index = self.get_index(parent)
            self.beginInsertRows(parent_index, len(parent.child_actions), len(parent.child_actions))
            parent.child_actions.append(action)
            self.endInsertRows()

    @QtCore.pyqtSlot(base_action.BaseAction)
    def update_action_status(self, action: base_action.BaseAction):
        # Find the index of the RequestAction object in the model
        index = self.createIndex(self.get_index(action).row(), 2, action)
        index2 = self.createIndex(self.get_index(action).row(), 3, action)
        self.dataChanged.emit(index, index2, [dispatcher_consts.ACTION_STATUS_ROLE])
        index3 = self.createIndex(self.get_index(action).row(), 1, action)
        self.dataChanged.emit(index3, index3, [QtCore.Qt.ItemDataRole.DisplayRole])
        index4 = self.createIndex(self.get_index(action).row(), 4, action)
        self.dataChanged.emit(index4, index4, [QtCore.Qt.ItemDataRole.DisplayRole])

    @QtCore.pyqtSlot(base_action.BaseAction)
    def on_action_tick(self, action: base_action.BaseAction):
        task_idx = self.createIndex(self.get_index(action).row(), 1, action)
        self.dataChanged.emit(task_idx, task_idx, [QtCore.Qt.ItemDataRole.DisplayRole])
        prg_idx = self.createIndex(self.get_index(action).row(), 3, action)
        self.dataChanged.emit(prg_idx, prg_idx, [dispatcher_consts.ACTION_PROGRESS_ROLE])


class ActionStatusDelegate(QtWidgets.QStyledItemDelegate):

    CIRCLE_SIZE = 6

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def paint(self, painter, option, index):
        if not index.isValid():
            return
        # get the correct color from the 'status role'
        painter.save()
        status = index.data(role=dispatcher_consts.ACTION_STATUS_ROLE)
        if status is not None:
            color = dispatcher_consts.ACTION_STATUS_COLORS.get(status, QtGui.QColor('#ff3838'))
            painter.setBrush(color)
            painter.drawEllipse(option.rect.center(), self.CIRCLE_SIZE, self.CIRCLE_SIZE)

        painter.restore()


class ProgressDelegate(QtWidgets.QStyledItemDelegate):

    PIXEL_BUFFER = 4

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def paint(self, painter, option, index):
        if not index.isValid():
            return
        # get the color from the status role
        status = index.data(role=dispatcher_consts.ACTION_STATUS_ROLE)
        if not status:
            color = QtGui.QColor('#2dccff')
        else:
            color = dispatcher_consts.ACTION_STATUS_COLORS.get(status, QtGui.QColor('#2dccff'))
        color_name = color.name()

        # draw the progress bar
        progress = index.data(role=dispatcher_consts.ACTION_PROGRESS_ROLE)

        if progress is not None:
            progressBar = QtWidgets.QProgressBar()
            progressBar.setMinimum(0)
            progressBar.setMaximum(100)
            progressBar.setValue(progress)
            progressBar.setFormat('%p%')
            progressBar.setTextVisible(True)
            progressBar.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            style = "QProgressBar { border: 2px solid grey; border-radius: 5px; text-align: center; margin-right: 0.2em;}"
            style += f"QProgressBar::chunk {{ background-color: {color_name}; width: 20px; }}"
            progressBar.setStyleSheet(style)
            progressBar.resize(option.rect.width() - (2 * self.PIXEL_BUFFER),
                               option.rect.height() - (2 * self.PIXEL_BUFFER))
            painter.save()
            painter.translate(option.rect.x() + self.PIXEL_BUFFER, option.rect.y() + self.PIXEL_BUFFER)
            progressBar.render(painter)
            painter.restore()
