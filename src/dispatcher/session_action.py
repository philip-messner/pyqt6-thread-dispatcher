import requests

import enum
import logging
import typing

from dispatcher import base_action, base_user


class SessionAction(base_action.BaseAction):

    logger = logging.getLogger('dispatcher.session_action')

    class ErrorFlags(enum.IntFlag):

        NO_ERROR = 0
        UNSPECIFIED = 1
        CON_ERROR = 2
        CRED_ERROR = 4
        SERVER_ERROR = 8
        KEY_VAL_ERROR = 16

    class UrlOperation(enum.IntEnum):

        GET = 0
        POST = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = kwargs.get('base_url', '')
        self.session: requests.Session = requests.Session()
        self.session_key: str = kwargs.get('session_key', None)
        session_values: dict[str, typing.Any] = kwargs.get('session_values', None)
        if session_values:
            self.session_values = session_values
        else:
            self.session_values = {}
        self.usr: base_user.BaseUser = kwargs.get('usr', None)
        session_cookies: dict[str, typing.Any] = kwargs.get('session_cookies', None)
        if session_cookies:
            self.session.cookies.update(session_cookies)

    def tear_down(self):
        self.session.close()
        self.session = None
        self.session_values.clear()
        self.session_key = None
        super().tear_down()

    def set_session_cookies(self, session_cookies: dict[str, typing.Any]):
        if not session_cookies:
            raise ValueError('Cannot set an invalid set of session cookies.')
        self.session.cookies.update(session_cookies)

    def set_session_values(self, session_values: dict[str, typing.Any]):
        self.session_values = session_values

    def set_session_key(self, session_key: str):
        self.session_key = session_key

    def set_user_info(self, user_object: base_user.BaseUser):
        self.usr = user_object

    def get_session_cookies(self):
        if self.session:
            return requests.utils.dict_from_cookiejar(self.session.cookies)
        else:
            return {}

    def url_request(self, op_type: UrlOperation, url: str, headers: dict, payload: dict,
                    neg_auth: bool = False, verbose_debug: bool = False):
        if headers is None:
            headers = {}
        if payload is None:
            payload = {}
        try:
            if op_type == SessionAction.UrlOperation.GET:
                if neg_auth:
                    r = self.session.get(self.base_url + url, headers=headers, auth=HttpNegotiateAuth())
                else:
                    r = self.session.get(self.base_url + url, headers=headers)
            elif op_type == SessionAction.UrlOperation.POST:
                if neg_auth:
                    r = self.session.post(self.base_url + url, headers=headers, data=payload, auth=HttpNegotiateAuth())
                else:
                    r = self.session.post(self.base_url + url, headers=headers, data=payload)
            else:
                raise ValueError('Unknown op_type sent to function.')
            if verbose_debug:
                self.logger.debug(f'{r.request.method} {r.request.url}')
                self.logger.debug(f'...Headers: {r.request.headers}')
                self.logger.debug(f'...Status code: {r.status_code}')
            if r.status_code == 400:
                self.logger.warning(f'{r.text}')
                self.error_flags = self.error_flags | SessionAction.ErrorFlags.SERVER_ERROR
                return None
            elif r.status_code > 400:
                self.logger.warning(f'{r.request.method} {r.request.url}: status code {r.status_code}')
                self.error_flags = self.error_flags | SessionAction.ErrorFlags.SERVER_ERROR
                return None

        except requests.exceptions.ConnectionError as err:
            self.error_flags = self.error_flags | SessionAction.ErrorFlags.CON_ERROR
            self.logger.exception(err)
            return None

        return r


class LoginAction(SessionAction):

    logger = logging.getLogger('dispatcher.login_action')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def description(self):
        return f'Login user action'

    @property
    def short_description(self):
        return f'Login user action'

    def execute_action(self):
        self.setup()
        self.do_work()

    def do_work(self):
        raise ValueError('This function cannot be executed on a base class')

    def get_session_values(self):
        return self.session_values.copy()

    def get_session_key(self):
        return self.session_key


class LogoutAction(SessionAction):

    logger = logging.getLogger('dispatcher.logout_action')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def description(self):
        return f'Logout user action'

    @property
    def short_description(self):
        return f'Logout user action'

    def do_work(self):
        raise ValueError('This function cannot be executed on a base class')


# these classes are sentinel classes to work as functional substitutes for passing NONE in signals
class LoginActionNone(LoginAction):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class LogoutActionNone(LogoutAction):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
