import os
import sys

from ddtrace import config
from ddtrace.internal.constants import COMPONENT
from ddtrace.internal.logger import get_logger
from ddtrace.internal.utils import get_argument_value
from ddtrace.internal.utils.formats import asbool

from . import _log as ddlogs
from .. import trace_utils
from .. import trace_utils_async
from ...pin import Pin
from ..trace_utils import wrap
from ._metrics import stats_client
from ._openai import CHAT_COMPLETIONS
from ._openai import COMPLETIONS
from ._openai import EMBEDDINGS
from ._openai import ENDPOINT_DATA
from ._openai import supported


config._add(
    "openai",
    {
        "logs_enabled": asbool(os.getenv("DD_OPENAI_LOGS_ENABLED", False)),
        "metrics_enabled": asbool(os.getenv("DD_OPENAI_METRICS_ENABLED", True)),
        "prompt_completion_sample_rate": float(os.getenv("DD_OPENAI_PROMPT_COMPLETION_SAMPLE_RATE", 1.0)),
        # TODO: truncate threshold on prompts/completions
        "_default_service": "openai",
    },
)


log = get_logger(__file__)


def patch():
    # Avoid importing openai at the module level, eventually will be an import hook
    import openai

    if getattr(openai, "__datadog_patch", False):
        return

    # The requests integration sets a default service name of `requests` which hides
    # the real response time of the request to OpenAI.
    # FIXME: try to set a pin on the requests instance that the openAI library uses
    #        so that we only override it for that instance.
    #  Pin.clone(service="openai").onto(openai.web_....requests.ClientSession)
    config.requests._default_service = None

    # TODO: we can probably remove these as there will be spans from the requests integration
    # which will show the retries
    # wrap(openai, "api_resources.abstract.engine_api_resource.EngineAPIResource.create", patched_create(openai))
    # wrap(openai, "api_resources.abstract.engine_api_resource.EngineAPIResource.acreate", patched_async_create(openai))

    # if supported(CHAT_COMPLETIONS):
    #     wrap(openai, "api_resources.chat_completion.ChatCompletion.create", patched_endpoint(openai))
    #     wrap(openai, "api_resources.chat_completion.ChatCompletion.acreate", patched_async_endpoint(openai))

    if supported(COMPLETIONS):
        wrap(openai, "api_resources.completion.Completion.create", patched_completion_create(openai))
        wrap(openai, "api_resources.completion.Completion.acreate", patched_completion_acreate(openai))

    if supported(CHAT_COMPLETIONS):
        wrap(openai, "api_resources.chat_completion.ChatCompletion.create", patched_chat_completion_create(openai))
        wrap(openai, "api_resources.chat_completion.ChatCompletion.acreate", patched_chat_completion_acreate(openai))

    if supported(EMBEDDINGS):
        wrap(openai, "api_resources.embedding.Embedding.create", patched_embedding_create(openai))
        wrap(openai, "api_resources.embedding.Embedding.acreate", patched_embedding_acreate(openai))

    # if supported(EMBEDDINGS):
    #     wrap(openai, "api_resources.embedding.Embedding.create", patched_endpoint(openai))
    #     wrap(openai, "api_resources.embedding.Embedding.acreate", patched_async_endpoint(openai))

    Pin().onto(openai)
    setattr(openai, "__datadog_patch", True)

    if config.openai.logs_enabled:
        ddsite = os.getenv("DD_SITE", "datadoghq.com")
        ddapikey = os.getenv("DD_API_KEY")
        if not ddapikey:
            raise ValueError("DD_API_KEY is required for sending logs from the OpenAI integration")

        ddlogs.start(
            site=ddsite,
            api_key=ddapikey,
        )
        # FIXME: these logs don't show up when DD_TRACE_DEBUG=1 set... same thing for all contribs?
        log.debug("started log writer")


def unpatch():
    # FIXME add unpatching. unwrapping the create methods results in a
    # >               return super().create(*args, **kwargs)
    # E               AttributeError: 'method' object has no attribute '__get__'
    pass


@trace_utils.with_traced_module
def patched_completion_create(openai, pin, func, instance, args, kwargs):
    g = _completion_create(openai, pin, instance, args, kwargs)
    g.send(None)
    resp, resp_err = None, None
    try:
        resp = func(*args, **kwargs)
        return resp
    except Exception as err:
        resp_err = err
        raise
    finally:
        try:
            g.send((resp, resp_err))
        except StopIteration:
            # expected
            pass


@trace_utils_async.with_traced_module
async def patched_completion_acreate(openai, pin, func, instance, args, kwargs):
    g = _completion_create(openai, pin, instance, args, kwargs)
    g.send(None)
    resp, resp_err = None, None
    try:
        resp = await func(*args, **kwargs)
        return resp
    except Exception as err:
        resp_err = err
        raise
    finally:
        try:
            g.send((resp, resp_err))
        except StopIteration:
            # expected
            pass


@trace_utils.with_traced_module
def patched_chat_completion_create(openai, pin, func, instance, args, kwargs):
    g = _chat_completion_create(openai, pin, instance, args, kwargs)
    g.send(None)
    resp, resp_err = None, None
    try:
        resp = func(*args, **kwargs)
        return resp
    except Exception as err:
        resp_err = err
        raise
    finally:
        try:
            g.send((resp, resp_err))
        except StopIteration:
            # expected
            pass


@trace_utils_async.with_traced_module
async def patched_chat_completion_acreate(openai, pin, func, instance, args, kwargs):
    g = _chat_completion_create(openai, pin, instance, args, kwargs)
    g.send(None)
    resp, resp_err = None, None
    try:
        resp = await func(*args, **kwargs)
        return resp
    except Exception as err:
        resp_err = err
        raise
    finally:
        try:
            g.send((resp, resp_err))
        except StopIteration:
            # expected
            pass


@trace_utils.with_traced_module
def patched_embedding_create(openai, pin, func, instance, args, kwargs):
    g = _embedding_create(openai, pin, instance, args, kwargs)
    g.send(None)
    resp, resp_err = None, None
    try:
        resp = func(*args, **kwargs)
        return resp
    except Exception as err:
        resp_err = err
        raise
    finally:
        try:
            g.send((resp, resp_err))
        except StopIteration:
            # expected
            pass


@trace_utils_async.with_traced_module
async def patched_embedding_acreate(openai, pin, func, instance, args, kwargs):
    g = _embedding_create(openai, pin, instance, args, kwargs)
    g.send(None)
    resp, resp_err = None, None
    try:
        resp = await func(*args, **kwargs)
        return resp
    except Exception as err:
        resp_err = err
        raise
    finally:
        try:
            g.send((resp, resp_err))
        except StopIteration:
            # expected
            pass


# set basic openai data for all openai spans
def init_openai_span(span, openai):
    span.set_tag_str(COMPONENT, config.openai.integration_name)
    if hasattr(openai, "api_base") and openai.api_base:
        span.set_tag_str("api_base", openai.api_base)
    if hasattr(openai, "api_version") and openai.api_version:
        span.set_tag_str("api_version", openai.api_version)
    if hasattr(openai, "organization") and openai.organization:
        span.set_tag_str("org_id", openai.org_id)


def _completion_create(openai, pin, instance, args, kwargs):
    span = pin.tracer.trace(
        "openai.request", resource="completions", service=trace_utils.ext_service(pin, config.openai)
    )
    init_openai_span(span, openai)
    model = kwargs.get("model")
    prompt = kwargs.get("prompt")
    if model:
        span.set_tag_str("model", model)
    for kw_attr in ENDPOINT_DATA[COMPLETIONS]["request"]:
        if kw_attr in kwargs:
            span.set_tag("request.%s" % kw_attr, kwargs[kw_attr])

    resp, error = yield span

    metric_tags = [
        "model:%s" % kwargs.get("model"),
        "endpoint:%s" % instance.OBJECT_NAME,
        "error:%d" % (1 if error else 0),
    ]
    completions = ""

    if error is not None:
        span.set_exc_info(*sys.exc_info())
        if isinstance(error, openai.error.OpenAIError):
            # TODO?: handle specific OpenAIError types
            pass
        stats_client().increment("error", 1, tags=metric_tags + ["error_type:%s" % error.__class__.__name__])
    if resp:
        if "choices" in resp:
            choices = resp["choices"]
            if len(choices) > 1:
                completions = "\n".join(["%s: %s" % (c.get("index"), c.get("text")) for c in choices])
            else:
                completions = choices[0].get("text")

            span.set_tag("response.choices.num", len(choices))
            for choice in choices:
                idx = choice["index"]
                span.set_tag_str("response.choices.%d.finish_reason" % idx, choice.get("finish_reason"))
                span.set_tag("response.choices.%d.logprobs" % idx, choice.get("logprobs"))
        span.set_tag("response.id", resp["id"])
        span.set_tag("response.object", resp["object"])
        for token_type in ["completion_tokens", "prompt_tokens", "total_tokens"]:
            if token_type in resp["usage"]:
                span.set_tag("response.usage.%s" % token_type, resp["usage"][token_type])
        usage_metrics(resp.get("usage"), metric_tags)

    # TODO: determine best format for multiple choices/completions
    ddlogs.log(
        "info" if error is None else "error",
        "sampled completion",
        tags=["model:%s" % kwargs.get("model")],
        attrs={
            "prompt": prompt,
            "completion": completions,  # TODO: should be completions (plural)?
        },
    )
    span.finish()
    stats_client().distribution("request.duration", span.duration_ns, tags=metric_tags)


def _chat_completion_create(openai, pin, instance, args, kwargs):
    span = pin.tracer.trace(
        "openai.request", resource="chat.completions", service=trace_utils.ext_service(pin, config.openai)
    )
    init_openai_span(span, openai)

    model = kwargs.get("model")
    messages = kwargs.get("messages")
    if model:
        span.set_tag_str("model", model)

    for kw_attr in ENDPOINT_DATA[CHAT_COMPLETIONS]["request"]:
        if kw_attr in kwargs:
            span.set_tag("request.%s" % kw_attr, kwargs[kw_attr])

    resp, error = yield span

    metric_tags = [
        "model:%s" % kwargs.get("model"),
        "endpoint:%s" % instance.OBJECT_NAME,
        "error:%d" % (1 if error else 0),
    ]
    completions = ""

    if error is not None:
        span.set_exc_info(*sys.exc_info())
        if isinstance(error, openai.error.OpenAIError):
            # TODO?: handle specific OpenAIError types
            pass
        stats_client().increment("error", 1, tags=metric_tags + ["error_type:%s" % error.__class__.__name__])
    if resp:
        if "choices" in resp:
            choices = resp["choices"]
            if len(choices) > 1:
                completions = "\n".join(["%s: %s" % (c.get("index"), c.get("text")) for c in choices])
            else:
                completions = choices[0].get("text")
            span.set_tag("response.choices.num", len(choices))
            for choice in choices:
                idx = choice["index"]
                span.set_tag_str("response.choices.%d.finish_reason" % idx, choice.get("finish_reason"))
                span.set_tag("response.choices.%d.logprobs" % idx, choice.get("logprobs"))
                span.set_tag("response.choices.%d.text" % idx, choice.get("text"))
                span.set_tag("response.choices.%d.prompt" % idx, 0)
        span.set_tag("response.id", resp["id"])
        span.set_tag("response.object", resp["object"])
        for token_type in ["completion_tokens", "prompt_tokens", "total_tokens"]:
            if token_type in resp["usage"]:
                span.set_tag("response.usage.%s" % token_type, resp["usage"][token_type])
        usage_metrics(resp.get("usage"), metric_tags)

    # TODO: determine best format for multiple choices/completions
    ddlogs.log(
        "info" if error is None else "error",
        "sampled completion",
        tags=["model:%s" % kwargs.get("model")],
        attrs={
            "messages": messages,
            "completion": completions,  # TODO: should be completions (plural)?
        },
    )
    span.finish()
    stats_client().distribution("request.duration", span.duration_ns, tags=metric_tags)


def _embedding_create(openai, pin, instance, args, kwargs):
    span = pin.tracer.trace("openai.request", resource="embedding", service=trace_utils.ext_service(pin, config.openai))
    init_openai_span(span, openai)

    model = kwargs.get("model")
    if model:
        span.set_tag_str("model", model)
    for kw_attr in ENDPOINT_DATA[COMPLETIONS]["request"]:
        if kw_attr in kwargs:
            span.set_tag("request.%s" % kw_attr, kwargs[kw_attr])

    resp, error = yield span

    metric_tags = [
        "model:%s" % kwargs.get("model"),
        "endpoint:%s" % instance.OBJECT_NAME,
        "error:%d" % (1 if error else 0),
    ]

    if error is not None:
        span.set_exc_info(*sys.exc_info())
        if isinstance(error, openai.error.OpenAIError):
            # TODO?: handle specific OpenAIError types
            pass
        stats_client().increment("error", 1, tags=metric_tags + ["error_type:%s" % error.__class__.__name__])
    if resp:
        if "data" in resp:
            span.set_tag("response.data.num-embeddings", len(resp["data"]))
            span.set_tag("response.data.embedding-length", len(resp["data"][0]["embedding"]))
        for kw_attr in ["model", "object", "usage"]:
            if kw_attr in kwargs:
                span.set_tag("response.%s" % kw_attr, kwargs[kw_attr])

        usage_metrics(resp.get("usage"), metric_tags)

    span.finish()
    stats_client().distribution("request.duration", span.duration_ns, tags=metric_tags)


def usage_metrics(usage, metrics_tags):
    if not usage:
        return
    for token_type in ["prompt", "completion", "total"]:
        num_tokens = usage.get(token_type + "_tokens")
        if not num_tokens:
            continue
        # format metric name into tokens.<token type>
        name = "{}.{}".format("tokens", token_type)
        # want to capture total count for token distribution
        stats_client().distribution(name, num_tokens, tags=metrics_tags)


# @trace_utils.with_traced_module
# def patched_create(openai, pin, func, instance, args, kwargs):
#     span = pin.tracer.trace(
#         "openai.request", resource=instance.OBJECT_NAME, service=trace_utils.ext_service(pin, config.openai)
#     )
#     try:
#         init_openai_span(span, openai)
#         resp = func(*args, **kwargs)
#         return resp
#     except openai.error.OpenAIError as err:
#         span.set_tag_str("error", err.__class__.__name__)
#         raise err
#     finally:
#         span.finish()


# @trace_utils_async.with_traced_module
# async def patched_async_create(openai, pin, func, instance, args, kwargs):
#     span = pin.tracer.trace(
#         "openai.request", resource=instance.OBJECT_NAME, service=trace_utils.ext_service(pin, config.openai)
#     )
#     try:
#         init_openai_span(span, openai)
#         resp = await func(*args, **kwargs)
#         return resp
#     except openai.error.OpenAIError as err:
#         span.set_tag_str("error", err.__class__.__name__)
#         raise err
#     finally:
#         span.finish()


# # set basic openai data for all openai spans
# def init_openai_span(span, openai):
#     span.set_tag_str(COMPONENT, config.openai.integration_name)
#     if hasattr(openai, "api_base") and openai.api_base:
#         span.set_tag_str("api_base", openai.api_base)
#     if hasattr(openai, "api_version") and openai.api_version:
#         span.set_tag_str("api_version", openai.api_version)
#     if hasattr(openai, "organization") and openai.organization:
#          span.set_tag_str("org_id", openai.org_id)


# def start_endpoint_span(openai, pin, instance, args, kwargs):
#     span = pin.tracer.trace(
#         "openai.create", resource=instance.OBJECT_NAME, service=trace_utils.ext_service(pin, config.openai)
#     )
#     init_openai_span(span, openai)
#     set_flattened_tags(
#         span,
#         append_tag_prefixes([REQUEST_TAG_PREFIX], process_request(openai, instance.OBJECT_NAME, args, kwargs)),
#         processor=process_text,
#     )
#     return span


# def finish_endpoint_span(span, resp, err, openai, instance, kwargs):
#     metric_tags = ["model:%s" % kwargs.get("model"), "endpoint:%s" % instance.OBJECT_NAME]
#     if resp:
#         set_flattened_tags(
#             span,
#             append_tag_prefixes([RESPONSE_TAG_PREFIX], process_response(openai, instance.OBJECT_NAME, resp)),
#             processor=process_text,
#         )
#         usage_metrics(resp.get("usage"), metric_tags)
#     elif err:
#         set_flattened_tags(
#             span,
#             append_tag_prefixes([RESPONSE_TAG_PREFIX, ERROR_TAG_PREFIX], {"code": err.code, "message": str(err)}),
#         )
#         stats_client().increment("error.{}".format(err.__class__.__name__), 1, tags=metric_tags)
#         span.finish()
#         raise err
#     span.finish()
#     stats_client().distribution("request.duration", span.duration_ns, tags=metric_tags)
