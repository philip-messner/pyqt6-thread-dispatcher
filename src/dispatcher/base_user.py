from PyQt6 import QtCore
from cryptography.fernet import Fernet

import logging
import pickle
import pathlib


class BaseUser(QtCore.QObject):

    logger = logging.getLogger('dispatcher.base_user')

    def __init__(self, *args, **kwargs):
        parent = kwargs.get('parent', None)
        super().__init__(parent=parent)
        self.username: str = kwargs.get('username', None)
        self.password: str = kwargs.get('password', None)
        self.pin: str = kwargs.get('pin', None)
        self._pin_verified_flag: bool = False

    def set_pin_verified(self):
        self._pin_verified_flag = True

    def load_data_from_file(self, fnet_key: bytes, file_path: str | pathlib.Path, **kwargs):
        if not fnet_key:
            raise ValueError('A Fernet key must be supplied in order to load user data from file.')
        if not file_path:
            raise ValueError('A file path is required.')

        if not file_path.is_file():
            self.logger.debug('No user data file found.')
            return False

        with open(file_path, 'rb') as f:
            try:
                (self.username, crypt_password, crypt_pin) = pickle.load(f)
            except pickle.PickleError as e:
                self.logger.warning('An error occurred when loading the user data.')
                self.logger.exception(e)
                return False

        fernet = Fernet(fnet_key)

        self.password = fernet.decrypt(crypt_password).decode()
        self.pin = fernet.decrypt(crypt_pin).decode()
        self.logger.debug('Successfully loaded user information.')
        return True

    def delete_user_file(self, file_path: str | pathlib.Path, **kwargs):
        if not file_path:
            raise ValueError(
                    '(BaseUser: load from file: a file_path must be supplied to this function.')

        file_path.unlink(missing_ok=True)

    def save_user_to_file(self, fnet_key: bytes, file_path: str | pathlib.Path, **kwargs):
        if not fnet_key:
            raise ValueError('A Fernet key must be supplied in order to save user data to file.')
        if not file_path:
            raise ValueError(
                    '(BaseUser: load from file: a file_path must be supplied to this function.')

        fernet = Fernet(fnet_key)
        crypt_password = fernet.encrypt(self.password.encode())
        crypt_pin = fernet.encrypt(self.pin.encode())

        with open(file_path, 'wb') as f:
            try:
                pickle.dump((self.username, crypt_password, crypt_pin), f)
                self.logger.debug(f'User data successfully writen to {file_path}')
            except pickle.PickleError as e:
                self.logger.warning('An error occurred while saving the user file.')
                self.logger.exception(e)
                return False

        return True

    def __repr__(self):
        return f'BaseUser(username={self.username}, password={self.password}, pin={self.pin})'

    def __str__(self):
        return self.username.upper()
