import math

# https://github.com/msgpack/msgpack/blob/master/spec.md
# https://stackoverflow.com/questions/7555689/python-3-building-an-array-of-bytes

def encode(thing):
    return recursive_encode(thing)

def recursive_encode(thing):
    if type(thing)==int:
        return encode_int(thing)
    if type(thing)==str:
        return encode_string(thing)
    if type(thing)==bytes:
        return encode_binary(thing)
    if type(thing)==list or type(thing)==set or type(thing)==tuple: 
        return encode_array(thing)
    if type(thing)==dict:
        return encode_map(thing)
    if type(thing)==Ext:
        return encode_ext(thing.t, thing.data)
    if type(thing)==UInt:
        return encode_uint(thing.i)
    raise ValueError(f'Unknown type: {type(thing)}')

class Ext:
    def __init__(self, t, data):
        self.t=t
        self.data=data
    def __repr__(self):
        return f'<Ext {self.t}: {self.data}>'

class UInt:
    def __init__(self, i):
        self.i=i
    def __repr__(self):
        return f'<UInt {self.i}>'

def encode_ext(t, data):
    l=len(data)
    if l==1:
        return bytes([0xd4,t])+data
    if l==2:
        return bytes([0xd5,t])+data
    if l==4:
        return bytes([0xd6,t])+data
    if l==8:
        return bytes([0xd7,t])+data
    if l==16:
        return bytes([0xd8,t])+data
    if l<=0xff:
        return bytes([0xc7,l,t])+data
    if l<0xffff:
        return bytes([0xc8])+l.to_bytes(2, byteorder='big')+bytes([t])+data
    if l<0xffffffff:
        return bytes([0xc9])+l.to_bytes(4, byteorder='big')+bytes([t])+data

def decode(b):
    return decode_at(b, 0)

def decode_at(b, pos):
    # ints
    if b[pos]==0xd0:
        return int.from_bytes(b[pos+1:pos+2], signed=True), pos+2
    if b[pos]==0xd1:
        return int.from_bytes(b[pos+1:pos+3], byteorder='big', signed=True), pos+3
    if b[pos]==0xd2:
        return int.from_bytes(b[pos+1:pos+5], byteorder='big', signed=True), pos+5
    # uints
    if b[pos]==0xcc:
        return int.from_bytes(b[pos+1:pos+2], signed=False), pos+2
    if b[pos]==0xcd:
        return int.from_bytes(b[pos+1:pos+3], byteorder='big', signed=False), pos+3
    if b[pos]==0xce:
        return int.from_bytes(b[pos+1:pos+5], byteorder='big', signed=False), pos+5
    # strings
    if b[pos]&0xe0 == 0xa0:
        strlen=b[pos] & 0x1f
        return b[pos+1:pos+1+strlen].decode('utf-8'), pos+1+strlen
    if b[pos]==0xd9:
        strlen=int.from_bytes(b[pos+1:pos+2])
        return b[pos+2:pos+2+strlen].decode('utf-8'), pos+2+strlen
    if b[pos]==0xda:
        strlen=int.from_bytes(b[pos+1:pos+3])
        return b[pos+3:pos+3+strlen].decode('utf-8'), pos+3+strlen
    if b[pos]==0xdb:
        strlen=int.from_bytes(b[pos+1:pos+5])
        return b[pos+5:pos+5+strlen].decode('utf-8'), pos+5+strlen
    # binary
    if b[pos]==0xc4:
        binlen=int.from_bytes(b[pos+1:pos+2])
        return b[pos+2:pos+2+binlen], pos+2+binlen
    if b[pos]==0xc5:
        binlen=int.from_bytes(b[pos+1:pos+3])
        return b[pos+3:pos+3+binlen], pos+3+binlen
    if b[pos]==0xc6:
        binlen=int.from_bytes(b[pos+1:pos+5])
        return b[pos+5:pos+5+binlen], pos+5+binlen
    # arrays
    if b[pos]&0xf0 == 0x90:
        arrlen=b[pos] & 0x0f
        return decode_array(b, pos+1, arrlen)
    if b[pos]==0xdc:
        arrlen=int.from_bytes(b[pos+1:pos+3])
        return decode_array(b, pos+3, arrlen)
    if b[pos]==0xdd:
        arrlen=int.from_bytes(b[pos+1:pos+5])
        return decode_array(b, pos+5, arrlen)
    # maps
    if b[pos]&0xf0 == 0x80:
        mapsize=b[pos] & 0x0f
        return decode_map(b, pos+1, mapsize)
    if b[pos]==0xde:
        arrlen=int.from_bytes(b[pos+1:pos+3])
        return decode_map(b, pos+3, arrlen)
    if b[pos]==0xdf:
        arrlen=int.from_bytes(b[pos+1:pos+5])
        return decode_map(b, pos+5, arrlen)
    # ext types
    if b[pos]==0xd4:
        return Ext(int.from_bytes(b[pos+1:pos+2]), b[pos+2:pos+3]), pos+3
    if b[pos]==0xd5:
        return Ext(int.from_bytes(b[pos+1:pos+2]), b[pos+2:pos+4]), pos+4
    if b[pos]==0xd6:
        return Ext(int.from_bytes(b[pos+1:pos+2]), b[pos+2:pos+6]), pos+6
    if b[pos]==0xd7:
        return Ext(int.from_bytes(b[pos+1:pos+2]), b[pos+2:pos+10]), pos+10
    if b[pos]==0xd8:
        return Ext(int.from_bytes(b[pos+1:pos+2]), b[pos+2:pos+18]), pos+18
    if b[pos]==0xc7:
        extlen=int.from_bytes(b[pos+1:pos+2])
        return Ext(int.from_bytes(b[pos+2:pos+3]), b[pos+3:pos+3+extlen]), pos+3+extlen
    if b[pos]==0xc8:
        extlen=int.from_bytes(b[pos+1:pos+3])
        return Ext(int.from_bytes(b[pos+3:pos+4]), b[pos+4:pos+4+extlen]), pos+4+extlen
    if b[pos]==0xc9:
        extlen=int.from_bytes(b[pos+1:pos+5])
        return Ext(int.from_bytes(b[pos+5:pos+6]), b[pos+6:pos+6+extlen]), pos+6+extlen
    # fixed ints
    return int.from_bytes(b[pos:pos+1], signed=True), pos+1

### Encoding ###

def encode_int(i):
    if i>=0 and i<=0x7f:
        return bytes([i])
    if i<0 and i>=-32:
        return i.to_bytes(1, signed=True)
    if i>=-0x80 and i<=0x7f:
        return bytes([0xd0])+i.to_bytes(1, signed=True)
    if i>=-0x8000 and i<=0x7fff:
        return bytes([0xd1])+i.to_bytes(2, byteorder='big', signed=True)
    if i>=-0x80000000 and i<=0x7fffffff:
        return bytes([0xd2])+i.to_bytes(4, byteorder='big', signed=True)
    raise ValueError('Couldn\'t encode that size of int')

def encode_uint(i):
    if i>0 and i<=0xff:
        return bytes([0xcc])+i.to_bytes(1, signed=False)
    if i>0 and i<=0xffff:
        return bytes([0xcd])+i.to_bytes(2, byteorder='big', signed=False)
    if i>0 and i<=0xffffffff:
        return bytes([0xce])+i.to_bytes(4, byteorder='big', signed=False)
    raise ValueError('Couldn\'t encode that size of int')

def encode_string(s):
    strbytes=bytes(s, 'utf-8')
    l=len(strbytes)
    if l<32:
        ident=0xa0 + l
        return bytes([ident])+strbytes
    if l<=0xff:
        return bytes([0xd9])+l.to_bytes(1)+strbytes
    if l<=0xffff:
        return bytes([0xda])+l.to_bytes(2, byteorder='big')+strbytes
    if l<=0xffffffff:
        return bytes([0xda])+l.to_bytes(4, byteorder='big')+strbytes
    raise ValueError('String is way to long to encode')

def encode_binary(b):
    l=len(b)
    if l<=0xff:
        return bytes([0xc4])+l.to_bytes(1)+b
    if l<=0xffff:
        return bytes([0xc5])+l.to_bytes(2, byteorder='big')+b
    if l<=0xffffffff:
        return bytes([0xc6])+l.to_bytes(4, byteorder='big')+b
    raise ValueError('binary is to long to encode')

def encode_array(array):
    out=encode_array_interior(array)
    l=len(array)
    if l<16:
        return bytes([0x90+l])+out
    if l<=0xffff:
        return bytes([0xdc])+l.to_bytes(2, byteorder='big')+out
    if l<=0xffffffff:
        return bytes([0xdd])+l.to_bytes(4, byteorder='big')+out
    raise ValueError('Too many array elements to encode')

def encode_array_interior(array):
    out=bytes([])
    for element in array:
        out+=recursive_encode(element)
    return out

def encode_map(m):
    out=encode_map_interior(m)
    l=len(m)
    if l<16:
        return bytes([0x80+l])+out
    if l<=0xffff:
        return bytes([0xde])+l.to_bytes(2, byteorder='big')+out
    if l<=0xffffffff:
        return bytes([0xdf])+l.to_bytes(4, byteorder='big')+out

def encode_map_interior(m):
    out=bytes([])
    for key in m:
        out+=recursive_encode(key)
        out+=recursive_encode(m[key])
    return out

### Decoding ###

def decode_array(b, pos, num):
    ret=[]
    for i in range(num):
        out, pos = decode_at(b, pos)
        ret.append(out)
    return ret, pos

def decode_map(b, pos, num):
    ret={}
    for i in range(num):
        key, pos = decode_at(b, pos)
        val, pos = decode_at(b, pos)
        ret[key]=val
    return ret, pos
