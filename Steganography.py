from PIL import Image

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



if __name__ == '__main__':
    with open('HumanRights.txt', 'r') as f:
        txt_msg = f.read()
    
    im = Image.open("images.png")
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
    im.save("images_altered.png")
    
    print 'Saved\n'
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
    
