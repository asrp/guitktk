from compgeo import distance2, norm2, distance_to_arc, point_in_closed_path
import numpy
from node import Node
from const import default_get, identity, transformed
import time

def flatten_seg(root, style = {}, transform = identity):
    if root.name in ["line", "curve", "arc"]:
        if root.name in "line":
            yield ("line_to", transformed(root["end"], transform))
        elif root.name == "curve":
            yield ("curve_to", transformed(root["start_control"], transform) +\
                   transformed(root["end_control"], transform) +\
                   transformed(root["end"], transform))
        elif root.name == "arc":
            center = transformed(root["center"], transform)
            yield ("arc", {"center": center,
                           "radius": root["radius"],
                           "angle": default_get(root, "angle"),
                           "style": style})

_cache = {}
def flatten(root, style={}, transform=identity, skip_transform=False):
    """ Cached version of _flatten. """
    if True or not (root["id"] in _cache and _cache[root["id"]][0] >= root.lastchange and\
            style == _cache[root["id"]][1] and (transform == _cache[root["id"]][2]).all()):
        _cache[root["id"]] = (time.time(), style.copy(), transform.copy(),
                              list(_flatten(root, style, transform, skip_transform)))
    return _cache[root["id"]][3]

def _flatten(root, style={}, transform=identity, skip_transform=False):
    """ Flatten tree into drawing commands."""
    assert(root.doc is not None)
    style = style.copy()
    for key in ["line_width", "stroke_color", "fill_color", "dash", "skip_points"]:
        if key in root:
            style[key] = root[key]
    if not skip_transform:
        transform = transform.dot(root.transform)
    if root.name in ["line", "curve", "arc", "path"]:
        if not default_get(root, "visible"):
            return
        children = root if root.name == "path" else [root]
        border = []
        if children:
            yield ("begin_region", ())
            if children[0].name == "arc":
                yield ("move_to", transformed(children[0]["center"], transform))
            else:
                yield ("move_to", transformed(children[0]["start"], transform))
        for child in children:
            for segment in flatten_seg(child, style = style,
                                       transform = transform):
                yield segment
        yield ("end_region", ())
        yield ("stroke_and_fill", style)
        if not default_get(style, "skip_points"):
            for child in children:
                for grandchild in child:
                    for elem in flatten(grandchild, style = style,
                                        transform = transform):
                        yield elem
    elif root.name == "point":
        if default_get(style, "skip_points"):
            return
        matrix = numpy.array([[1, 0, root["value"][0]],
                              [0, 1, root["value"][1]],
                              [0, 0,       1]])
        transform = transform.dot(matrix)
        for elem in flatten(root.doc[default_get(root, "icon")],
                            transform=transform, style={"skip_points":True}):
            yield elem
    elif root.name == "text":
        if "value" in root:
            value = root["value"]
        elif "ref_id" in root:
            value = str(root.doc[root["ref_id"]][root["ref_param"]])
        else:
            raise Exception('Text node with no value or ref_id: %s' % root)
        yield ("text", {"text": value,
                        "transform": transform,
                        "font_size": default_get(root, "font_size"),
                        "botleft": transformed(root["botleft"], transform)})
    elif root.name == "group":
        yield ("group", ())
    if root.name in ["group", "text"]:
        if default_get(root, "visible"):
            for child in root:
                for elem in flatten(child, style = style,
                                    transform = transform):
                    yield elem

def collide(root, xy, style = {}, transform=identity, tolerance=3, skip=False):
    style = style.copy()
    for key in ["line_width", "stroke_color", "fill_color", "dash"]:
        if key in root:
            style[key] = root[key]
    if root.name in ["path", "group"]:
        if not skip:
            transform = transform.dot(root.transform)
        if root.name == "path" and style.get("fill_color"):
            # print "Testing fill"
            path = [(transformed(seg["start"], transform),
                     transformed(seg["end"], transform))
                    for seg in root if seg.name == 'line']
            # print "Input", xy, path
            if point_in_closed_path(xy, path):
                return True
        return any(collide(child, xy, style, transform, tolerance)
                   for child in root)
    elif root.name == "line":
        line = (transformed(root["start"], transform),
                transformed(root["end"], transform))
        xy = numpy.array(xy)
        dist2 = default_get(style, "line_width") + tolerance**2
        #print "dist", distance2(transform[:2,:2] * xy, line), dist2
        return distance2(xy, line) < dist2
    elif root.name == "arc":
        center=transformed(root["center"], transform)
        return distance_to_arc(xy, center, root["radius"], default_get(root, "angle")) < tolerance
    elif root.name == "point":
        point = transformed(root, transform)
        xy = numpy.array(xy)
        return norm2(xy - point) < tolerance**2
    elif root.name == "text":
        top_left, bottom_right = root.bbox(transform)
        def contains(top_left, bottom_right, xy):
            if numpy.array_equal((top_left, bottom_right), (None, None)):
                return False
            return all(top_left <= xy) and all(xy <= bottom_right)
            #return numpy.all(top_left <= xy <= bottom_right)
        tol = (tolerance, tolerance)
        return contains(top_left - tol,
                        bottom_right + tol,
                        xy)
    else:
        # Not yet implemented
        return False

def simplify_transform(node, transform = identity):
    if node.name == "point":
        node["value"] = transformed(node, transform)
        if "transforms" in node:
            #node["transforms"] = TransformDict(node=node)
            node["transforms"].clear()
            #node["transforms"].replace({})
    else:#if node.name in ["path", "group", ]:
        transform = transform.dot(node.transform)
        if "transforms" in node:
            node["transforms"].clear()
        for child in node:
            simplify_transform(child, transform)
