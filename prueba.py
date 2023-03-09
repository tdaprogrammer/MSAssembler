import binascii, struct

class Test:
    pass
t = Test()
print(Test.__class__.__name__)

# with open("PROG2.MS", "ab") as f:
#     for _ in range(0x184-(16*3+8)):
#         f.write(struct.pack('>b', 2))
