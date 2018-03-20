from draw import collide, simplify_transform
from const import rounded, identity, get_matrix
import numpy
import persistent.document as pdocument
from persistent.document import Expr, Ex

pdocument.scope = {"P": P}

input_callbacks = ""
