import numpy, math
from config import GRID
from persistent_doc.document import Expr, Ex

transformed_layers = ["drawing", "editor", "grid"]

default = {"line_width": 2,
           "stroke_color": (0, 0, 0),
           "fill_color": None,
           "dash": ([], 0),
           "font_size": 20,
           "skip_points": False,
           "angle": (0, 2*math.pi),
           "icon": "point_icon",
           "visible": True}

#identity = numpy.matrix(numpy.identity(3, dtype = int))
identity = numpy.identity(3, dtype = int)

def default_get(d, key):
    return d.get(key, default[key])

def transformed(point, transform=identity):
    transform = transform.dot(point.transform)
    return transform.dot(numpy.append(point["value"], 1))[:2]

def P(*args):
    return numpy.array(args)

def exr(expr):
    return Ex(expr, "reeval")

def exc(expr):
    return Ex(expr, "on first read")

def get_translate(node, key):
    transform = node.transforms.get(key, ("translate", P(0,0)))
    if transform[0] != "translate":
        raise Exception('Transform is not a translation: %s' % transform)
    else:
        return transform[1]

def get_scale(node, key):
    transform = node.transforms.get(key, ("scale", P(1.0, 1.0)))
    if transform[0] != "scale":
        raise Exception('Transform is not a scaling: %s' % transform)
    else:
        return transform[1]

def rounded(point):
    return (point + GRID/2) // GRID * GRID

def get_matrix(transform):
    operation, args = transform
    if operation == "linear":
        matrix = args
    elif operation == "translate":
        matrix = numpy.array([[1, 0, args[0]],
                              [0, 1, args[1]],
                              [0, 0,       1]])
    elif operation == "scale":
        matrix = numpy.array([[args[0], 0, 0],
                              [0, args[1], 0],
                              [0,       0, 1]])
    else:
        raise Exception('Unknown transform %s' % operation)
    return matrix
