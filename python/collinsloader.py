import sys
import mymsgpack
import collinsvm
import extcodes
import re

def module_from_file(filename):
    with open(filename, 'rb') as file:
        raw_code=file.read()
    module, pos=mymsgpack.decode(raw_code)
    out={}
    for f in module['funcs']:
        out[f]=load_function(module['funcs'][f])
    for a in module['atoms']:
        if a in collinsvm.atoms:
            if collinsvm.atoms[a]!=module['atoms'][a]:
                raise Exception(f'Atom Collision! {a} is both {collinsvm.atoms[a]} and {module["atoms"][a]}')
        else:
            collinsvm.atoms[a]=module['atoms'][a]
    return out

def load_function(f):
    return collinsvm.Function(f[0], [load_impl(impl) for impl in f[1]])

def load_impl(i):
    patterns=[load_pattern(p) for p in i[0]]
    # patterns, guard, closure, mem_size, code
    return collinsvm.FuncImpl(patterns, i[1], i[2], i[3], i[4])

def load_pattern(p):
    if type(p) is mymsgpack.Ext:
        if p.t==extcodes.exists:
            return collinsvm.Exists()
        if p.t==extcodes.param:
            return collinsvm.Variable(p.data[0], None)
        if p.t==extcodes.param_match:
            patt, pos=mymsgpack.decode(p.data[1:])
            return collinsvm.Variable(p.data[0], load_pattern(patt))
        if p.t==extcodes.int:
            return collinsvm.IntType()
        if p.t==extcodes.string:
            return collinsvm.StringType()
        if p.t==extcodes.func:
            return collinsvm.FuncType(p.data[0])
    elif type(p) is list:
        return [load_pattern(x) for x in p]
    elif type(p) is dict:
        out={}
        for k in p:
            out[k]=load_pattern(p[k])
        return out
    else:
        return p

pathpart=re.compile(r'.*[/\\]')
def just_module_name(filename):
        m=pathpart.match(filename)
        module_name=filename
        if m:
            module_name=module_name[len(m[0]):]
        return module_name[:module_name.index('.')]

if __name__=='__main__':
    module_name='guesser'
    if len(sys.argv)>1:
        for filen in sys.argv[1:]:
            module_name=just_module_name(filen)
            collinsvm.environment[module_name]=module_from_file(filen)

        module_name=just_module_name(sys.argv[1])
        collinsvm.SendMessage(sys.argv[1:], module_name, 0, 'system', 0)

        while not collinsvm.process_queue.empty():
            collinsvm.process_once()
