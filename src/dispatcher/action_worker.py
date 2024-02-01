import enum

from PyQt6 import QtCore

import logging
import queue
import enum
import time

from dispatcher import base_action, thread_action
from dispatcher import worker_signal
from dispatcher import dispatcher_consts


class ActionWorker(QtCore.QRunnable):

    logger = logging.getLogger('dispatcher.worker')

    def __init__(self, action_queue: queue.PriorityQueue, signal: worker_signal.WorkerSignals,
                 worker_id: int):
        super().__init__()
        self.action_queue: queue.PriorityQueue = action_queue
        self.worker_id: int = worker_id
        self.signal: worker_signal.WorkerSignals = signal
        self._wait_flag: bool = False
        # maintain reference to the last completed action by the worker to ensure that the reference count never goes to 0
        self._last_action_completed: base_action.BaseAction = None

    def run(self):
        self.signal.worker_started.emit(self.worker_id)
        while True:
            priority: int
            action: base_action.BaseAction
            try:
                if isinstance(self.action_queue, queue.PriorityQueue):
                    priority, action = self.action_queue.queue[0]
                else:
                    action = self.action_queue.queue[0]
            except IndexError:
                time.sleep(dispatcher_consts.WORKER_WAIT_TIME)
                continue

            if self._wait_flag:
                if action and type(action) != thread_action.ThreadResumeAction:
                    time.sleep(dispatcher_consts.WORKER_WAIT_TIME)
                    continue
            else:
                if action and type(action) == thread_action.ThreadResumeAction:
                    time.sleep(dispatcher_consts.WORKER_WAIT_TIME)
                    continue

            priority: int
            action: base_action.BaseAction
            if isinstance(self.action_queue, queue.PriorityQueue):
                priority, action = self.action_queue.get()
            else:
                action = self.action_queue.get()

            # inform the dispatcher that the action has been removed
            self.signal.worker_starting_action.emit(self.worker_id, action)

            if type(action) == thread_action.ThreadShutdownAction:
                action.tick('Killing thread...')
                self.action_queue.task_done()
                action.execute_action()
                self.signal.worker_shutdown.emit(self.worker_id)
                self.logger.debug(f'Worker thread {self.worker_id} has stopped.')
                self._last_action_completed = action
                # self.signal.worker_done_with_action.emit(self.worker_id, action)
                return
            elif type(action) == thread_action.ThreadPauseAction:
                action.tick('Pausing thread...')
                self._wait_flag = True
                self.action_queue.task_done()
                action.execute_action()
                self.signal.worker_paused.emit(self.worker_id)
                self.logger.debug(f'Worker thread {self.worker_id} has been paused.')
                self._last_action_completed = action
                continue
            elif type(action) == thread_action.ThreadResumeAction:
                action.tick('Restarting thread...')
                self._wait_flag = False
                self.action_queue.task_done()
                action.execute_action()
                self.signal.worker_resumed.emit(self.worker_id)
                self.logger.debug(f'Worker thread {self.worker_id} has been restarted.')
                self._last_action_completed = action
                continue
            else:
                self.logger.debug(f'Worker {self.worker_id}: {action.description}')
                action.execute_action()
                self.action_queue.task_done()
                self.signal.worker_done_with_action.emit(self.worker_id, action)
                self._last_action_completed = action
