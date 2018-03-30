from persistent_doc.document import FrozenNode, map_type, get_eval, Ex, Expr
from persistent_doc.transform import TransformDict
import persistent_doc.document as pdocument
from const import default_get, identity, transformed, get_matrix
from compgeo import arc_endpoints, extents
from collections import OrderedDict
import numpy
from pdb import set_trace as bp

def _repr(value):
    from pyrsistent import PMap
    if isinstance(value, TransformDict):
        return dict(value.dict_).__repr__()
    elif isinstance(value, Expr):
        if value.expr is not None and value.expr.calc == "reeval":
            return "exr(%r)" % value.expr
        else:
            if value.expr is None:
                return repr(value.cache)
            else:
                return "exc(%r)" % value.expr
    elif isinstance(value, Ex):
        if value is None:
            return value
        return "exc(%r)" % value
    elif isinstance(value, numpy.ndarray) and value.shape == (2,):
        return "P" + str(tuple(value))
    else:
        return repr(value)

class PointRepr:
    def __init__(self, array):
        self.array = array

    def __repr__(self):
        return "P(%s)" % ", ".join(map(str, self.array))

node_num = 0
class Node(FrozenNode):
    def __new__(cls, name=None, params=None, children=(), doc=None, parent=None, _parent=None, **kwargs):
        global node_num
        doc = doc if doc is not None else pdocument.default_doc
        params = kwargs if params is None else params
        children = list(children)
        if type(params) == map_type:
            params = params.evolver()
        if "id" not in params:
            params["id"] = "n_%s" % node_num
            node_num += 1
        for key, value in kwargs.items():
            if key.startswith("p_"):
                children.append(Node("point", child_id=key[2:], value=value))
                del kwargs[key]
                params[key[2:]] = Ex("`%s" % children[-1]["id"], "reeval")
            elif key.startswith("px_"):
                # bp()
                child_id = key[3:]
                children.append(Node("point", child_id=child_id, value=value))
                del kwargs[key]
                params[child_id] = Ex("`%s" % children[-1]["id"], "on first read")
            elif key.startswith("r_"):
                raise Exception("ref nodes are depricated! Use expressions with a single id instead.")
            elif key == "transform":
                # Should not have both transform and transforms.
                kwargs["transforms"] = TransformDict(dict_={"singleton":value}, node=params["id"], doc=doc)
                del kwargs["transform"]
            elif key == "transforms":
                if type(value) not in [map_type, Ex]:
                    kwargs["transforms"] = TransformDict(dict_=value, node=params["id"], doc=doc)
        # Had problem where this overwrote value passed by param!
        # Need to know if "children" is the intended change or
        # params is the intended change!
        # Setting to "params overwrites children" for now.
        # NO, there are bigger problems with children not synced to the
        # new param values
        # Could use the latest one of the two if we had timestamps

        # General problem: This loop is called at modification instead of
        # only at initialization
        # Should decide on the semantics of appending a node with
        # child_id (or removing one with child_id) means for params
        # anyways.
        for child_id in children:
            child = get_eval(child_id)
            if "child_id" in child and child["child_id"] not in params:
                params[child["child_id"]] = child_id
        if type(params).__name__ == '_Evolver':
            params = params.persistent()
        return FrozenNode.__new__(cls, name=name, params=params,
                                  children=children, doc=doc, parent=parent,
                                  _parent=_parent)

    def set(self, **kwargs):
        return FrozenNode.set(self, **kwargs)

    def __setitem__(self, key, value):
        self.set_path([key], value)

    def change_id(self, new_id):
        index = self.parent.index(self)
        self["id"] = new_id
        self = self.doc[new_id]
        self.parent[index] = self
        #for child in self:
        #    child.change(_parent=wrap3(new_id, doc))

    def latest(self):
        return self.doc.get_node(self["id"])

    @property
    def transform(self):
        transform = identity
        if "transforms" not in self.params:
            return identity
        else:
            for key in self.params["transforms"]:
                matrix = get_matrix(self["transforms"][key])
                transform = transform.dot(matrix)
            return transform

    @property
    def transforms(self):
        self = self.L
        if "transforms" not in self:
            self["transforms"] = TransformDict(node=self["id"], doc=self.doc)
            self = self.latest()
        return self["transforms"]

    def params_repr(self, exclude=(), exclude_empty=True, points=True,
                    sep=", "):
        empty = []
        if exclude_empty:
            if self["id"].startswith("n_"):
                empty.append("id")
            if not self.transforms:
                empty.append("transforms")

        items = list(self.params.items())
        if points:
            for child in self:
                if "child_id" in child:
                    empty.append(child["child_id"])
                    if child.name == "point":
                        value = child.get_expr("value")
                        value = PointRepr(value) if isinstance(value, numpy.ndarray) else value
                        prefix = "px_" if child.parent.get_expr(child["child_id"]).expr.calc == "on first read" else "p_"
                        items.append(("%s%s" % (prefix, child["child_id"]), value))
                    if child.name == "ref":
                        items.append(("r_%s" % child["child_id"],
                                      child["ref_id"]))
        return sep.join("%s=%s" % (key, _repr(value)) for key, value in items
                        if key not in exclude and key not in empty)

    def pprint(self, exclude=["transform_updated"]):
        for line in self.pprint_string(exclude=exclude):
            print line

    def pprint_string(self, indent = 0, exclude = ["transform_updated"]):
        params = self.params_repr(exclude, sep=" ")
        yield "%s%s: %s" % (indent*" ", self.name, params)
        for child in self:
            if not (child.name in ["point", "ref"] and "child_id" in child):
                for line in child.pprint_string(indent + 2, exclude):
                    yield line

    def code(self, indent = 0, exclude = ["transform_updated"]):
        params = self.params_repr(exclude)
        if params:
            params = ", " + params
        s = '%sNode("%s"%s' % (indent*" ", self.name, params)
        children = [child for child in self
                    if not (child.name in ["point", "ref"] and "child_id" in child)]
        if len(children):
            s += ", children = [\n"
            s += ",\n".join(child.code(indent + 2, exclude)
                            for child in children)
            s += "]"
        s += ")"
        return s

    def combined_transform(self, stop=None):
        """ Cumulate all transforms on the path from parent of node to stop.
        Probably works poorly with refs."""
        if stop is None:
            stop = self.doc.tree_root
        if self == stop:
            return identity
        else:
            return self.parent.combined_transform(stop).dot(self.parent.transform)

    def bbox(self, transform=identity, skip=False):
        """ Bound box. Includes self's transform."""
        # Want some way to cache the answer for children?
        # Would need transforms to be applied after instead of before.
        # Could almost make this an expression

        # transformed() already applies the last transform to points
        if not skip and self.name != "point":
            transform = transform.dot(self.transform)
        if self.name in ["group", "path"]:
            boxes = [child.bbox(transform)
                     for child in self]
            boxes = zip(*[box for box in boxes if not numpy.array_equal(box, (None, None))])
            if not boxes:
                return (None, None)
            return (numpy.min(numpy.vstack(boxes[0]), 0),
                    numpy.max(numpy.vstack(boxes[1]), 0))
        elif self.name == "ref":
            return self.reference().bbox(transform, skip=True)
        elif self.name == "line":
            m = numpy.vstack([transformed(self["start"], transform),
                              transformed(self["end"], transform)])
            line_width = default_get(self, "line_width")
            return numpy.min(m, 0)-line_width, numpy.max(m, 0)+line_width
        elif self.name == "arc":
            end0, end1 = arc_endpoints(transformed(self["center"], transform),
                                       self["radius"],
                                       default_get(self, "angle"))
            m = numpy.vstack([end0, end1])
            line_width = default_get(self, "line_width")
            return numpy.min(m, 0)-line_width, numpy.max(m, 0)+line_width
        elif self.name == "point":
            point = transformed(self, transform)
            return point, point
        elif self.name == "text":
            botleft = transformed(self["botleft"], transform)
            xy, wh, dxy = extents(unicode(self["value"]), default_get(self, "font_size"))
            botright = botleft + dxy
            topleft = botleft + xy
            return topleft, botright

    def dfs(self):
        visited = [(self, identity)]
        for node, transform in visited:
            yield node, transform
            transform = transform.dot(node.transform)
            visited.extend((child, transform) for child in node)
