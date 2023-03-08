import binascii, struct



with open("test.MS", "wb") as f:
    f.write(struct.pack('>H', 2))
