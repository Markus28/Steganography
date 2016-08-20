from PIL import Image
import os
import base64
import ntpath

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
    im = Image.open("images_altered.png")
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

def write_file(src_path, target_path, altered_target_path):
    txt = file_to_txt(src_path)
    txt = '{{{&&filename %s&&}}}%s'%(filename(src_path), txt)
    write_txt(txt, target_path, altered_target_path)

def read_file(altered_path, target_directory):
    txt = read_txt(altered_path)
    if txt.find('{{{&&filename ') == -1:
        raise Exception('The message found is no file')
    else:
        end = txt.find('&&}}}')
        target_file_name = txt[len('{{{&&filename '):end]
        encoded_content = txt[end+len('&&}}}'):]
        target_path = os.path.join(target_directory, target_file_name)
        txt_to_file(encoded_content, target_path)

if __name__ == '__main__':
    write_file("C:\Users\Markus\Downloads\mini.jpg", "images.png", "images_altered.png")
    read_file("images_altered.png", "")
    
    
