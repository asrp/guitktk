from draw import collide, simplify_transform
from const import rounded, identity, get_matrix
import numpy
import persistent_doc.document as pdocument
from persistent_doc.document import Expr, Ex

pdocument.scope = {"P": P}

input_callbacks = """
exec = key_press(Return)
      (~key_press(Return) (key_press !add_letter(console) | @anything))*
      key_press(Return) !run_text(console) !clear(console)
button = mouse_press(1) ?run_button mouse_release(1)
text = key_press(t) (?edit_text | !create_text)
      (~key_press(Return) (key_press !add_letter | @anything))*
      key_press(Return) !finished_edit_text
grammar = ( @exec | @button | @text | @anything)*
"""

def finished_edit_text():
    node = doc[doc["editor.focus"]]
    text = node["value"]
    if text.startswith("!"):
        node["on_click"] = text[1:]
    elif text.startswith("="):
        node["value"] = Ex(text[1:], calc="reeval")

def edit_text():
    root = doc[doc["selection.root"]]
    for child, transform in root.dfs():
        if child.name == "text" and\
           collide(child, doc["editor.mouse_xy"], transform=transform, tolerance=8):
            doc["editor.focus"] = child["id"]
            return True
    return False

def create_text():
    doc["drawing"].append(Node("text", value="",
                           p_botleft=doc["editor.mouse_xy"]))
    doc["editor.focus"] = doc["drawing"][-1]["id"]

def run_button():
    root = doc[doc["selection.root"]]
    xy = doc["editor.mouse_xy"]
    for child in reversed(root):
        if collide(child, xy):
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

def add_letter(node_id=None):
    node_id = node_id if node_id is not None else doc["editor.focus"]
    if doc["editor.key_name"] == "BackSpace":
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

"### Add keypress handling"

def key_press(event, key_name=None):
    return event.type == Event.key_press and\
        (key_name is None or event.key_name == key_name)


# doc['drawing'].append(Node("text", value="hello world", p_botleft=P(100, 100)))
# doc['drawing'][-1].change_id("console")
# doc["console"]["value"] = ""
# doc['drawing'].append(Node("text", id="button1", value="Click me!", p_botleft=P(10, 210)))
# doc['button1.on_click'] = "doc['button1.value'] = 'Clicked!'"
