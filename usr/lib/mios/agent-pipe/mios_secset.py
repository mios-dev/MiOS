# AI-hint: Re-export shim for mios_pipe.access.secset
import sys
import types
import importlib

class _ShimModule(types.ModuleType):
    def __init__(self, name, target_name):
        super().__init__(name)
        self.__dict__["_target_name"] = target_name
        self.__dict__["_target_module"] = None

    def _get_target(self):
        m = self.__dict__["_target_module"]
        if m is None:
            m = importlib.import_module(self.__dict__["_target_name"])
            self.__dict__["_target_module"] = m
        return m

    def __getattr__(self, name):
        return getattr(self._get_target(), name)

    def __setattr__(self, name, value):
        setattr(self._get_target(), name, value)

    def __dir__(self):
        return dir(self._get_target())

sys.modules[__name__] = _ShimModule(__name__, "mios_pipe.access.secset")
