import hashlib

# Integer byte size to use for internal representation of atoms. Smaller means
# more likely to have collisions. 32-bit integers are unlikely to collide
# before 77397 of them (https://www.bdayprob.com/). 64-bit integers are
# astronomically unlikely to collide. I think Python treats UInt64s as a fancy
# structure and might not be efficient. Efficiency is supposed to be the point.
size=4

def of(s):
    return int.from_bytes(hashlib.sha256(s.encode('utf-8')).digest()[:size])
