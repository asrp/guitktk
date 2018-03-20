from pymetaterp.util import simple_wrap_tree
from pymetaterp import boot_tree, boot_stackless as boot, boot_grammar
# Otherwise creates strange inheritance bug when tree_lang is imported...
from pymetaterp import python
from pymetaterp.boot_stackless import Eval, Frame, MatchError
from pdb import set_trace as bp

# apply! = ('\t'|' ')* {name ('(' {balanced=args} ')')?}
gui_grammar = r"""
grammar = {rule*} spaces
rule = spaces {name=rule_name '!'?=flags and=args ("=" {or})}
name = (letter | '_') (letter | digit | '_')*

or = and ("|" {and})*
and = bound*
bound = quantified ('=' {name=inline})?
quantified = not (('*' | '+' | '?')=quantifier)?
not = "~" {expr=negation} | expr
expr = call | apply | parenthesis

call! = indentation? {('!'|'?')?=type name ('(' {balanced=args} ')')?}
apply! = indentation? '@' {name ('(' {balanced=args} ')')?}
parenthesis = "(" {or} ")"
escaped_char! = '\\' {'n'|'r'|'t'|'b'|'f'|'"'|'\''|'\\'}
balanced = (escaped_char | '(' balanced ')' | ~')' anything)*

comment = '#' (~'\n' anything)*
hspace = ' ' | '\t' | comment
indentation = (hspace* ('\r' '\n' | '\r' | '\n'))* hspace+
space = '\n' | '\r' | hspace
"""

inp = """
text = key_press(Return)
       (~key_press(Return) key_press !add_letter(editor.text))*
       !run_text(editor.text) !clear
grammar = (@text | ())*
"""

class Wait:
    pass

def pop(input):
    input[1] += 1
    try:
        return input[0][input[1]]
    except IndexError:
        input[1] -= 1
        return Wait

class Interpreter(boot.Interpreter):
    def match(self, root, input=None, pos=-1, scope=None):
        """ >>> g.match(g.rules['grammar'][-1], "x='y'") """
        self.input = [input, pos]
        self.stack = [Frame(root, self.input)]
        self.join_str = False
        self.scope = scope
        self.memoizer = {}
        #return self.match_loop(True)

    def match_loop(self, new):
        output = self.new_step() if new else self.next_step()
        while output is not Wait:
            new = output is Eval
            if output is Eval:
                root = self.stack[-1].calls[len(self.stack[-1].outputs)]
                self.stack.append(Frame(root, self.input))
                output = self.new_step()
            else:
                self.stack.pop()
                if not self.stack:
                    return True, output
                #print len(self.stack)*" ", "returned", output
                self.stack[-1].outputs.append(output)
                output = self.next_step()
        return False, new

    def new_step(self):
        root = self.stack[-1].root
        name = root.name
        calls = self.stack[-1].calls
        if name == "call":
            if len(root[0]) == 0:
                event = pop(self.input)
                if event is Wait:
                    return Wait
                args = root[2] if len(root) > 2 else []
                if not eval(root[1], self.scope)(event, *args):
                    return MatchError("Not exactly %s" % (root[1]))
            elif root[0][0] == '!':
                # Should return None instead?
                args = root[2] if len(root) > 2 else []
                return eval(root[1], self.scope)(*args)
            elif root[0][0] == '?':
                # Should return None instead?
                args = root[2] if len(root) > 2 else []
                if not eval(root[1], self.scope)(*args):
                    return MatchError("Predicate %s is false" % root[1])
            else:
                raise Exception()
        else:
            return boot.Interpreter.new_step(self)

def interpreter(inp):
    i1 = boot.Interpreter(simple_wrap_tree(boot_tree.tree))
    match_tree1 = i1.match(i1.rules['grammar'][-1], gui_grammar + boot_grammar.extra)
    i2 = boot.Interpreter(match_tree1)
    match_tree2 = i2.match(i2.rules['grammar'][-1], inp)
    return Interpreter(match_tree2)

if __name__ == "__main__":
    from wrap_event import Event

    interp = interpreter(inp)
    events = []
    interp.match(interp.rules['grammar'][-1], events)
    print interp.stack
    new = True
    finished, new = interp.match_loop(new)
    print finished, new
    finished, new = interp.match_loop(new)
    print finished, new

    event = Event()
    event.__dict__.update({"type": "key_press",
                           "key_name": "Return"})
    events.append(event)

    def key_press(event, key_name=None):
        return event.type == Event.key_press and\
            (key_name is None or event.key_name == key_name)

    finished, new = interp.match_loop(new)
    print finished, new

    event = Event()
    event.__dict__.update({"type": "key_press",
                           "key_name": "h"})
    events.append(event)

    def add_letter(*args):
        print "adding", args

    finished, new = interp.match_loop(new)
    print finished, new

    event = Event()
    event.__dict__.update({"type": "key_press",
                           "key_name": "Return"})
    events.append(event)

    def run_text(*args):
        print "running", args

    def clear():
        print "clear"

    finished, new = interp.match_loop(new)
    print finished, new

    #finished, self.new = interp.match_loop(self.new)
    #if finished:
    #    return new
