from draw import collide, simplify_transform
from const import rounded, identity, get_matrix, transformed
from const import get_translate, get_scale
import numpy
import persistent_doc.document as pdocument
from persistent_doc.document import Expr, Ex
from time import time as cur_time
# from pyinstrument import Profiler
from ast import literal_eval

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

def run_button():
    root = doc[doc["selection.root"]]
    txy = doc["editor.mouse_txy"]
    for child in reversed(root):
        if collide(child, txy):
            print "clicked on", child["id"]
            if "on_click" in child:
                run_text(child["id"], "on_click")
            return True
    return False

def mouse_press(event, button=None):
    return event.type == Event.mouse_press and\
           (button is None or event.button == int(button))

def mouse_release(event, button=None):
    return event.type == Event.mouse_release and\
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

def grab_point():
    root = doc[doc["selection.root"]]
    mxy = doc["editor.mouse_xy"] if root["id"] == "drawing" else \
          doc["editor.mouse_txy"]
    for child, transform in root.dfs():
        if child.name == "point" and\
           collide(child, mxy, transform=transform, tolerance=8):
            doc["editor.drag_start"] = doc["editor.mouse_txy"]
            doc["editor.grabbed"] = child["id"]
            child.transforms["editor"] = Ex("('translate', `editor.mouse_txy - `editor.drag_start)", calc='on first read')
            return True
    return False

def drop_point():
    node = doc[doc["editor.grabbed"]]
    simplify_transform(node)
    doc["editor.drag_start"] = None
    doc["editor.grabbed"] = None

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
    txy = doc["editor.mouse_txy"]
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
    for ref in doc["selection"]:
        node = ref["ref"]
        print "Layout", node, node.name
        # Maybe not needed
        if node.name not in ["group", "path"]:
            continue
        node.L["auto_layout"] = True
        node.L["side"] = 0
        node.L["axis"] = 0
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
                   all_bbox=all_bbox)

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
    mxy = doc["editor.mouse_xy"] if root["id"] == "drawing" else \
          doc["editor.mouse_txy"]
    for child, transform in root.dfs():
        if child.name not in ["group", "path"] and\
           collide(child, mxy, transform=transform, tolerance=8):
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

def paste_selection():
    for id_ in doc['editor.selected']:
        doc['drawing'].append(doc[id_].deepcopy())

def selected_nodes():
    return [ref['ref'] for ref in doc['selection']]

def clear_selection():
    for node in selected_nodes():
        selection_del(doc, node)

if __init__:
    doc.saved = [doc.m]
    doc.undo_index = -1
    doc['overlay.transforms'] = exr('`drawing.transforms')
    doc.sync()

input_callbacks = """
exec = key_press(return)
       (~key_press(return) (key_press !add_letter(console) | @anything))*
       key_press(return) !run_text(console) !clear(console)
button = mouse_press(1) ?run_button mouse_release(1)
text = key_press(t) (?edit_text | !create_text)
       (~key_press(return) (key_press !add_letter | @anything))*
       key_press(return) !finished_edit_text
move_point = key_press(e) ?grab_point (~key_press(e) @anything)* key_press(e) !drop_point
new_line = key_press(l) !add_line
new_rect = key_press(r) !add_rectangle
select = key_press(s) !toggle_selection
group = key_press(g) !group_selection
ungroup = key_press(u) !ungroup_selection
move_selection = key_press(m) !move_selection
                 (~key_press(m) @anything)* key_press(m) !drop_selection
layout = key_press(f) !set_auto_layout
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
clear_selection = key_press(escape) !clear_selection

command = @exec | @button | @text | @move_point | @new_line | @new_rect
        | @select | @group | @ungroup | @layout | @move_selection
        | @update_layout | @visualize | @delete
        | @profile_start | @profile_end 
        | @zoom | @scroll
        | @paste | @clear_selection
        | @gui_add_sibling | @update_gui_tree | @gui_select
        | @undo | @redo
grammar = (@command !save_undo | @anything)*
"""
        # | @gui_add_child 
