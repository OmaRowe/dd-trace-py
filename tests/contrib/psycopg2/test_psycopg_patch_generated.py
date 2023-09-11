# This test script was automatically generated by the contrib-patch-tests.py
# script. If you want to make changes to it, you should make sure that you have
# removed the ``_generated`` suffix from the file name, to prevent the content
# from being overwritten by future re-generations.

from ddtrace.contrib.psycopg.patch import get_version
from ddtrace.contrib.psycopg.patch import get_versions
from ddtrace.contrib.psycopg.patch import patch


try:
    from ddtrace.contrib.psycopg.patch import unpatch
except ImportError:
    unpatch = None
from tests.contrib.patch import emit_integration_and_version_to_test_agent
from tests.contrib.patch import PatchTestCase


class TestPsycopgPatch(PatchTestCase.Base):
    __integration_name__ = "psycopg"
    __module_name__ = "psycopg2"
    __patch_func__ = patch
    __unpatch_func__ = unpatch
    __get_version__ = get_version
    __get_versions__ = get_versions

    def assert_module_patched(self, psycopg):
        pass

    def assert_not_module_patched(self, psycopg):
        pass

    def assert_not_module_double_patched(self, psycopg):
        pass

    def assert_module_implements_get_version(self):
        patch()
        assert get_version() == ""
        versions = get_versions()
        assert "psycopg2" in versions
        assert versions["psycopg2"] != ""
        emit_integration_and_version_to_test_agent("psycopg2", versions["psycopg2"])
        unpatch()

    def test_and_emit_get_version(self):
        pass
