"""
Regression test: hannah_proto.v2 re-exports every scope-split *_pb2 module's public names onto
hannah_pb2 (the WebUI uses hannah_pb2.User, hannah_pb2.Room, ... for all of them). This walks
every *_pb2 module of the package and asserts nothing got left out — same class of bug as
gessinger/voice/hannah#125.
"""

import pkgutil

from hannah_proto import v2
from hannah_proto.v2 import hannah_pb2


def _scope_pb2_modules():
    for _, name, _ in pkgutil.iter_modules(v2.__path__):
        if name.endswith("_pb2") and name != "hannah_pb2":
            yield name


def test_every_scope_module_is_patched_onto_hannah_pb2():
    scope_modules = list(_scope_pb2_modules())
    assert scope_modules, "expected at least one scope-split *_pb2 module"

    missing = []
    for module_name in scope_modules:
        module = __import__(f"hannah_proto.v2.{module_name}", fromlist=["_"])
        for name in dir(module):
            if name.startswith("_"):
                continue
            if not hasattr(hannah_pb2, name):
                missing.append(f"{module_name}.{name}")

    assert not missing, f"not re-exported onto hannah_pb2: {missing}"
