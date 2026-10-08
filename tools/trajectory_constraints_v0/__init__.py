"""Typed Trajectory Constraints V0 reference contract.

This package is a standalone semantic reference. It does not integrate with the
Character Dynamics runtime and its synthetic projectors are not runtime facts.
"""

from .types import *
from .ast import *
from .trace import *
from .compiler import *
from .monitor import *
from .evaluation import project_registered
