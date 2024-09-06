from PyQt6 import QtCore

import logging
import queue
import datetime
import enum

from dispatcher import base_action, thread_action
from dispatcher import worker_signal
from dispatcher import action_worker
from dispatcher import dispatcher_consts



class ActionDispatcher(QtCore.QObject):

    logger = logging.getLogger('dispatcher')

    signal_dispatcher_logged_out = QtCore.pyqtSignal()
    signal_dispatcher_ready = QtCore.pyqtSignal()
    signal_dispatcher_shutdown = QtCore.pyqtSignal()

    signal_immediate_queue_contents_changed = QtCore.pyqtSignal()
    signal_demand_queue_contents_changed = QtCore.pyqtSignal()
    signal_series_queue_contents_changed = QtCore.pyqtSignal()

    signal_thread_status_changed = QtCore.pyqtSignal(int)
    signal_thread_action_changed = QtCore.pyqtSignal(int)

    signal_all_threads_running = QtCore.pyqtSignal()
    signal_all_threads_suspended = QtCore.pyqtSignal()
    signal_all_threads_shutdown = QtCore.pyqtSignal()

    signal_dispatcher_created_action = QtCore.pyqtSignal(base_action.BaseAction)

    class DispatcherStatus(enum.IntEnum):

        UNINT = -1
        IDLE = 0
        STARTING = 1
        READY = 2
        PAUSED = 3
        STOPPING = 4
        SHUTDOWN = 5

    def __init__(self, *args, **kwargs):
        parent = kwargs.get('parent', None)
        super().__init__(parent=parent)
        self.dispatcher_status: ActionDispatcher.DispatcherStatus = ActionDispatcher.DispatcherStatus.UNINT
        self.num_parallel_threads = kwargs.get('num_parallel_threads', dispatcher_consts.NUM_PARALLEL_THREADS)

        # define queues
        self.immediate_queue = queue.PriorityQueue()
        self.demand_queue = queue.Queue()
        self.series_queue = queue.PriorityQueue()

        # define the threads for workers
        self.parallel_thread_pool = QtCore.QThreadPool()
        self.parallel_thread_pool.setMaxThreadCount(self.num_parallel_threads)
        self.series_thread = QtCore.QThreadPool()
        self.series_thread.setMaxThreadCount(1)   # there can be only 1...

        # initialize the status dictionary of the worker threads
        self.thread_status_dict: dict[int, dispatcher_consts.ThreadStatus] = {}
        self.thread_action_dict: dict[int, base_action.BaseAction] = {}
        for i in range(self.parallel_thread_pool.maxThreadCount() + self.series_thread.maxThreadCount()):
            self.thread_status_dict[i] = dispatcher_consts.ThreadStatus.UNINIT
            self.thread_action_dict[i] = None

        self.dispatcher_status = ActionDispatcher.DispatcherStatus.IDLE

    def get_num_parallel_threads(self):
        return self.parallel_thread_pool.maxThreadCount()

    @QtCore.pyqtSlot()
    def start_dispatcher(self):
        if self.dispatcher_status != ActionDispatcher.DispatcherStatus.IDLE and \
                self.dispatcher_status != ActionDispatcher.DispatcherStatus.SHUTDOWN:
            self.logger.warning('Attempt was made to start dispatcher while in an invalid state.')
            return
        self.dispatcher_status = ActionDispatcher.DispatcherStatus.STARTING

        self.launch_threads()
        self.dispatcher_status = ActionDispatcher.DispatcherStatus.READY
        self.signal_dispatcher_ready.emit()

    @QtCore.pyqtSlot()
    def stop_dispatcher(self):
        if self.dispatcher_status != ActionDispatcher.DispatcherStatus.READY:
            self.logger.warning('Attempted to shutdown dispatcher in an invalid state.')
            return
        self.dispatcher_status = ActionDispatcher.DispatcherStatus.STOPPING
        self.kill_threads()

        # clear the queues
        while not self.immediate_queue.empty():
            try:
                self.immediate_queue.get(block=False)
            except queue.Empty:
                continue
            self.immediate_queue.task_done()
        while not self.demand_queue.empty():
            try:
                self.demand_queue.get(block=False)
            except queue.Empty:
                continue
            self.demand_queue.task_done()
        while not self.series_queue.empty():
            try:
                self.series_queue.get(block=False)
            except queue.Empty:
                continue
            self.series_queue.task_done()

        self.dispatcher_status = ActionDispatcher.DispatcherStatus.SHUTDOWN
        self.signal_dispatcher_shutdown.emit()

    def launch_threads(self):
        # verify that threads are in a state that supports resuming
        ready = True
        for val in self.thread_status_dict.values():
            ready = ready and (val == dispatcher_consts.ThreadStatus.UNINIT or val == dispatcher_consts.ThreadStatus.DEAD)
        if not ready:
            self.logger.warning('Attempted to launch threads which are not shutdown')
            return

        for i in range(self.parallel_thread_pool.maxThreadCount() + self.series_thread.maxThreadCount()):
            self.thread_status_dict[i] = dispatcher_consts.ThreadStatus.STARTING
            signal = worker_signal.WorkerSignals()
            signal.worker_started.connect(self.on_worker_started)
            signal.worker_shutdown.connect(self.on_worker_shutdown)
            signal.worker_paused.connect(self.on_worker_paused)
            signal.worker_resumed.connect(self.on_worker_resumed)
            signal.worker_starting_action.connect(self.on_worker_starting_action)
            signal.worker_done_with_action.connect(self.on_worker_done_with_action)

            self.logger.debug(f'Launching worker thread {i}')
            if i < self.parallel_thread_pool.maxThreadCount():
                self.parallel_thread_pool.start(action_worker.ActionWorker(action_queue=self.immediate_queue,
                                                                  signal=signal,
                                                                  worker_id=i))
            else:
                self.series_thread.start(action_worker.ActionWorker(action_queue=self.series_queue,
                                                                  signal=signal,
                                                                  worker_id=i))

    def kill_threads(self):
        # verify that threads are in a state that supports resuming
        running = True
        for thread_num, val in self.thread_status_dict.items():
            running = running and (
                        val == dispatcher_consts.ThreadStatus.IDLE or val == dispatcher_consts.ThreadStatus.ACTIVE)
        if not running:
            self.logger.warning('Attempted to kill threads which are not running')
            return

        thread_shutdown = thread_action.ThreadShutdownAction()
        self.signal_dispatcher_created_action.emit(thread_shutdown)
        self.series_queue.put((dispatcher_consts.QUEUE_SHUTDOWN_PRIORITY, thread_shutdown))
        self.signal_series_queue_contents_changed.emit()
        self.logger.debug(f'Killing series action thread')
        self.series_thread.waitForDone()
        for i in range(self.parallel_thread_pool.maxThreadCount()):
            thread_shutdown = thread_action.ThreadShutdownAction()
            self.signal_dispatcher_created_action.emit(thread_shutdown)
            self.immediate_queue.put((dispatcher_consts.QUEUE_SHUTDOWN_PRIORITY, thread_shutdown))
            self.signal_immediate_queue_contents_changed.emit()
            self.logger.debug(f'Killing worker thread {i}')
        self.parallel_thread_pool.waitForDone()
        self.logger.debug('All worker threads have completed.')


    @QtCore.pyqtSlot()
    def suspend_threads(self):
        # verify that threads are in a state that supports suspension
        ready = True
        for val in self.thread_status_dict.values():
            ready = ready and (val == dispatcher_consts.ThreadStatus.IDLE or val == dispatcher_consts.ThreadStatus.ACTIVE)
        if not ready:
            self.logger.warning('Attempted to suspend threads which are not running')
            return

        for i in range(self.parallel_thread_pool.maxThreadCount() + self.series_thread.maxThreadCount()):
            action = thread_action.ThreadPauseAction()
            self.signal_dispatcher_created_action.emit(action)
            if i < self.parallel_thread_pool.maxThreadCount():
                self.immediate_queue.put((dispatcher_consts.WORKER_PAUSE_PRIORITY, action))
                self.signal_immediate_queue_contents_changed.emit()
            else:
                self.series_queue.put((dispatcher_consts.WORKER_PAUSE_PRIORITY, action))
                self.signal_series_queue_contents_changed.emit()

    @QtCore.pyqtSlot()
    def resume_threads(self):
        # verify that threads are in a state that supports resuming
        ready = True
        for val in self.thread_status_dict.values():
            ready = ready and val == dispatcher_consts.ThreadStatus.SUSPENDED
        if not ready:
            self.logger.warning('Attempted to resume threads which are not suspended')
            return

        for i in range(self.parallel_thread_pool.maxThreadCount() + self.series_thread.maxThreadCount()):
            action = thread_action.ThreadResumeAction()
            self.signal_dispatcher_created_action.emit(action)
            if i < self.parallel_thread_pool.maxThreadCount():
                self.immediate_queue.put((dispatcher_consts.WORKER_RESUME_PRIORITY, action))
                self.signal_immediate_queue_contents_changed.emit()
            else:
                self.series_queue.put((dispatcher_consts.WORKER_RESUME_PRIORITY, action))
                self.signal_series_queue_contents_changed.emit()

    @QtCore.pyqtSlot(base_action.BaseAction)
    def add_action_to_demand_queue(self, action: base_action.BaseAction):
        if action:
            self.demand_queue.put(action)
            self.signal_demand_queue_contents_changed.emit()

    @QtCore.pyqtSlot()
    def start_demand_queue(self):
        for _ in range(self.demand_queue.qsize()):
            action: base_action.BaseAction = self.demand_queue.get()
            self.dispatch_action(action)
            self.demand_queue.task_done()
            self.signal_demand_queue_contents_changed.emit()

    @QtCore.pyqtSlot(base_action.BaseAction)
    def dispatch_action(self, action: base_action.BaseAction):
        action.tick('Idle', msg_only=True)
        child_actions: list[base_action.BaseAction] = action.dispatch()
        if child_actions:
            action.total_ticks = len(child_actions) + 1 # each child action plus the process children function
            for child in child_actions:
                self.signal_dispatcher_created_action.emit(child)
                self.dispatch_action(child)
        else:
            if action.series_limited:
                self.series_queue.put((dispatcher_consts.STD_ACTION_PRIORITY, action))
                self.signal_series_queue_contents_changed.emit()
            else:
                self.immediate_queue.put((dispatcher_consts.STD_ACTION_PRIORITY, action))
                self.signal_immediate_queue_contents_changed.emit()

    @QtCore.pyqtSlot(int)
    def on_worker_started(self, worker_id: int):
        self.thread_status_dict[worker_id] = dispatcher_consts.ThreadStatus.IDLE
        self.signal_thread_status_changed.emit(worker_id)
        self.thread_action_dict[worker_id] = None
        self.signal_thread_action_changed.emit(worker_id)

        all_active = True
        for val in self.thread_status_dict.values():
            all_active = all_active and (val == dispatcher_consts.ThreadStatus.IDLE or
                                         val == dispatcher_consts.ThreadStatus.ACTIVE)
            if not all_active:
                break
        if all_active:
            self.signal_all_threads_running.emit()

    @QtCore.pyqtSlot(int)
    def on_worker_shutdown(self, worker_id: int):
        self.thread_status_dict[worker_id] = dispatcher_consts.ThreadStatus.DEAD
        self.signal_thread_status_changed.emit(worker_id)
        self.thread_action_dict[worker_id] = None
        self.signal_thread_action_changed.emit(worker_id)

        all_dead = True
        for val in self.thread_status_dict.values():
            all_dead = all_dead and val == dispatcher_consts.ThreadStatus.DEAD
            if not all_dead:
                break
        if all_dead:
            self.signal_all_threads_shutdown.emit()

    @QtCore.pyqtSlot(int)
    def on_worker_paused(self, worker_id: int):
        self.thread_status_dict[worker_id] = dispatcher_consts.ThreadStatus.SUSPENDED
        self.signal_thread_status_changed.emit(worker_id)
        self.thread_action_dict[worker_id] = None
        self.signal_thread_action_changed.emit(worker_id)

        all_paused = True
        for val in self.thread_status_dict.values():
            all_paused = all_paused and val == dispatcher_consts.ThreadStatus.SUSPENDED
            if not all_paused:
                break
        if all_paused:
            self.dispatcher_status = ActionDispatcher.DispatcherStatus.PAUSED
            self.signal_all_threads_suspended.emit()

    @QtCore.pyqtSlot(int)
    def on_worker_resumed(self, worker_id: int):
        self.thread_status_dict[worker_id] = dispatcher_consts.ThreadStatus.IDLE
        self.signal_thread_status_changed.emit(worker_id)
        self.thread_action_dict[worker_id] = None
        self.signal_thread_action_changed.emit(worker_id)

        all_active = True
        for val in self.thread_status_dict.values():
            all_active = all_active and (val == dispatcher_consts.ThreadStatus.IDLE or
                                         val == dispatcher_consts.ThreadStatus.ACTIVE)
            if not all_active:
                break
        if all_active:
            self.dispatcher_status = ActionDispatcher.DispatcherStatus.READY
            self.signal_dispatcher_ready.emit()

    @QtCore.pyqtSlot(int, base_action.BaseAction)
    def on_worker_starting_action(self, worker_id: int, action: base_action.BaseAction):
        if worker_id < self.parallel_thread_pool.maxThreadCount():
            self.signal_immediate_queue_contents_changed.emit()
        else:
            self.signal_series_queue_contents_changed.emit()
        self.thread_status_dict[worker_id] = dispatcher_consts.ThreadStatus.ACTIVE
        self.signal_thread_status_changed.emit(worker_id)
        self.thread_action_dict[worker_id] = action
        self.signal_thread_action_changed.emit(worker_id)

        # if the action has a parent, update this action status
        while action.parent_action:
            action = action.parent_action
            if action.action_status < dispatcher_consts.ActionStatus.IN_PROGRESS:
                action.action_status = dispatcher_consts.ActionStatus.IN_PROGRESS
                action.datetime_start = datetime.datetime.now()
                action.signal_action_started.emit()
                action.tick('Children Running', msg_only=True)

    @QtCore.pyqtSlot(int, base_action.BaseAction)
    def on_worker_done_with_action(self, worker_id: int, action: base_action.BaseAction):
        self.thread_status_dict[worker_id] = dispatcher_consts.ThreadStatus.IDLE
        self.signal_thread_status_changed.emit(worker_id)
        self.thread_action_dict[worker_id] = None
        self.signal_thread_action_changed.emit(worker_id)

        if action.follow_up_action:
            self.dispatch_action(action.follow_up_action)
            self.signal_dispatcher_created_action.emit(action.follow_up_action)

        if action.parent_action:
            action.parent_action.tick()

        while action.parent_action:

            action = action.parent_action
            if action.action_status < dispatcher_consts.ActionStatus.COMPLETE:
                children_complete = True
                child_state = dispatcher_consts.ActionStatus.IN_PROGRESS
                for child in action.child_actions:
                    if child.action_status < dispatcher_consts.ActionStatus.COMPLETE:
                        children_complete = False
                        break
                    if child.action_status > child_state:
                        child_state = child.action_status
                if children_complete:
                    action.datetime_end = datetime.datetime.now()
                    if action.parent_action:
                        action.parent_action.tick()
                    if child_state == dispatcher_consts.ActionStatus.FAILED:
                        action.action_status = dispatcher_consts.ActionStatus.FAILED
                        action.tick('One or more children failed!', msg_only=True)
                        action.error_exit()
                        return
                    if child_state == dispatcher_consts.ActionStatus.ERROR:
                        action.action_status = dispatcher_consts.ActionStatus.ERROR
                        action.tick('Children Complete (with errors)', msg_only=True)
                    else:
                        action.action_status = dispatcher_consts.ActionStatus.COMPLETE
                        action.tick('Children Complete', msg_only=True)
                    action.process_children()
                    if action.follow_up_action:
                        self.dispatch_action(action.follow_up_action)
                        self.signal_dispatcher_created_action.emit(action.follow_up_action)
