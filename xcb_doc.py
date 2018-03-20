import cairocffi as cairo
import xcffib as xcb
from xcffib.xproto import GC, CW, EventMask, WindowClass, ExposeEvent, ButtonPressEvent
import numpy
from const import default_get, identity, transformed
import math
from draw import flatten
import time
from collections import OrderedDict

class Surface:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.connection = xcb.connect()
        self.xsetup = self.connection.get_setup()
        self.window = self.connection.generate_id()
        self.pixmap = self.connection.generate_id()
        self.gc = self.connection.generate_id()
        events = [self.xsetup.roots[0].white_pixel,
                  EventMask.ButtonPress | EventMask.ButtonRelease | EventMask.EnterWindow | EventMask.LeaveWindow | EventMask.Exposure | EventMask.PointerMotion | EventMask.ButtonMotion | EventMask.KeyPress | EventMask.KeyRelease]
        self.connection.core.CreateWindow(self.xsetup.roots[0].root_depth,
                                          self.window,
                                          # Parent is the root window
                                          self.xsetup.roots[0].root,
                                          0, 0, self.width, self.height,
                                          0, WindowClass.InputOutput,
                                          self.xsetup.roots[0].root_visual,
                                          CW.BackPixel | CW.EventMask,
                                          events)

        self.connection.core.CreatePixmap(self.xsetup.roots[0].root_depth,
                                          self.pixmap,
                                          self.xsetup.roots[0].root,
                                          self.width,
                                          self.height)

        self.connection.core.CreateGC(self.gc,
                                      self.xsetup.roots[0].root,
                                      GC.Foreground | GC.Background,
                                      [self.xsetup.roots[0].black_pixel,
                                       self.xsetup.roots[0].white_pixel])

        self.surface = cairo.XCBSurface (self.connection,
                                         self.pixmap,
                                         self.xsetup.roots[0].allowed_depths[0].visuals[0],
                                         self.width,
                                         self.height)
        self.context = cairo.Context(self.surface)
        self.surfaces = {"screen":self.surface}
        self.contexts = {"screen":self.context}
        self.layers = OrderedDict() #Layer roots
        self.lastupdate = {}
        self.lastdrawn = {}

    def addlayer(self, doc, root_id):
        layer = root_id
        self.surfaces[layer] = self.surface.create_similar(cairo.CONTENT_COLOR_ALPHA, self.width, self.height)
        self.contexts[layer] = cairo.Context(self.surfaces[layer])
        #self.contexts[layer].set_operator(cairo.OPERATOR_ONTO)
        self.contexts[layer].set_operator(cairo.OPERATOR_SOURCE)
        self.contexts[layer].set_antialias(cairo.ANTIALIAS_DEFAULT)
        self.layers[layer] = (doc, root_id)
        self.clear(layer)

    def clear(self, layer = "drawing"):
        if layer == "drawing":
            self.contexts[layer].set_source_rgb (1, 1, 1)
        else:
            self.contexts[layer].set_source_rgba (1, 1, 1, 0)
        self.contexts[layer].paint()
        #self.context.scale(self.width, self.height)

    def show(self):
        self.connection.core.MapWindow(self.window)
        self.connection.flush()

    def draw(self, layer = "drawing", root = None):
        if root is None:
            doc, root_id = self.layers[layer]
            root = doc[root_id]
        context = self.contexts[layer]
        for func, args in flatten(root):
            if func == "stroke_and_fill":
                if default_get(args, "fill_color"):
                    context.set_source_rgb(*default_get(args, "fill_color"))
                    if args.get("stroke_color") is not None:
                        context.fill_preserve()
                    else:
                        context.fill()
                if default_get(args, "stroke_color"):
                    context.set_line_width(default_get(args, "line_width"))
                    context.set_source_rgb(*default_get(args, "stroke_color"))
                    context.set_dash(*default_get(args, "dash"))
                    context.stroke()
            elif func == "text":
                if args["text"] is None:
                    continue
                context.set_source_rgb(*default_get(args, "stroke_color"))
                context.move_to(*args["botleft"])
                context.set_font_size(1.5 * args["font_size"])
                if numpy.array_equal(args["transform"], identity):
                    context.show_text(unicode(args["text"]))
                else:
                    context.save()
                    matrix = cairo.Matrix(*args["transform"].T[:,:2].flatten())
                    context.transform(matrix)
                    context.show_text(unicode(args["text"]))
                    context.restore()
            elif func == "group":
                pass
            elif func in ["begin_region", "end_region"]:
                pass
            elif func == "arc":
                flat = list(args["center"]) + [args["radius"]] + list(args["angle"])
                context.arc(*flat)
            else:
                getattr(context, func)(*args)

    def redraw(self, layer):
        self.clear(layer)
        self.draw(layer)
        self.expose()

    def update_all(self):
        drawn = False
        for layer_id in self.contexts:
            if layer_id == "screen":
                continue
            if True: # self.lastupdate.get(layer_id, 0) > self.lastdrawn.get(layer_id, -1):
                self.clear(layer_id)
                self.draw(layer_id)
                self.lastdrawn[layer_id] = time.time()
                drawn = True
        if drawn:
            self.expose()
        return drawn

    def update_layer(self, layer_id):
        self.lastupdate[layer_id] = time.time()

    def expose(self):
        for layer in ["drawing", "ui"]:
            self.context.set_source_surface(self.surfaces[layer])
            self.context.paint()
        self.connection.core.CopyArea(self.pixmap, self.window, self.gc, 0, 0, 0, 0, self.width, self.height)
        self.connection.flush()

    def poll(self):
        return self.connection.poll_for_event()
