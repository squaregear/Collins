import ply.lex as lex
import codecs

# https://www.dabeaz.com/ply/ply.html

reserved = {
    'msg' : 'MSG',
    'int' : 'INTTYPE',
    'float' : 'FLOATTYPE',
    'string' : 'STRINGTYPE',
    'where' : 'WHERE',
    'or' : 'OR',
    'and' : 'AND',
}

# List of token names
tokens = [
    'IDENTIFIER',
    'IGNORED',
    'INT',
    'STRING',
    'PLUS',
    'MINUS',
    'TIMES',
    'SLASH',
    'MOD',
    'OPAREN',
    'CPAREN',
    'OBRACKET',
    'CBRACKET',
    'OBRACE',
    'CBRACE',
    'ASSIGN',
    'PIPE',
    'SEND',
    'ANON',
    'LESS',
    'GREATER',
    'EQUAL',
    'COMMA',
    'COLON',
    'DOT',
]+list(reserved.values())

t_IGNORED = r'_[0-9A-Za-z_]*'
t_PLUS = r'\+'
t_MINUS = r'-'
t_TIMES = r'\*'
t_SLASH = r'/'
t_MOD = r'%'
t_OPAREN = r'\('
t_CPAREN = r'\)'
t_OBRACKET = r'\['
t_CBRACKET = r']'
t_OBRACE = r'{'
t_CBRACE = r'}'
t_ASSIGN = r'=>'
t_PIPE = r'\|>'
t_SEND = r':>'
t_ANON = r'&'
t_LESS = r'<'
t_GREATER = r'>'
t_EQUAL = r'='
t_COMMA = r','
t_COLON = r':'
t_DOT = r'\.'
t_ignore_COMMENT = r'\#.*'

literals = [',','.']

def t_IDENTIFIER(t):
    r'[A-Za-z][0-9A-Za-z_]*'
    t.type=reserved.get(t.value, 'IDENTIFIER')
    return t

def t_INT(t):
    r'\d+'
    t.value=int(t.value)
    return t

def t_STRING(t):
    r'"(\\.|[^"\\])*"'
    t.value=codecs.decode(t.value[1:-1], 'unicode-escape')
    return t

# rule so we can track line numbers
def t_newline(t):
    r'\n+'
    t.lexer.lineno+=len(t.value)

# A string containing ignored characters (spaces and tabs)
t_ignore  = ' \t'

# error handling rule
def t_error(t):
    print(f'Illegal character {t.value[0]}')
    t.lexer.skip(1)

# Build the lexer
lexer = lex.lex()
