"""
Mathematics element renderers, split by concept to stay under the file-size limit.

  graph     — coordinate_plane
  fraction  — fraction_model, bar_model
  geometry  — geometry_shape
  solid     — solid_shape
  number    — factor_array, number_line_jumps, step_pattern

The merged RENDERERS dict keeps the original import contract
(`from .renderers_math import RENDERERS` in spec_renderer.py) unchanged.
ELEMENT_SPECS merges all subject-specific specs for registry registration.
"""

from .graph    import RENDERERS as _GRAPH,    ELEMENT_SPECS as _ES_GRAPH
from .fraction import RENDERERS as _FRACTION, ELEMENT_SPECS as _ES_FRACTION
from .geometry import RENDERERS as _GEOMETRY, ELEMENT_SPECS as _ES_GEOMETRY
from .solid    import RENDERERS as _SOLID,    ELEMENT_SPECS as _ES_SOLID
from .number   import RENDERERS as _NUMBER,   ELEMENT_SPECS as _ES_NUMBER
from .equation import RENDERERS as _EQUATION, ELEMENT_SPECS as _ES_EQUATION

RENDERERS = {**_GRAPH, **_FRACTION, **_GEOMETRY, **_SOLID, **_NUMBER, **_EQUATION}

ELEMENT_SPECS = [*_ES_GRAPH, *_ES_FRACTION, *_ES_GEOMETRY, *_ES_SOLID, *_ES_NUMBER, *_ES_EQUATION]

