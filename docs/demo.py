# This is a DIY demo. To follow along,
# Start python flow_editor.py docs/demo.py
# Read the lines below and follow the instructions in the
# string comments

from draw import collide, simplify_transform
from const import rounded, identity, get_matrix
import numpy
import persistent.document as pdocument
from persistent.document import Expr, Ex
from time import time as cur_time

pdocument.excluded = {"P": P, "cur_time": cur_time}

input_callbacks = ""

"# Hello world"

"""
Instructions: 
   1. Uncomment the line of code below
   2. Save this file
   3. Press ctrl-r to reload in guitktk's main window
   4. See "hello world" appear
   5. Recomment the line of code below

Move down this document. Do the same every time you see
commented blocks of code.
"""

# doc['drawing'].append(Node("text", value="hello world", p_botleft=P(100, 100)))






"# Interpreter"

"""
Instructions: do the same as above: uncomment, save, reload, recomment
Don't forget to always recomment!
"""

# doc['drawing'][-1].change_id("console")
# doc["console"]["value"] = ""


"""
Instructions: Delete the triple single quote below and paste them
below "Paste triple quotes here!"
"""

'''
input_callbacks = """
exec = key_press(Return)
      (~key_press(Return) (key_press !add_letter(console) | @anything))*
      key_press(Return) !run_text(console) !clear(console)
grammar = ( @exec | @anything)*
"""

"## Add missing function calls"

"### Core of add_letter is the last line"

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

"Paste triple quotes here! You'll be asked to move them again later."
"And reload the main window (ctrl-r)"

"""
Instructions: After saving this file and reloading, the console should be enabled.

To test it, in the main guitktk window, press enter and type

    doc['console.botleft.value'] = P(0, 100)

(Backspace should work but there is otherwise no cursor.)

Or you can try a simpler command like "print(1)".

After you're done, move the triple quote to the next "Paste triple quotes here!" below.

In the future always save this file and reload in the main window after moving triple quotes.
"""






"# Buttons"

input_callbacks += """
button = mouse_press(1) ?run_button mouse_release(1)
grammar = ( @exec | @button | @anything)*
"""

"## Add missing function calls"

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

"### Detect single button or any button click"

def mouse_press(event, button=None):
    return event.type == Event.mouse_press and\
           (button is None or event.button == int(button))

def mouse_release(event, button=None):
    return event.type == Event.mouse_release and\
           (button is None or event.button == int(button))

# doc['drawing'].append(Node("text", id="button1", value="Click me!", p_botleft=P(10, 210)))
# doc['button1.on_click'] = "doc['button1.value'] = 'Clicked!'"

"Paste triple quotes here!"

"""
Instructions:
After moving the single triple quotes to the previous line, uncomment the two commented line, save, reload. recomment the above.

This should add "Click me!" to the document. Click it and it should turn to "Clicked!".

Try adding other buttons by modifying the two commented lines (then uncomment, save, reload, recomment).

When you're down, move the triple single quotes to the next "Paste triple quotes here!" below.
"""



"# Labels"

input_callbacks += """
text = key_press(t) !create_text
       (~key_press(Return) (key_press !add_letter | @anything))*
       key_press(Return)
grammar = (@exec | @button | @text | @anything)*
"""

def create_text():
    doc["drawing"].append(Node("text", value="",
                           p_botleft=doc["editor.mouse_xy"]))
    doc["editor.focus"] = doc["drawing"][-1]["id"]

"Paste triple quotes here!"

"""
Instructions:
[Text labels added!]

Create text by pressing t. Then type and press enter when you're done.

Create a few more text labels this way.

When you're down, move the triple single quotes to the next "Paste triple quotes here!" below.
"""





"# Text input"

input_callbacks += """
text = key_press(t) (?edit_text | !create_text)
       (~key_press(Return) (key_press !add_letter | @anything))*
       key_press(Return)
"""

def edit_text():
    root = doc[doc["selection.root"]]
    for child, transform in root.dfs():
        if child.name == "text" and\
           collide(child, doc["editor.mouse_xy"], transform=transform, tolerance=8):
            doc["editor.focus"] = child["id"]
            return True
    return False

"Paste triple quotes here!"

"""
Instructions:
[Label/textfield editing added!]

Press t over a label you added to the previous step. Press backspace a few times to delete some of it. Then type some new text and press enter when you're done.
"""




"# Buttons again"

input_callbacks += """
text = key_press(t) (?edit_text | !create_text)
       (~key_press(Return) (key_press !add_letter | @anything))*
       key_press(Return) !finished_edit_text
"""

def finished_edit_text():
    node = doc[doc["editor.focus"]]
    text = node["value"]
    if text.startswith("!"):
        node["on_click"] = text[1:]

"Paste triple quotes here!"

"""
Instructions:
[We got better buttons!]

Create a label containing

!doc['drawing'].pop()

Create some more text labels with anything in them.

Click on the "!doc['drawing'].pop()" and it should remove the newest of the other labels. Anything starting with "!" is now a button!
"""





"# Status bar"

def finished_edit_text():
    node = doc[doc["editor.focus"]]
    text = node["value"]
    if text.startswith("!"):
        node["on_click"] = text[1:]
    elif text.startswith("="):
        node["value"] = Ex(text[1:], calc="reeval")

"Paste triple quotes here!"

""" 
Instructions:

Create a label with text

=`editor.mouse_xy

Create another one with

=`editor.mouse_xy + P(100, 0)

Move your mouse around the main window.
"""

"#### End"
"#### Of"
"#### This"
"#### Demo"

"""
Instructions:

You can try to move the triple quotes further along but explicit
instructions are missing.
"""



"# Move points"

input_callbacks += """
move_point = key_press(e) ?grab_point (~key_press(e) @anything)* key_press(e) !drop_point
grammar = (@exec | @button | @text | @move_point | @anything)*
"""


def grab_point():
    root = doc[doc["selection"]["root"]]
    for child, transform in root.dfs():
        if child.name == "point" and\
           collide(child, doc["editor.mouse_xy"], transform=transform, tolerance=8):
            doc["editor.drag_start"] = doc["editor.mouse_xy"]
            doc["editor.grabbed"] = child["id"]
            child.transforms["editor"] = Ex("('translate', `editor.mouse_xy - `editor.drag_start)", 'reeval')
            return True
    return False

def drop_point():
    node = doc[doc["editor.grabbed"]]
    simplify_transform(node)
    doc["editor.drag_start"] = None
    doc["editor.grabbed"] = None








"# Add lines"

input_callbacks += """
new_line = key_press(l) !add_line
grammar = ( @exec | @button | @text | @move_point
          | @new_line | @anything)*
"""

def add_line():
    doc["drawing"].append(Node("path", fill_color=None, children=[
                           Node("line", p_start=doc["editor.mouse_xy"],
                                p_end=doc["editor.mouse_xy"] + P(50, 50))]))







"# Layouts"
"## Alignment"


def bboxes(nodes, transform=identity):
    boxes = [child.bbox(child.transform.dot(transform))
             for child in nodes]
    boxes = zip(*[box for box in boxes if box != (None, None)])
    if not boxes:
        return (None, None)
    return (numpy.min(numpy.vstack(boxes[0]), 0),
            numpy.max(numpy.vstack(boxes[1]), 0))

def align(nodes, side=0, axis=0, all_bbox=None):
    all_bbox = bboxes(nodes) if all_bbox is None else all_bbox
    for node in nodes:
        diff = all_bbox[side][axis] - node.bbox(node.transform)[side][axis]
        if diff and axis == 0:
            node.transforms["align"] = ('translate', P(diff, 0))
        elif diff and axis == 1:
            node.transforms["align"] = ('translate', P(0, diff))

# Try
# align(doc['drawing'][-3:])




"# Evenly distributing elements"

def distribute(nodes, side=0, axis=0, spacing=10, all_bbox=None):
    all_bbox = bboxes(nodes) if all_bbox is None else all_bbox
    val = all_bbox[side][axis]
    for node in nodes:
        bbox = node.bbox(node.transform)
        diff = val - bbox[side][axis]
        node.transforms["distribute"] = ('translate',
                                         P(diff, 0) if axis == 0 else P(0, diff))
        val += abs(bbox[1-side][axis] - bbox[side][axis])
        val += spacing


# Try
# distribute(doc['drawing'][-5:])







"# Automatically aligned groups"

def layout_callback(source, func, *args):
    if source.get('auto_layout'):
        self = source if type(source) == Node else source.node
        nodes = self[1:]
        for node in nodes:
            if "distribute" in node.transforms:
                del node.transforms["distribute"]
            if "align" in node.transforms:
                del node.transforms["align"]
        all_bbox = self[0].bbox(self[0].transform)
        align(nodes, side=self["side"], axis=1-self["axis"],
              all_bbox=all_bbox)
        distribute(nodes, self["side"], self["axis"],
                   all_bbox=all_bbox)



# Try
"""
doc['drawing'].append(Node('group', id='layout',
                           auto_layout=True,
                           side=0, axis=1, children=[
                         Node("line", p_start=P(400, 200),
                                      p_end=P(600, 500))]))
doc['layout'].callbacks.append(layout_callback)

and see that it places its contents as they are added

doc['layout'].append(doc['drawing'][4])
doc['layout'].append(doc['drawing'][4])
doc['layout'].append(doc['drawing'][4])
"""





input_callbacks = """
exec = key_press(Return)
      (~key_press(Return) (key_press !add_letter(console) | @anything))*
      key_press(Return) !run_text(console) !clear(console)
button = mouse_press(1) ?run_button mouse_release(1)
text = key_press(t) (?edit_text | !create_text)
       (~key_press(Return) (key_press !add_letter | @anything))*
       key_press(Return) !finished_edit_text
move_point = key_press(e) ?grab_point (~key_press(e) @anything)* key_press(e) !drop_point
new_line = key_press(l) !add_line
grammar = ( @exec | @button | @text | @move_point
          | @new_line | @anything)*
"""
'''
