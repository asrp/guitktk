#from gui_lang import simple_wrap_tree, boot_tree, boot, boot_grammar, python
from pymetaterp.util import simple_wrap_tree
from pymetaterp import boot_tree, boot_stackless as boot, boot_grammar
from pymetaterp.boot_stackless import Eval, Frame, MatchError
from pymetaterp import python
from node import Node
from pdb import set_trace as bp

def paramdict(params, children):
    d = {} if params is None else\
        dict([params] if type(params) == tuple else\
        params)
    if children:
        if d.get('children'):
            d['children'].extend(children)
        else:
            d['children'] = children
    return d

tree_grammar = r"""
grammar = { (INDENT NEWLINE+ SAME_INDENT node (NEWLINE+ | ~anything))+
          | node } spaces
escaped_char! = '\\' {'n'|'r'|'t'|'b'|'f'|'"'|'\''|'\\'}
node = ("." {NAME} "=")?:child_id ({NAME:name} ':') (spaces {param})*:params 
       hspaces suite:children -> DNode(name, child_id=child_id, **paramdict(params, children))
param = NAME:name "=" expr:val -> (name, val)
expr = STRING:val -> val
     | NUMBER:val -> float(val) if '.' in val else int(val)
     | (NAME balanced | NAME | balanced | list_balanced):val -> eval(val) # val
     # | LAZY_EVAL:val -> val
suite = (INDENT (NEWLINE+ SAME_INDENT node)+ DEDENT
      | node | void):value -> to_list(value)
balanced = '(' (escaped_char | balanced | ~')' anything)* ')'
list_balanced = '[' (escaped_char | balanced | ~']' anything)* ']'
STRING = hspaces ( '"' {(~'"' anything)*} '"'
                  | '\'' {(~'\'' anything)*} '\'')
NEWLINE = hspaces ('\n' | '\r') {} | COMMENT_LINE
COMMENT_LINE = hspaces {comment} hspaces ('\n' | '\r')
SAME_INDENT = hspaces:s ?(self.indentation[-1] == (len(s) if s != None else 0))
INDENT = ~~(NEWLINE hspaces:s ?(self.indentation[-1] < (len(s) if s != None else 0))) !(self.indentation.append(len(s) if s != None else 0))
DEDENT = !(self.indentation.pop())
NAME = (letter | '_') (letter | digit | '_' | '.')*
NUMBER = '-'? (digit | '.')+

comment = ('#' {(~'\n' {anything})*})=comment
space = '\n' | '\r' | hspace
spaces = space*
spacesp = space+
hspaces = (' ' | '\t')*
hspacesp = (' ' | '\t')+
"""
# expr should join everything together

inp = """
 group: id="root"
  group: id="references"
  group: id="drawing"
    transforms=dict(zoom=("scale" P(1.0 1.0))
                    scroll_xy=("translate" P(0 0)))
  group: id="ui"
    group: id="editor" stroke_color=tuple(0 0.5 0) mode="edit"
      .path=path: stroke_color=tuple(0 0.5 0)
      .lastxy=point: value=(0 0)
      .text=text: value="" botleft=Ex("`self.parent.lastxy")
    group: id="overlay"
      group: id="selection" root="drawing"
      group: id="selection_bbox" stroke_color=tuple(0.5 0 0)
             dash=tuple([5 5] 0) skip_points=True
      group: id="clipboard" visible=False
      group: id="mouseover" root="drawing"
      group: id="status" root="drawing"
        text: ref_id="editor.lastxy" ref_param="value"
          .botleft=point: value=(0 600)
        text: ref_id="ui" ref_param="mode"
          .botleft=point: value=(100 600)
    group: id="grid" line_width=1 stroke_color=tuple(0 0 1) 
           skip_points=True

"""
inp2 = """
 group: id="root"
  group: id="references"
  group: id="drawing"
    text: value="inner1"
  group: id="overlay"
"""
inp3 = """
    group: transforms=dict(pos=("translate", (100, 200)))
      .left=text:   value='a' p_botleft=(-30, -10)
      .middle=text: value='b' p_botleft=(-10, -10)
      .right=text:  value='c' p_botleft=( 10, -10)
"""
inp4 = """
    group: foo=1.0
"""

def interpreter():
    i1 = boot.Interpreter(simple_wrap_tree(boot_tree.tree))
    grammar = boot_grammar.bootstrap + boot_grammar.extra + boot_grammar.diff
    match_tree1 = i1.match(i1.rules['grammar'][-1], grammar)
    i2 = boot.Interpreter(match_tree1)
    match_tree2 = i2.match(i2.rules['grammar'][-1], tree_grammar + boot_grammar.extra)
    return python.Interpreter(match_tree2)

interp = interpreter()
interp.source = tree_grammar
def parse(tree_str, **kwargs):
    global interp
    # Problem with nested matches!
    # Need a different inner interpreter in that case!
    if getattr(interp, "stack", []):
        interp = interpreter()
        interp.source = tree_grammar
    if 'locals' in kwargs:
        kwargs['locals'].update({'DNode': Node, 'paramdict': paramdict})
    out = interp.parse("grammar", tree_str, **kwargs)
    #out.pprint()
    return out

if __name__ == "__main__":
    import persistent_doc.document as pdocument
    #python.DNode = DNode
    #python.Node = DNode
    pdocument.default_doc = pdocument.Document(Node("group", id="root"))
    #out = interp.parse("grammar", inp, locals={"DNode": Node})
    out = parse(inp4, locals=globals(), debug=True)
    #pdocument.default_doc.tree_root.append(out)
    out.pprint()

