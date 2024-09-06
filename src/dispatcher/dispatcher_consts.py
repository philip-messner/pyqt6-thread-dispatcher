from PyQt6 import QtGui, QtCore

import datetime
import enum


class ThreadStatus(enum.IntEnum):
    UNINIT = -999
    STARTING = -1
    IDLE = 0
    ACTIVE = 1
    SUSPENDED = 2
    DEAD = 3

class ActionStatus(enum.IntEnum):
    UNINIT = -999
    IDLE = 0
    PENDING = 1
    IN_PROGRESS = 2
    COMPLETE = 3
    ERROR = 4
    FAILED = 5


ACTION_STATUS_COLORS = {
    ActionStatus.UNINIT: QtGui.QColor('#000000'),
    ActionStatus.IDLE: QtGui.QColor('#9ea7ad'),
    ActionStatus.PENDING: QtGui.QColor('#2dccff'),
    ActionStatus.IN_PROGRESS: QtGui.QColor('#fce83a'),
    ActionStatus.COMPLETE: QtGui.QColor('#56f000'),
    ActionStatus.ERROR: QtGui.QColor('#ffb302'),
    ActionStatus.FAILED: QtGui.QColor('#ff3838')
}


THREAD_STATUS_COLORS = {
    ThreadStatus.UNINIT: QtGui.QColor('#000000'),
    ThreadStatus.STARTING: QtGui.QColor('#9ea7ad'),
    ThreadStatus.IDLE: QtGui.QColor('#2dccff'),
    ThreadStatus.ACTIVE: QtGui.QColor('#fce83a'),
    ThreadStatus.SUSPENDED: QtGui.QColor('#ffb302'),
    ThreadStatus.DEAD: QtGui.QColor('#ff3838')
}

NUM_PARALLEL_THREADS = 10

# priority queue constants
QUEUE_SHUTDOWN_PRIORITY = -5
WORKER_PAUSE_PRIORITY = 0
WORKER_RESUME_PRIORITY = 1
STD_ACTION_PRIORITY = 2

# worker constants
WORKER_WAIT_TIME = 0.5

ACTION_STATUS_ROLE = QtCore.Qt.ItemDataRole.UserRole + 11
ACTION_PROGRESS_ROLE = QtCore.Qt.ItemDataRole.UserRole + 12
THREAD_STATUS_ROLE = QtCore.Qt.ItemDataRole.UserRole + 13
ACTION_PENDING_ROLE = QtCore.Qt.ItemDataRole.UserRole + 14

DF_INDEX_NAME = 'Index'