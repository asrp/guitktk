from draw import collide, simplify_transform
from const import rounded, identity, get_matrix, transformed, default_get
from const import get_translate, get_scale
import numpy
import persistent_doc.document as pdocument
from persistent_doc.document import Expr, Ex
from time import time as cur_time
# from pyinstrument import Profiler
from ast import literal_eval
import tree_lang
from itertools import chain, groupby
from pdb import set_trace as bp

def n(inp):
    return tree_lang.parse(inp, locals=globals())

def pause_timer():
    if not doc['timer.paused']:
        doc['timer.total'] = cur_time()
        doc['timer.paused'] = True

def unpause_timer():
    if doc['timer.paused']:
        doc['timer.paused'] = False
        doc['timer.start'] = time.time()

def toggle_timer():
    if doc['timer.paused']:
        unpause_timer()
    else:
        pause_timer()

def cur_time():
    if doc['timer.paused']:
        return doc['timer.total']
    else:
        return doc['timer.total'] + time.time() - doc['timer.start']

pdocument.scope = {"P": P, "cur_time": cur_time, "transformed": transformed}

#doc['drawing'].append(Node("text", value="hello world", p_botleft=P(100, 100)))
#doc['drawing'][-1]["id"] = "console"
#doc["console"]["value"] = ""

def add_letter(node_id=None):
    node_id = node_id if node_id is not None else doc["editor.focus"]
    if doc["editor.key_name"] == "backspace":
        doc[node_id + ".value"] = doc[node_id + ".value"][:-1]
    else:
        doc[node_id + ".value"] += doc["editor.key_char"]

def run_text(node_id, param="value"):
    try:
        co = compile(doc[node_id][param], "<ui>", "single")
        exec co in globals()
    except:
        traceback.print_exc()

def clear(node_id):
    doc[node_id]["value"] = ""

def key_press(event, key_name=None):
    return event.type == Event.key_press and\
        (key_name is None or (event.key_name == key_name and (not key_name.isalpha or "shift" not in event.mods)))

def shift_key_press(event, key_name=None):
    return event.type == Event.key_press and "shift" in event.mods and\
        (key_name is None or event.key_name.lower() == key_name)

def control_key_press(event, key_name=None):
    return event.type == Event.key_press and "control" in event.mods and\
        (key_name is None or event.key_name.lower() == key_name)

def run_button(mod=None):
    root = doc[doc["selection.root"]]
    txy = doc["editor.mouse_txy"]
    cui = doc['custom_ui'] if default_get(doc['custom_ui'], 'visible') else []
    more = []
    for child in chain(cui, reversed(root)):
        if collide(child, txy):
            print "clicked on", child["id"], "on_click" in child, mod
            if "on_click" in child and not mod:
                run_text(child["id"], "on_click")
            elif "on_shift_click" in child and mod == "shift":
                run_text(child["id"], "on_shift_click")
            elif child.get("button_group"):
                # Wrong. Should test children right away in reverse order.
                more.extend([(gc, child.transform) for gc in child])
                print "Button group", len(more) #[n['id'] for n in more]
                continue
            return True
    # TODO: refactor
    for child, transform in more:
        if collide(child, txy, transform=transform):
            print "clicked on", child["id"], "on_click" in child, mod
            if "on_click" in child and not mod:
                run_text(child["id"], "on_click")
            elif "on_shift_click" in child and mod == "shift":
                run_text(child["id"], "on_shift_click")
            elif child.get("button_group"):
                more.extend([(gc, child.transform) for gc in child])
                print "Button group", [n['id'] for n in more]
                continue
            return True
    return False

def mouse_press(event, button=None):
    return event.type == Event.mouse_press and\
           (button is None or event.button == int(button))

def mouse_release(event, button=None):
    return event.type == Event.mouse_release and\
           (button is None or event.button == int(button))

def shiftless_mouse_press(event, button=None):
    return event.type == Event.mouse_press and "shift" not in event.mods and\
           (button is None or event.button == int(button))

def create_text():
    doc[doc['selection.root']].append(Node("text", value="",
                               p_botleft=doc["editor.mouse_txy"]))
    doc["editor.focus"] = doc[doc['selection.root']][-1]["id"]

def edit_text():
    root = doc[doc["selection.root"]]
    mxy = doc["editor.mouse_xy"] if root["id"] == "drawing" else \
          doc["editor.mouse_txy"]
    for child, transform in root.dfs():
        # Problem: dfs includes child's transform and so does bbox.
        if child.name == "text" and\
           collide(child, mxy, transform=transform, tolerance=8):
            doc["editor.focus"] = child["id"]
            return True
    return False

def finished_edit_text():
    node = doc[doc["editor.focus"]]
    text = node["value"]
    if text.startswith("!"):
        node["on_click"] = text[1:]
    elif text.startswith("="):
        node["value"] = Ex(text[1:], calc="reeval")
    elif text.startswith("@"):
        node["filename"] = text[1:]
        # Child would actually be top left
        #node.L['transforms.move'] = ('translate', node['botleft.value'])
        node.L['botleft.child_id'] = 'topleft'
        node.L.change(name="image")

def finished_edit_formula():
    node = doc[doc["formula.node"]]
    text = doc["formula.value"]
    doc["formula.visible"] = False
    if text.startswith("!"):
        node[doc["formula.param"]] = text[1:]
    elif text.startswith("="):
        node["value"] = Ex(text[1:], calc="reeval")
    elif text.startswith("@"):
        node["filename"] = text[1:]
        # Child would actually be top left
        #node.L['transforms.move'] = ('translate', node['botleft.value'])
        node.L['botleft.child_id'] = 'topleft'
        node.L.change(name="image")

def grab_point():
    root = doc[doc["selection.root"]]
    cui = doc['custom_ui'].dfs() if default_get(doc['custom_ui'], 'visible') else []
    for child, transform in chain(root.dfs(), cui):
        if child.name == "point" and\
           collide(child, doc["editor.mouse_txy"], transform=transform, tolerance=8):
            doc["editor.drag_start"] = doc["editor.mouse_txy"]
            doc["editor.grabbed"] = child["id"]
            child.transforms["editor"] = Ex("('translate', `editor.mouse_txy - `editor.drag_start)", calc='on first read')
            return True
    return False

def rounded(xy):
    # Note: numpy rounding is weird. May want to calculate this manually later.
    return numpy.around(xy, doc['editor.grid']) if doc['editor.grid'] else xy

def drop_point():
    node = doc[doc["editor.grabbed"]]
    simplify_transform(node)
    # coord / GRIDSIZE) * GRIDSIZE 
    doc["editor.drag_start"] = None
    doc["editor.grabbed"] = None
    if doc['editor.grid']:
        print(rounded(node.L['value']))
        node.L['value'] = rounded(node.L['value'])

def add_line():
    doc[doc['selection.root']].append(Node("path", fill_color=None, children=[
                           Node("line", p_start=doc["editor.mouse_txy"],
                                p_end=doc["editor.mouse_txy"] + P(50, 50))]))

def rectangle1(topleft, botright):
    topleft = topleft["value"]
    bottomright = botright["value"]
    if (topleft >= bottomright).all():
        topleft, bottomright = bottomright, topleft
    topright = P(bottomright[0], topleft[1])
    bottomleft = P(topleft[0], bottomright[1])
    newnode = Node("path", skip_points=True, p_topleft=topleft, p_botright=bottomright,
                   p_topright=topright, p_botleft=bottomleft, children = [
        Node("line", start=Ex("`self.parent.topleft", "reeval"), end=Ex("`self.parent.topright", "reeval")),
        Node("line", start=Ex("`self.parent.topright", "reeval"), end=Ex("`self.parent.botright", "reeval")),
        Node("line", start=Ex("`self.parent.botright", "reeval"), end=Ex("`self.parent.botleft", "reeval")),
        Node("line", start=Ex("`self.parent.botleft", "reeval"), end=Ex("`self.parent.topleft", "reeval")),
    ])
    return newnode

#doc['drawing'].append(Node("group", id="rect", p_topleft=P(300, 300), p_botright=P(500, 400), children=[rectangle2()]))

# Can't transform corners this way! Need corners to be a pair of points
def topright(corners):
    if numpy.array_equal(corners, (None, None)):
        return None
    return Node("point", value=P(corners[1][0], corners[0][1]))

def botleft(corners):
    return Node("point", value=P(corners[0][0], corners[1][1]))

pdocument.scope["topright"] = topright
pdocument.scope["botleft"] = botleft


def rectangle2(**params):
    params_str = " ".join("%s=%s" % (key, _repr(value))
                          for key, value in params.items())
    inp = """
    group:
      corners=exc('(transformed(`self.topleft), transformed(`self.botright))')
      topright=exc('topright(`self.corners)')
      botleft=exc('botleft(`self.corners)')
      %s
      path: skip_points=True
        line: start=exc('`self.parent.parent.topleft')
              end=exc('`self.parent.parent.topright')
        line: start=exc('`self.parent.parent.topright')
              end=exc('`self.parent.parent.botright')
        line: start=exc('`self.parent.parent.botright')
              end=exc('`self.parent.parent.botleft')
        line: start=exc('`self.parent.parent.botleft')
              end=exc('`self.parent.parent.topleft')
    """ % params_str
    return tree_lang.parse(inp, locals=globals())

#pdocument.scope["rectangle2"] = rectangle2
#pdocument.scope["rectangle3"] = rectangle3

def selection_bbox(node_id):
    newnode = Node("group",
                   id="%s_bbox" % node_id, stroke_color=(0, 0.5, 0),
                   ref=exr("`%s" % node_id),
                   fill_color=None, skip_points=True,
                   dash=([5,5],0), children=[
                       rectangle4(corners=exc("(`%s).bbox()" % node_id))])
    return newnode

# Problem with this approach above: Nodes are created all the time. id references are unstable...
#def selection_bboxes(selected):
#    newnode = Node("group", children=[selection_bbox(node_id)
#                                      for node_id in selected])
#    return newnode

# pdocument.scope["selection_bboxes"] = selection_bboxes

def toggle_selection():
    root = doc[doc["selection"]["root"]]
    # Assumes root.combined_transform().dot(root.transform) is the identity.
    txy = doc["editor.mouse_txy"]
    # Otherwise, use the alternative below.
    #_txy = doc["editor.mouse_txy"]
    #transform = numpy.linalg.inv(root.combined_transform().dot(root.transform))
    #txy = transformed(Node("point", value=_txy), transform)
    for child in reversed(root):
        if collide(child, txy):
            print "clicked on", child["id"]
            if child["id"] in doc["editor.selected"]:
                selection_del(doc, child)
            else:
                selection_add(doc, child)
            break

def selection_add(doc, node):
    node_id = node["id"]
    doc["selection"].append(selection_bbox(node_id))
    doc["editor.selected.%s" % node_id] = True

def selection_del(doc, node):
    node_id = node["id"]
    doc["selection"].remove(doc["%s_bbox" % node_id])
    del doc["editor.selected.%s" % node_id]

def least_common_ancestor(nodes):
    node = nodes[0]
    path_to_root = [node['id']]
    while node.parent:
        node = node.parent
        path_to_root.append(node['id'])
    for node in nodes:
        parent = node
        while parent['id'] not in path_to_root:
            parent = parent.parent
        path_to_root = path_to_root[path_to_root.index(parent['id']):]
    return doc[path_to_root[0]]

def group_selection():
    nodes = [ref['ref'] for ref in doc["selection"]]
    ancestor = least_common_ancestor(nodes)
    for node in nodes:
        node.deparent()
    parent = Node("group", children=[node.L for node in reversed(nodes)])
    ancestor.L.append(parent)

    doc["editor.selected"] = pdocument.pmap()
    doc["selection"].clear()
    selection_add(doc, parent)

def ungroup_selection():
    for selected_node in list(doc["selection"]):
        node = selected_node["ref"]
        if node.name == "group":
            index = node.parent.index(node)
            parent = node.parent
            node.parent.remove(node)
            selection_del(doc, node)
            parent = parent.L
            parent.multi_insert(index, node)
            for child in reversed(node):
                selection_add(doc, child)

def bboxes(nodes, transform=identity):
    boxes = [child.bbox(child.transform.dot(transform))
             for child in nodes]
    boxes = zip(*[box for box in boxes
                  if not numpy.array_equal(box, (None, None))])
    if not boxes:
        return (None, None)
    return (numpy.min(numpy.vstack(boxes[0]), 0),
            numpy.max(numpy.vstack(boxes[1]), 0))

def align(nodes, side=0, axis=0, all_bbox=None):
    for node in nodes:
        if "align" in node.transforms:
            del node["transforms.align"]
    nodes = [node.L for node in nodes]
    all_bbox = bboxes(nodes) if all_bbox is None else all_bbox
    for node in nodes:
        diff = all_bbox[side][axis] - node.bbox(node.transform)[side][axis]
        if diff and axis == 0:
            node.transforms["align"] = ('translate', P(diff, 0))
        elif diff and axis == 1:
            node.transforms["align"] = ('translate', P(0, diff))

def distribute(nodes, side=0, axis=0, spacing=10, all_bbox=None):
    for node in nodes:
        if "distribute" in node.transforms:
            del node["transforms.distribute"]
    nodes = [node.L for node in nodes]
    all_bbox = bboxes(nodes) if all_bbox is None else all_bbox
    val = all_bbox[side][axis]
    for node in nodes:
        bbox = node.bbox(node.transform)
        diff = val - bbox[side][axis]
        node.transforms["distribute"] = ('translate',
                                         P(diff, 0) if axis == 0 else P(0, diff))
        val += abs(bbox[1-side][axis] - bbox[side][axis])
        val += spacing

def set_auto_layout():
    for ref in reversed(doc["selection"]):
        node = ref["ref"]
        print "Layout", node, node["id"]
        # Maybe not needed
        if node.name not in ["group", "path"]:
            continue
        node.L["auto_layout"] = True
        node.L["side"] = 0
        node.L["axis"] = 1
        node.L["spacing"] = 12
        auto_layout_update(ref["ref"])

def update_layout():
    for ref in doc["selection"]:
        auto_layout_update(ref["ref"])

def auto_layout_update(source):
    if source.get('auto_layout'):
        self = source if type(source) == Node else doc[source.node]
        nodes = self
        # Should make recursive auto_layout_update call here.
        for node in nodes:
            if "distribute" in node.transforms:
                del node["transforms.distribute"]
                node = node.L
            if "align" in node.transforms:
                del node["transforms.align"]
        all_bbox = bboxes(nodes)
        align(nodes, side=self["side"], axis=1-self["axis"],
              all_bbox=all_bbox)
        distribute(nodes, self["side"], self["axis"],
                   all_bbox=all_bbox, spacing=self.get("spacing", 10))

def center(nodes, axis="all", all_bbox=None):
    for node in nodes:
        if "center" in node.transforms:
            del node["transforms.center"]
    nodes = [node.L for node in nodes]
    all_bbox = bboxes(nodes) if all_bbox is None else all_bbox
    def mid((tl, br)):
        return (tl + br) / 2
    all_bbox_mid = mid(all_bbox)
    for node in nodes:
        diff = all_bbox_mid - mid(node.bbox(node.transform))
        if axis == 0:
            diff[1] = 0
        elif axis == 1:
            diff[0] = 0
        else:
            assert(axis == "all")
        if diff.any():
            node.transforms["center"] = ('translate', diff)

def move_selection():
    doc["editor.drag_start"] = doc["editor.mouse_xy"]
    for ref in doc["selection"]:
        # / get_scale(editor.zoom)
        ref["ref"].transforms["editor"] = exc("('translate', `editor.mouse_xy - `editor.drag_start)")

def drop_selection():
    for ref in doc["selection"]:
        node = ref["ref"]
        if "move" not in node.transforms:
            node.transforms["move"] = ("translate", P(0, 0))
            node = node.L
        new = node["transforms.move"][1] + node["transforms.editor"][1]
        node.transforms["move"] = ("translate", new)
        del node.L.transforms["editor"]
    doc["editor.drag_start"] = None

def add_rectangle():
    doc[doc['selection.root']].append(rectangle2(px_topleft=doc["editor.mouse_xy"],
                                     px_botright=doc["editor.mouse_xy"] + P(50, 50)))

def visualize_cb(node):
    from visualize import visualize
    if "visualization" in doc.m:
        doc["visualization"].deparent()
    doc[doc['selection.root']].append(Node("group", id="visualization",
                               children=list(visualize(node))))

def add_visualize():
    assert(len(doc["selection"]) == 1)
    node = doc["selection.0.ref"]
    #visualize_cb(node)
    pdocument.scope['visualize_cb'] = visualize_cb
    doc['editor.callbacks.visualize'] = Ex('visualize_cb(`%s)' % node['id'])

profiler_state = "ended"
def profile_start():
    global profiler, profiler_state
    profiler_state = "started"
    print "Started profiler"
    profiler = Profiler() # or Profiler(use_signal=False), see below
    profiler.start()

def profile_end():
    global profiler, profiler_state
    profiler.stop()
    profiler_state = "ended"

    print(profiler.output_text(unicode=True, color=True))

def ended_profiler():
    return profiler_state == "ended"

def delete():
    for ref in list(doc["selection"]):
        selection_del(doc, ref["ref"])
        ref["ref"].deparent()

def scroll(axis_side):
    axis, side = literal_eval(axis_side)
    #print "axis, side", axis, side,
    side = -1 if side == 0 else 1
    diff = P(50 * side, 0) if axis == 0 else P(0, 50 * side)
    #print diff
    scale = get_scale(doc['drawing'], "zoom")
    xy = get_translate(doc['drawing'], "scroll_xy") + diff / scale
    doc['drawing.transforms.scroll_xy'] = ("translate", xy)

def shift_mouse_press(event, button=None):
    return event.type == Event.mouse_press and\
           "shift" in event.mods and\
           (button is None or event.button == int(button))

def control_mouse_press(event, button=None):
    return event.type == Event.mouse_press and\
           "control" in event.mods and\
           (button is None or event.button == int(button))

def zoom(out):
    # Should conjugate by current mouse position
    out = literal_eval(out)
    zoom = get_scale(doc["drawing"], "zoom") / 1.25 if out else\
           get_scale(doc["drawing"], "zoom") * 1.25
    doc["drawing"].transforms["zoom"] = ("scale", zoom)

def add_child():
    # Need multi-color selection?
    parent = doc["selection.0.ref"]
    child = doc["selection.1.ref"]
    #child.deparent()
    parent.append(child)
    selection_del(doc, child)
    update_layout()

def add_sibling():
    # Need multi-color selection?
    print "Adding sibling"
    sibling = doc["editor.gui_selected"]
    parent = sibling.parent
    #child = doc["selection.0.ref"]
    index = parent.index(sibling)
    selection = [node["ref"] for node in doc['selection']]
    doc["editor.selected"] = pdocument.pmap()
    doc["selection"].clear()
    parent.multi_insert(index+1, selection)
    auto_layout_update(parent.L)

# Need clipping and scrolling before this can be put into overlay
# Maybe using only add_visualize would be enough?
# Maybe want selecting a new item deselects the previous one?
def update_gui_tree():
    from visualize import visualize
    if 'gui_tree' in doc:
        doc['gui_tree'].deparent()
    # Should instead find the right index
    doc['overlay'].append(Node("group",
                               children=list(visualize(doc[doc['selection.root']]))))

def gui_select():
    root = doc[doc["selection"]["root"]]
    xy = doc["editor.mouse_xy"]
    for child, transform in root.dfs():
        if child.name not in ["group", "path"] and\
           collide(child, xy, transform=transform, tolerance=8):
            print "gui elem selected", child["id"]
            doc["editor.gui_selected"] = exr("`%s" % child["id"])
            break

def doc_undo():
    if doc.undo_index == -1:
        save_undo()
        doc.undo_index -= 1
    doc.undo_index -= 1
    doc.log("undo", doc.saved[doc.undo_index])
    doc.dirty.clear()

def doc_redo():
    if doc.undo_index < -1:
        doc.undo_index += 1
    doc.log("redo", doc.saved[doc.undo_index])
    doc.dirty.clear()

def save_undo():
    if doc.undo_index != -1:
        del doc.saved[doc.undo_index+1:]
    doc.saved.append(doc.m)
    doc.undo_index = -1

def fail():
    # Do not write undo/redo events into history.
    return False

def duplicate():
    id_ = doc['editor.selected'].keys()[0]
    node = doc[id_]
    doc[doc['selection.root']].append(Node("group", render=exr('[`%s]' % id_),
                               skip_points=True, id=id_ + "_copy",
                               transforms={"clone": ('translate', P(10, 10))}))

# TODO: Add new values around the mouse.
def paste_selection(translate=True):
    copies = [ref['ref'].deepcopy() for ref in doc['selection']]
    doc[doc['selection.root']].extend(copies)
    if translate:
        # Because .extend is non-destructive so the content of `copies` and
        # the end of the list `doc[doc['selection.root']]` are not the same
        copies = [node.L for node in copies]
        # Not quite right if multiple elements with transforms['copy'] selected.
        for node in copies:
            if "copy" in node.transforms:
                del node["transforms.copy"]
        boxes = [ref.L.bbox(ref.L.combined_transform(doc[doc['selection.root']]))
                 for ref in copies]
        boxes = zip(*[box for box in boxes if not numpy.array_equal(box, (None, None))])
        if bboxes:
            bbox = (numpy.min(numpy.vstack(boxes[0]), 0),
                    numpy.max(numpy.vstack(boxes[1]), 0))
            diff = doc['editor.mouse_txy'] - ((bbox[0] + bbox[1]) / 2)
            for node in copies:
                node.L.transforms["copy"] = ("translate", diff)
            copies = [node.L for node in copies]
    for ref in doc['selection']:
        selection_del(doc, ref['ref'])
    for node in copies:
        selection_add(doc, node)

def n(inp):
    return tree_lang.parse(inp, locals=globals())

def toggle_ui_layer():
    print "toggling"
    if doc['selection.root'] == "custom_ui":
        doc['selection.root'] = doc['editor.slide.id']
    else:
        doc['selection.root'] = "custom_ui"


def toggle_ui_visible():
    doc['custom_ui.visible'] = not default_get(doc['custom_ui'], 'visible')

def slide_index():
    return doc['editor.slides'].index(doc['editor.slide.id'])

def change_slide(diff=1):
    diff = int(diff)
    index = slide_index() + diff
    slides = doc['editor.slides']
    doc['selection.root'] = slides[index % len(slides)]
    doc['editor.slide'] = exr('`%s' % doc['selection.root'])
    doc['editor.slide.count'] = 0

def font_change(factor=1.2):
    factor = float(factor)
    for ref in doc['selection']:
        for node, transform in ref['ref'].dfs():
            if node.name == "text":
                node['font_size'] = default_get(node, "font_size") * factor

def font_face_change(new_font="monospace"):
    for ref in doc['selection']:
        for node, transform in ref['ref'].dfs():
            if node.name == "text":
                node['font_face'] = new_font

def add_slide(before_id=None):
    new_id = "slide%s" % (len(doc['editor.slides']) + 1)
    slide = Node("group", id=new_id, t=0, count=0,
                 visible=exr('`editor.slide.id == `self.id'))
    if before_id is None:
        doc['editor.slides'].append(new_id)
        doc['drawing'].append(slide)
        index = len(doc['editor.slides']) - 1
    else:
        index = doc['drawing'].index(doc[before_id])
        doc['drawing'].multi_insert(index, [slide])
        index = doc['editor.slides'].index(before_id)
        doc['editor.slides'].insert(index, new_id)
    change_slide(index - slide_index())

def move_to_layer():
    print "Moving to layer"
    for ref in doc['selection']:
        doc[doc['selection.root']].append(ref['ref'])

def enter_selection():
    doc['selection.root'] = doc["selection.0.ref.id"]
    selection_del(doc, doc['selection.0.ref'])

def exit_selection():
    # Clear current selection?
    doc['selection.root'] = doc[doc["selection.root"]].parent['id']

def make_blue():
    for ref in doc['selection']:
        ref['ref']['stroke_color'] = (0, 0, 1)

def make_red():
    for ref in doc['selection']:
        ref['ref']['stroke_color'] = (0.8, 0, 0)

def make_green():
    for ref in doc['selection']:
        ref['ref']['stroke_color'] = (0, 0.6, 0)

def center_title():
    node = doc['selection.0.ref']
    if 'tcenter' in node.transforms:
        del node.L.transforms['tcenter']
    tl, br = node.L.bbox()
    newtl = P(doc['editor.window_width'], 150)/2 - (br - tl)/2
    print "translate by", newtl - tl
    node.L.transforms['tcenter'] = ('translate', newtl - tl)
    #node.L['transforms.tcenter'] = ('translate', newtl - tl)
    #doc['selection.0.ref.transforms.tcenter'] = ('translate', newtl - tl)
    # Should also set id to something that involves titles?
    if not node.L['id'].startswith('title'):
        selection_del(doc, node.L)
        i = 1
        while True:
            if 'title%s' % i not in doc.m:
                break
            i += 1
        print 'New title id: title%s' % i
        node.L.change_id('title%s' % i)
        selection_add(doc, doc['title%s' % i])

def max_count(animations):
    return sum(1 for node in animations if node.name == 'anim_wait')

def slide_transition(diff=1):
    diff = int(diff)
    slide = doc['editor.slide']
    if 'count' not in slide:
        slide['count'] = 0
        slide = slide.L
    if diff > 0 and ("animations" not in slide or slide['count'] >= max_count(slide['animations'])):
        change_slide(1)
    elif diff < 0 and ("animations" not in slide or slide['count'] == 0):
        # Should set t to max_t here?
        change_slide(-1)
        slide = doc['editor.slide']
        if 'animations' in slide:
            slide.L['count'] = max_count(slide.L['animations'])
    else:
        slide['count'] = max(0, slide['count'] + diff)
        pause_timer()
        doc['editor.slide.animations.start_t'] = cur_time()
        setstate()
        if diff > 0:
            runanim()

# For testing TkTerp undo
def add_buggy():
    doc[doc['selection.root']].append(Node("point", value=doc["editor.mouse_xy"]))
    #causeerror

# Snippets
# Manually set timing
# doc['selection.0.ref.visible'] = exr('self.parent.t >= 2')
# Manually bottom align nodes
# align([ref['ref'] for ref in doc['selection']], 1, 1)

def paste_text(font_size=11.5, spacing=16):
    # Need similar thing for OpenGL backend.
    text = tkroot.clipboard_get()
    ydiff = P(0, spacing * 1.5)
    for i, line in enumerate(text.splitlines()):
        new_node = Node("text", value=line, font_size=font_size,
                        p_botleft=i*ydiff + doc["editor.mouse_txy"])
        doc[doc['selection.root']].append(new_node)
        selection_add(doc, new_node)

def paste_styled():
    #paste_text(14, 18)
    paste_text(10, 16)
    font_face_change("monospace")
    make_blue()

# !move_up(doc['selection.0.ref'])
# !move_down(doc['selection.0.ref'])
def move_down(node):
    if node["id"] in doc["editor.slides"]:
        index = doc['editor.slides'].index(node["id"])
        doc['editor.slides'].remove(node["id"])
        doc['editor.slides'].insert(index + 1, node["id"])
    index = node.parent.index(node)
    node.parent.multi_insert(index + 1, [node])

# move_up(doc[doc['editor.slide']])
def move_up(node):
    if node["id"] in doc["editor.slides"]:
        index = doc['editor.slides'].index(node["id"])
        doc['editor.slides'].remove(node["id"])
        doc['editor.slides'].insert(max(0, index - 1), node["id"])
    index = node.parent.index(node)
    node.parent.multi_insert(max(0, index - 1), [node])

def selected_nodes():
    return [ref['ref'] for ref in doc['selection']]

def bullet_points_align(**kwargs):
    align(selected_nodes(),
          all_bbox=(P(30, 150), (700, 600)), **kwargs)

def empty_selection():
    for node in selected_nodes():
        selection_del(doc, node)

def heavyside(t):
    return t > 0

def add_fadein_transition():
    print "Adding new fadein"
    slide = doc['editor.slide']
    if "animations" not in slide:
        slide.append(Node("group", child_id="animations"))
    slide.L['animations'].extend([Node('anim_wait'),
        Node("group", children=[
            Node('anim', target="%s.opacity" % node["id"],
                 start=0, end=1, max_t=1) for node in selected_nodes()]),
        ])

# Need a better way than to set max_t to epsilon.
def add_appear_transition():
    print "Adding new appear"
    slide = doc['editor.slide']
    if "animations" not in slide:
        slide.append(Node("group", child_id="animations"))
    slide.L['animations'].extend([Node('anim_wait'),
        Node("group", children=[
            Node('anim', target="%s.visible" % node["id"],
                 start=False, end=True, max_t=0.01, func="heavyside") for node in selected_nodes()]),
        ])

def runanim():
    doc['editor.slide.animations.start_t'] = cur_time()
    #doc['animations.finished'] = False
    doc['drawing.transforms.dummy'] = exr("animstep()")
    unpause_timer()

# ![simplify_transform(node) for node in selected_nodes()]
# !distribute(selected_nodes(), axis=1, spacing=20)

# doc['drawing'].remove(doc['drawing.0'])
# !doc[doc['editor.slide']]['max_t'] = 0

def to_back():
    node = doc['selection.0.ref']
    node.parent.multi_insert(0, [node])

def toggle_skip_points():
    doc['drawing.skip_points'] = not doc['drawing'].get('skip_points', False)

def print_all_text(roots=None):
    roots = roots if roots is not None else selected_nodes()
    texts = [node for selected in roots for node, _ in selected.dfs()
             if node.name == "text"]
    texts.sort(key=lambda n: (n['botleft.value'][1], -n['botleft.value'][0]))
    for text in texts:
        print text['value']
    
def xcb_screenshot(n=10):
    for i in range(n):
        doc.surface.surfaces['screen'].write_to_png('screenshots/slides%s.png' % i)
        if i < n-1:
            slide_transition()
            doc.surface.update_all()

def addanim():
    node = n("""
    group:
      group:
        anim: target="slide1.-1.opacity"
              start=0 end=1 max_t=2 func=half
        anim: target="slide1.-1.botleft.value"
              start=P(100, 100) end=P(300, 100) max_t=1 func=cube_root
        anim: target="slide1.-2.botleft.value"
              start=P(100, 250) end=P(300, 250) max_t=1
      anim_wait:
      anim: target="drawing.-2.opacity"
            start=0 end=1 max_t=1
      anim_wait:
      anim: target="drawing.-1.botleft.value"
            start=P(100, 200) end=P(300, 200) max_t=1
    """)
    doc['animations'].clear()
    doc['animations'].extend(node)

def interpolate(node, t):
    # Calling globals() so saving is easier but may want to cache values
    if "func" in node:
        t = globals()[node["func"]](t)
    return node['start'] * (1 - t) + node['end'] * t

def animstep():
    animations = doc['editor.slide.animations']
    count = doc['editor.slide.count']
    t = cur_time() - animations['start_t']
    print "t=%s count=%s" % (t, count)
    waits = 0
    for group in animations:
        if group.name == "anim_wait":
            waits += 1
            continue
        if waits != count:
            continue
        if group.name != "group":
            group = [group]
        for node in group:
            _t = min(node['max_t'], t) if node['max_t'] is not None else t
            doc[node['target']] = interpolate(node, _t)
        # Only last element controls ending time in group.
        if t < node['max_t']:
            break
        else:
            t = t - node['max_t']
    else:
        doc.remove_expr('drawing.transforms.dummy', newval=None,
                        if_expr=True)

def setstate():
    """ Compute state from all animations instead of just diffs. """
    animations = doc['editor.slide.animations']
    count = doc['editor.slide.count']
    t = cur_time() - animations['start_t']
    print "setting state to t=%s count=%s" % (t, count)
    waits = 0
    # Should probably traverse values that are higher than count in reverse order for.
    reindexed = [list(group) for k, group in groupby(animations, lambda x: x.name == "anim_wait") if not k]
    print "max_count=", len(reindexed)
    for one_set in reindexed[:count]:
        for group in one_set:
            if group.name != "group":
                group = [group]
            for node in group:
                if node['max_t'] is None:
                    continue
                doc[node['target']] = interpolate(node, node['max_t'])

    for one_set in reversed(reindexed[count+1:]):
        for group in one_set:
            if group.name != "group":
                group = [group]
            for node in group:
                if node['max_t'] is None:
                    continue
                doc[node['target']] = interpolate(node, 0)

    if count >= len(reindexed):
        return
    one_set = reindexed[count]
    for group in one_set:
        if group.name != "group":
            group = [group]
        for node in group:
            _t = min(node['max_t'], t) if node['max_t'] is not None else t
            doc[node['target']] = interpolate(node, _t)
        # Only last element controls ending time in group.
        if t < node['max_t']:
            break
        else:
            t = t - node['max_t']

pdocument.scope['animstep'] = animstep
pdocument.scope['setstate'] = setstate

def test_setstate():
    doc['slide1.count'] = 0
    doc['slide1.animations.start_t'] = cur_time()
    setstate()

def test_image():
    doc[doc['selection.root']].append(Node("image", id="pathimg",
                                           filename="path-close.png"))
    #doc['pathimg.transforms.test'] = ('translate', P(100, 100))
    doc['pathimg.transforms.test'] = ('scale', P(2, 2))

def rectangle_lasso():
    root = doc[doc["selection"]["root"]]
    txy = doc["editor.mouse_txy"]
    for rect in reversed(root):
        if collide(rect, txy):
            topleft, botright = rect.bbox()
            for child in reversed(root):
                topleft2, botright2 = child.bbox()
                if child['id'] != rect['id'] and (topleft <= topleft2).all() and (botright2 <= botright).all():
                    if child["id"] not in doc["editor.selected"]:
                        selection_add(doc, child)
            break

def copy_executable(mod=""):
    """Copy first selected's function to all selection."""
    command = doc['selection.0.ref.on_click']
    print("Copying with mod %s: %s" % (mod, command))
    for node in doc['selection']:
        node['ref']['on_%sclick' % mod] = command

def add_line_group():
    line = Node("line", p_start=rounded(doc["editor.mouse_txy"]),
                p_end=doc["editor.mouse_txy"])
    doc[doc['selection.root']].append(Node("path", children=[line]))
    doc["editor.drag_start"] = doc["editor.mouse_txy"]
    doc["editor.grabbed"] = line['end.id']
    line['end'].transforms["editor"] = Ex("('translate', `editor.mouse_txy - `editor.drag_start)", calc='on first read')

def add_line_start():
    group = doc[doc['selection.root']][-1]
    line = Node("line",
                start=Ex("`self.parent.%s.end" % (len(group) - 1), "reeval"),
                p_end=doc["editor.mouse_txy"])
    group.append(line)
    doc["editor.drag_start"] = doc["editor.mouse_txy"]
    doc["editor.grabbed"] = line['end.id']
    line['end'].transforms["editor"] = Ex("('translate', `editor.mouse_txy - `editor.drag_start)", calc='on first read')

def close_line_group():
    group = doc[doc['selection.root']][-1]
    if (group['-1.end.value'] == group['0.start.value']).all():
        print("Closed line")
        group[-1].remove(group[-1]['end'])
        group['-1.end'] = Ex("`self.parent.0.start", "reeval")

def rectangle_lasso_points():
    root = doc[doc["selection.root"]]
    cui = doc['custom_ui'].dfs() if default_get(doc['custom_ui'], 'visible') else []

    root = doc[doc["selection"]["root"]]
    txy = doc["editor.mouse_txy"]
    for rect in reversed(root):
        if collide(rect, txy):
            topleft, botright = rect.bbox()
            print("Found rect", topleft, botright)
            for child, transform in chain(root.dfs(), cui):
                if child.name == "point" and\
                   (topleft <= child['value']).all() and\
                   (child['value'] <= botright).all():
                    if child["id"] not in doc["editor.selected"]:
                        selection_add(doc, child)
            break

def interpreter_to_button(font_size=11.5, spacing=16):
    """Paste last interpreter line as text."""
    text = terp.history[-2]
    new_node = Node("text", value="!" + text, font_size=font_size, on_click=text,
                    p_botleft=doc["editor.mouse_txy"])
    doc[doc['selection.root']].append(new_node)

palette = [[0.09803921568627451, 0.6823529411764706, 1.0],
 [0.0, 0.5176470588235295, 0.7843137254901961],
 [0.0, 0.3607843137254902, 0.5803921568627451],
 [1.0, 0.2549019607843137, 0.2549019607843137],
 [0.8627450980392157, 0.0, 0.0],
 [0.7098039215686275, 0.0, 0.0],
 [1.0, 1.0, 0.24313725490196078],
 [1.0, 0.6, 0.0],
 [1.0, 0.4, 0.0],
 [1.0, 0.7529411764705882, 0.13333333333333333],
 [0.7215686274509804, 0.5058823529411764, 0.0],
 [0.5019607843137255, 0.30196078431372547, 0.0],
 [0.8, 1.0, 0.25882352941176473],
 [0.6039215686274509, 0.8705882352941177, 0.0],
 [0.0, 0.5686274509803921, 0.0],
 [0.9450980392156862, 0.792156862745098, 1.0],
 [0.8431372549019608, 0.4235294117647059, 1.0],
 [0.7294117647058823, 0.0, 1.0],
 [0.7411764705882353, 0.803921568627451, 0.8313725490196079],
 [0.6196078431372549, 0.6705882352941176, 0.6901960784313725],
 [0.21176470588235294, 0.3058823529411765, 0.34901960784313724],
 [0.054901960784313725, 0.13725490196078433, 0.1803921568627451],
 [1.0, 1.0, 1.0],
 [0.8, 0.8, 0.8],
 [0.6, 0.6, 0.6],
 [0.4, 0.4, 0.4],
 [0.17647058823529413, 0.17647058823529413, 0.17647058823529413]]

def color_palette():
    size = 30
    group = Node("group", transform=("translate", doc['editor.mouse_txy']),
                 button_group=True,
                 skip_points=True,
                 children=[
        rectangle2(px_topleft=P(i*size, 0),
                   px_botright=P(i*size, 0) + P(size, size),
                   fill_color=col,
                   on_click="doc['selection.0.ref.fill_color'] = %s" % (col,),
                   on_shift_click="doc['selection.0.ref.stroke_color'] = %s" % (col,))
                     for i, col in enumerate(palette)])
    doc[doc['selection.root']].append(group)

def formula_focus(node, param):
    print("formula focus %s %s" % (node['id'], param))
    doc["editor.focus"] = "formula"
    doc["formula.visible"] = True
    doc["formula.value"] = "!" + node[param]
    doc["formula.node"] = node["id"]
    doc["formula.param"] = param
    doc["formula.botleft.value"] = doc['editor.mouse_txy']
    # doc[doc["custom_ui.target"]] = self["value"]

def edit_formula(mod=None):
    print("f2 pressed")
    root = doc[doc["selection.root"]]
    txy = doc["editor.mouse_txy"]
    cui = doc['custom_ui'] if default_get(doc['custom_ui'], 'visible') else []
    more = []
    for child in chain(cui, reversed(root)):
        if collide(child, txy):
            print "clicked on", child["id"], "on_click" in child, mod
            if "on_click" in child and not mod:
                formula_focus(child, "on_click")
            elif "on_shift_click" in child and mod == "shift":
                formula_focus(child["id"], "on_shift_click")
            elif child.get("button_group"):
                # Wrong. Should test children right away in reverse order.
                more.extend([(gc, child.transform) for gc in child])
                print "Button group", len(more) #[n['id'] for n in more]
                continue
            return True
    # TODO: refactor
    for child, transform in more:
        if collide(child, txy, transform=transform):
            print "clicked on", child["id"], "on_click" in child, mod
            if "on_click" in child and not mod:
                formula_focus(child, "on_click")
            elif "on_shift_click" in child and mod == "shift":
                formula_focus(child, "on_shift_click")
            elif child.get("button_group"):
                more.extend([(gc, child.transform) for gc in child])
                print "Button group", [n['id'] for n in more]
                continue
            return True
    return False

if __init__:
    doc['editor.slide'] = exr('`slide1')
    doc['drawing'].extend(n("""
    group:
      group: id="custom_ui" visible=True
      group: id="slide1" visible=exr('`editor.slide.id == `self.id')
      group: id="slide2" visible=exr('`editor.slide.id == `self.id')
      group: id="slide3" visible=exr('`editor.slide.id == `self.id')
    """))
    doc['selection.root'] = 'slide1'
    # Should be a pvector
    doc['editor.slides'] = ['slide1', 'slide2', 'slide3']
    doc['editor.window_width'], doc['editor.window_height'] = 800, 600
    doc['editor.filename'] = 'extraui_doc.py'
    doc['root'].append(Node("group", id='animations'))
    doc['root'].append(Node("group", id="timer", paused=True, total=0))
    doc.saved = [doc.m]
    doc.undo_index = -1
    doc['overlay.transforms'] = exr('`drawing.transforms')
    doc.sync()
    doc.load()
    doc['editor.grid'] = -2

input_callbacks = """
exec = key_press(return)
       (~key_press(return) (key_press !add_letter(console) | @anything))*
       key_press(return) !run_text(console) !clear(console)
button = shift_mouse_press(1) ?run_button(shift) mouse_release(1)
       | shiftless_mouse_press(1) ?run_button mouse_release(1)
text = key_press(t) (?edit_text | !create_text) @text_editor !finished_edit_text
text_editor = (~key_press(return) (key_press !add_letter | @anything))*
              key_press(return)
move_point = key_press(e) ?grab_point (~key_press(e) @anything)* key_press(e) !drop_point
new_line = key_press(l) !add_line
multi_segment_line1 = shift_key_press(l) !add_line_group
           (mouse_press(1) !add_line_start
             (~mouse_press(1) @anything)* mouse_press(1) !drop_point
           | ~key_press @anything)*
multi_segment_line = shift_key_press(l) !add_line_group
             ( mouse_press(1) !drop_point !add_line_start
             | mouse_press(3) !drop_point ?fail
             | ~mouse_press(3) @anything )*
             mouse_press(3) !close_line_group
new_rect = key_press(r) !add_rectangle
rect_lasso = shift_key_press(e) !rectangle_lasso
rect_lasso_points = shift_key_press(w) !rectangle_lasso_points
select = key_press(s) !toggle_selection
group = key_press(g) !group_selection
ungroup = key_press(u) !ungroup_selection
move_selection = key_press(m) !move_selection
                 (~key_press(m) @anything)* key_press(m) !drop_selection
layout = shift_key_press(f) !set_auto_layout
update_layout = key_press(q) !update_layout
visualize = key_press(v) !add_visualize
profile_start = key_press(p) ?ended_profiler !profile_start
profile_end   = key_press(p) !profile_end
delete = key_press(x) !delete
zoom = control_mouse_press(4) !zoom(False)
     | control_mouse_press(5) !zoom(True)
scroll = shift_mouse_press(4) !scroll(0, 1)
       | shift_mouse_press(5) !scroll(0, 0)
       | mouse_press(4) !scroll(1, 1)
       | mouse_press(5) !scroll(1, 0)
gui_add_child = key_press(c) !add_child
gui_add_sibling = key_press(a) !add_sibling
update_gui_tree = key_press(h) update_gui_tree
gui_select = mouse_press(3) !gui_select mouse_release(3)
undo = key_press(z) !doc_undo ?fail
redo = shift_key_press(z) !doc_redo ?fail
paste = key_press(c) !paste_selection
next_slide = (key_press(page_down) | key_press(next)) !change_slide(1)
prev_slide = (key_press(page_up) | key_press(prior)) !change_slide(-1)
move_to_layer = shift_key_press(m) !move_to_layer
toggle_ui_layer = key_press(i) !toggle_ui_layer
toggle_ui_visible = shift_key_press(i) !toggle_ui_visible
enter_selection = shift_key_press(s) !enter_selection
exit_selection = shift_key_press(a) !exit_selection
font_increase = shift_key_press(equal) !font_change
font_decrease = key_press(minus) !font_change(0.83)
transition_forward = key_press(right) !slide_transition
transition_back    = key_press(left) !slide_transition(-1)
empty_selection = key_press(escape) !empty_selection
toggle_skip_points = shift_key_press(p) !toggle_skip_points
copy_exec = key_press(n) !copy_executable
          | shift_key_press(n) !copy_executable(shift_)
terp_button = key_press(b) !interpreter_to_button
formula_edit = ( key_press(f2) ?edit_formula
               | shift_key_press(f2) ?edit_formula(shift) )
               @text_editor !finished_edit_formula

command = @button | @text | @move_point | @new_line | @new_rect
        | @select | @group | @ungroup | @layout | @move_selection
        | @update_layout | @visualize | @delete
        | @profile_start | @profile_end 
        | @zoom | @scroll
        | @empty_selection
        | @paste | @next_slide | @prev_slide | @move_to_layer
        | @toggle_ui_layer | @toggle_ui_visible
        | @enter_selection | @exit_selection
        | @font_increase | @font_decrease
        | @transition_forward | @transition_back
        | @toggle_skip_points
        | @gui_add_sibling | @update_gui_tree | @gui_select
        | @rect_lasso | @copy_exec | @multi_segment_line
        | @rect_lasso_points | @terp_button
        | @formula_edit
        | @undo | @redo
grammar = (@command !save_undo | @anything)*
"""
# @exec | 
# | @gui_add_child 

# Only works in Tkinter!
# key_press(Z)
