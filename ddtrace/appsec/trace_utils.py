from typing import Optional
from typing import TYPE_CHECKING

from ddtrace.appsec import _asm_request_context
from ddtrace.contrib.trace_utils import set_user
from ddtrace.internal import core


if TYPE_CHECKING:
    from ddtrace import Span
    from ddtrace import Tracer

from ddtrace import config
from ddtrace import constants
from ddtrace.appsec._constants import APPSEC
from ddtrace.appsec._constants import LOGIN_EVENTS_MODE
from ddtrace.appsec._constants import WAF_CONTEXT_NAMES
from ddtrace.ext import SpanTypes
from ddtrace.ext import user
from ddtrace.internal.compat import six
from ddtrace.internal.logger import get_logger


log = get_logger(__name__)


def _asm_manual_keep(span):
    # type: (Span) -> None
    from ddtrace.internal.constants import SAMPLING_DECISION_TRACE_TAG_KEY
    from ddtrace.internal.sampling import SamplingMechanism

    span.set_tag(constants.MANUAL_KEEP_KEY)
    # set decision maker to ASM = -5
    span.set_tag_str(SAMPLING_DECISION_TRACE_TAG_KEY, "-%d" % SamplingMechanism.APPSEC)


def _track_user_login_common(
    tracer,  # type: Tracer
    success,  # type: bool
    metadata=None,  # type: Optional[dict]
    login_events_mode=LOGIN_EVENTS_MODE.SDK,  # type: str
    login=None,  # type: Optional[str]
    name=None,  # type: Optional[str]
    email=None,  # type: Optional[str]
    span=None,  # type: Optional[Span]
):
    # type: (...) -> Optional[Span]

    if span is None:
        span = tracer.current_root_span()
    if span:
        success_str = "success" if success else "failure"
        tag_prefix = "%s.%s" % (APPSEC.USER_LOGIN_EVENT_PREFIX, success_str)
        span.set_tag_str("%s.track" % tag_prefix, "true")

        # This is used to mark if the call was done from the SDK of the automatic login events
        if login_events_mode == LOGIN_EVENTS_MODE.SDK:
            span.set_tag_str("%s.sdk" % tag_prefix, "true")
        else:
            span.set_tag_str("%s.auto.mode" % tag_prefix, str(login_events_mode))

        if metadata is not None:
            for k, v in six.iteritems(metadata):
                span.set_tag_str("%s.%s" % (tag_prefix, k), str(v))

        if login:
            span.set_tag_str("%s.login" % tag_prefix, login)

        if email:
            span.set_tag_str("%s.email" % tag_prefix, email)

        if name:
            span.set_tag_str("%s.username" % tag_prefix, name)

        _asm_manual_keep(span)
        return span
    else:
        log.warning(
            "No root span in the current execution. Skipping track_user_success_login tags. "
            "See https://docs.datadoghq.com/security_platform/application_security/setup_and_configure/"
            "?tab=set_user&code-lang=python for more information.",
        )
    return None


def track_user_login_success_event(
    tracer,  # type: Tracer
    user_id,  # type: str
    metadata=None,  # type: Optional[dict]
    login=None,  # type: Optional[str]
    name=None,  # type: Optional[str]
    email=None,  # type: Optional[str]
    scope=None,  # type: Optional[str]
    role=None,  # type: Optional[str]
    session_id=None,  # type: Optional[str]
    propagate=False,  # type: bool
    login_events_mode=LOGIN_EVENTS_MODE.SDK,  # type: str
    span=None,  # type: Optional[Span]
):
    # type: (...) -> None # noqa: E501
    """
    Add a new login success tracking event. The parameters after metadata (name, email,
    scope, role, session_id, propagate) will be passed to the `set_user` function that will be called
    by this one, see:
    https://docs.datadoghq.com/logs/log_configuration/attributes_naming_convention/#user-related-attributes
    https://docs.datadoghq.com/security_platform/application_security/setup_and_configure/?tab=set_tag&code-lang=python

    :param tracer: tracer instance to use
    :param user_id: a string with the UserId
    :param metadata: a dictionary with additional metadata information to be stored with the event
    """

    span = _track_user_login_common(tracer, True, metadata, login_events_mode, login, name, email, span)
    if not span:
        return

    # usr.id will be set by set_user
    set_user(tracer, user_id, name, email, scope, role, session_id, propagate, span)


def track_user_login_failure_event(tracer, user_id, exists, metadata=None, login_events_mode=LOGIN_EVENTS_MODE.SDK):
    # type: (Tracer, str, bool, Optional[dict], str) -> None
    """
    Add a new login failure tracking event.
    :param tracer: tracer instance to use
    :param user_id: a string with the UserId if exists=True or the username if not
    :param exists: a boolean indicating if the user exists in the system
    :param metadata: a dictionary with additional metadata information to be stored with the event
    """

    span = _track_user_login_common(tracer, False, metadata, login_events_mode)
    if not span:
        return

    span.set_tag_str("%s.failure.%s" % (APPSEC.USER_LOGIN_EVENT_PREFIX, user.ID), str(user_id))
    exists_str = "true" if exists else "false"
    span.set_tag_str("%s.failure.%s" % (APPSEC.USER_LOGIN_EVENT_PREFIX, user.EXISTS), exists_str)


def track_user_signup_event(tracer, user_id, success, login_events_mode=LOGIN_EVENTS_MODE.SDK):
    # type: (Tracer, str, bool, str) -> None
    span = tracer.current_root_span()
    if span:
        success_str = "true" if success else "false"
        span.set_tag_str(APPSEC.USER_SIGNUP_EVENT, success_str)
        span.set_tag_str(user.ID, user_id)
        _asm_manual_keep(span)

        # This is used to mark if the call was done from the SDK of the automatic login events
        if login_events_mode == LOGIN_EVENTS_MODE.SDK:
            span.set_tag_str("%s.sdk" % APPSEC.USER_SIGNUP_EVENT, "true")
        else:
            span.set_tag_str("%s.auto.mode" % APPSEC.USER_SIGNUP_EVENT, str(login_events_mode))

        return
    else:
        log.warning(
            "No root span in the current execution. Skipping track_user_signup tags. "
            "See https://docs.datadoghq.com/security_platform/application_security/setup_and_configure/"
            "?tab=set_user&code-lang=python for more information.",
        )


def track_custom_event(tracer, event_name, metadata):
    # type: (Tracer, str, dict) -> None
    """
    Add a new custom tracking event.

    :param tracer: tracer instance to use
    :param event_name: the name of the custom event
    :param metadata: a dictionary with additional metadata information to be stored with the event
    """

    if not event_name:
        log.warning("Empty event name given to track_custom_event. Skipping setting tags.")
        return

    if not metadata:
        log.warning("Empty metadata given to track_custom_event. Skipping setting tags.")
        return

    span = tracer.current_root_span()
    if not span:
        log.warning(
            "No root span in the current execution. Skipping track_custom_event tags. "
            "See https://docs.datadoghq.com/security_platform/application_security"
            "/setup_and_configure/"
            "?tab=set_user&code-lang=python for more information.",
        )
        return

    span.set_tag_str("%s.%s.track" % (APPSEC.CUSTOM_EVENT_PREFIX, event_name), "true")

    for k, v in six.iteritems(metadata):
        span.set_tag_str("%s.%s.%s" % (APPSEC.CUSTOM_EVENT_PREFIX, event_name, k), str(v))
        _asm_manual_keep(span)


def should_block_user(tracer, userid):  # type: (Tracer, str) -> bool
    """
    Return true if the specified User ID should be blocked.

    :param tracer: tracer instance to use
    :param userid: the ID of the user as registered by `set_user`
    """

    if not config._appsec_enabled:
        log.warning(
            "One click blocking of user ids is disabled. To use this feature please enable "
            "Application Security Monitoring"
        )
        return False

    # Early check to avoid calling the WAF if the request is already blocked
    span = tracer.current_root_span()
    if not span:
        log.warning(
            "No root span in the current execution. should_block_user returning False"
            "See https://docs.datadoghq.com/security_platform/application_security"
            "/setup_and_configure/"
            "?tab=set_user&code-lang=python for more information.",
        )
        return False

    if core.get_item(WAF_CONTEXT_NAMES.BLOCKED, span=span):
        return True

    _asm_request_context.call_waf_callback(custom_data={"REQUEST_USER_ID": str(userid)})
    return bool(core.get_item(WAF_CONTEXT_NAMES.BLOCKED, span=span))


def block_request():  # type: () -> None
    """
    Block the current request and return a 403 Unauthorized response. If the response
    has already been started to be sent this could not work. The behaviour of this function
    could be different among frameworks, but it usually involves raising some kind of internal Exception,
    meaning that if you capture the exception the request blocking could not work.
    """
    if not config._appsec_enabled:
        log.warning("block_request() is disabled. To use this feature please enable" "Application Security Monitoring")
        return

    _asm_request_context.block_request()


def block_request_if_user_blocked(tracer, userid):  # type: (Tracer, str) -> None
    """
    Check if the specified User ID should be blocked and if positive
    block the current request using `block_request`.

    :param tracer: tracer instance to use
    :param userid: the ID of the user as registered by `set_user`
    """
    if not config._appsec_enabled:
        log.warning("should_block_user call requires ASM to be enabled")
        return

    if should_block_user(tracer, userid):
        span = tracer.current_root_span()
        if span:
            span.set_tag_str(user.ID, str(userid))
        _asm_request_context.block_request()


def _on_django_login(
    pin, request, user, mode, _get_user_info, _get_username, _find_in_user_model, _POSSIBLE_USER_ID_FIELDS
):
    if not config._appsec_enabled:
        return

    if user and str(user) != "AnonymousUser":
        user_id, user_extra = _get_user_info(user)
        if not user_id:
            log.debug(
                "Automatic Login Events Tracking: " "Could not determine user id field user for the %s user Model",
                type(user),
            )
            return

        with pin.tracer.trace("django.contrib.auth.login", span_type=SpanTypes.AUTH):
            from ddtrace.contrib.django.compat import user_is_authenticated

            if user_is_authenticated(user):
                session_key = getattr(request, "session_key", None)
                track_user_login_success_event(
                    pin.tracer,
                    user_id=user_id,
                    session_id=session_key,
                    propagate=True,
                    login_events_mode=mode,
                    **user_extra
                )
                return
            else:
                # Login failed but the user exists
                track_user_login_failure_event(pin.tracer, user_id=user_id, exists=True, login_events_mode=mode)
                return
    else:
        # Login failed and the user is unknown
        if user:
            if mode == "extended":
                user_id = _get_username(user)
            else:  # safe mode
                user_id = _find_in_user_model(user, _POSSIBLE_USER_ID_FIELDS)
            if not user_id:
                user_id = "AnonymousUser"

            track_user_login_failure_event(pin.tracer, user_id=user_id, exists=False, login_events_mode=mode)
            return


def _on_django_auth(result_user, mode, kwargs, pin, _POSSIBLE_USER_ID_FIELDS, _POSSIBLE_LOGIN_FIELDS):
    if not config._appsec_enabled:
        return True, result_user

    userid_list = _POSSIBLE_USER_ID_FIELDS if mode == "safe" else _POSSIBLE_LOGIN_FIELDS

    for possible_key in userid_list:
        if possible_key in kwargs:
            user_id = kwargs[possible_key]
            break
    else:
        user_id = "missing"

    if not result_user:
        with pin.tracer.trace("django.contrib.auth.login", span_type=SpanTypes.AUTH):
            track_user_login_failure_event(pin.tracer, user_id=user_id, exists=False, login_events_mode=mode)
    return False, None


core.on("django.login", _on_django_login)
core.on("django.auth", _on_django_auth)
