from dispatcher import base_action
from dispatcher import dispatcher_consts
import logging


class ThreadAction(base_action.BaseAction):

    logger = logging.getLogger('dispatcher.thread_action')

    def __init__(self):
        super().__init__()
        self.total_ticks = 1

    def do_work(self):
        self.action_status = dispatcher_consts.ActionStatus.COMPLETE

class ThreadPauseAction(ThreadAction):

    logger = logging.getLogger('dispatcher.thread_pause')

    def __init__(self):
        super().__init__()

    @property
    def description(self):
        return 'Pause Thread Action'

    @property
    def short_description(self):
        return f'{self.id:4}: Pause Thread'

    def do_work(self):
        self.logger.debug(f'Action ID: {self.id} - Pause worker thread.')
        super().do_work()


class ThreadResumeAction(ThreadAction):

    logger = logging.getLogger('dispatcher.thread_resume')

    def __init__(self):
        super().__init__()

    @property
    def description(self):
        return 'Resume Thread Action'

    @property
    def short_description(self):
        return f'{self.id:4}: Restart Thread'

    def do_work(self):
        self.logger.debug(f'Action ID: {self.id} - Resume worker thread.')
        super().do_work()


class ThreadShutdownAction(ThreadAction):

    logger = logging.getLogger('dispatcher.thread_shutdown')

    def __init__(self):
        super().__init__()

    @property
    def description(self):
        return 'Shutdown Thread Action'

    @property
    def short_description(self):
        return f'{self.id:4}: Kill thread'

    def do_work(self):
        self.logger.debug(f'Action ID: {self.id} - Shutdown Worker Thread.')
        super().do_work()
