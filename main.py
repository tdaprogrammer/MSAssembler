import sys, re, string, struct, binascii
from pathlib import Path

'''
TODO:
escribir en .dat 30 bytes
'''
"""
add: 0
cmp: 1
mov: 2
beq: 3
"""
DAT_FILE = 'C:/Users/Alfredo/Desktop/uni/2/ACI/dosboxMS/FICHMS.DAT'
OUT = 'test.DAT'

def write_to_dat(file_out, pos=2): # 0xf programas como maximo
    # leer y luego escribir en la posicion 2 no me voy a complicar...
    junk = 30
    assert(pos >= 0 and pos <= 0xf)
    to_write = b''
    with open(DAT_FILE, 'rb') as f:
        
        content = ' '
        ind =0
        while content:
            content = f.read(junk)
            if ind == pos:
                x = bytes(file_out,encoding='ascii')
                x += b"\0"*(30-len(file_out)) 
                to_write += binascii.unhexlify(binascii.hexlify(x))
            else:
                to_write += content
            ind += 1
    with open(OUT, 'wb') as f:
        f.write(to_write)
            


def pad_to_4_bit(n):
    return bin(n)[2:].rjust(4,'0')

class Assembler:
    def __init__(self, code, data):
        self.code = code
        self.source = code | data # res = {**code, **data}
        self.data = { d.name:d.line_number for d in data.values() }
        self.labels = {c.label:c.line_number for c in code.values() if c.label is not None}
        self.out = []

    # TODO: class Assembler? una clase para cada instruccion y luego invocar un metodo virtual para evitar ifs...
    def decode_program(self):       
        for i in range(len(self.source)):
            class_name = type(self.source[i]).__name__
            if  class_name == 'Data':
                bin = self.source[i].value
                self.out.append(int(bin,16))
            # TODO: quitar Instruction constante magica
            if class_name == 'Instruction': # FIN: beq no es valido beq tiene que seguir con una etiqueta
                if self.source[i].name != 'beq': # not beq
                    arg1, arg2 = self.source[i].args
                    bin = Instruction.INSTRUCTIONS[self.source[i].name]+'000'+pad_to_4_bit(self.data[arg1])+'000'+pad_to_4_bit(self.data[arg2])
                else:
                    arg1 = self.source[i].args[0]
                    bin = Instruction.INSTRUCTIONS[self.source[i].name]+'000'+pad_to_4_bit(0)+'000'+pad_to_4_bit(self.labels[arg1])
                self.out.append(int(bin,2))
            

    def write_to_file(self,file_name='test.MS'):
        #f.write(struct.pack('<H', ))
        self.decode_program()
        written_bytes = 0
        with open(file_name, "wb") as f:
            written_bytes = len(self.code)-1
            f.write(struct.pack('<I', written_bytes)) # 4 bytes al principio
            written_bytes //= 2
            for x in self.out:
                written_bytes += 2
                f.write(struct.pack('<H', x))
            
            for _ in range((0x80-written_bytes)//2):
                f.write(struct.pack('<H', 0))
                written_bytes += 2
            
            for _ in range((0x104-written_bytes)//2): 
                f.write(struct.pack('<H', 0))
                written_bytes += 2
            
            # TODO: y si los datos no val al final sino al principio? como lo interpreta?
            for val in self.source.values():
                class_name = type(val).__name__ # TODO: metodo estatico de la clase
                byte = 1 if class_name == "Instruction" else 2
                f.write(struct.pack('<b', byte))
                written_bytes += 1
            
            for _ in range(0x184-written_bytes): 
                f.write(struct.pack('<b', 0))
            
            ld = []
            for i in range(len(self.source)):
                class_name = type(self.source[i]).__name__ 
                s = ''
                nline = 0
                if class_name == 'Instruction':
                    if self.source[i].label is not None:
                        s = self.source[i].label
                        nline = self.source[i].line_number
                else:
                    s = self.source[i].name
                    nline = self.source[i].line_number
                if s:
                    ld.append(nline)
                    written_bytes += 6
                    x = bytes(s,encoding='ascii')
                    x += b"\0"*(6-len(s)) 
                    f.write(binascii.unhexlify(binascii.hexlify(x)))
            for nline in ld: 
                f.write(struct.pack('>H', nline))


def split_tokens(s):
    arguments = list(map(lambda r : r.strip() ,re.split(r"([,: ])",s)))
    return [s for s in arguments if s]

class Data:
    def __init__(self, ins, line_number, splitted_tokens=None):
        tokens = splitted_tokens
        self.line_number = line_number
        if splitted_tokens is None:
            tokens = split_tokens(ins)
        if Data.is_data(tokens):
            self.name, self.value = self.get_constant(tokens)

    def is_data(s):
        return len(s) == 4 and s[2] == 'dato' and s[1] == ':' and len(s[-1]) == 4 and \
            all(c in string.hexdigits for c in s[-1])
    
    def get_constant(self, s):
        return s[0],s[-1]

line_number = 0

def syntax_error():
    global line_number
    print("syntax error at line " + str(line_number))
    exit(-1)

class Instruction:
    INSTRUCTIONS = dict({"add": '00',
                     "cmp": '01',
                     "mov": '10',
                     "beq":  '11'
                    })
    def __init__(self, ins, line_number, splitted_tokens=None):
        self.name = ''
        self.line_number = line_number
        self.args = []
        self.label = None
        tokens = splitted_tokens
        if splitted_tokens is None:
            tokens = split_tokens(ins)
        if self.has_label(tokens):
            self.label = tokens[0] # TODO: don't allow stuff like ':'
            tokens = tokens[2:]
        self.name = tokens[0]
        if  self.name not in Instruction.INSTRUCTIONS.keys():
            syntax_error()
        args = self.parse(tokens)
        if args is None:
            syntax_error()
        self.args = args

    def has_all_letters(self, arg):
        return re.search('[a-zA-Z]+',arg) # isalpha return True if the string is unicode too

    def parse_add_arguments(self, args):
        if len(args) != 2:
            return False
        for arg in args:
            if not self.has_all_letters(arg):
                return False
        return True
    
    def parse_mov_arguments(self, args):
        return self.parse_add_arguments(args)
    
    def parse_cmp_arguments(self, args):
        return self.parse_add_arguments(args)

    def parse_beq_arguments(self, args):
        return len(args) == 1 and self.has_all_letters(args[0])

    def parse(self, args):
        args = args[1:] # get rid off instruction name
        if self.name in ['add' ,'cmp','mov']:
            if args[1] != ',' or args.count(',') != 1:
                return None
            del args[1]
            arg1, arg2 = args[0], args[-1]
            if self.parse_add_arguments(args):
                return [arg1,arg2]           
        elif self.name == 'beq':
            if self.parse_beq_arguments(args):
                return [args[0]] if len(args) else []
        return None
    
    def has_label(self, s):
        return s[1] == ':' and s.count(':') == 1


def parse_lines(lines):
    global line_number
    code = dict()
    data = dict()
    for line in lines:
        line = line.lower().strip()
        splitted_tokens = split_tokens(line)
        if Data.is_data(splitted_tokens):
            data[line_number] = Data(line, line_number, splitted_tokens)
        else:
            code[line_number] = Instruction(line, line_number, splitted_tokens)
        line_number += 1
    a = Assembler(code,data)
    a.write_to_file()
    # for line in code.values():
    #     print(line.name, ' ', line.label)
    # print("data...")
    # for line in data.values():
    #     print(line.name, ' ', line.value)

    # print("code ",code)
    # print("data ", data)

# parse arguments
def main(): 
    assert(Data.is_data(split_tokens("NUM1  :  dato 0002")))
    assert(Data.is_data(split_tokens("CONTAD   : dato 0000")))
    assert(Data.is_data(split_tokens("CONTAD: dato 0000")))
    assert(not Data.is_data(split_tokens("CONTAD   :dat 0000")))
    assert(Data.is_data(split_tokens("CONTAD:dato 0000")))
    assert(not Data.is_data(split_tokens("CONTAD:dato 000g")))
    assert(Data.is_data(split_tokens("CONTAD:dato 1234")))
    # lines = []
    # # if len(sys.argv) != 2:
    # #     print("error")
    # #     return
    # with open("examples-programs/multiplicacion.txt") as f:
    #     lines = list(filter(lambda x : x,f.read().strip().split("\n")))
    # parse_lines(lines)

    write_to_dat("IRONMAN")
main()