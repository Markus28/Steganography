from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import os
import base64
import ntpath
import StringIO
from Crypto.Cipher import AES
from Crypto import Random
import hashlib

class AESCipher(object):

    def __init__(self, key): 
        self.bs = 32
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]
    

def filename(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)

def add_bit(byte, bit):
    if bit:
        return byte | 1
    else:
        return byte & 0b11111110

def str_to_bytes(string):
    return [ord(c) for c in string]

def last_bit(byte):
    return byte & 1

def apply_bytes(target, msg):
    if len(target)<8*len(msg):
        raise IndexError('Target is too small')
    else:
        header = '%d:'%(len(msg)*8)
        header_bytes = str_to_bytes(header)
        msg = header_bytes + msg
        for i, byte in enumerate(msg):
            for n in xrange(8):
                target[(i*8)+n] = add_bit(target[(i*8)+n],last_bit(byte>>n))
        return target

def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

def file_to_txt(path):
    with open(path, 'rb') as f:
        content = f.read()
    return base64.b64encode(content)

def txt_to_file(txt, path):
    with open(path, 'wb') as f:
        f.write(txt.decode('base64'))

def write_txt(txt_msg, path, altered_path):
    im = Image.open(path)
    im = im.convert('RGB')
    width, height = im.size
    pix = im.load()
    pixels = []
    index_dict = {}
    print 'Reading pixels...'
    for y in xrange(height-1):
        for x in xrange(width-1):
            index_dict[(len(pixels)/3)] = (x,y)
            pixels += [pix[x,y][0], pix[x,y][1], pix[x,y][2]]
    print 'Adding message..'
    altered = apply_bytes(pixels, str_to_bytes(txt_msg))
    print 'Converting to RGB...'
    altered = chunks(altered, 3)
    print 'Writing image...'
    for i, pixel in enumerate(altered):
        pix[index_dict[i]] = tuple(pixel)
    print 'Saving image...'
    im.save(altered_path)
    print 'Saved'

def read_txt(path):
    im = Image.open(path)
    im = im.convert('RGB')
    width, height = im.size
    pix = im.load()
    pixels = []
    index_dict = {}
    print 'Reading pixels...'
    for y in xrange(height-1):
        for x in xrange(width-1):
            index_dict[(len(pixels)/3)] = (x,y)
            pixels += [pix[x,y][0], pix[x,y][1], pix[x,y][2]]

    chunked_pixels = chunks(pixels,8)
    tot = 0
    message = ''
    receiving = False
    for i, encoded_byte in enumerate(chunked_pixels):
        for n, byte in enumerate(encoded_byte):
            tot += (2**n)*last_bit(byte)
        if chr(tot) == ':' and not receiving:
            following = int(message)
            receiving = True
            message = ''
            received = 0
        elif not receiving:
            message += chr(tot)
        elif received < following:
            received += 8
            message += chr(tot)
        else:
            break
        tot = 0
    return message

def write_encrypted_txt(txt_msg, path, altered_path, key=""):
    c = AESCipher(key)
    encrypted_msg = c.encrypt(txt_msg)
    write_txt(encrypted_msg, path, altered_path)

def read_encrypted_txt(path, key=""):
    encrypted_msg = read_txt(path)
    c = AESCipher(key)
    return c.decrypt(encrypted_msg)

def write_file(src_path, target_path, altered_target_path, key=""):
    txt = file_to_txt(src_path)
    txt = '{{{&&filename %s&&}}}%s'%(filename(src_path), txt)
    write_encrypted_txt(txt, target_path, altered_target_path, key)

def read_file_content(altered_path, key=""):
    txt = read_encrypted_txt(altered_path, key)
    if txt.find('{{{&&filename ') == -1:
        raise Exception('The message found is no file')
    else:
        end = txt.find('&&}}}')
        target_file_name = txt[len('{{{&&filename '):end]
        encoded_content = txt[end+len('&&}}}'):]
        return encoded_content, target_file_name
    
def read_file(altered_path, target_directory, key=""):
    encoded_content, target_file_name = read_file_content(altered_path, key)
    target_path = os.path.join(target_directory, target_file_name)
    txt_to_file(encoded_content, target_path)

def show_image(altered_path, key=""):
    encoded_content, file_name = read_file_content(altered_path, key)
    content = encoded_content.decode('base64')
    encoded_content = None
    buff = StringIO.StringIO()
    buff.write(content)
    buff.seek(0)
    im = Image.open(buff)
    imgplot = plt.imshow(im)
    plt.title(file_name)
    plt.show()
    

if __name__ == '__main__':
    write_file('small_galaxy.jpg', 'images.png', 'images_altered.png', 'pass')
    read_file('images_altered.png', '', 'pass')
    
