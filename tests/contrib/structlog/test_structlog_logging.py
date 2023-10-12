import json

import pytest
import structlog

from ddtrace import config
from ddtrace.constants import ENV_KEY
from ddtrace.constants import SERVICE_KEY
from ddtrace.constants import VERSION_KEY
from ddtrace.contrib.structlog import patch
from ddtrace.contrib.structlog import unpatch
from tests.utils import DummyTracer


cf = structlog.testing.CapturingLoggerFactory()


def _test_logging(output, span, env="", service="", version=""):
    dd_trace_id, dd_span_id = (span.trace_id, span.span_id) if span else (0, 0)

    assert json.loads(output[0].args[0])["event"] == "Hello!"
    assert json.loads(output[0].args[0])["dd.trace_id"] == str(dd_trace_id)
    assert json.loads(output[0].args[0])["dd.span_id"] == str(dd_span_id)
    assert json.loads(output[0].args[0])["dd.env"] == env or ""
    assert json.loads(output[0].args[0])["dd.service"] == service or ""
    assert json.loads(output[0].args[0])["dd.version"] == version or ""

    cf.logger.calls.clear()


@pytest.fixture(autouse=True)
def patch_structlog():
    patch()
    structlog.configure(
        processors=[structlog.processors.JSONRenderer()],
        logger_factory=cf,
    )
    yield
    unpatch()


@pytest.fixture(autouse=True)
def global_config():
    config.service = "logging"
    config.env = "global.env"
    config.version = "global.version"
    yield
    config.service = config.env = config.version = None


def test_log_trace_global_values():
    """
    Check trace info includes global values over local span values
    """

    tracer = DummyTracer()
    span = tracer.trace("test.logging")
    span.set_tag(ENV_KEY, "local-env")
    span.set_tag(SERVICE_KEY, "local-service")
    span.set_tag(VERSION_KEY, "local-version")

    structlog.get_logger().info("Hello!")
    if span:
        span.finish()

    output = cf.logger.calls

    _test_logging(output, span, config.env, config.service, config.version)


def test_log_no_trace():
    structlog.get_logger().info("Hello!")
    output = cf.logger.calls

    _test_logging(output, None, config.env, config.service, config.version)


def test_no_processors():
    structlog.configure(processors=[], logger_factory=cf)
    logger = structlog.get_logger()

    tracer = DummyTracer()
    tracer.trace("test.logging")
    logger.info("Hello!")

    output = cf.logger.calls

    assert output[0].kwargs["event"] == "Hello!"
    assert "dd.trace_id" not in output[0].kwargs
    assert "dd.span_id" not in output[0].kwargs
    assert "dd.env" not in output[0].kwargs
    assert "dd.service" not in output[0].kwargs
    assert "dd.version" not in output[0].kwargs

    cf.logger.calls.clear()


@pytest.mark.subprocess(env=dict(DD_TRACE_128_BIT_TRACEID_GENERATION_ENABLED="False"))
def test_log_trace():
    """
    Check logging patched and formatter including trace info when 64bit trace ids are generated.
    """

    import json

    import structlog

    from ddtrace import config
    from ddtrace.contrib.structlog import patch
    from ddtrace.contrib.structlog import unpatch
    from tests.utils import DummyTracer

    config.service = "logging"
    config.env = "global.env"
    config.version = "global.version"

    patch()

    cf = structlog.testing.CapturingLoggerFactory()
    structlog.configure(
        processors=[structlog.processors.JSONRenderer()],
        logger_factory=cf,
    )
    logger = structlog.getLogger()

    tracer = DummyTracer()
    span = tracer.trace("test.logging")
    logger.info("Hello!")
    if span:
        span.finish()

    output = cf.logger.calls
    dd_trace_id, dd_span_id = (span.trace_id, span.span_id) if span else (0, 0)

    assert json.loads(output[0].args[0])["event"] == "Hello!"
    assert json.loads(output[0].args[0])["dd.trace_id"] == str(dd_trace_id)
    assert json.loads(output[0].args[0])["dd.span_id"] == str(dd_span_id)
    assert json.loads(output[0].args[0])["dd.env"] == "global.env"
    assert json.loads(output[0].args[0])["dd.service"] == "logging"
    assert json.loads(output[0].args[0])["dd.version"] == "global.version"

    cf.logger.calls.clear()
    unpatch()


@pytest.mark.subprocess(
    env=dict(DD_TRACE_128_BIT_TRACEID_GENERATION_ENABLED="True", DD_TRACE_128_BIT_TRACEID_LOGGING_ENABLED="True")
)
def test_log_trace_128bit_trace_ids():
    """
    Check if 128bit trace ids are logged when `DD_TRACE_128_BIT_TRACEID_LOGGING_ENABLED=True`
    """

    import json

    import structlog

    from ddtrace import config
    from ddtrace.contrib.structlog import patch
    from ddtrace.contrib.structlog import unpatch
    from ddtrace.internal.constants import MAX_UINT_64BITS
    from tests.utils import DummyTracer

    config.service = "logging"
    config.env = "global.env"
    config.version = "global.version"

    patch()

    cf = structlog.testing.CapturingLoggerFactory()
    structlog.configure(
        processors=[structlog.processors.JSONRenderer()],
        logger_factory=cf,
    )
    logger = structlog.getLogger()

    tracer = DummyTracer()
    span = tracer.trace("test.logging")
    logger.info("Hello!")
    if span:
        span.finish()

    assert span.trace_id > MAX_UINT_64BITS

    output = cf.logger.calls
    dd_trace_id, dd_span_id = (span.trace_id, span.span_id) if span else (0, 0)

    assert json.loads(output[0].args[0])["event"] == "Hello!"
    assert json.loads(output[0].args[0])["dd.trace_id"] == str(dd_trace_id)
    assert json.loads(output[0].args[0])["dd.span_id"] == str(dd_span_id)
    assert json.loads(output[0].args[0])["dd.env"] == "global.env"
    assert json.loads(output[0].args[0])["dd.service"] == "logging"
    assert json.loads(output[0].args[0])["dd.version"] == "global.version"

    cf.logger.calls.clear()
    unpatch()


@pytest.mark.subprocess(
    env=dict(DD_TRACE_128_BIT_TRACEID_GENERATION_ENABLED="True", DD_TRACE_128_BIT_TRACEID_LOGGING_ENABLED="False")
)
def test_log_trace_128bit_trace_ids_log_64bits():
    """
    Check if a 64 bit trace, trace id is logged when `DD_TRACE_128_BIT_TRACEID_LOGGING_ENABLED=False`
    """

    import json

    import structlog

    from ddtrace import config
    from ddtrace.contrib.structlog import patch
    from ddtrace.contrib.structlog import unpatch
    from ddtrace.internal.constants import MAX_UINT_64BITS
    from tests.utils import DummyTracer

    config.service = "logging"
    config.env = "global.env"
    config.version = "global.version"

    patch()

    cf = structlog.testing.CapturingLoggerFactory()
    structlog.configure(
        processors=[structlog.processors.JSONRenderer()],
        logger_factory=cf,
    )
    logger = structlog.getLogger()

    tracer = DummyTracer()
    span = tracer.trace("test.logging")
    logger.info("Hello!")
    if span:
        span.finish()

    assert span.trace_id > MAX_UINT_64BITS

    output = cf.logger.calls
    dd_trace_id, dd_span_id = (span._trace_id_64bits, span.span_id) if span else (0, 0)

    assert json.loads(output[0].args[0])["event"] == "Hello!"
    assert json.loads(output[0].args[0])["dd.trace_id"] == str(dd_trace_id)
    assert json.loads(output[0].args[0])["dd.span_id"] == str(dd_span_id)
    assert json.loads(output[0].args[0])["dd.env"] == "global.env"
    assert json.loads(output[0].args[0])["dd.service"] == "logging"
    assert json.loads(output[0].args[0])["dd.version"] == "global.version"

    cf.logger.calls.clear()
    unpatch()


@pytest.mark.subprocess(env=dict(DD_TAGS="service:ddtagservice,env:ddenv,version:ddversion"))
def test_log_DD_TAGS():
    import json

    import structlog

    from ddtrace.constants import ENV_KEY
    from ddtrace.constants import SERVICE_KEY
    from ddtrace.constants import VERSION_KEY
    from ddtrace.contrib.structlog import patch
    from ddtrace.contrib.structlog import unpatch
    from tests.utils import DummyTracer

    patch()

    cf = structlog.testing.CapturingLoggerFactory()
    structlog.configure(
        processors=[structlog.processors.JSONRenderer()],
        logger_factory=cf,
    )
    logger = structlog.getLogger()

    tracer = DummyTracer()
    span = tracer.trace("test.logging")
    span.set_tag(ENV_KEY, "local-env")
    span.set_tag(SERVICE_KEY, "local-service")
    span.set_tag(VERSION_KEY, "local-version")

    logger.info("Hello!")
    if span:
        span.finish()

    output = cf.logger.calls
    dd_trace_id, dd_span_id = (span.trace_id, span.span_id) if span else (0, 0)

    assert json.loads(output[0].args[0])["event"] == "Hello!"
    assert json.loads(output[0].args[0])["dd.trace_id"] == str(dd_trace_id)
    assert json.loads(output[0].args[0])["dd.span_id"] == str(dd_span_id)
    assert json.loads(output[0].args[0])["dd.env"] == "ddenv"
    assert json.loads(output[0].args[0])["dd.service"] == "ddtagservice"
    assert json.loads(output[0].args[0])["dd.version"] == "ddversion"

    cf.logger.calls.clear()
    unpatch()
