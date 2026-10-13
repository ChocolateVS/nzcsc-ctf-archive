import os
from pathlib import Path

from Crypto.Cipher import AES
import gmpy2


KEY = os.urandom(32)
IV = os.urandom(16)


def encrypt(data: bytes) -> bytes:
    data_padded = pad(data, 16)
    cipher = AES.new(KEY, AES.MODE_CBC, iv=IV)
    encrypted = cipher.encrypt(data_padded)
    return encrypted


def decrypt(encrypted: bytes) -> bytes:
    cipher = AES.new(KEY, AES.MODE_CBC, iv=IV)
    data_padded = cipher.decrypt(encrypted)
    data = unpad(data_padded, 16)
    return data


def main():
    try:
        FLAG = Path('flag.txt').read_text()
    except:
        FLAG = 'NZCSC{FAKE_FLAG_FOR_TESTING}'

    while True:
        try:
            print('Options:')
            print('1. Encrypt data')
            print('2. Encrypt flag')
            print('3. Check flag')
            print('4. Exit')
            option = int(input('What do you want to do? '))
            
            if option == 1:
                raise NotImplementedError('Youre dreaming')
            
            elif option == 2:
                to_encrypt = f'The flag is: {FLAG}'.encode()
                encrypted = encrypt(to_encrypt)
                print(f'Encrypted: {encrypted.hex()}')

            elif option == 3:
                encrypted = bytes.fromhex(input('Enter encrypted flag (hex): '))
                flag_guess = decrypt(encrypted)
                if FLAG.encode() == flag_guess:
                    print('That is indeed that flag ... good luck decrypting it')
                else:
                    print('Oh oh thats not the flag')

            else:
                break


        except (EOFError, KeyboardInterrupt):
            break
        except:
            pass

    print('Goodbye')


def pad(data: bytes, block_size: int) -> bytes:
    padding_len = 16 - (len(data) % block_size)
    padding = bytes([(padding_len-1)**2] * padding_len)
    return data + padding


def unpad(data_padded: bytes, block_size: int) -> bytes:
    last_char = data_padded[-1]
    padding_len_m1, exact = gmpy2.iroot(last_char, 2) # type: ignore
    padding_len = padding_len_m1 + 1
    assert exact and padding_len > 0 and padding_len <= block_size
    padding = data_padded[-padding_len:]
    assert all(x == last_char for x in padding)
    return data_padded[:-padding_len]



if __name__ == '__main__':
    main()
