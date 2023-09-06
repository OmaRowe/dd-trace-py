# This test script was automatically generated by the contrib-patch-tests.py
# script. If you want to make changes to it, you should make sure that you have
# removed the ``_generated`` suffix from the file name, to prevent the content
# from being overwritten by future re-generations.
from ddtrace._monkey import PATCH_MODULES
from ddtrace.contrib.falcon import get_version
from ddtrace.contrib.falcon.patch import patch
from ddtrace.internal.telemetry import telemetry_writer


try:
    from ddtrace.contrib.falcon.patch import unpatch
except ImportError:
    unpatch = None
from tests.contrib.patch import PatchTestCase


class TestFalconPatch(PatchTestCase.Base):
    __integration_name__ = "falcon"
    __module_name__ = "falcon"
    __patch_func__ = patch
    __unpatch_func__ = unpatch

    def assert_module_patched(self, falcon):
        pass

    def assert_not_module_patched(self, falcon):
        pass

    def assert_not_module_double_patched(self, falcon):
        pass

    def assert_module_implements_get_version(self):
        version = get_version()
        assert type(version) == str
        assert version != ""

    def emit_integration_and_tested_version_telemetry_event(self):
        # emits a telemetry event that will be consumed by the Test Agent and sent to metabase describing
        # the integration and its tested versions

        version = get_version()
        telemetry_writer.add_integration("falcon", True, PATCH_MODULES.get("falcon") is True, "", version=version)
        integrations = telemetry_writer._flush_integrations_queue()
        telemetry_writer._app_integrations_changed_event(integrations)
