import os
from pathlib import Path

from Crypto.Cipher import ChaCha20

try:
    FLAG = Path('flag.txt').read_text()
except:
    FLAG = 'NZCSC{FAKE_FLAG}'


key = os.urandom(32)
nonce = os.urandom(12)

def roll_keys():
    global key, nonce
    print(f'For security measures - the key is going to roll')
    key = os.urandom(32)
    nonce = os.urandom(12)


def main():
    global key, nonce
    print('Welcome to the ChaCha Slide')
    key = os.urandom(32)
    nonce = os.urandom(12)

    while True:
        print('Options:')
        print(' 1. Encrypt text')
        print(' 2. Encrypt flag')
        print(' 3. Decrypt text')

        option = int(input('> '))

        if option == 1:
            plaintext = input('Enter text to encrypt: ')
            chacha = ChaCha20.new(key=key, nonce=nonce)
            enc = chacha.encrypt(plaintext.encode())
            print(f'Encrypted: {enc.hex()}')
            roll_keys()

        elif option == 2:
            chacha = ChaCha20.new(key=key, nonce=nonce)
            enc = chacha.encrypt(FLAG.encode())
            print(f'Encrypted: {enc.hex()}')
            roll_keys()

        elif option == 3:
            roll_keys()
            enc = bytes.fromhex(input('Enter text to decrypt (hex): '))
            chacha = ChaCha20.new(key=key, nonce=nonce)
            plaintext = chacha.decrypt(enc)
            print(f'Decrypted: {plaintext.hex()}')

        else:
            return



if __name__ == '__main__':
    try:
        main()
    except:
        print('Error!')
    finally:
        print('Goodbye')
