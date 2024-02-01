from PyQt6 import QtCore
import pandas as pd

import logging

from dispatcher import base_action


class AuxAction(base_action.BaseAction):

    logger = logging.getLogger('dispatcher.aux_action')

    def __init__(self, *arg, **kwargs):
        super().__init__(**kwargs)

    @property
    def description(self):
        return 'AuxAction class'

    @property
    def short_description(self):
        return 'AuxAction class'


class DataframeExcelAction(AuxAction):

    logger = logging.getLogger('dispatcher.df_export')

    def __init__(self, df: pd.DataFrame, file_path: str, *args ,**kwargs):
        super().__init__(*args, **kwargs)
        self.file_path: str = file_path
        self.df: pd.DataFrame = df
        self.total_ticks = 1
        self.sheet_name = kwargs.get('sheet_name', 'Sheet1')
        self.na_rep = kwargs.get('na_rep', '')
        self.float_format = kwargs.get('float_format', None)
        self.index = kwargs.get('index', False)
        self.columns = kwargs.get('columns', None)
        self.engine = kwargs.get('engine', 'xlsxwriter')

    @property
    def short_description(self):
        return f'{self.id:4}: Export dataframe to excel'

    @property
    def description(self):
        return f'{self.id:4} Export dataframe to excel'

    def do_work(self):
        self.tick('Exporting', msg_only=True)
        try:
            self.df.to_excel(self.file_path,
                             sheet_name=self.sheet_name,
                             na_rep=self.na_rep,
                             float_format=self.float_format,
                             index=self.index,
                             columns=self.columns,
                             engine=self.engine)
        except PermissionError:
            self.logger.warning(f'Unable to open file {self.file_path}. Permission denied!')
            self.action_status = consts.ActionStatus.FAILED
            return
        self.action_status = consts.ActionStatus.COMPLETE
