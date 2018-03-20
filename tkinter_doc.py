import numpy
from const import default_get, identity, transformed
import math
from draw import flatten
import Tkinter
from collections import OrderedDict
import logging
logger = logging.getLogger("tk_draw")

def hexcol(color):
    if color is None:
        return ""
    return '#%02x%02x%02x' % tuple(c*255 for c in color)

class TkCanvas:
    def __init__(self, width, height, root=None):
        self.width = width
        self.height = height
        self.canvas = Tkinter.Canvas(root, width=width, height=height)
        self.layers = OrderedDict()

    def draw(self, root):
        points = []
        for func, args in flatten(root):
            #if func not in ["begin_region", "move_to", "line_to"]: continue
            if func == "stroke_and_fill":
                # Hack for arcs
                if len(points) <= 1: continue
                flat_pts = [coord for point in points for coord in point]
                self.canvas.create_polygon(*flat_pts,
                                     width=default_get(args, "line_width"),
                                     dash=default_get(args, "dash")[0],
                                     outline=hexcol(default_get(args, "stroke_color")),
                                     fill=hexcol(default_get(args, "fill_color")))
            elif func == "text":
                font = ("TkFixedFont", args["font_size"])
                self.canvas.create_text(*args["botleft"], font=font, text=args["text"], anchor="sw")
            elif func == "group":
                pass
            elif func == "begin_region":
                points = []
            elif func == "end_region":
                pass
            elif func in ["move_to", "line_to"]:
                points.append(args)
            elif func == "arc":
                # Doesn't work inside polygons yet.
                x, y = args["center"]
                r = args["radius"]
                start = args["angle"][0] * 180/math.pi,
                angle_diff = (args["angle"][0] - args["angle"][1]) * 180/math.pi
                slice_type = Tkinter.PIESLICE if default_get(args["style"], "fill_color") else Tkinter.ARC
                if angle_diff % 360 == 0:
                    #self.canvas.create_arc(x-r, y-r, x+r, y+r, start=0, extent=360, fill="red")
                    start = 0.0
                    # Must be a tkinter bug
                    angle_diff = 359
                self.canvas.create_arc(x-r, y-r, x+r, y+r,
                                       start=start,
                                       extent=angle_diff,
                                       style=slice_type,
                                       outline=hexcol(default_get(args["style"], "stroke_color")),
                                       fill=hexcol(default_get(args["style"], "fill_color")))
            else:
                raise Exception('Unknown function %s, %s' % (func, args))

    def addlayer(self, doc, root_id):
        self.layers[root_id] = (doc, root_id)

    def expose(self):
        import time
        starttime = time.time()
        self.canvas.delete("all")
        logger.debug("Emptied %.5f", (time.time() - starttime))
        for doc, root_id in self.layers.values():
            root = doc[root_id]
            self.draw(root)
            logger.debug("Finished %s %.5f", root["id"], time.time() - starttime)
        logger.debug("Draw finished %.5f", time.time() - starttime)

    def update_all(self):
        self.expose()
        return True

    def show(self):
        self.canvas.pack()

    def update_layer(self, root_id):
        pass
