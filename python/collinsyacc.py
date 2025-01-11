import ply.yacc as yacc

# https://www.dabeaz.com/ply/ply.html

msg_func='Receive/5'


from collinslex import tokens

# Assiciativity is for when the thing happens multiple times in a row, like
# "foo X bar X baz". Left associativity says but foo and bar together first,
# and then baz. 'nonassoc' prevents them from chaining and would make that an
# error.
precedence = (
    ('left', 'VARIABLE', 'ANONDEF'),
    ('left', 'OR'),
    ('left', 'AND'),
    ('left', 'LESS', 'GREATER'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'SLASH', 'MOD'),
    ('right', 'UMINUS'),
    ('left', 'DOT', 'ANON'),
    ('left', 'OPAREN', 'CPAREN', 'OBRACKET', 'CBRACKET'),
    ('left', 'COLON'),
)

# Modules

def p_module_just_message(p):
    'module : '
    p[0]={}

def p_module_message(p):
    'module : module message_impl'
    p[0]=p[1]
    if msg_func not in p[0]: p[0][msg_func]=[]
    p[0][msg_func].append(func_from_message(p[2]))

def p_module_function(p):
    'module : module function_impl'
    p[0]=p[1]
    signature=p[2]['name']+'/'+str(len(p[2]['params']))
    if (signature) not in p[0]: p[0][signature]=[]
    p[0][signature].append(p[2])

def func_from_message(msg):
    params=[('parameter','state'),
            msg[0],
            ('parameter','ident'),
            ('parameter','from_module'),
            ('parameter','from_ident')]
    return {'name':msg_func , 'params':params, 'guard':msg[1], 'code':msg[2]}

# Message Implementations

def p_message_impl(p):
    'message_impl : MSG matchable block'
    p[0]=(p[2], (), p[3])

def p_message_guard_imp(p):
    'message_impl : MSG matchable WHERE guard block'
    p[0]=(p[2], p[4], p[5])

# Function Implementations

def p_simple_function_impl(p):
    'function_impl : IDENTIFIER OPAREN CPAREN block'
    p[0]={'name': p[1], 'params': [], 'guard':(), 'code':p[4]}

def p_function_impl(p):
    'function_impl : IDENTIFIER OPAREN patterns CPAREN block'
    p[0]={'name': p[1], 'params': p[3], 'guard':(), 'code':p[5]}

def p_function_impl_guard(p):
    'function_impl : IDENTIFIER OPAREN patterns CPAREN WHERE guard block'
    p[0]={'name': p[1], 'params': p[3], 'guard':p[6], 'code':p[7]}

# Patterns

def p_one_pattern(p):
    'patterns : matchable'
    p[0]=[p[1]]

def p_patterns(p):
    'patterns : patterns COMMA matchable'
    p[0]=p[1]
    p[0].append(p[3])

def p_identifier_only(p):
    'matchable : IDENTIFIER'
    p[0]=('parameter', p[1])

def p_ignored(p):
    'matchable : IGNORED'
    p[0]=('ignored',)

def p_match_identifier(p):
    'matchable : pattern ASSIGN IDENTIFIER'
    p[0]=('parameter_match', p[3], p[1])

def p_match_pattern(p):
    'matchable : pattern'
    p[0]=p[1]

def p_type_pattern(p):
    '''pattern : simple_literal
               | atom
               | type
               | match_map
               | match_list'''
    p[0]=p[1]

def p_simple_literal(p):
    '''simple_literal : INT
                      | STRING'''
    p[0]=('simple_literal', p[1])

def p_types(p):
    '''type : INTTYPE
            | FLOATTYPE
            | STRINGTYPE'''
    p[0]=(p[1],)

def p_func_type(p):
    'type : ANON SLASH INT'
    p[0]=('function', p[3])

def p_match_empty_list(p):
    'match_list : OBRACKET CBRACKET'
    p[0]=('match_list', [])

def p_match_list(p):
    'match_list : OBRACKET match_list_entries CBRACKET'
    p[0]=('match_list', p[2])

def p_match_one_list_entry(p):
    'match_list_entries : matchable'
    p[0]=[p[1]]

def p_match_list_entry(p):
    'match_list_entries : match_list_entries COMMA matchable'
    p[0]=p[1]
    p[0].append(p[3])

def p_match_empty_map(p):
    'match_map : OBRACE CBRACE'
    p[0]=('match_map', [])

def p_match_map(p):
    'match_map : OBRACE match_map_entries CBRACE'
    p[0]=('match_map', p[2])

def p_match_one_map_entry(p):
    '''match_map_entries : INT COLON matchable
                         | STRING COLON matchable'''
    p[0]=[(p[1], p[3])]

def p_match_map_entry(p):
    '''match_map_entries : match_map_entries COMMA INT COLON matchable
                         | match_map_entries COMMA STRING COLON matchable'''
    p[0]=p[1]
    p[0].append((p[3], p[5]))

# Guard

def p_basic_guard(p):
    'guard : compare_guard'
    p[0]=p[1]

def p_and_guard(p):
    'guard : guard AND guard'
    p[0]=('and', p[1], p[3])

def p_or_guard(p):
    'guard : guard OR guard'
    p[0]=('or', p[1], p[3])

def p_less_guard(p):
    'compare_guard : guard_spec LESS guard_spec'
    p[0]=('less', p[1], p[3])

def p_greater_guard(p):
    'compare_guard : guard_spec GREATER guard_spec'
    p[0]=('greater', p[1], p[3])

def p_equal_guard(p):
    'compare_guard : guard_spec EQUAL guard_spec'
    p[0]=('equal', p[1], p[3])

def p_simple_guard_spec(p):
    '''guard_spec : IDENTIFIER
                  | simple_literal'''
    p[0]=p[1]

# zzz I think you can always build your pattern so you don't need this
#def p_guard_spec_index(p):
    #'''guard_spec : guard_spec OBRACKET INT CBRACKET
                  #| guard_spec OBRACKET STRING CBRACKET'''
    #p[0]=('index', p[1], p[3])

# Blocks

def p_block(p):
    'block : assignments expression'
    p[0]=p[1]
    p[0].append(p[2])

def p_single_assignment(p):
    'assignments : '
    p[0]=[]

def p_assignments(p):
    'assignments : assignments assignment'
    p[0]=p[1]
    p[0].append(p[2])

def p_assignment(p):
    'assignment : expression ASSIGN IDENTIFIER'
    p[0]=('assign', p[1], p[3])

#def p_message_send(p):
#    'assignment : expression SEND expression COLON expression'
#    p[0]=('send', p[1], p[3], p[5])

def p_message_send_literal(p):
    'assignment : expression SEND IDENTIFIER COLON expression'
    p[0]=('send', p[1], ('literal', p[3]), p[5])

# Expressions

def p_expression(p):
    '''expression : literal
                  | atom
                  | variable
                  | accessor
                  | calculation
                  | function_call
                  | anon_call
                  | anon_function %prec ANONDEF'''
    p[0]=p[1]

def p_parenthesis(p):
    'expression : OPAREN expression CPAREN'
    p[0]=p[2]

def p_func_pipe(p):
    'expression : expression PIPE function_call'
    p[0]=('pipe', p[1], p[3])

def p_map_pipe(p): # zzz only works with expression evaluates to a map or list
    '''expression : expression PIPE map
                  | expression PIPE list'''
    p[0]=(p[3][0], p[1], p[3][2])

# Literals

def p_simple_type(p):
    '''literal : INT
               | STRING'''
    p[0]=('literal', p[1])

def p_literal_map_list(p):
    '''literal : map
               | list'''
    p[0]=p[1]

def p_empty_map(p):
    'map : OBRACE CBRACE'
    p[0]=('map', ('literal', {}), [])

def p_map(p):
    'map : OBRACE map_entries CBRACE'
    p[0]=('map', ('literal', {}), p[2])

def p_one_map_entry(p):
    'map_entries : expression COLON expression'
    p[0]=[(p[1], p[3])]

def p_map_entry(p):
    'map_entries : map_entries COMMA expression COLON expression'
    p[0]=p[1]
    p[1].append((p[3], p[5]))

def p_empty_list(p):
    'list : OBRACKET CBRACKET'
    p[0]=('list', ('literal', ('empty_list',)), [])

def p_list(p):
    'list : OBRACKET list_entries CBRACKET'
    p[0]=('list', ('literal', ('empty_list',)), p[2])

def p_one_list_entry(p):
    'list_entries : expression'
    p[0]=[p[1]]

def p_list_entry(p):
    'list_entries : list_entries COMMA expression'
    p[0]=p[1]
    p[1].append(p[3])

# Atoms

def p_simple_atom(p):
    'atom : COLON IDENTIFIER'
    p[0]=('atom', p[2])

# Variables

def p_simple_variable(p):
    'variable : IDENTIFIER %prec VARIABLE'
    p[0]=('variable', p[1])

# Accessors

def p_map_get(p):
    'accessor : expression OBRACKET expression CBRACKET'
    p[0]=('call', 'map_get', [p[1], p[3]])

# Calculations

def p_or(p):
    'calculation : expression OR expression'
    p[0]=('call', 'or', [p[1], p[3]])

def p_and(p):
    'calculation : expression AND expression'
    p[0]=('call', 'and', [p[1], p[3]])

def p_less(p):
    'calculation : expression LESS expression'
    p[0]=('call', 'less', [p[1], p[3]])

def p_greater(p):
    'calculation : expression GREATER expression'
    p[0]=('call', 'greater', [p[1], p[3]])

def p_plus(p):
    'calculation : expression PLUS expression'
    p[0]=('call', 'plus', [p[1], p[3]])

def p_minus(p):
    'calculation : expression MINUS expression'
    p[0]=('call', 'minus', [p[1], p[3]])

def p_times(p):
    'calculation : expression TIMES expression'
    p[0]=('call', 'times', [p[1], p[3]])

def p_divide(p):
    'calculation : expression SLASH expression'
    p[0]=('call', 'divide', [p[1], p[3]])

def p_mod(p):
    'calculation : expression MOD expression'
    p[0]=('call', 'mod', [p[1], p[3]])

def p_unary_minus(p):
    'calculation : MINUS expression %prec UMINUS'
    #p[0]=(p[2][0], -p[2][1])
    p[0]=('call', 'times', [p[2], ('literal', -1)])

# Function Call

def p_local_function_call(p):
    'function_call : function_name OPAREN parameters CPAREN'
    p[0]=('call', p[1][1], p[1][2], p[3])

def p_local_function_name(p):
    'function_name : DOT IDENTIFIER'
    p[0]=('function_name', '', p[2])

def p_function_name(p):
    'function_name : IDENTIFIER DOT IDENTIFIER'
    p[0]=('function_name', p[1], p[3])

def p_anon_function_call(p):
    'anon_call : expression OPAREN parameters CPAREN'
    p[0]=('anon_call', '', p[1], p[3])

def p_empty_parameters(p):
    'parameters :'
    p[0]=[]

def p_one_param(p):
    'parameters : parameter'
    p[0]=[p[1]]

def p_parameters(p):
    'parameters : parameters COMMA parameter'
    p[0]=p[1]
    p[0].append(p[3])

def p_parameter(p):
    'parameter : expression'
    p[0]=p[1]

def p_func_parameter(p):
    'parameter : function_name SLASH INT'
    p[0]=p[1]+(p[3],)

# Anonymous Functions

def p_anon_function_single(p):
    'anon_function : anon_impl'
    paramcount=len(p[1]['params'])
    p[0]=('anon_function', paramcount, [p[1]])

def p_anon_function(p):
    'anon_function : anon_function anon_impl'
    paramcount=p[1][1]
    newcount=len(p[2]['params'])
    if newcount!=paramcount:
        print(f'anonymous function expected {paramcount} but got {newcount}')
        raise SyntaxError
    p[0]=p[1]
    p[0][2].append(p[2])

def p_anon_input_empty(p):
    'anon_impl : ANON OPAREN CPAREN OBRACE block CBRACE'
    p[0]={'name': '__ANON__', 'params': [], 'guard':(), 'code':p[5]}

def p_anon_input(p):
    'anon_impl : ANON OPAREN patterns CPAREN OBRACE block CBRACE'
    p[0]={'name': '__ANON__', 'params': p[3], 'guard':(), 'code':p[6]}

def p_anon_input_guard(p):
    'anon_impl : ANON OPAREN patterns CPAREN guard OBRACE block CBRACE'
    p[0]={'name': '__ANON__', 'params': p[3], 'guard':p[5], 'code':p[7]}

# Errors

def p_error(p):
    if p==None:
        print(f'syntax error: at end of file')
        return
    print(f'syntax error: {p.value} ({p.type}) on line {p.lineno} ({p.lexpos})')

def find_column(token):
    print(f'fin_column: {dir(token.lexer.input)}')
    line_start=token.lexer.input.rfind('\n', 0, token.lexpos) + 1
    print(f'line_start: {line_start}')
    return 0

#build the parser
parser = yacc.yacc()

# import langYacc
# langYacc.parser.parse('lamantas pamnatsa')


# Syntax Choices I'm not sure of:
# 	& for defining anonymous functions, elixir uses fn
#   You can only > into named functions, not anonymous
#     6>bar()() would be ambigous otherwise
#   You can't directly call an anon func as the ident part of |>mod:ident
#     You can do it like 5|>mod:(foo())
#   same symbol for updating a map or list as for piping into a function
#     plus var>{"foo":23} goes against the general flow from left to right(?)
#     is it "this variable goes into this change" or the other way around?

# Things to do:
# have some built in thing which means "this module"
# file i/o
