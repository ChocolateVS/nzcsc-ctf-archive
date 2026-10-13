class Suss():
    # Inspired by: https://maplebacon.org/2024/02/dicectf2024-irs/
    # (archive) https://web.archive.org/web/20260905195444/https://maplebacon.org/2024/02/dicectf2024-irs/
    def __index__(self):
        global six_seven
        sigma.clear()
        six_seven = bytearray()
        sigma.extend([0]*bytearray.__basicsize__)
        return 0x1

sigma = bytearray(bytearray.__basicsize__)
sigma[0x18-1] = Suss()

no_cap = id(print)
print(f'cappa: {hex(no_cap)}')

brainrot = int(input('brainrot >'))

vibe = b''
vibe = bytes.fromhex(input('vibe >'))
for i in range(len(vibe)):
    six_seven[brainrot + i] = vibe[i]

print(input('skibidi >'))