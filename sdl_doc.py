import numpy
from const import default_get, identity, transformed, P
import math
from draw import flatten
from collections import OrderedDict
import pygame
import logging
logger = logging.getLogger("sdl_draw")

def intcol(color):
    if color is None:
        return None
    return tuple(c*255 for c in color)

fonts = {}
font_files = {"monospace": "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
              None: None}

def get_font(font):
    if font not in fonts:
        fonts[font] = pygame.font.Font(font_files[font[0]], font[1])
    return fonts[font]

class SDLCanvas:
    def __init__(self, width, height, root=None):
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((self.width, self.height),
                                              pygame.DOUBLEBUF)
        self.layers = OrderedDict()

    def draw(self, root, surface=None):
        surface = surface if surface is not None else self.screen
        points = []
        for func, args in flatten(root):
            #if func not in ["begin_region", "move_to", "line_to"]: continue
            if func == "stroke_and_fill":
                # Hack for arcs
                if len(points) <= 1: continue
                #flat_pts = [coord for point in points for coord in point]
                # Problem: with alpha, want a bbox and then translate...
                if default_get(args, "fill_color") and len(points) > 2:
                    pygame.draw.polygon(surface,
                                        intcol(default_get(args, "fill_color")),
                                        map(tuple, points),
                                        0)
                if default_get(args, "stroke_color"):
                    if default_get(args, "dash"):
                        #[start*t + end*(1-t) for t in midpoints]
                        pass
                    pygame.draw.lines(surface,
                                        intcol(default_get(args, "stroke_color")),
                                        False,
                                        points,
                                        int(default_get(args, "line_width")))
            elif func == "text":
                font_size = args['font_size'] if numpy.array_equal(args["transform"], identity) or args['transform'][0][1] or args['transform'][1][0]\
                            else args['font_size'] * args["transform"][0][0]
                #font_size = args['font_size']
                font_param = (args.get("font_face"),
                              int(round(1.5 * font_size)))
                color = intcol(default_get(args, "stroke_color"))
                text = get_font(font_param).render(str(args["text"]), True, color)
                surface.blit(text, args["botleft"] - P(0, text.get_height()))
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
                topleft = args["center"] - P(args["radius"], args["radius"])
                wh = P(2*args["radius"], 2*args["radius"])
                angles = args["angle"]
                if angles == (0, 2*math.pi):
                    pygame.draw.circle(surface,
                                       intcol(default_get(args["style"], "stroke_color")),
                                       map(int, args["center"]),
                                       args["radius"],
                                       0)
                else:
                    pygame.draw.arc(surface,
                                intcol(default_get(args["style"], "stroke_color")),
                                (topleft, wh),
                                angles[0], angles[1],
                                default_get(args, "line_width"))
            else:
                raise Exception('Unknown function %s, %s' % (func, args))

    def addlayer(self, doc, root_id):
        self.layers[root_id] = (doc, root_id)

    def expose(self):
        import time
        starttime = time.time()
        self.screen.fill((255, 255, 255))
        logger.debug("Emptied %.5f", (time.time() - starttime))
        for doc, root_id in self.layers.values():
            root = doc[root_id]
            self.draw(root)
            logger.debug("Finished %s %.5f", root["id"], time.time() - starttime)
        logger.debug("Draw finished %.5f", time.time() - starttime)
        #pygame.display.update()
        pygame.display.flip()

    def update_all(self):
        self.expose()
        return True

    def show(self):
        pass

    def update_layer(self, root_id):
        pass
