from PyQt6 import QtCore

import logging
import typing
import datetime
import enum

from dispatcher import base_user
from dispatcher import dispatcher_consts


class BaseAction(QtCore.QObject):

    logger = logging.getLogger('dispatcher.base_action')
    num_actions = 0

    # signals
    signal_action_started = QtCore.pyqtSignal()
    signal_action_tick = QtCore.pyqtSignal()
    signal_action_finished = QtCore.pyqtSignal()

    class ErrorFlags(enum.IntFlag):

        NO_ERROR = 0
        UNSPECIFIED = 1

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.id: int = BaseAction.num_actions
        if BaseAction.num_actions == 999999999:
            BaseAction.num_actions = 0
        else:
            BaseAction.num_actions += 1
        self.error_flags = BaseAction.ErrorFlags.NO_ERROR
        self.payload: typing.Any = None
        self.current_process: str = 'Idle...'
        self.tick_count: int = 0
        self.total_ticks: int = 0
        self.pct_complete: int = 0
        self.datetime_start: datetime.datetime = None
        self.datetime_end: datetime.datetime = None
        self.action_status: dispatcher_consts.ActionStatus = dispatcher_consts.ActionStatus.IDLE
        self.parent_action: BaseAction = kwargs.get('parent_action', None)
        self.child_actions: list[BaseAction] = []
        self.follow_up_action: BaseAction = None
        self.series_limited: bool = False
        # self.logger.debug(f'Action id \'{self.id}\' created. {self.description}')

    @property
    def description(self):
        return 'BaseAction class'

    @property
    def short_description(self):
        return 'BaseAction class'

    @property
    def duration_in_seconds(self) -> str:
        if self.datetime_start is None or self.datetime_end is None:
            return '----'
        else:
            diff = self.datetime_end - self.datetime_start
            return f'{diff.total_seconds():.2f} sec'

    def setup(self):
        self.datetime_start = datetime.datetime.now()
        self.logger.debug(f'Starting: {self.description}')
        self.action_status = dispatcher_consts.ActionStatus.IN_PROGRESS
        self.current_process = 'Pending'

    def do_work(self):
        raise ValueError('BaseAction objects are not intended to be executed.')

    def tear_down(self):
        self.datetime_end = datetime.datetime.now()
        self.tick_count = self.total_ticks
        self.pct_complete = 100
        if self.action_status < dispatcher_consts.ActionStatus.COMPLETE:
            self.logger.warning('Action Status has not been properly updated at tear down.')
        if self.action_status == dispatcher_consts.ActionStatus.COMPLETE:
            self.current_process = 'Complete!'
        elif self.action_status == dispatcher_consts.ActionStatus.ERROR:
            self.current_process = 'Complete (Error exists)'
        else:
            self.current_process = 'Failed!'
        self.signal_action_finished.emit()

    def execute_action(self):
        self.setup()
        self.do_work()
        self.tear_down()

    def tick(self, curr_process: str = '', msg_only: bool = False):
        if curr_process:
            self.current_process = curr_process
        if not msg_only:
            self.tick_count += 1
            if self.total_ticks > 0:
                self.pct_complete = int((self.tick_count / self.total_ticks) * 100)
                if self.pct_complete > 100:
                    self.pct_complete = 100
        self.signal_action_tick.emit()

    def dispatch(self):
        return []

    def process_children(self):
        self.signal_action_finished.emit()
        return

    def error_exit(self):
        self.signal_action_finished.emit()

    def set_session_values(self, session_values: dict[str, typing.Any]):
        return

    def set_user_info(self, user_object: base_user.BaseUser):
        return

    def set_session_cookies(self, session_values: dict[str, typing.Any]):
        return

    def set_session_key(self, session_key: str):
        return

    def __lt__(self, other):
        if isinstance(other, BaseAction):
            return self.id < other.id
        return False

    def __eq__(self, other):
        if isinstance(other, BaseAction):
            return self.id == other.id
        return True

    def __le__(self, other):
        if isinstance(other, BaseAction):
            return self.id <= other.id
        return True
