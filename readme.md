# guitktk - Make and evolve a GUI and its toolkit simultaneously

Get the flexibility of not using a UI toolkit while still writing little code, and avoid "callback hells" of GUI making,

![Example usage](docs/preview.gif)

[Full slower video with that example](docs/demo.mp4) and more. All typing is fast forwarded. [Source by the end of the video](docs/video-final.py).

[Text description matching the video and more usage after the video](https://blog.asrpo.com/gui_toolkit)

## Intended use

guitktk is a toolkit for making GUI toolkits (i.e., a GUI toolkit toolkit).

Quickly experiment with different user interactions by alternating between editing (and using) the visual interface in guitktk and editing your program's source in an external text editor. Faster feedback makes adding helper elements for building the final interface worthwhile. Well suited for free-form canvas editing style interfaces but also allows building more traditional GUIs.

While all examples in this readme demonstrate how to create well known GUI elements with guitktk, guitktk is made for assembling other graphical and interactive elements. Especially ones better suited for the problem domain than generic elements. I made guitktk with the intention of building editors with it.

[TODO: Add an example of making an (atypical) editor.]

You can make GUI toolkits out of guitktk but the intended use is actually to make your UI and the toolkit to support it simultaneously. Altering a python source file and document, trying things out, visualizing the result and modify as you go.

## Event handling language

guitktk uses a parser to match keyboard, mouse and other events. Here's an example of a rule describing a console with an interpreter:

    exec = key_press(Return)
           (~key_press(Return) (key_press !add_letter(console) | @anything))*
           key_press(Return) !run_text(console) !clear(console)

- the user presses Return to start typing a command (`key_press(Return)`),
- then any key press that isn't Return is treated as character to add to the command (`~key_press(Return) (key_press !add_letter(console)`). Mouse events are ignored (`| @anything)`).
- this is repeated (`(...)*`) until Return is pressed  (`key_press(Return) !run_text(console) !clear(console)`)

The functions `key_press`, `add_letter`, `run_text` and `clear` are *not* hard-coded into the library for maximum flexibility. (But there are templates where you can copy-paste pre-existing functions like these for your project.)

[Full blog post describing and extending the above](https://blog.asrpo.com/gui_toolkit) (the syntax for `Expr` objects is slightly out of date).

The syntax of the language can be modified without too much difficulty. The default language is [pymetaterp](https://github.com/asrp/pymetaterp) with the following changes:

Input events are treated as a stream of "characters" defined by the "language" described in `input_callbacks`.

Names can be preceeded by 3 different prefixes (plus the empty prefix):

- `@` for calling another grammar rule
- `!` for calling a python function
- `?` for calling a python predicate: a function returning a `bool` for match success or failure
- no prefix for matching an event. The named function should be defined

All names can be optionally be called with an argument which is passed as a string.

# Installation

## Dependencies

The required dependencies are numpy, tkui, persistent_doc, pymetaterp and pyrsistent. Install with `pip install -r requirements.txt`.

There are [optional dependencies](optional.txt) for using the OpenGL (PyOpenGL) and Cairo backends (xpybutil, xcffib and cairoffi). A version of [xpybutil](https://github.com/BurntSushi/xpybutil) is bundled in.

The default Tkinter backend doesn't need extra packages.

## Running

    python flow_editor.py <filename>

`<filename>` is the *source file* being edited and defaults to `examples/functions.py`.

Also try `examples/empty.py`.

## Basic usage

After running guitktk, two windows open: a main window and a debugging window (more on their usage below). Open the source file (default: `functions.py`) in a text editor.

- Edit and use the interface in the main window.
- Edit the source file in your text editor, save and press Ctrl-r in the main window to load your changes (this runs `execfile` on the source).
- Repeat.

A number of functions are provided for convenience but they aren't connected to any UI elements or keyboard shortcut by default. Edit the source file and interface to add them. Paste code snippets from sample source files in `examples`.

## Default globals

`doc` - the current document. See [persistent_doc](https://github.com/asrp/persistent_doc) for basic usage.

Typically, you'd get nodes by id with `doc['<some_id>']` (or some dot separated path instead of `id`) and alter values there,

`input_callbacks` - string containing a description of the user's interaction, written in the language `gui_lang.py`. Input events are treated as a stream of "characters" defined by the "language" described in `input_callbacks`.

# Examples

[See this post first](https://blog.asrpo.com/gui_toolkit)

**DIY demo**: There's now a Do-It Yourself demo of that post where you can progressively move down a triple quoted comment marker down a file, save and reload (control-r in the main window). The demo is `docs/demo.py`.

[Example of adding (selection) rectangles](http://blog.asrpo.com/removing_polling)

## Different interfaces for adding a line

As another showcase, here are different possible interfaces for adding a line. (The source is available in `example/line_demo.py`. Delete definitions of `new_line` in `input_callbacks` to get different behaviour.)

All example assume the root grammar rule is something like

    grammar = (@new_line | @other_rule1 | @other_rule1 | ... | anything )*

and each defines a different `new_line` rule.

### Single keypress

First up is the default in `functions.py`. Add a line at the mouse cursor when `l` is pressedd.

Grammar rule:

    new_line = key_press(l) !add_line

Functions:

    def add_line():
        doc["drawing"].append(Node("path", fill_color=None, children=[
                               Node("line", p_start=doc["editor.mouse_txy"],
                                    p_end=doc["editor.mouse_txy"] + P(50, 50))]))

    def key_press(event, key_name=None):
        return event.type == Event.key_press and\
            (key_name is None or event.key_name == key_name)

### Modal

In this variation, pressing `l` puts us in "line mode" and each left mouse click creates a line. Exit line mode by pressing any key (switching to a different mode in a more complex UI).

Grammar:

    new_line = key_press(l) (~key_press mouse_press(1) !add_line)*

Functions:

    def mouse_press(event, button=None):
        return event.type == Event.mouse_press and\
               (button is None or event.button == int(button))

Other functions are the same as before.

### Modal two endpoints

Same as above but the first click gives the first endpoint of the line and a second click puts the other endpoint.

Grammar:

    new_line = key_press(l)
               (mouse_press(1) !add_line_start
                 (~mouse_press(1) @anything)* mouse_press(1) !drop_point
               | ~key_press @anything)*

Functions:

    def add_line_start():
        line = Node("line", p_start=doc["editor.mouse_txy"],
                    p_end=doc["editor.mouse_txy"])
        doc["drawing"].append(Node("path", fill_color=None, children=[line]))
        doc["editor.drag_start"] = doc["editor.mouse_txy"]
        doc["editor.grabbed"] = line[1]["id"]
        line[1].transforms["editor"] = Ex("('translate', `editor.mouse_txy - `editor.drag_start)", calc='on first read')
    
    def drop_point():
        node = doc[doc["editor.grabbed"]]
        simplify_transform(node)
        doc["editor.drag_start"] = None
        doc["editor.grabbed"] = None

# Document

`p_something` is shorthand a child `point` Node with `child_id="something"`.

## Node types

Create with `Node("<type>", **params, children=[<list of child nodes>])`. `.param_name` below refers to keys in `params`.

- `group`: Node for holding other nodes
- `point`: a point at position `.value`, represented as a 2 by 1 `numpy.array` (shorthand: `P`)
- `text`: the string `.value` rendered at `.font_size` with the bottom left corner at Point `.botleft` 
- `line`: line from Point `.start` to Point `.end`
- `path`: group of multiple lines
- `arc`: arc of radius `.radius` centered at `.center` between the angles of `.angle` (a tuple or `None`) in radians.

[TODO: Add examples of each. See examples in the sample interfaces for the moment.]

## Special properties

- `id`
- `child_id`: To get a "named" child accessible with `paramt["<child_id>"]`
- `transforms`: dictionary (`pysistent.pmap`) from string to 3 by 3 `numpy.array` (same format as SVG).

## Propagates to subtree

`line_width, stroke_color, fill_color, dash, skip_points`

The value of a parameter is that of the first ancestor of a node (including itself) that defines that parameter.

# Default interface

## Hard-coded keys

- **Ctrl-r**: Reload the source file
- **Ctrl-z**: Attempts to undo the last reload wiht `Ctrl-r`.

## Default UI

Its best to read the `input_callbacks` from the respective files but here's a high level description for `funtions.py`.

The UI is essentially modeless and the entire keyboard is thought of as many more buttons for the mouse.

- Add new text: `t`, edit the text and press enter when done
- Edit text: `t` with mouse cursor over text
- Add line: `l`
- Move points (blue filled circles): `e` with mouse over the point, move the mouse cursor, `e` again when done
- Select: `s` with mouse cursor over element toggles selection
- Group selection: `g`
- Ungroup selection: `u`
- Move selection: `m`, move mouse cursor, `m` again when done
- Zoom: Ctrl + mouse wheel
- Scroll: mouse wheel and shift + mouse wheel

### Special elements

**Buttons**: Any text starting with `!` is a button that runs the rest of that text when clicked.
**Status bars**: Any text starting with `=` will evaluate the remaining expression. References to the rest of the document should be preceeded with a backtick.

## Debugging window

Right now there's a second window that pops up and helps with debugging. In future versions, that window may no longer be needed. It includes a text representation of the `drawing` subtree and a console to run commands (outputs are in the terminal where Python was started).

Some debug buttons are there to make quick post-mortem debugging easier.

## Changing the default grammar

The grammar in which the grammar is written is in `gui_lang.py` and can be edited. It is written in the default [pymetaterp](https://github.com/asrp/pymetaterp) language (and thus can itself be modified if needed).

## Formulas referencing nodes in the document

See [persistent_doc's readme](https://github.com/asrp/persistent_doc).

## Changing backends

Manually edit `config.py`.

## Helper languages for describing trees

# Undo redo and debugging

Because guitktk uses `eval` and `execfile` quite a bit in order to gives you a lot of expressive power, it makes it very eazy to break things.

## Undo reload

By default, pressing **Ctrl-z** attempts to undo to before the last reload (with `Ctrl-r`).

## Undo individual changes

`doc.undo()` and `doc.redo()` are very low level and undoes a single modification to `doc`. Even simple actions usually result in many changes at this level.

A more practical approach is to save a `doc.m` pointer and restore to it with `doc.log("undo", pointer)`. For example, the sample file `functions.py` defines

    def doc_undo():
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
        return False

    if __init__:
        doc.saved = [doc.m]
        doc.undo_index = -1

and adds a wrapper to the root grammar rule that calls save_undo on successful interactions

    grammar = (@command !save_undo | @anything)*

and adds keyboards shortcuts (`z` for undo, `shift-z` for redo)

    command = ... | @undo | @redo
    undo = key_press(z) !doc_undo ?fail
    redo = key_press(Z) !doc_redo ?fail

## Saving and loading documents

`doc.save()` or `doc.save('<filename>.py')`. And later `doc.load()` or `doc.load('<filename>')`.

As you can see from the file generated, this does *not* save the document's edit history so undo after a document load is not possible.

## Reading the source

Here are a few hints about reading the source. `flow_editor.py` is the starting point for execution but I would probably look at `node.py` (and maybe some of the source for dependency [persistent_doc](https://github.com/asrp/persistent_doc)) first. Or `gui_lang.py` which describes the language `input_callbacks` is written in.

For the backend, look at `wrap_events.py` and `draw.py` first and then one of `tkinter_doc.py`, `xcb_doc` or `ogl_doc.py`

`compgeo.py` contains a small number of geometry algorithms.

## To document

- Helper `tree_lang`
- Event record and replay
- Document graphic elements
- Backend renders
- Computational geometry helpers
- Things to try in the default document
