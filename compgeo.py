from numpy import dot, array, sum
from numpy.linalg import norm
import math
from config import BACKEND

surface = None
rot90 = array([[0, -1], [1, 0]])

def norm2(v):
    return sum(dot(v.T,v))

def distance2(point, line):
    start = line[0] - point
    end = line[1] - point
    perp = rot90.dot(end - start)
    proj = (start.dot(perp)) / norm(perp)
    if norm2(proj - start) > norm2(end - start):
        return norm2(end)
    elif norm2(proj - end) > norm2(end - start):
        return norm2(start)
    else:
        return norm2(proj)

def arc_endpoints(center, radius, angle):
    end0 = (radius * math.cos(angle[0]),
            radius * math.sin(angle[0]))
    end1 = (radius * math.cos(angle[1]),
            radius * math.sin(angle[1]))
    return end0 + center, end1 + center

def distance_to_arc(point, center, radius, angle):
    dist_to_circle = abs(norm(center - point) - radius)
    point_angle = math.atan2(*reversed(point - center))
    point_angle = point_angle + (point_angle<0)*2*math.pi
    if angle[0] <= point_angle <= angle[1]:
        return dist_to_circle
    else:
        end0, end1 = arc_endpoints(center, radius, angle)
        return min(norm(end0 - point), norm(end1 - point))

def is_left(point, segment):
    area1 = (segment[1][0] - segment[0][0]) * (point[1] - segment[0][1])
    area2 = (segment[1][1] - segment[0][1]) * (point[0] - segment[0][0])
    return cmp(area1, area2)

def point_in_closed_path(point, path):
    # Compute the winding number
    # Pick any direction from point and corresponding half infinite segment.
    # See how mnay times that segment is crossed.
    # We pick the half infinite line going straight right
    winding_number = 0
    for segment in path:
        # Cross up
        if segment[0][1] <= point[1] < segment[1][1] and is_left(point, segment) > 0:
            winding_number += 1
        # Cross down
        if segment[0][1] > point[1] >= segment[1][1] and is_left(point, segment) < 0:
            winding_number -= 1
    # print "Winding number", winding_number
    return winding_number != 0

def extents(text, font_size, font_face=None):
    if BACKEND == "tkinter":
        font = (font_face if font_face else "TkFixedFont",
                int(round(font_size)))
        item = surface.canvas.create_text(0, 0,
                                          font=font,
                                          text=text, anchor="sw")
        x1, x2, y1, y2 = surface.canvas.bbox(item)
        return (0, x2 - x1), (x1 - x2, y1 - y2), (y1 - y2, 0)
    elif BACKEND == "xcb":
        surface.context.set_font_size(font_size * 1.5)
        if font_face:
            surface.context.select_font_face(font_face)
        else:
            surface.context.set_font_face(None)
        x, y, width, height, dx, dy = surface.context.text_extents(text)
        return (x, y), (width, height), (dx, dy)
    elif BACKEND == "sdl":
        import sdl_doc
        font_size = int(round(font_size * 1.5))
        text = sdl_doc.get_font((font_face, font_size)).render(text, True, (0, 0, 0))
        w, h = text.get_width(), text.get_height()
        return (0, -h), (w, h), (w, 0)
    else:
        # TODO: Get actual text extents
        w, h = (len(text) * font_size, font_size)
        #import pdb; pdb.set_trace()
        return (0, -h), (w, h), (w, 0)
