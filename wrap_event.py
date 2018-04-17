import numpy
import numpy.linalg
from collections import deque, defaultdict
from config import BACKEND, DRAW_FREQUENCY
import logging
logger = logging.getLogger("event")
proc_logger = logging.getLogger("proc")

class Event:
    pass

all_events = ["mouse_press", "mouse_release", "motion", "key_press", "key_release", "expose"]

for event in all_events:
    setattr(Event, event, event)

if BACKEND == "xcb":
    from xcffib.xproto import GC, CW, EventMask, WindowClass, ExposeEvent, ButtonPressEvent, ButtonReleaseEvent, MotionNotifyEvent, KeyPressEvent, KeyReleaseEvent, KeyButMask, NoExposureEvent
    from xpybutil import keybind
    import unikeysym

    xcb_event = {ButtonPressEvent: "mouse_press",
                 ButtonReleaseEvent: "mouse_release",
                 MotionNotifyEvent: "motion",
                 KeyPressEvent: "key_press",
                 KeyReleaseEvent: "key_release",
                 ExposeEvent: "expose",
                 NoExposureEvent: "no_exposure"}

    def key_name(keycode):
        return keybind.get_keysym_string(keybind.get_keysym(keycode))

    startdrag = None

    def wrap_xcb_event(event, doc):
        global startdrag
        event.type = xcb_event.get(event.__class__, event.__class__)
        if event.type == Event.key_press:
            event.key_name = key_name(event.detail)
            keysym = keybind.get_keysym(event.detail, event.state & 0b111)
            event.char = unikeysym.keys[keysym]["unicode"]\
                         if keysym in unikeysym.keys else u""
            if event.char == unichr(0):
                event.char = ""
            event.mods = []
            for attrib in dir(KeyButMask):
                if not attrib.startswith("__"):
                    if event.state & getattr(KeyButMask, attrib):
                        event.mods.append(attrib)
        elif event.type in [Event.mouse_press, Event.mouse_release]:
            event.button = event.detail
            event.xy = numpy.array([event.event_x, event.event_y])
            event.txy = numpy.linalg.solve(doc["drawing"].transform, numpy.append(event.xy, [1]))[:2]
            event.mods = []
            for attrib in dir(KeyButMask):
                if not attrib.startswith("__"):
                    if event.state & getattr(KeyButMask, attrib):
                        event.mods.append(attrib)
            if event.type == Event.mouse_press and event.button == 1:
                startdrag = event.xy
            logger.info("Wrapped: %s", (event.__class__.__name__, event.button, event.xy, event.mods))
        elif event.type == Event.motion:
            event.xy = numpy.array([event.event_x, event.event_y])
            event.txy = numpy.linalg.solve(doc["drawing"].transform, numpy.append(event.xy, [1]))[:2]
            if event.state & EventMask.Button1Motion:
                event.drag_button = 1
            elif event.state & EventMask.Button2Motion:
                event.drag_button = 2
            elif event.state & EventMask.Button1Motion:
                event.drag_button = 3
            else:
                event.drag_button = None
            if event.drag_button:
                event.diff = event.xy - startdrag
            if event.drag_button:
                logger.info("Wrapped: %s", (event.__class__.__name__, event.drag_button, event.xy, event.diff))
            logger.info("Wrapped: %s", (event.type, event.__class__.__name__, event.xy))

    def xcb_poll(doc):
        event = doc.surface.poll()
        if event is None: return None
        wrap_xcb_event(event, doc)
        return event

    backend_poll = xcb_poll

elif BACKEND == "tkinter":
    tk_event = {"<Button-%s>": "mouse_press",
                "<ButtonRelease-%s>": "mouse_release",
                "<B%s-Motion>": "motion",
                "<Motion>": "motion",
                "<Key>": "key_press",
                "<???>": "key_release",
                "<expose>": "expose"}

    tk_mods = ["Shift", "Caps", "Control", "LeftAlt", "NumLock",
               "Right Alt", "Button 1", "Button 2", "Button 3"]

    tk_events = deque()

    def newevent(event_type, event):
        #print "Tk event", event_type, event.__dict__
        event.raw_type = event_type
        tk_events.append(event)

    def tk_bind(tk_root):
        for event in ["<Button-%s>", "<ButtonRelease-%s>", "<B%s-Motion>"]:
            for button_num in range(1, 6):
                tk_root.bind(event % button_num,
                             lambda e, t=(event, button_num): newevent(t, e))
        tk_root.bind("<Key>", lambda e: newevent(("<Key>", None), e))
        tk_root.bind("<Motion>", lambda e: newevent(("<Motion>", 0), e))

    def wrap_tk_event(event, doc):
        global startdrag
        event.type = tk_event[event.raw_type[0]]
        if event.type == Event.key_press:
            event.key_name = event.keysym
            event.mods = []
            for i, attrib in enumerate(tk_mods):
                if event.state & 1<<i:
                    event.mods.append(attrib)
            logger.info("Wrapped: %s", (event.type, event.key_name))
        elif event.type in [Event.mouse_press, Event.mouse_release]:
            event.widget.focus_set()
            event.button = event.raw_type[1]
            event.xy = numpy.array([event.x, event.y])
            event.txy = numpy.linalg.solve(doc["drawing"].transform, numpy.append(event.xy, [1]))[:2]
            event.mods = []
            for i, attrib in enumerate(tk_mods):
                if event.state & 1<<i:
                    event.mods.append(attrib)
            if event.type == Event.mouse_press and event.button == 1:
                startdrag = event.xy
            logger.info("Wrapped: %s", (event.type, event.button, event.xy, event.mods))
        elif event.type == Event.motion:
            event.xy = numpy.array([event.x, event.y])
            event.txy = numpy.linalg.solve(doc["drawing"].transform, numpy.append(event.xy, [1]))[:2]
            event.drag_button = event.raw_type[1]
            if event.drag_button:
                event.diff = event.xy - startdrag
                logger.info("Wrapped: %s", (event.type, event.drag_button, event.xy, event.diff))

    def tk_poll(doc):
        try:
            event = tk_events.popleft()
        except IndexError:
            return None
        wrap_tk_event(event, doc)
        proc_logger.info("Processing %s", event)
        return event

    backend_poll = tk_poll

elif BACKEND == "opengl":
    from OpenGL.GLUT import *
    from config import MAINLOOP
    ogl_events = defaultdict(deque)
    glut_mods = [(GLUT_ACTIVE_SHIFT, "Shift"),
                 (GLUT_ACTIVE_CTRL, "Control"),
                 (GLUT_ACTIVE_ALT, "Alt")]

    event_poll = None
    event_doc = {}
    def add_event(event):
        event.win_id = glutGetWindow()
        ogl_events[event.win_id].append(event)
        if MAINLOOP == "glut":
            event_poll() #event_doc[event.win_id]
            glutPostRedisplay()
        #event_poll(event_doc[event.win_id])
        #event_draw()

    def glut_key(key, x, y):
        event = Event()
        event.__dict__.update({"raw_type": "key_press",
                               "char": key,
                               "raw_mods": glutGetModifiers(),
                               "xy": numpy.array([x, y])})
        add_event(event)

    def glut_mouse(button, state, x, y):
        event = Event()
        event.__dict__.update({"raw_type": "mouse",
                               "button": button,
                               "state": state,
                               "raw_mods": glutGetModifiers(),
                               "xy": numpy.array([x, y])})
        add_event(event)

    def glut_motion(x, y):
        event = Event()
        event.__dict__.update({"raw_type": "motion",
                               "button": None,
                               "xy": numpy.array([x, y])})
        add_event(event)

    def glut_bmotion(x, y):
        event = Event()
        event.__dict__.update({"raw_type": "motion",
                               "button": GLUT_LEFT,
                               "xy": numpy.array([x, y])})
        add_event(event)

    def set_callbacks(win_id):
        glutSetWindow(win_id)
        glutKeyboardFunc(glut_key)
        glutMouseFunc(glut_mouse)
        glutMotionFunc(glut_bmotion)
        glutPassiveMotionFunc(glut_motion)

    startdrag = None

    def wrap_ogl_event(event, doc):
        global startdrag
        event.type = event.raw_type
        if event.raw_type == "mouse":
            event.type = {GLUT_UP:"mouse_release",
                          GLUT_DOWN:"mouse_press"}[event.state]
            event.txy = numpy.linalg.solve(doc["drawing"].transform,
                                           numpy.append(event.xy, [1]))[:2]
            event.mods = []
            for attrib, name in glut_mods:
                if event.raw_mods & attrib:
                    event.mods.append(name)
            if event.type == Event.mouse_press and event.button == GLUT_LEFT_BUTTON:
                startdrag = event.xy
            event.button = {GLUT_LEFT:1, 2:3, 3:4, 4:5}[event.button]
        elif event.type == Event.key_press:
            #event.key_name = event.key #key_name(event.key)
            event.key_name = event.char
            if event.char == unichr(8):
                event.key_name = "BackSpace"
            elif event.char == unichr(13):
                event.key_name = "Return"
            event.mods = []
            for mod, mod_name in [(GLUT_ACTIVE_SHIFT, "Shift"),
                                  (GLUT_ACTIVE_CTRL, "Control"),
                                  (GLUT_ACTIVE_ALT, "Alt")]:
                if event.raw_mods & mod:
                    event.mods.append(mod_name)
        elif event.type == Event.motion:
            event.txy = numpy.linalg.solve(doc["drawing"].transform,
                                           numpy.append(event.xy, [1]))[:2]
            event.drag_button = {GLUT_LEFT:1, 2:3, 3:4, 4:5, None:None}[event.button]
            if event.drag_button:
                event.diff = event.xy - startdrag
            if event.drag_button:
                logger.info("Wrapped: %s", (event.__class__.__name__, event.drag_button, event.xy, event.diff))
        return event

    def ogl_poll(doc):
        #glutSetWindow(doc.surface.win_id)
        if MAINLOOP != "glut":
            glutMainLoopEvent()
        try:
            event = ogl_events[doc.surface.win_id].popleft()
        except IndexError:
            return None
        wrap_ogl_event(event, doc)
        proc_logger.info("Processing %s", event.__dict__)
        return event

    backend_poll = ogl_poll
