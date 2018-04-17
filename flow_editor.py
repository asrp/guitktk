import persistent_doc.document as pdocument
from node import Node, _repr
import node

from const import P, exr, exc, Ex
import compgeo
from uielem import uidict, UI
try:
    from tkui import TkTerp, Entry, ScrolledText
    import tkui
except:
    from tkui import tkui
    from tkui.tkui import TkTerp, Entry, ScrolledText
from Tkinter import Tk, Label, Frame, Button, Canvas, Checkbutton, Toplevel
from config import BACKEND, LOG_EVENTS, MAINLOOP, DRAW_FREQUENCY, POLL_FREQUENCY
import tree_lang
import gui_lang
import pdb
from pdb import set_trace as bp
import traceback, sys
import os

import time
import logging

logformat = "[%(name)8s:%(levelno)3s] --- %(message)s" # (%(filename)s:%(lineno)s)"
logging.basicConfig(level=logging.DEBUG, format=logformat)
for name in ["draw", "poll", "proc", "event", "callback", "tk_draw", "ogl_draw", "tree", "transform", "eval", "key", "document", "recalc"]:
    logging.getLogger(name).propagate = False
for name in ["tree", "eval", "key"]:
    logging.getLogger(name).propagate = True
event_logger = logging.getLogger("poll")
tree_logger = logging.getLogger("tree")
eval_logger = logging.getLogger("eval")
key_logger = logging.getLogger("key")
draw_logger = logging.getLogger("draw")
cb_logger = logging.getLogger("callback")
recalc_logger = logging.getLogger("recalc")

if BACKEND == "xcb":
    from xcb_doc import Surface
elif BACKEND == "tkinter":
    from tkinter_doc import TkCanvas
    from wrap_event import tk_bind
elif BACKEND == "opengl":
    from OpenGL import GLUT
    GLUT.glutInit()
    GLUT.glutInitDisplayMode(GLUT.GLUT_RGB|GLUT.GLUT_DEPTH)
    from ogl_doc import OGLCanvas

class Document(pdocument.Document):
    def __init__(self, surface, root):
        pdocument.Document.__init__(self, root)
        self.surface = surface
        self.tree_ui = None
        self.tree_doc = None

    def draw_loop(self, timer, delay):
        starttime = time.time()
        try:
            drawn = self.surface.update_all()
        except:
            print "Error drawing"
            self.last_tb = sys.exc_traceback
            traceback.print_exc()
        draw_logger.debug("Drawtime %.5f" % (time.time() - starttime))
        if delay is not None:
            timer.after(delay, self.draw_loop, timer, delay)

    def layer_root(self, node):
        if hasattr(node, "node"):
            node = node.node
        # Assuming all root children are layers (which might not be true!)
        while "id" not in node or node not in self.tree_root:
            node = node.parent
        return node

    def save(self, filename = "saved_doc.py"):
        import node
        from shutil import copyfile
        timestr = time.strftime("%Y%m%d-%H%M%S")
        f = open(filename, "w")
        f.write("from node import Node\n")
        f.write("from numpy import array\n")
        f.write("from const import P, exr, exc\n")
        f.write("from persistent_doc.document import pmap\n")
        f.write("import node\n")
        f.write("node.node_num = %s\n" % node.node_num)
        f.write("root = %s" % self.tree_root.code())
        f.close()
        if not os.path.exists("saves"):
            os.makedirs("saves")
        copyfile(filename, os.path.join("saves", "%s-%s" % (filename, timestr)))

    def load(self, filename = "saved_doc"):
        # A bit dangerous because of eval at the moment.
        if filename.endswith(".py"):
            filename = filename[:-3]
        import importlib
        # Clear doc dict
        doc.log("load_doc", pdocument.pmap())
        doc.set_root(Node("group"))
        module = importlib.import_module(filename)
        reload(module)
        doc.set_root(module.root)

    def update_text(self, *args, **kwargs):
        if not self.tree_ui:
            return
        id_ = doc.m.get('editor.text_root')
        if id_ is None:
            newtext = ""
        else:
            newtext = "\n".join(self[id_].pprint_string())
        #newtext = "\n".join(self.tree_root.pprint_string())
        #newtext = ""
        #newtext = "\n".join(self.root.pprint_string())
        #tree_logger.debug("Text changed %s" % (uidict["tree"].get(1.0, 'end') != newtext+"\n"))
        if self.tree_ui.text != newtext+"\n":
            if self.tree_doc:
                self.tree_doc["drawing"].replace(list(visualize.visualize(self.tree_root)))
            self.tree_ui.text = newtext

def icons():
    inp = """
    group:
      arc: id='point_icon' radius=5 fill_color=(0, 0, 0.5) p_center=P(0, 0)
      arc: id='text_icon' radius=10 fill_color=(0, 0, 1) p_center=P(0, 0)
      arc: id='arc_icon' radius=10 fill_color=(0, 0, 0.8) p_center=P(0, 0)
      rectangle: id='rectangle_icon'
                 p_bottomright=P(10, 8) p_topleft=P(-10, -8)
      rectangle: id='square_icon' p_bottomright=P(8, 8) p_topleft=P(-8, -8)
      group: id='line_icon' skip_points=True
        rectangle: stroke_color=(0, 0, 0)
                   p_bottomright=P(10, 10) p_topleft=P(-10, -10)
        line: stroke_color=(0, 0, 0) p_start=(-5, 0) p_end=(5, 0)
      group: id='path_icon' skip_points=True
        rectangle: stroke_color=(0, 0, 0)
                   p_bottomright=P(10, 10) p_topleft=P(-10, -10)
        path: stroke_color=(0, 0, 0)
          line: p_start=P(-8, 2) p_end=P(-4, 6)
          line: p_start=P(-4, 6) p_end=P(4, -6)
          line: p_start=P(4, -6) p_end=P(8, -2)
      group: id='group_icon'
        arc: stroke_color=(0, 0, 0) radius=12 p_center=P(0, 0)
        arc: radius=4 fill_color=(0, 0, 0.8) p_center=P(0, -5)
        arc: radius=4 fill_color=(0, 0.8, 0) p_center=P(5, 4)
        arc: radius=4 fill_color=(0.8, 0, 0) p_center=P(-5, 4)
      group: id='ref_icon'
        path: stroke_color=(0, 0, 0)
          line: child_id='0' p_start=P(-10, 0) p_end=P(10, 0)
        path: stroke_color=(0, 0, 0) fill_color=(0, 0, 0)
          line: p_start=P(10, 0) p_end=P(0, -5)
          line: start=exr('`self.parent.parent.0.end') p_end=P(5, 0)
          line: start=exr('`self.parent.parent.1.end') p_end=P(0, 5)
          line: start=exr('`self.parent.parent.2.end')
                end=exr('`self.parent.parent.0.start')
    """
    return tree_lang.parse(inp, locals=globals())

def test_drawing():
    return [
        Node("group", id="edit node"),
    Node("line", id="aline", dash=([10,10], 0), stroke_color=(0, 0, 0),
             transform = ("linear", numpy.array([[1,0,30],[0,1,0],[0,0,1]])),
             children = [Node("point", child_id="start", value=P(0, 0)),
                         Node("point", child_id="end", value=P(100, 100))]),
        Node("path", id="square", stroke_color=(0.5, 0, 0), fill_color=(0, 1, 0), children=[
            Node("line", child_id="1", p_start=P(200, 200), p_end=P(250, 200)),
            Node("line", child_id="2", r_start="square.1.end", r_end="square.3.start"),
            Node("line", child_id="3", p_start=P(250, 250), p_end=P(200, 250)),
            Node("line", child_id="4", r_start="square.3.end", r_end="square.1.start") ]),
        Node("arc", id="aarc", fill_color=(0.5, 0, 0), p_center=P(200, 50), radius=50,
             angle=(0, 5*math.pi/8)), ]


def debug(*args, **kwargs):
    pdb.pm()

def doc_debug():
    doc.pm()

def terp_debug():
    terp.pm()

def quit():
    logging.info("Shutting down...")
    if "terp" in globals():
        try:
            terp.save()
        except:
            logging.error("Error saving.")
    uidict["root"].quit()

class EditorDocument(Document):
    def __init__(self, set_compgeo_surface=True):
        root = Node("group", id="root")
        if BACKEND == "xcb":
            Document.__init__(self, Surface(800, 600), root)
        elif BACKEND == "tkinter":
            Document.__init__(self, TkCanvas(800, 600, Toplevel()), root)
        elif BACKEND == "opengl":
            Document.__init__(self, OGLCanvas(800, 600), root)
        pdocument.default_doc = self
        self.set_root(empty_doc())
        self.tree_ui = None
        self.surface.addlayer(self, "drawing")
        self.surface.addlayer(self, "ui")
        #self['grid'].parent.remove(self['grid'])
        # Hack!
        if set_compgeo_surface:
            compgeo.surface = self.surface
        self.surface.show()
        self.STOP_POLLING = False
        self.event_log = []
        self.events = []

    def reload(self, grammar):
        if not grammar:
            self.interp = None
            return
        self.interp = gui_lang.interpreter(grammar)
        self.new = True
        self.interp.match(self.interp.rules['grammar'][-1], self.events,
                          pos=len(self.events), scope=globals())

    def poll(self):
        starttime = time.time()
        last_mouse = None
        last_event = None
        num_events = 0
        while True:
            if last_event:
                event, last_event = last_event, None
            else:
                event = backend_poll(self)
            # Combine contiguous region of mouse move events.
            if event and event.type == Event.motion:
                last_mouse = event
                continue
            elif last_mouse:
                last_event, event, last_mouse = event, last_mouse, None
            elif event is None:
                break
            if LOG_EVENTS:
                self.events.append(event)
                self.event_log.append((event, time.time()))
            out = None
            if event.type == Event.key_press:
                self["editor.key_name"] = event.key_name
                self["editor.key_char"] = event.char
                self["editor.key_mods"] = event.mods
            elif event.type == Event.motion:
                recalc_logger.debug("New mouse position")
                self["editor.mouse_xy"] = event.xy
                self["editor.mouse_txy"] = event.txy
            # Callbacks
            #if event.type == Event.key_press:
            #    self.add_letter("echo")
            if event.type == Event.key_press:
                if "Control" in event.mods and event.key_name.lower() == "r":
                    if "save_undo" in globals():
                        save_undo()
                    print "Reloading"
                    try:
                        execfile(script_name, globals())
                        self.reload(input_callbacks)
                        doc.script_versions.log("load", open(script_name).read())
                    except:
                        self.last_tb = sys.exc_traceback
                        traceback.print_exc()
                elif "Control" in event.mods and event.key_name.lower() == "z":
                    self.undo_reload()
                #print event.mods, event.key_name
            if self.interp:
                try:
                    inp = self.interp.input[:]
                    finished, self.new = self.interp.match_loop(self.new)
                    assert(not finished)
                except:
                    traceback.print_exc()
                    self.interp.input = inp[:]
                    self.last_tb = sys.exc_traceback
                    # Not sure about this one. Might just want to reset the
                    # state to the root grammar rule?
                    self.reload(input_callbacks)
            if time.time() - starttime > 0.2:
                print "Over time!", time.time() - starttime
            if event.type != "no_exposure":
                num_events += 1
        if num_events:
            self.sync()
            event_logger.debug("Eventtime %s %.5f" % (num_events, time.time() - starttime))
            self.update_text()
            if DRAW_FREQUENCY is None:
                self.draw_loop(uidict["root"], None)
        if not self.STOP_POLLING:
            uidict["root"].after(POLL_FREQUENCY, self.poll)

    def undo_reload(self):
        self.script_versions.undo()
        try:
            exec self.script_versions.current() in globals()
            self.reload(input_callbacks)
            # Should really be tracked with script_versions
            # but indices are off by one.
            doc_undo()
        except:
            self.last_tb = sys.exc_traceback
            traceback.print_exc()

    def pm(self):
        pdb.post_mortem(self.last_tb)

    def add_letter(self, node_id):
        if self["editor.key_name"] == "BackSpace":
            self[node_id]["value"] = self[node_id]["value"][:-1]
        else:
            self[node_id]["value"] += self["editor.key_char"]

uiroot = UI(Toplevel, packanchor = 'n', title = 'XCB Cairo', name = 'root', children = [
    UI(Frame, packside = 'top', children = [
        UI(ScrolledText, name = 'tree', width=50, height=30, font=('Arial',12)),
        UI(Frame, packside = 'left', children = [
            UI(Button, text = 'Debug', command=debug),
            UI(Button, text = 'DocDebug', command=doc_debug),
            UI(Button, text = 'TerpDebug', command=terp_debug)]),
        UI(Frame, packside = 'left', children = [
            UI(Label, text = 'Text: '),
            UI(Entry, defaulttext = 'test', name = 'text')]),
        UI(Frame, packside = 'left', children = [
            UI(Label, text = 'Id: '),
            UI(Entry, defaulttext = '', name = 'id')]),
        UI(Frame, packside = 'left', children = [
            UI(Label, text = 'Exec: '),
            UI(Entry, defaulttext = '', name = 'exec')]),
        UI(ScrolledText, name = 'node edit',
           width=50, height=3, font=('Arial',12)),
        ])])

def demo_empty_doc():
    inp = """
    group: id="root"
      group: id="references"
        arc: id="point_icon" radius=5 fill_color=(0, 0, 0.5) p_center=P(0, 0)
      group: id="drawing"
        transforms=dict(zoom=("scale", P(1.0, 1.0)),
                        scroll_xy=("translate", P(0, 0)))
        text: value='Press control-r to reload' p_botleft=P(0, 30)
      group: id="ui"
        group: id="editor" stroke_color=(0, 0.5, 0)
          mouse_xy=P(0, 0) key_name=None key_char=None key_mods=None
          mode="edit" selected=pdocument.pmap()
          callbacks=pdocument.pmap() gui_selected=None p_lastxy=P(0, 0)
          text_root="drawing"
          .path=path: stroke_color=(0, 0.5, 0)
          .text=text: value="" botleft=Ex("`self.parent.lastxy", calc="reeval")
        group: id="overlay"
          group: id="selection" root="drawing"
          group: id="selection_bbox" stroke_color=(0.5, 0, 0)
                 dash=([5, 5], 0) skip_points=True
                 children=[rectangle4(corners=exc("(`selection).bbox()"),
                                      visible=exc("len(`selection) > 1"))]
    """
    return tree_lang.parse(inp, locals=globals())

def rectangle4(**params):
    """ Expects to receive corners as params """
    # Parsing is very slow for now for some reason.
    params_str = " ".join("%s=%s" % (key, _repr(value))
                          for key, value in params.items())
    inp = """
    path:
      %s
      topright=exr('topright(`self.corners)')
      botleft=exr('botleft(`self.corners)')
      p_botright=exr('`self.parent.corners[1]')
      p_topleft=exr('`self.parent.corners[0]')
      line: start=exr('`self.parent.topleft') end=exr('`self.parent.topright')
      line: start=exr('`self.parent.topright') end=exr('`self.parent.botright')
      line: start=exr('`self.parent.botright') end=exr('`self.parent.botleft')
      line: start=exr('`self.parent.botleft') end=exr('`self.parent.topleft')
    """ % params_str
    out = tree_lang.parse(inp, locals=globals())
    return out

def full_empty_doc():
    inp = """
    group: id="root"
      group: id="references" children=icons()
      group: id="drawing"
        transforms=dict(zoom=("scale", P(1.0, 1.0)),
                        scroll_xy=("translate", P(0, 0)))
      group: id="ui"
        group: id="editor" stroke_color=(0, 0.5, 0)
          mouse_xy=P(0, 0) key_name=None key_char=None key_mods=None
          mode="edit" selected=pdocument.pmap()
          callbacks=pdocument.pmap() gui_selected=None p_lastxy=P(0, 0)
          text_root="drawing"
          .path=path: stroke_color=(0, 0.5, 0)
          .text=text: value="" botleft=Ex("`self.parent.lastxy", calc="reeval")
        group: id="overlay"
          group: id="selection" root="drawing"
          group: id="selection_bbox" stroke_color=(0.5, 0, 0)
                 dash=([5, 5], 0) skip_points=True
                 children=[rectangle4(corners=exc("(`selection).bbox()"),
                                      visible=exc("len(`selection) > 1"))]
          group: id="clipboard" visible=False
          group: id="mouseover" root="drawing"
          group: id="status" root="drawing"
            text: id="foo" value="testing" p_botleft=P(0, 600)
            text: id="echo" value="" p_botleft=P(0, 400)
            text: ref_id="editor" ref_param="mode"
                  p_botleft=P(100, 600)
        group: id="grid" line_width=1 stroke_color=(0, 0, 1)
               skip_points=True
    """
    return tree_lang.parse(inp, locals=globals())

def tkui_sendexec(event):
    if not hasattr(doc, "saved"):
        terp.sendexec(event)
        return
    save_undo()
    is_error = terp.sendexec(event)
    if is_error:
        doc_undo()

if __name__ == "__main__":
    #empty_doc = full_empty_doc
    empty_doc = demo_empty_doc
    tkroot = Tk()
    tkroot.withdraw()
    doc = EditorDocument()
    from wrap_event import Event, backend_poll
    #doc.tree_doc = EditorDocument()
    uiroot.makeelem()
    doc.tree_ui = uidict["tree"]
    doc.update_text()
    tkui.setfonts()

    histfile = "flow_editor_history"
    terp = TkTerp(histfile, globals())
    uidict['exec'].bind('<Return>', tkui_sendexec) #terp.sendexec
    uidict['exec'].bind('<KP_Enter>', tkui_sendexec)
    uidict['exec'].bind('<Up>', terp.hist)
    uidict['exec'].bind('<Down>', terp.hist)
    uidict["root"].protocol("WM_DELETE_WINDOW", quit)

    script_name = "final-demo.py"
    script_name = "full-demo.py"
    script_name = os.path.join("examples", "functions.py")
    if len(sys.argv) > 1:
        script_name = sys.argv[1]
    doc.script_versions = pdocument.UndoLog()
    doc.script_versions.log("load", open(script_name).read())
    __init__ = True
    execfile(script_name, globals())
    doc.reload(input_callbacks)
    __init__ = False

    import wrap_event
    if MAINLOOP == "tkinter":
        uidict["root"].after(10, doc.draw_loop, uidict["root"], DRAW_FREQUENCY)
        #uidict["root"].after(10, doc.tree_doc.draw_loop, uidict["root"], DRAW_FREQUENCY)
        uidict["root"].after(10, doc.poll)
        #uidict["root"].after(10, doc.tree_doc.poll)
        if BACKEND == "tkinter":
            tk_bind(doc.surface.canvas)
        elif BACKEND == "opengl":
            wrap_event.set_callbacks(doc.surface.win_id)
            #wrap_event.set_callbacks(doc.tree_doc.surface.win_id)
        logging.debug("Testing")

        uidict["root"].mainloop()
    elif MAINLOOP == "glut":
        def draw(self):
            self.draw_loop(uidict["root"], None)
        Document.ogl_draw = draw
        from OpenGL.GLUT import (glutIdleFunc, glutMainLoop, glutDisplayFunc,
                                 glutPostRedisplay, glutSetWindow)
        wrap_event.event_doc = {doc.surface.win_id: doc,}
                                #doc.tree_doc.surface.win_id: doc.tree_doc}
        wrap_event.event_poll = doc.poll
        wrap_event.event_draw = draw
        wrap_event.set_callbacks(doc.surface.win_id)
        #wrap_event.set_callbacks(doc.tree_doc.surface.win_id)
        glutMainLoop()
    else:
        raise Exception("Unknown main loop %s." % MAINLOOP)
