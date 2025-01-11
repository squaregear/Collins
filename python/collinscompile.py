import sys
import collinsyacc
import opcodes
import extcodes
import guardcodes
import mymsgpack
import atom

def comp(ast, module_name):
    out={'funcs':{}}
    fun=out['funcs']
    for name in ast:
        func=ast[name]
        for impl in func:
            if name in fun:
                if fun[name][0]!=len(impl['params']):
                    return f'Error: function {name} expecting {fun[name][0]} parameters, but got {len(ast[name]["params"])}'
            else:
                fun[name]=(len(impl['params']), [])
            fun[name][1].append(build_impl(impl, module_name))
    # add a default msg handler that ignores
    if 'Receive/5' not in fun:
        fun['Receive/5']=(5, [])
    dflt={'name':'Receive', 'params': [('parameter', 'state'), ('ignored',),
        ('ignored',), ('ignored',), ('ignored',)], 'guard':(), 
        'code': [('variable', 'state')]}
    fun['Receive/5'][1].append(build_impl(dflt, module_name))
    # add a default Initial if none was given
    if 'Initial/1' not in fun:
        fun['Initial/1']=(1, [])
        dflt={'name':'Initial', 'params': [('ignored',)], 'guard':(), 
            'code': [('literal', 0)]}
        fun['Initial/1'][1].append(build_impl(dflt, module_name))
    out['atoms']={}
    for a in atoms:
        out['atoms'][mymsgpack.UInt(a)]=atoms[a]
    return out

def build_impl(ast, name):
    variables=[]
    closure={}
    patterns=[]
    for p in ast['params']:
        patterns.append(build_pattern(p, variables))
    guard=build_guard(ast['guard'], variables)
    code=build_code(ast['code'], variables, closure, name)
    if len(closure)>0:
        print(f'use of unassigned variables {[x for x in closure.keys()]}')
        raise Exception # zzz I need better error handling here
    return [patterns, guard, [], len(variables), code]

def build_closure_impl(ast, name):
    variables=[]
    closure={}
    patterns=[]
    for p in ast['params']:
        patterns.append(build_pattern(p, variables))
    guard=build_guard(ast['guard'], variables)
    code=build_code(ast['code'], variables, closure, name)
    closure=[(x, closure[x]) for x in closure]
    return [patterns, guard, closure, len(variables), code]

atoms={}

def get_atom(s):
    a=atom.of(s)
    if a in atoms:
        if atoms[a]!=s:
            raise Exception('atom {a} was already {atoms[a]}, received {s}')
    else:
        atoms[a]=s
    return a

def build_pattern(ast, variables):
    if ast[0]=='ignored':
        out=mymsgpack.Ext(extcodes.exists,bytes([0]))
    elif ast[0]=='simple_literal':
        out=ast[1]
    elif ast[0]=='atom':
        out=mymsgpack.UInt(get_atom(ast[1]))
    elif ast[0]=='int':
        out=mymsgpack.Ext(extcodes.int,bytes([0]))
    elif ast[0]=='string':
        out=mymsgpack.Ext(extcodes.string,bytes([0]))
    elif ast[0]=='function':
        out=mymsgpack.Ext(extcodes.func,bytes([ast[1]]))
    elif ast[0]=='parameter':
        try:
            i=variables.index(ast[1])
        except:
            i=len(variables)
            variables.append(ast[1])
        out=mymsgpack.Ext(extcodes.param,bytes([i]))
    elif ast[0]=='parameter_match':
        try:
            i=variables.index(ast[1])
        except:
            i=len(variables)
            variables.append(ast[1])
        patt=build_pattern(ast[2], variables)
        out=mymsgpack.Ext(extcodes.param_match,bytes([i])+mymsgpack.encode(patt))
        # zzz gives us encoding nested withing encoding, is there a better way?
    elif ast[0]=='match_list':
        out=[]
        for p in ast[1]:
            out.append(build_pattern(p, variables))
    elif ast[0]=='match_map':
        out={}
        for p in ast[1]:
            out[p[0]]=build_pattern(p[1], variables)
    return out

def build_guard(ast, variables):
    if ast==():
        return bytes()
    if type(ast) is tuple:
        if ast[0]=='index':
            out=build_guard(ast[1], variables)
            return out+mymsgpack.encode(guardcodes.index)+mymsgpack.encode(ast[2])
        if ast[0]=='simple_literal':
            return mymsgpack.encode(guardcodes.literal)+mymsgpack.encode(ast[1])
        out=build_guard(ast[1], variables)
        out+=build_guard(ast[2], variables)
        return out+mymsgpack.encode(guardcodes.lookup[ast[0]])
    return mymsgpack.encode(variables.index(ast))

basic_calls={'or':opcodes.lor, 'and':opcodes.land,
    'less':opcodes.less, 'greater':opcodes.greater,
    'plus':opcodes.add, 'minus':opcodes.sub, 'times':opcodes.mult,
    'divide':opcodes.div, 'mod':opcodes.mod, 'map_get':opcodes.mapget}

def build_code(ast, variables, closure, name):
    if type(ast) is list:
        out=bytes()
        for line in ast:
            out+=build_code(line, variables, closure, name)
    elif type(ast) is tuple:
        if ast[0]=='literal':
            out=bytes([opcodes.literal])+build_code(ast[1], variables, closure, name)
        elif ast[0]=='atom':
            out=bytes([opcodes.literal])+mymsgpack.encode(mymsgpack.UInt(get_atom(ast[1])))
        elif ast[0]=='call' or ast[0]=='anon_call':
            if ast[1] in basic_calls:
                out=build_code(ast[2][0], variables, closure, name)
                out+=build_code(ast[2][1], variables, closure, name)
                out+=bytes([basic_calls[ast[1]]])
            else:
                out=bytes()
                # zzz I should probably ensure here that len(ast[3]) == the
                # right number for the function called, -1 if it was piped
                for param in ast[3]:
                    out+=build_code(param, variables, closure, name)
                if ast[0]=='call':
                    # zzz can I encode this so that we're not doing so much
                    # string comparison? maybe translate to some index in vm?
                    out+=bytes([opcodes.call])
                    if len(ast[1])>0:
                        out+=mymsgpack.encode(ast[1])
                        # zzz add ast[1] to "uses" set
                    else:
                        out+=mymsgpack.encode(name)
                    out+=mymsgpack.encode(ast[2])
                    if len(ast)==5 and ast[4]: ast[3].append(True)
                    out+=mymsgpack.encode(len(ast[3]))
                else:
                    out+=build_code(ast[2], variables, closure, name)
                    out+=bytes([opcodes.callanon])+mymsgpack.encode(len(ast[3]))
        elif ast[0]=='function_name':
            out=bytes([opcodes.pushfunc])
            if len(ast[1])>0:
                out+=mymsgpack.encode(ast[1])
            else:
                out+=mymsgpack.encode(name)
            out+=mymsgpack.encode(ast[2])
            out+=mymsgpack.encode(ast[3])
        elif ast[0]=='anon_function':
            out=bytes([opcodes.deffunc])
            impls=[]
            for impl_ast in ast[2]:
                impl=build_closure_impl(impl_ast, name)
                new_closure=[]
                for pair in impl[2]:
                    # This builds the final closure by mapping the parent
                    # memory location to the memory location in the anonymous
                    # function that it needs to go into.
                    try:
                        i=variables.index(pair[0])
                    except:
                        i=len(variables)
                        variables.append(pair[0])
                        closure[pair[0]]=i
                    new_closure.append((i, pair[1]))
                impl[2]=new_closure
                impls.append(impl)
            print(f'  anonymous: {ast[1]}, {impls}')
            # zzz this leads to double encoding, there's probably a better way:
            out+=mymsgpack.encode((ast[1], impls))
        elif ast[0]=='send':
            out=build_code(ast[1], variables, closure, name)
            out+=build_code(ast[2], variables, closure, name)
            out+=build_code(ast[3], variables, closure, name)
            out+=bytes([opcodes.msg])
        elif ast[0]=='pipe':
            out=build_code(ast[1], variables, closure, name)
            out+=build_code(ast[2]+(True,), variables, closure, name)
        elif ast[0]=='assign':
            out=build_code(ast[1], variables, closure, name)
            try:
                i=variables.index(ast[2])
            except:
                i=len(variables)
                variables.append(ast[2])
            out+=bytes([opcodes.pop,i])
        elif ast[0]=='variable':
            try:
                i=variables.index(ast[1])
            except:
                i=len(variables)
                variables.append(ast[1])
                closure[ast[1]]=i
            out=bytes([opcodes.push,i])
        elif ast[0]=='map':
            out=build_code(ast[1], variables, closure, name)
            for pair in ast[2]:
                out+=build_code(pair[0], variables, closure, name)
                out+=build_code(pair[1], variables, closure, name)
                out+=bytes([opcodes.mapset])
        elif ast[0]=='list':
            out=build_code(ast[1], variables, closure, name)
            for item in ast[2]:
                out+=build_code(item, variables, closure, name)
                out+=bytes([opcodes.append])
        elif ast[0]=='empty_list':
            out=mymsgpack.encode([])
    else:
        out=mymsgpack.encode(ast)
    return out

code='''
Initial(ident)
    .foo(:test)=>out
    0

foo(:test)
    6
'''

# zzz If you include an IDENTIFIER in a match pattern, it just assigns the
# corresponding value to a variable named that in the new scope. Can I make it
# so you can instead match against such a variable in the enclosing scope when
# defining an anonymous function. (Is this "pinning" from elixir?)

if __name__=='__main__':
    module_name='testing'
    if len(sys.argv)>1:
        with open(sys.argv[1], 'r') as file:
            code=file.read()
        module_name=sys.argv[1]
        module_name=module_name[:module_name.index('.')]

    ast=collinsyacc.parser.parse(code)
    #print(ast)

    compiled=comp(ast, module_name)
    #print(compiled)
    if len(sys.argv)>2:
        with open(sys.argv[2], 'wb') as output:
            output.write(mymsgpack.encode(compiled))
