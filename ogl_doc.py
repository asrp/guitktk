import numpy
from const import default_get, identity, transformed
from config import MAINLOOP
import math
from draw import flatten
from collections import OrderedDict
import ctypes
from OpenGL.GL import *
from OpenGL.GLUT import *
import logging
logger = logging.getLogger("ogl_draw")

class OGLCanvas:
    def __init__(self, width, height, root=None):
        self.width = width
        self.height = height
        glutInitWindowSize(width, height)
        self.win_id = glutCreateWindow("pyxcbcairo")
        glutDisplayFunc(self.show)
        glClearColor(1.0, 1.0, 1.0, 1.0)
        glOrtho(0, width, height, 0, 0, 1)
        glLineWidth(2)
        #glMatrixMode(GL_PROJECTION)
        #glLoadIdentity()
        #glViewport(0, 0, self.width, self.height)
        self.layers = OrderedDict()
        if MAINLOOP == "glut":
            glutDisplayFunc(self.update_all)
            glutPostRedisplay()

    def draw(self, root):
        points = []
        for func, args in flatten(root):
            #if func not in ["begin_region", "move_to", "line_to"]: continue
            if func == "stroke_and_fill":
                # Hack for arcs
                if len(points) <= 1: continue
                if default_get(args, "fill_color"):
                    glColor3f(*default_get(args, "fill_color"))
                    glBegin(GL_POLYGON)
                    for point in points:
                        glVertex2d(*(point))
                    glEnd()
                if default_get(args, "stroke_color"):
                    glColor3f(*default_get(args, "stroke_color"))
                    glBegin(GL_LINE_LOOP)
                    for point in points:
                        glVertex2d(*(point))
                    glEnd()
            elif func == "text":
                glWindowPos2f(args["botleft"][0], self.height-args["botleft"][1])
                for ch in args["text"]:
                    glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24,
                                        ctypes.c_int(ord(ch)))
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
                if "fill_color" in args["style"]:
                    glColor3f(*default_get(args["style"], "fill_color"))
                    glBegin(GL_POLYGON)
                else:
                    glColor3f(*default_get(args["style"], "stroke_color"))
                    glBegin(GL_LINES)
                N = 20
                for i in xrange(N):
                    theta = i * 2*math.pi / N
                    glVertex2d(x + r * math.sin(theta),
                               y + r * math.cos(theta))
                glEnd()
            else:
                raise Exception('Unknown function %s, %s' % (func, args))

    def addlayer(self, doc, root_id):
        self.layers[root_id] = (doc, root_id)

    def expose(self):
        import time
        starttime = time.time()
        glutSetWindow(self.win_id)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        logger.debug("Emptied %.5f", (time.time() - starttime))
        for doc, root_id in self.layers.values():
            self.draw(doc[root_id])
            logger.debug("Finished %s %.5f", root_id, time.time() - starttime)
        glutSwapBuffers()
        logger.debug("Draw finished %.5f", time.time() - starttime)

    def update_all(self):
        self.expose()
        return True

    def show(self):
        pass

    def update_layer(self, root_id):
        pass
