import os
from pathlib import Path
from Crypto.Util.number import long_to_bytes, bytes_to_long, getPrime
from Crypto.Util.strxor import strxor

try:
    flag = (Path(__file__).parent.parent / 'src' / 'flag.txt').read_text().strip()
except:
    flag = 'NZCSC{FAKE_FLAG_FOR_TESTING}'

e = 0x10001

def round1(pt: bytes):
    p = getPrime(2048)
    q = getPrime(2048)
    hint = (p+e)*(q+e)

    N = p*q

    pt_int = bytes_to_long(pt)
    ct = pow(pt_int, e, N)

    print(f'round1_{N=}')
    print(f'round1_{hint=}')
    print(f'round1_{ct=}')
    return ct


def round2(pt: bytes):
    p = getPrime(2048)
    q = getPrime(2048)
    hint = abs(p - q)

    N = p*q

    pt_int = bytes_to_long(pt)
    ct = pow(pt_int, e, N)

    print(f'round2_{N=}')
    print(f'round2_{hint=}')
    print(f'round2_{ct=}')
    return ct


one_time_pad = os.urandom(len(flag))
flag_enc = strxor(flag.encode(), one_time_pad)

round1(one_time_pad)
round2(flag_enc)