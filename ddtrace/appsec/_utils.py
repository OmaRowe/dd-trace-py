import os

from ddtrace.appsec import _asm_request_context
from ddtrace.appsec._constants import API_SECURITY
from ddtrace.constants import APPSEC_ENV
from ddtrace.internal.logger import get_logger
from ddtrace.internal.utils.http import _get_blocked_template  # noqa
from ddtrace.internal.utils.http import parse_form_multipart  # noqa
from ddtrace.internal.utils.http import parse_form_params  # noqa
from ddtrace.settings import _config as config


log = get_logger(__name__)


def parse_response_body(raw_body):
    import json

    import xmltodict

    from ddtrace.appsec._constants import SPAN_DATA_NAMES
    from ddtrace.contrib.trace_utils import _get_header_value_case_insensitive

    if not raw_body:
        return

    if isinstance(raw_body, dict):
        return raw_body

    headers = _asm_request_context.get_waf_address(SPAN_DATA_NAMES.RESPONSE_HEADERS_NO_COOKIES)
    if not headers:
        return
    content_type = _get_header_value_case_insensitive(
        dict(headers),
        "content-type",
    )
    if not content_type:
        return

    def access_body(bd):
        if isinstance(bd, list) and isinstance(bd[0], (str, bytes)):
            bd = bd[0][:0].join(bd)
        if getattr(bd, "decode", False):
            bd = bd.decode("UTF-8", errors="ignore")
        if len(bd) >= API_SECURITY.MAX_PAYLOAD_SIZE:
            raise ValueError("response body larger than 16MB")
        return bd

    req_body = None
    try:
        # TODO handle charset
        if "json" in content_type:
            req_body = json.loads(access_body(raw_body))
        elif "xml" in content_type:
            req_body = xmltodict.parse(access_body(raw_body))
        else:
            return
    except BaseException:
        log.debug("Failed to parse response body", exc_info=True)
    else:
        return req_body


def _appsec_rc_features_is_enabled() -> bool:
    if config._remote_config_enabled:
        return APPSEC_ENV not in os.environ
    return False


class _UserInfoRetriever:
    def __init__(self, user):
        self.user = user

        self.possible_user_id_fields = ["pk", "id", "uid", "userid", "user_id", "PK", "ID", "UID", "USERID"]
        self.possible_login_fields = ["username", "user", "login", "USERNAME", "USER", "LOGIN"]
        self.possible_email_fields = ["email", "mail", "address", "EMAIL", "MAIL", "ADDRESS"]
        self.possible_name_fields = ["name", "fullname", "full_name", "NAME", "FULLNAME", "FULL_NAME"]

    def find_in_user_model(self, possible_fields):
        for field in possible_fields:
            value = getattr(self.user, field, None)
            if value:
                return value

        return None  # explicit to make clear it has a meaning

    def get_userid(self):
        user_login = getattr(self.user, config._user_model_login_field, None)
        if user_login:
            return user_login

        return self.find_in_user_model(self.possible_user_id_fields)

    def get_username(self):
        username = getattr(self.user, config._user_model_name_field, None)
        if username:
            return username

        if hasattr(self.user, "get_username"):
            try:
                return self.user.get_username()
            except Exception:
                log.debug("User model get_username member produced an exception: ", exc_info=True)

        return self.find_in_user_model(self.possible_login_fields)

    def get_user_email(self):
        email = getattr(self.user, config._user_model_email_field, None)
        if email:
            return email

        return self.find_in_user_model(self.possible_email_fields)

    def get_name(self):
        name = getattr(self.user, config._user_model_name_field, None)
        if name:
            return name

        return self.find_in_user_model(self.possible_name_fields)

    def get_user_info(self):
        """
        In safe mode, try to get the user id from the user object.
        In extended mode, try to also get the username (which will be the returned user_id),
        email and name.
        """
        user_extra_info = {}

        if config._automatic_login_events_mode == "extended":
            user_id = self.get_username()
            if not user_id:
                user_id = self.find_in_user_model(self.possible_user_id_fields)

            user_extra_info = {
                "login": user_id,
                "email": self.get_user_email(),
                "name": self.get_name(),
            }
        else:  # safe mode, default
            user_id = self.get_userid()

        if not user_id:
            return None, {}

        return user_id, user_extra_info
