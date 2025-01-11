import sys
import mymsgpack
import threading
import queue
import random
import opcodes
import guardcodes
import collinsloader
import copy
import sqlite3
import atom

environment={}

def one_step(process):
    """
    Takes the state of a running process, executes the next instruction, and
    returns the new state of the process.

    Args:
        process: A Process object to be run
    """
    frame=process.call_frames[-1]
    pc=frame.pc
 
    if pc>=len(frame.code):
        # If you're off the end of the code, return from the current call frame.
        # The top of the stack is assumed to be the return value.
        ret=frame.stack[-1]
        process.call_frames.pop()
        if len(process.call_frames)>0:
            process.call_frames[-1].stack.append(ret)
            return process
        else:
            # we just returned from the outermost call frame
            return ret

    instruction=frame.code[pc]
    stack=frame.stack
    #print(f'{process.module}:{process.ident} depth:{len(process.call_frames)} stack:{stack} memory:{frame.memory} inst:{instruction} pc:{pc} code:{frame.code}')

    if instruction==opcodes.push: # push from memory
        # zzz enforce some kind of stack size limit?
        # zzz this limits memory to 255, should we msgpack an int instead?
        stack.append(copy.deepcopy(frame.memory[frame.code[pc+1]]))
        pc+=2
    elif instruction==opcodes.pop: # pop to memory
        frame.memory[frame.code[pc+1]]=stack.pop()
        pc+=2
    elif instruction==opcodes.literal: # push literal
        val, pos = mymsgpack.decode_at(frame.code, pc+1)
        stack.append(val)
        pc=pos

    elif instruction==opcodes.lor:
        b=stack.pop()
        a=stack.pop()
        stack.append(TRUE if a==TRUE or b==TRUE else FALSE)
        pc+=1
    elif instruction==opcodes.land:
        b=stack.pop()
        a=stack.pop()
        stack.append(TRUE if a==TRUE and b==TRUE else FALSE)
        pc+=1
    elif instruction==opcodes.less:
        b=stack.pop()
        a=stack.pop()
        stack.append(TRUE if a<b else FALSE)
        pc+=1
    elif instruction==opcodes.greater:
        b=stack.pop()
        a=stack.pop()
        stack.append(TRUE if a>b else FALSE)
        pc+=1
    elif instruction==opcodes.add:
        b=stack.pop()
        a=stack.pop()
        stack.append(a+b)
        pc+=1
    elif instruction==opcodes.sub:
        b=stack.pop()
        a=stack.pop()
        stack.append(a-b)
        pc+=1
    elif instruction==opcodes.mult:
        b=stack.pop()
        a=stack.pop()
        stack.append(a*b)
        pc+=1
    elif instruction==opcodes.div:
        b=stack.pop()
        a=stack.pop()
        if type(a) is int and type(b) is int:
            stack.append(a//b)
        else:
            stack.append(a/b)
        pc+=1
    elif instruction==opcodes.mod:
        b=stack.pop()
        a=stack.pop()
        stack.append(a%b)
        pc+=1

    elif instruction==opcodes.mapset: # add to map
        val=stack.pop()
        key=stack.pop()
        stack[-1][key]=val
        pc+=1
    elif instruction==opcodes.append: # add to map
        val=stack.pop()
        stack[-1].append(val)
        pc+=1
    elif instruction==opcodes.mapget: # get from  map
        key=stack.pop()
        m=stack.pop()
        stack.append(m[key])
        pc+=1

    elif instruction==opcodes.msg: # send message
        ident=stack.pop()
        module=stack.pop()
        msg=stack.pop()
        SendMessage(msg, module, ident, process.module, process.ident)
        #stack.append(True) #zzz what does sending a message return?
        pc+=1

    elif instruction==opcodes.call or instruction==opcodes.callanon:
        # expects the stack to contain the parameters for the function call
        if instruction==opcodes.call:
            module, pc = mymsgpack.decode_at(frame.code, pc+1)
            func_id, pc = mymsgpack.decode_at(frame.code, pc)
            arity, pc = mymsgpack.decode_at(frame.code, pc)
            func=environment[module][f'{func_id}/{arity}']
            #print(f'trying to call {module}.{func_id}')
        else:
            arity, pc = mymsgpack.decode_at(frame.code, pc+1)
            func=stack.pop()
            if func.param_count!=arity:
                print(f'called with arity {arity} but wants {func.param_count}')
                raise Exception('bad arity') # zzz should handle better
        params=[]
        for i in range(func.param_count):
            params.insert(0,stack.pop())
        for impl in func.implementations:
            memory=match_params(impl, params)
            if type(memory) is list:
                # fill in memory based on this impl's closure
                for cl in impl.closure:
                    memory[cl[1]]=cl[0]
                if type(impl.code) is bytes:
                    new_frame=CallFrame(impl.code, memory)
                    frame.pc=pc
                    if pc>=len(frame.code):
                        process.call_frames.pop()
                    process.call_frames.append(new_frame)
                    return process
                # it's a built in func, do its thing and push result
                stack.append(impl.code(params,process.module,process.ident))
                frame.pc=pc
                return process
        return False #zzz should return useful error information
        pc+=3

    elif instruction==opcodes.pushfunc:
        module, pc = mymsgpack.decode_at(frame.code, pc+1)
        func_id, pc = mymsgpack.decode_at(frame.code, pc)
        arity, pc = mymsgpack.decode_at(frame.code, pc)
        func=environment[module][f'{func_id}/{arity}']
        stack.append(func)

    elif instruction==opcodes.deffunc:
        func_def, pc = mymsgpack.decode_at(frame.code, pc+1)
        func=collinsloader.load_function(func_def)
        for impl in func.implementations:
            for cl in impl.closure:
                cl[0]=frame.memory[cl[0]]
        stack.append(func)

    else:
        raise Exception(f'Bad Instruction: {instruction}')

    frame.pc=pc
    return process

class Process:
    def __init__(self, module, ident):
        """
        Args:
            module: This process is running code from module
            ident: The identity of the instance this process is from
        """
        self.module=module
        self.ident=ident
        self.call_frames=[]
    def __repr__(self):
        if len(self.call_frames)==0:
            return f'Process: {self.module}:{self.ident} noCallFrames'
        return f'Process: {self.module}:{self.ident} in {self.call_frames[-1]}'

class CallFrame:
    def __init__(self, code, memory):
        """
        Args:
            code: The code to be executed in this frame as a binary
            memory: The initial memory as a list (with parameters assigned)
        """
        self.code=code
        self.pc=0
        self.memory=memory
        self.stack=[]
    def __repr__(self):
        return f'CallFrame: stack{self.stack} mem{self.memory} code{self.code} pc{self.pc}'

# As a first pass, environment will consist of a dictionary mapping function
# IDs to functions. A function ID will be a 2-tuple, with the first part
# identifying the module (0 for this) and the second part identifying the
# function
# Maybe environment is a map of module names to definitions. When you load a
# file, it will also load everything it imports (if it can find it (by name?))
# and continue recurisvely until it has everything it needs.
# A module definition would map function names to Function definitions (with
# all their associated implementations)
# When you import, you might need some kind of version specification to say
# which version of the module you intent to use.
# The environment doesn't belong to a process, but processes keep a pointer to
# the environment.

# Execution time will be shared between running instances consisting of a type
# and an ID, their state, their list of pending messages (if any), and their
# current running process (if any)
# It could just be a list (priority queue) of running processes, each with a
# pointer to its type and ID, and with that you could look up their mailbox or
# retrieve their state.
# Your place in line could change after you're added if the scheduler
# prioritizes instances with a lot of pending messages, so a simple priority
# queue might not do the job.

class Function:
    def __init__(self, param_count, implementations):
        """
        Args:
            param_count: Number of parameters the function will take
            implementations: List of FuncImpl
        """
        self.param_count=param_count
        self.implementations=implementations
    def __repr__(self):
        return f'<Function params:{self.param_count} impls:{len(self.implementations)}>'

class FuncImpl:
    """
    Represents one implementation of a function, including the parameter
    patterns that will match this implementation.
    """
    def __init__(self, patterns, guard, closure, mem_size, code):
        """
        Args:
            patterns: List of patterns to match input parameters on
            mem_size: The amount of memory the function will need to run
            code: As binary
        """
        self.patterns=patterns
        self.guard=guard
        self.closure=closure
        self.mem_size=mem_size
        self.code=code
    def __repr__(self):
        return f'<FuncImpl:{len(self.patterns)},{self.mem_size},{self.code}>'

def match_params(impl, params):
    """
    Attempts to match a set of input parameters against a function
    implementation.

    Args:
        impl: The function implementation to match against
        params: The input parameters

    Returns:
        New internal memory for the function run if the parameters matched
        those expected by the function implementation. Returns False if the
        parameters didn't match.
    """
    #print(f'match_params {impl.patterns} {params}')
    if len(params)!=len(impl.patterns):
        return False
    memory=[None]*impl.mem_size
    memout=match_list(impl.patterns, params, memory)
    if type(memout) is list:
        if check_guard(impl.guard, memout):
            return memout
    return False

class Exists:
    """
    Represents a pattern matching any input.
    """
    None

class IntType:
    """
    Represents a pattern matching any integer.
    """
    None

class StringType:
    """
    Represents a pattern matching any string.
    """
    None

class FuncType:
    """
    Represents a pattern matching a function.
    """
    def __init__(self, arity):
        """
        Args:
            arity: The number of parameters to expect
        """
        self.arity=arity
    def __repr__(self):
        return f'<FuncType:{self.arity}>'

class Variable:
    """
    Represents a pattern where the value found should be kept in memory.
    """
    def __init__(self, address, pattern):
        """
        Args:
            address: The address in the local memory where the matched value should
            be stored.
            pattern: The pattern to match
        """
        self.address=address
        self.pattern=pattern
    def __repr__(self):
        return f'<Variable:{self.address},{self.pattern}>'

def match(pattern, candidate, memory):
    """
    Args:
        pattern: The expected pattern
        candidate: An input to be tested against the pattern
        memory: A list representing function internal memory

    Returns:
        Internal memory with variables filled in if the candidate matched
        the expected pattern. Returns False if it didn't match.
    """
    #print(f'match {pattern} {candidate} {memory}')
    if type(pattern) is list and type(candidate) is list:
        return match_list(pattern, candidate, memory)
    if type(pattern) is dict and type(candidate) is dict:
        return match_dict(pattern, candidate, memory)
    if type(pattern) is Variable:
        if memory[pattern.address] is None:
            memory[pattern.address]=candidate
        elif memory[pattern.address]!=candidate:
            return False
        if pattern.pattern is not None:
            return match(pattern.pattern, candidate, memory)
        return memory
    if type(pattern) is IntType:
        if type(candidate) is not int:
            return False
        return memory
    if type(pattern) is StringType:
        if type(candidate) is not str:
            return False
        return memory
    if type(pattern) is FuncType:
        dummy_func=Function(pattern.arity,[])
        if type(candidate) is not type(dummy_func):
            return False
        if candidate.param_count!=pattern.arity:
            return False
        return memory
    if type(pattern) is not Exists and pattern!=candidate:
        return False
    return memory

def match_list(pattern, candidate, memory):
    """
    Performs a match where the pattern is known to be a list.

    Args:
        pattern: The expected list-type pattern
        candidate: An input to be tested against the pattern
        memory: A list representing function internal memory

    Returns:
        Internal memory with variables filled in if the candidate matched
        the expected pattern. Returns False if it didn't match.
    """
    #print(f'match_list {pattern} {candidate} {memory}')
    if len(candidate)<len(pattern):
        return False
    for i in range(len(pattern)):
        new_mem=match(pattern[i], candidate[i], memory)
        if new_mem==False:
            return False
        memory=new_mem
    return memory

def match_dict(pattern, candidate, memory):
    """
    Performs a match where the pattern is known to be a dictionary.

    Args:
        pattern: The expected dictionary-type pattern
        candidate: An input to be tested against the pattern
        memory: A list representing function internal memory

    Returns:
        Internal memory with variables filled in if the candidate matched
        the expected pattern. Returns False if it didn't match.
    """
    #print(f'match_dict {pattern} {candidate} {memory}')
    for key in pattern:
        if key not in candidate:
            return False
        new_mem=match(pattern[key], candidate[key], memory)
        if not new_mem:
            return False
        memory=new_mem
    return memory

def check_guard(guard, memory):
    #print(f'check_guard {guard} {memory}')
    if len(guard)==0:
        return True
    pos=0
    l=len(guard)
    stack=[]
    while pos<l:
        #print(f'check_guard {guard} {pos} {memory} {stack}')
        code, pos=mymsgpack.decode_at(guard,pos)
        if code==guardcodes.index:
            idx, pos=mymsgpack.decode_at(guard, pos)
            stack.append(stack.pop()[idx])
        if code==guardcodes.literal:
            lit, pos=mymsgpack.decode_at(guard, pos)
            stack.append(lit)
        elif code==guardcodes.lookup['and']:
            stack.append(stack.pop() and stack.pop())
        elif code==guardcodes.lookup['or']:
            stack.append(stack.pop() or stack.pop())
        elif code==guardcodes.lookup['less']:
            stack.append(stack.pop() > stack.pop())
        elif code==guardcodes.lookup['greater']:
            stack.append(stack.pop() < stack.pop())
        elif code==guardcodes.lookup['equal']:
            stack.append(stack.pop() == stack.pop())
        else:
            stack.append(memory[code])
    return stack[-1]

#################################################
# Scheduler
#################################################

process_queue=queue.SimpleQueue()

def schedule(module, ident, state, message, from_module, from_ident):
    proc=Process(module, ident)
    code=bytes([opcodes.call])+mymsgpack.encode(module)
    code+=mymsgpack.encode('Receive')+mymsgpack.encode(5)
    cframe=CallFrame(code, [])
    cframe.stack.append(state)
    cframe.stack.append(message)
    cframe.stack.append(ident)
    cframe.stack.append(from_module)
    cframe.stack.append(from_ident)
    proc.call_frames.append(cframe)
    process_queue.put(proc)

def process_once():
    proc=process_queue.get()
    result=one_step(proc)
    if type(result) is Process:
        process_queue.put(result)
    else:
        StoreResult(result, proc.module, proc.ident)
        result # zzz what to do with this return value? anything?

#################################################
# Persistence Layer
#################################################

# The toy, in-memory version of persistence will consist of a map of module
# types by name to Module. Module will have a map of instance IDs to Instances.

persistence={} # zzz is there a concurrent version of map that I should use?
persist_lock=threading.Lock()

class Module:
    def __init__(self):
        self.lock=threading.Lock()
        self.map={}
    def __repr__(self):
        return f'<Module locked:{self.lock.locked()} ids:{self.map.keys()}>'

class Instance:
    def __init__(self, state):
        self.lock=threading.Lock()
        self.running=True
        self.state=state
        self.mailbox=queue.SimpleQueue()
    def __repr__(self):
        return f'<Instance locked:{self.lock.locked()} running:{self.running} box:{self.mailbox.qsize()} state:{self.state}>'

class Message:
    def __init__(self, message, from_module, from_ident):
        self.message=message
        self.from_module=from_module
        self.from_ident=from_ident
    def __repr__(self):
        return f'<Message {self.message} from {self.from_module}:{self.from_ident}>'

def SendMessage(message, module, ident, from_module, from_ident):
    with persist_lock:
        if module not in persistence:
            persistence[module]=Module()
        mod=persistence[module]
    with mod.lock:
        if ident not in mod.map:
            inst=Instance(0)
            inst.mailbox.put(Message(message, from_module, from_ident))
            mod.map[ident]=inst
            #print(f'scheduling Initial for {module}:{ident}')
            proc=Process(module, ident)
            code=bytes([opcodes.literal])+mymsgpack.encode(ident)
            code+=bytes([opcodes.call])+mymsgpack.encode(module)
            code+=mymsgpack.encode('Initial')+mymsgpack.encode(1)
            cframe=CallFrame(code, [])
            proc.call_frames.append(cframe)
            process_queue.put(proc)
            return
    inst=mod.map[ident]
    with inst.lock:
        if inst.running:
            inst.mailbox.put(Message(message, from_module, from_ident))
        else:
            inst.running=True
            #print(f'scheduling Receive for {module}:{ident} with {message}')
            schedule(module, ident, inst.state, message, from_module,from_ident)

def StoreResult(result, module, ident):
    mod=persistence[module]
    inst=mod.map[ident]
    with inst.lock:
        inst.state=result
        if inst.mailbox.empty():
            inst.running=False
        else:
            next_msg=inst.mailbox.get()
            #print(f'scheduling Receive for {module}:{ident} with {next_msg.message}')
            schedule(module, ident, result, next_msg.message, next_msg.from_module, next_msg.from_ident)

#################################################
# Relationship Tracking
#################################################

db_lock=threading.Lock()

sql_statements=['CREATE TABLE relations (from_module text NOT NULL, from_ident blob NOT NULL, relation text NOT NULL, to_module text NOT NULL, to_ident blob NOT NULL);',
'CREATE UNIQUE INDEX unique_relation ON relations (from_module, from_ident, relation, to_module, to_ident);',
'CREATE INDEX from_relation ON relations (from_module, from_ident, relation);',
'CREATE INDEX to_relation ON relations (to_module, to_ident, relation);']

with db_lock:
    rdb=sqlite3.connect(':memory:')
    cursor=rdb.cursor()
    for statement in sql_statements: cursor.execute(statement)
    rdb.commit

def add_relation(from_mod, from_ident, relation, to_mod, to_ident):
    if from_mod==to_mod and from_ident==to_ident: return
    try:
        with db_lock:
            ident1=mymsgpack.encode(from_ident)
            ident2=mymsgpack.encode(to_ident)
            cursor.execute('INSERT INTO relations(from_module,from_ident,relation,to_module,to_ident) VALUES(?,?,?,?,?)', (from_mod, ident1, relation, to_mod, ident2))
            rdb.commit()
    except sqlite3.IntegrityError:
        None

def get_to_relation(from_mod, from_ident, relation):
    with db_lock:
        cursor.execute('SELECT * FROM relations WHERE from_module=? AND from_ident=? AND relation=?', (from_mod, mymsgpack.encode(from_ident), relation))
        return [relation_decode(x) for x in cursor.fetchall()]

def get_all_to_relations(from_mod, from_ident):
    with db_lock:
        cursor.execute('SELECT * FROM relations WHERE from_module=? AND from_ident=?', (from_mod, mymsgpack.encode(from_ident)))
        return [relation_decode(x) for x in cursor.fetchall()]

def get_from_relation(to_mod, to_ident, relation):
    with db_lock:
        cursor.execute('SELECT * FROM relations WHERE to_module=? AND to_ident=? AND relation=?', (to_mod, mymsgpack.encode(to_ident), relation))
        return [relation_decode(x) for x in cursor.fetchall()]

def get_all_from_relations(to_mod, to_ident):
    with db_lock:
        cursor.execute('SELECT * FROM relations WHERE to_module=? AND to_ident=?', (to_mod, mymsgpack.encode(to_ident)))
        return [relation_decode(x) for x in cursor.fetchall()]

def relation_decode(rel):
    ident1=mymsgpack.decode(rel[1])
    ident2=mymsgpack.decode(rel[4])
    return (rel[0],ident1[0],rel[2],rel[3],ident2[0])

#print(match(1, 1, [0,0]))
#print(match(2.1, 2.1, [0,0]))
#print(not match(1, 2.1, [0,0]))
#print(not match(1, {}, [0,0]))
#print(not match({"a":1}, 1, [0,0]))
#print(match({"a":1}, {"a":1, "b":2}, [0,0]))
#print(match({"a":Exists()}, {"a":1, "b":2}, [0,0]))
#print(not match({"a":1}, {"b":2}, [0,0]))
#print(not match({"a":Exists()}, {"b":2}, [0,0]))
#print(match({"a":Variable(0, None)}, {"a":1, "b":2}, [0,0]))
#print(not match({"a":Variable(0, None)}, {"b":2}, [0,0]))
#print(match(Variable(0, None), {"a":1, "b":2}, [0,0]))
#print(match(Variable(0, {}), {"a":1, "b":2}, [0,0]))
#print(not match(Variable(0, {}), 1, [0,0]))
#print(match(Variable(0, {"a":1}), {"a":1, "b":2}, [0,0]))
#print(not match(Variable(0, {"a":1}), {"a":5, "b":2}, [0,0]))
#print(match(Variable(0, {"a":Variable(1, None)}), {"a":1, "b":2}, [0,0]))
#print(match([], [1,2,3], [0,0]))
#print(match([1], [1,2,3], [0,0]))
#print(not match([5], [1,2,3], [0,0]))
#print(match([1,2], [1,2,3], [0,0]))
#print(not match([1,5], [1,2,3], [0,0]))
#print(match([Exists(),2], [1,2,3], [0,0]))
#print(match([Exists(),Variable(0, None)], [1,2,3], [0,0]))
#print(not match([1,2], [1], [0,0]))
#print(not match([1,2], {}, [0,0]))
#print(not match([1], 1, [0,0]))

atoms={}
atom_of={}
def make_atom(s):
    a=atom.of(s)
    atom_of[s]=a
    atoms[a]=s
make_atom('true')
make_atom('false')
make_atom('input_result')
make_atom('read_lines_result')
make_atom('read_lines')
make_atom('read_result')
make_atom('read')
make_atom('relation_added')
make_atom('from')
make_atom('to')
make_atom('add')
make_atom('add_to')
make_atom('add_from')
TRUE=atom_of['true']
FALSE=atom_of['false']

# random module
def BuiltInRandomInt(params, module, ident):
    return random.randrange(params[0])
bi_rand_int_impl=FuncImpl([Variable(0,Exists())],bytes(),[],1,BuiltInRandomInt)
bi_rand_int_func=Function(1, [bi_rand_int_impl])
bi_rand_module={'RandomInt/1': bi_rand_int_func}
environment['Random']=bi_rand_module

# convert module
def BuiltInToInt(params, module, ident):
    return int(params[0])
bi_convert_toint_impl=FuncImpl([Exists()], bytes(), [], 0, BuiltInToInt)
bi_convert_toint_func=Function(1, [bi_convert_toint_impl])
def BuiltInToStr(params, module, ident):
    return f'{params[0]}'
bi_convert_tostr_impl=FuncImpl([Exists()], bytes(), [], 0, BuiltInToStr)
bi_convert_tostr_func=Function(1, [bi_convert_tostr_impl])
bi_convert_module={'ToInt/1':bi_convert_toint_func,
        'ToStr/1':bi_convert_tostr_func}
environment['Convert']=bi_convert_module

# string module
def BuiltInStringSplit(params, module, ident):
    return params[0].split()
bi_string_split_impl=FuncImpl([StringType()], bytes(), [], 0,BuiltInStringSplit)
bi_string_split_func=Function(1, [bi_string_split_impl])
bi_string_module={'Split/1':bi_string_split_func}
environment['String']=bi_string_module

# list module
def BuiltInListLen(params, module, ident):
    return len(params[0])
bi_list_len_impl=FuncImpl([Exists()], bytes(), [], 0, BuiltInListLen)
bi_list_len_func=Function(1, [bi_list_len_impl])
def BuiltInListUpdate(params, module, ident):
    params[0][params[1]]=params[2]
    return params[0]
bi_list_update_impl=FuncImpl([Exists()]*3, bytes(), [], 0, BuiltInListUpdate)
bi_list_update_func=Function(3, [bi_list_update_impl])
bi_list_module={'Length/1':bi_list_len_func, 'Update/3':bi_list_update_func}
environment['List']=bi_list_module

# enum module
def EnumRange(params, module, ident):
    return [i for i in range(params[0])]
enum_range_impl=FuncImpl([Exists()], bytes(), [], 0, EnumRange)
enum_range_func=Function(1, [enum_range_impl])
def EnumEach(params, module, ident):
    for item in params[0]:
        proc=Process(module, ident)
        code=bytes([opcodes.callanon])+mymsgpack.encode(1)
        cframe=CallFrame(code, [])
        cframe.stack.append(item)
        cframe.stack.append(params[1])
        proc.call_frames.append(cframe)
        while type(proc) is Process:
            proc=one_step(proc)
    return params[0]
enum_each_impl=FuncImpl([Exists()]*2, bytes(), [], 2, EnumEach)
enum_each_func=Function(2, [enum_each_impl])
def EnumMap(params, module, ident):
    # zzz I would love to make this parallel by default somehow
    ret=[]
    for item in params[0]:
        proc=Process(module, ident)
        code=bytes([opcodes.callanon])+mymsgpack.encode(1)
        cframe=CallFrame(code, [])
        cframe.stack.append(item)
        cframe.stack.append(params[1])
        proc.call_frames.append(cframe)
        while type(proc) is Process:
            proc=one_step(proc)
        ret.append(proc)
    return ret
enum_map_impl=FuncImpl([Exists()]*2, bytes(), [], 2, EnumMap)
enum_map_func=Function(2, [enum_map_impl])
def EnumReduce2(params, module, ident):
    ret=params[0][0]
    for item in params[0][1:]:
        proc=Process(module, ident)
        code=bytes([opcodes.callanon])+mymsgpack.encode(2)
        cframe=CallFrame(code, [])
        cframe.stack.append(ret)
        cframe.stack.append(item)
        cframe.stack.append(params[1])
        proc.call_frames.append(cframe)
        while type(proc) is Process:
            proc=one_step(proc)
        ret=proc
    return ret
enum_reduce2_impl=FuncImpl([Exists()]*2, bytes(), [], 2, EnumReduce2)
enum_reduce2_func=Function(2, [enum_reduce2_impl])
def EnumReduce3(params, module, ident):
    ret=params[1]
    for item in params[0]:
        proc=Process(module, ident)
        code=bytes([opcodes.callanon])+mymsgpack.encode(2)
        cframe=CallFrame(code, [])
        cframe.stack.append(ret)
        cframe.stack.append(item)
        cframe.stack.append(params[2])
        proc.call_frames.append(cframe)
        while type(proc) is Process:
            proc=one_step(proc)
        ret=proc
    return ret
enum_reduce3_impl=FuncImpl([Exists()]*3, bytes(), [], 3, EnumReduce3)
enum_reduce3_func=Function(3, [enum_reduce3_impl])
def EnumAny(params, module, ident):
    for item in params[0]:
        proc=Process(module, ident)
        code=bytes([opcodes.callanon])+mymsgpack.encode(1)
        cframe=CallFrame(code, [])
        cframe.stack.append(item)
        cframe.stack.append(params[1])
        proc.call_frames.append(cframe)
        while type(proc) is Process:
            proc=one_step(proc)
        if TRUE==proc:
            return TRUE
    return FALSE
enum_any_impl=FuncImpl([Exists()]*2, bytes(), [], 2, EnumAny)
enum_any_func=Function(2, [enum_any_impl])
enum_module={'Range/1':enum_range_func, 'Each/2':enum_each_func, 'Map/2':enum_map_func, 'Reduce/2':enum_reduce2_func, 'Reduce/3':enum_reduce3_func, 'Any/2':enum_any_func}
environment['Enum']=enum_module

# print module
print_init_impl=FuncImpl([Exists()], bytes(), [], 0, bytes([opcodes.literal,0]))
print_init_func=Function(1, [print_init_impl])
def BuiltInPrint(params, module, ident):
    print(params[1])
    return 0
print_rec_impl=FuncImpl([Exists()]*5, bytes(), [], 1, BuiltInPrint)
print_rec_func=Function(5, [print_rec_impl])
print_module={'Initial/1':print_init_func, 'Receive/5':print_rec_func}
environment['Print']=print_module

# input module
input_init_impl=FuncImpl([Exists()], bytes(), [], 0, bytes([opcodes.literal,0]))
input_init_func=Function(1, [input_init_impl])
def BuiltInInput(params, module, ident):
    back=input(params[1])
    SendMessage([atom_of['input_result'], back], params[3], params[4], 'Input', 0)
    return 0
input_rec_impl=FuncImpl([Exists()]*5, bytes(), [], 1, BuiltInInput)
input_rec_func=Function(5, [input_rec_impl])
input_module={'Initial/1':input_init_func, 'Receive/5':input_rec_func}
environment['Input']=input_module

# file module
file_init_impl=FuncImpl([Exists()], bytes(), [], 0, bytes([opcodes.literal,0]))
file_init_func=Function(1, [file_init_impl])
def BuiltInFileReadLines(params, module, ident):
    with open(params[2], 'r') as file:
        SendMessage([atom_of['read_lines_result'],[line.strip() for line in file]], params[3], params[4], 'File', params[2])
    return params[0]
file_rec_impl1=FuncImpl([Exists(), atom_of['read_lines'], Exists(), Exists(), Exists()], bytes(), [], 0, BuiltInFileReadLines)
def BuiltInFileRead(params, module, ident):
    with open(params[2], 'r') as file:
        SendMessage([atom_of['read_result'],file.read()], params[3],params[4],'File',params[2])
    return params[0]
file_rec_impl2=FuncImpl([Exists(), atom_of['read'], Exists(), Exists(), Exists()], bytes(), [], 0, BuiltInFileRead)
file_rec_func=Function(5, [file_rec_impl1, file_rec_impl2])
file_module={'Initial/1':file_init_func, 'Receive/5':file_rec_func}
environment['File']=file_module

# relation module
relat_init_impl=FuncImpl([Exists()], bytes(), [], 0, bytes([opcodes.literal,0]))
relation_init_func=Function(1, [relat_init_impl])
def BuiltInRelationAdd(params, module, ident):
    add_relation(params[1][1], params[1][2], params[1][3], params[1][4], params[1][5])
    SendMessage([atom_of['relation_added'],atom_of['from'],params[1][3],params[1][1],params[1][2]], params[1][4], params[1][5], 'Relation', 0)
    SendMessage([atom_of['relation_added'],atom_of['to'],params[1][3],params[1][4],params[1][5]], params[1][1], params[1][2], 'Relation', 0)
    return 0
relation_rec_impl_0=FuncImpl([Exists(),[atom_of['add'],StringType(),Exists(),StringType(),StringType(),Exists()],Exists(),StringType(),Exists()], bytes(), [], 0, BuiltInRelationAdd)
def BuiltInRelationAddTo(params, module, ident):
    add_relation(params[3], params[4], params[1][1], params[1][2], params[1][3])
    SendMessage([atom_of['relation_added'],atom_of['from'],params[1][1],params[1][2],params[1][3]], params[3], params[4], 'Relation', 0)
    return 0
relation_rec_impl_1=FuncImpl([Exists(),[atom_of['add_to'],StringType(),StringType(),Exists()],Exists(),StringType(),Exists()], bytes(), [], 0, BuiltInRelationAddTo)
def BuiltInRelationAddFrom(params, module, ident):
    add_relation(params[1][2], params[1][3], params[1][1], params[3], params[4])
    SendMessage([atom_of['relation_added'],atom_of['to'],params[1][1],params[1][2],params[1][3]], params[3], params[4], 'Relation', 0)
    return 0
relation_rec_impl_2=FuncImpl([Exists(),[atom_of['add_from'],StringType(),StringType(),Exists()],Exists(),StringType(),Exists()], bytes(), [], 0, BuiltInRelationAddFrom)
relation_rec_func=Function(5, [relation_rec_impl_0, relation_rec_impl_1, relation_rec_impl_2])
def BuiltInRelationGetTo(params, module, ident):
    return get_to_relation(module, ident, params[0])
relation_get_to_impl=FuncImpl([Exists()], bytes(), [], 0, BuiltInRelationGetTo)
relation_get_to_func=Function(1, [relation_get_to_impl])
def BuiltInRelationGetTos(params, module, ident):
    return get_all_to_relations(module, ident)
relation_get_tos_impl=FuncImpl([], bytes(), [], 0, BuiltInRelationGetTos)
relation_get_tos_func=Function(0, [relation_get_tos_impl])
def BuiltInRelationGetFrom(params, module, ident):
    return get_from_relation(module, ident, params[0])
relation_get_from_impl=FuncImpl([Exists()],bytes(),[],0,BuiltInRelationGetFrom)
relation_get_from_func=Function(1, [relation_get_from_impl])
def BuiltInRelationGetFroms(params, module, ident):
    return get_all_from_relations(module, ident)
relation_get_froms_impl=FuncImpl([], bytes(), [], 0, BuiltInRelationGetFroms)
relation_get_froms_func=Function(0, [relation_get_froms_impl])
relation_module={'Initial/1':relation_init_func, 'Receive/5':relation_rec_func, 'GetTos/1':relation_get_to_func, 'GetTos/0':relation_get_tos_func, 'GetFroms/1':relation_get_from_func, 'GetFroms/0':relation_get_froms_func}
environment['Relation']=relation_module

if __name__=='__main__':
    SendMessage(['guesser'], 'guesser', 0, 'system', 0)

    while not process_queue.empty():
        process_once()

# I can imagine four types of message handlers: the normal one that takes in a
# state and returns a new state, one that doesn't take in a state but does
# output one (could be used to do a reset on an instance), one that takes in a
# state but doesn't change it (for side-effect-only things like printing a
# current status), and one that neither takes in a state nor returns one
# (purely performs some calculation, not sure you would evet need this,
# especially if you can import the regular functions from a file). If you don't
# have any message ordering guarantees, then the ones that don't return a new
# state wouldn't have to wait in the queue for others to get done. It could get
# picked up by another worker thread and just run. The ones that set the state
# would have to run one at a time for a specific instanciation in order for
# them to act atomically. The problem with the transient ones that can run
# without waiting in line is that the scheduler has to know which is which. So
# either those are two different types of messaging and the caller has to know
# which one it is sending to, or the scheduler has to be able to figure out
# which one it is based on the message or something. I'm not sure the
# performance gain of transient messages not having to wait is worth the
# complications of implementing it, especially for a toy implementation like
# I'm doing.
