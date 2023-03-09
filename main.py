import sys, re, string, struct, binascii
from pathlib import Path
import shutil

'''
TODO:

'''

DAT_FILE = 'FICHMS.DAT'

def write_to_dat(file_out, pos=2):
    junk = 30
    shutil.copyfile(DAT_FILE, DAT_FILE+'.copy') # make a copy just in case
    assert(pos >= 0 and pos <= 0xf)
    buf = b''
    with open(DAT_FILE, 'rb') as f:
        content = ' '
        ind =0
        while content:
            content = f.read(junk)
            if ind == pos:
                x = bytes(file_out,encoding='ascii')
                x += b"\0"*(30-len(file_out)) 
                buf += binascii.unhexlify(binascii.hexlify(x))
            else:
                buf += content
            ind += 1
    with open(DAT_FILE, 'wb') as f:
        f.write(buf)

def pad_to_7_bit(n):
    return bin(n)[2:].rjust(7,'0')

class Assembler:
    def __init__(self, code, data):
        self.code = code
        self.source = {**code, **data}
        self.data = { d.name:d.line_number for d in data.values() }
        self.labels = {c.label:c.line_number for c in code.values() if c.label is not None}
        self.ram_content = []

    # TODO: class Assembler? una clase para cada instruccion y luego invocar un metodo virtual para evitar ifs...
    def decode_program(self):       
        for i in range(len(self.source)):
            class_name = type(self.source[i]).__name__
            if  class_name == Data.__name__:
                bin = self.source[i].value
                self.ram_content.append(int(bin,16))
            elif class_name == Instruction.__name__: 
                if self.source[i].name != 'beq':
                    arg1, arg2 = self.source[i].args
                    bin = Instruction.INSTRUCTIONS[self.source[i].name]+pad_to_7_bit(self.data[arg1])+pad_to_7_bit(self.data[arg2])
                else:
                    arg1 = self.source[i].args[0]
                    bin = Instruction.INSTRUCTIONS[self.source[i].name]+pad_to_7_bit(0)+pad_to_7_bit(self.labels[arg1])
                self.ram_content.append(int(bin,2))
            

    def write_to_file(self,file_name='PROG2.MS'):
        #f.write(struct.pack('<H', ))
        self.decode_program()
        written_bytes = 4
        with open(file_name, "wb") as f:
            st = len(self.labels)+len(self.data)
            f.write(struct.pack('<I', st)) # 4 bytes al principio
            # for i in range(len(self.ram_content)):
            #     print(hex(self.ram_content[i]))
            for x in self.ram_content:
                written_bytes += 2
                f.write(struct.pack('<H', x))
                    
            for _ in range((0x104-written_bytes)): 
                f.write(struct.pack('<b', 0))
                written_bytes += 1
            
            #TODO: y si los datos no van al final sino al principio? como lo interpreta?
            for val in self.source.values():
                byte = val.get_type()
                f.write(struct.pack('<b', byte))
                written_bytes += 1
            
            for _ in range(0x184-written_bytes): 
                f.write(struct.pack('<b', 0))
            
            labels_and_data_names = []
            for i in range(len(self.source)):
                name= self.source[i].get_label()
                nline = self.source[i].line_number
                if name is not None:
                    labels_and_data_names.append(nline)
                    x = bytes(name.upper(),encoding='ascii')
                    x += b"\0"*(7-len(name)) 
                    f.write(binascii.unhexlify(binascii.hexlify(x)))
            for nline in labels_and_data_names: 
                f.write(struct.pack('<H', nline))


def split_tokens(s):
    arguments = list(map(lambda r : r.strip() ,re.split(r"([,: ])",s)))
    return [a for a in arguments if a]

class Data:
    def __init__(self, ins, line_number, tokens=None):                         
        self.line_number = line_number
        if tokens is None:
            tokens = split_tokens(ins)
        if Data.is_data(tokens):
            self.name, self.value = self.get_constant(tokens)

    def is_data(s):
        return len(s) == 4 and s[2] == 'dato' and s[1] == ':' and len(s[-1]) == 4 and \
            all(c in string.hexdigits for c in s[-1])
    
    def get_label(self):
        return self.name

    def get_type(self):
        return 0x2

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
    def __init__(self, ins, line_number, tokens=None):
        self.name = ''
        self.line_number = line_number
        self.args = []
        self.label = None        
        if tokens is None:
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

    def get_label(self):
        return self.label
    
    def get_type(self):
        return 0x1
    
    def has_all_letters(self, arg):
        return re.search('[a-zA-Z]+',arg) # isalpha return true if the string is unicode too, so I don't want

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
    lines = []
    # if len(sys.argv) != 2:
    #     print("error")
    #     return
    with open("examples-programs/p2.txt") as f:
        lines = list(filter(lambda x : x,f.read().strip().split("\n")))
    parse_lines(lines)

    write_to_dat("IRONMAN")
main()