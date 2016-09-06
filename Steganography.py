from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
import base64
import ntpath
import StringIO
from Crypto.Cipher import AES
from Crypto import Random
import hashlib
import random
import cv2
import time
import numpy as np
from scipy.io import wavfile
import subprocess
from shutil import copyfile
import contextlib
import signal



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

class AudioWriter(object):
    def __init__(self, source, target):
        self.source = source
        self.target = target
        
    def write_txt(self, msg):
        sample_rate, data = wavfile.read(self.source)
        msg = "%d:%s"%(8*len(msg), msg)
        msg = str_to_bytes(msg)
        result = apply_bytes(data, msg)
        wavfile.write(self.target, sample_rate, result)

    def write_file(self, src_path, key=""):
        print '[Write file]'
        txt = file_to_txt(src_path)
        txt = '{{{&&filename %s&&}}}%s'%(filename(src_path), txt)
        self.write_encrypted_txt(txt, key)
        print 'Done\n'

    def write_encrypted_txt(self, txt_msg, key=""):
        c = AESCipher(key)
        print 'Encrypting...'
        encrypted_msg = c.encrypt(txt_msg)
        self.write_txt(encrypted_msg)


class AudioReader(object):
    def __init__(self, source):
        self.source = source

    def read_txt(self):
        sample_rate, data = wavfile.read(self.source)
        count = 0
        receiving = False
        msg = ''
        encoded_byte = []
        tot = 0
        following = 0
        received = 0
        for i, encoded in enumerate(data):
            if (i+1)%8 == 0:
                tot = 0
                for pos, bit in enumerate(encoded_byte):
                    tot += (2**pos)*bit

                encoded_byte = []
                
                if chr(tot) == ':' and not receiving:
                    following = int(msg)
                    receiving = True
                    msg = ''
                elif not receiving:
                    msg += chr(tot)
                elif received < following:
                    received += 8
                    msg += chr(tot)
                else:
                    return msg
            else:
                encoded_byte.append(last_bit(encoded))
        return msg

    def read_file_content(self, key=""):
        txt = self.read_encrypted_txt(key)
        if txt.find('{{{&&filename ') == -1:
            raise Exception('The message found is no file')
        else:
            end = txt.find('&&}}}')
            target_file_name = txt[len('{{{&&filename '):end]
            encoded_content = txt[end+len('&&}}}'):]
            return encoded_content, target_file_name
    
    def read_file(self, target_directory, key=""):
        print '[Read file]'
        encoded_content, target_file_name = self.read_file_content(key)
        target_path = os.path.join(target_directory, target_file_name)
        txt_to_file(encoded_content, target_path)
        print 'Done\n'

    def read_encrypted_txt(self, key=""):
        encrypted_msg = self.read_txt()
        c = AESCipher(key)
        print 'Decrypting...'
        return c.decrypt(encrypted_msg)

class VideoReader(object):
    def __init__(self, source):
        self.source = source

    def read_txt(self):
        print 'Opening video...'
        vidcap = cv2.VideoCapture(self.source)
        fps = vidcap.get(cv2.CAP_PROP_FPS)
        count = 0
        success = True
        print 'Saving frames...'
        while success:
            success, image = vidcap.read()
            cv2.imwrite('C:\Users\Markus\AppData\Local\Temp\\frame%d.png'%count, image)
            count += 1

        receiving = False
        message = ''
        tot = 0
        for n in xrange(count-1):
            print 'Opening frame...'
            im = Image.open('C:\Users\Markus\AppData\Local\Temp\\frame%d.png'%n)
            im = im.convert('RGB')
            width, height = im.size
            max_info = (width*height*3)/8
            pix = im.load()
            pixels = []
            index_dict = {}
            tot = 0
            c = 0
            print 'Reading pixels...'
            pixels = [item for row in im.getdata() for item in row]
            chunked_pixels = chunks(pixels,8)
            print 'Looking for message...'
            for i, encoded_byte in enumerate(chunked_pixels):
                if c>max_info:
                    print 'Reached end, next frame...'
                    break
                
                for pos, byte in enumerate(encoded_byte):
                    tot += (2**pos)*last_bit(byte)
                if chr(tot) == ':' and not receiving:
                    try:
                        following = int(message)
                    except ValueError as e:
                        print 'No message'
                        return message
                    receiving = True
                    message = ''
                    received = 0
                elif not receiving:
                    message += chr(tot)
                elif received < following:
                    received += 8
                    message += chr(tot)
                else:
                    return message
                tot = 0
            srm('C:\Users\Markus\AppData\Local\Temp\\frame%d.png'%n)
        return message

    def read_file_content(self, key=""):
        txt = self.read_encrypted_txt(key)
        if txt.find('{{{&&filename ') == -1:
            raise Exception('The message found is no file')
        else:
            end = txt.find('&&}}}')
            target_file_name = txt[len('{{{&&filename '):end]
            encoded_content = txt[end+len('&&}}}'):]
            return encoded_content, target_file_name
    
    def read_file(self, target_directory, key=""):
        print '[Read file]'
        encoded_content, target_file_name = self.read_file_content(key)
        target_path = os.path.join(target_directory, target_file_name)
        txt_to_file(encoded_content, target_path)
        print 'Done\n'

    def read_encrypted_txt(self, key=""):
        encrypted_msg = self.read_txt()
        c = AESCipher(key)
        print 'Decrypting...'
        return c.decrypt(encrypted_msg)

        #For debugging only
    def show_image(self, key=""):
        print '[Show image]'
        encoded_content, file_name = self.read_file_content(key)
        content = encoded_content.decode('base64')
        encoded_content = None
        txt_to_image(content, name=file_name)
        print 'Done\n'

class VideoWriter(object):
    def __init__(self, source, target):
        self.source = source
        self.target = target

    def write_txt(self, msg):
        msg = "%d:%s"%(8*len(msg), msg)
        vidcap = cv2.VideoCapture(self.source)
        fps = vidcap.get(cv2.CAP_PROP_FPS)
        #success, image = vidcap.read()
        count = 0
        success = True
        while success:
            success, image = vidcap.read()
            cv2.imwrite('C:\Users\Markus\AppData\Local\Temp\\frame%d.png'%count, image)
            count += 1
        vidcap.release()
        im = Image.open('C:\Users\Markus\AppData\Local\Temp\\frame0.png')
        im = im.convert('RGB')
        width, height = im.size
        res = width * height
        max_info = (res*3)/8
        if max_info*(count-1)<len(msg):
            raise IndexError('Target too small')
        msg = chunks(msg, max_info)
        for i, fragment in enumerate(msg):
            with silent_print():
                writer = ImageWriter('C:\Users\Markus\AppData\Local\Temp\\frame%d.png'%i, 'C:\Users\Markus\AppData\Local\Temp\\frame%d.png'%i)
                writer.write_txt(fragment, header=False)

        print 'Creating Video, %d frames'%count
        img1 = cv2.imread('C:\Users\Markus\AppData\Local\Temp\\frame0.png')
        height , width , layers =  img1.shape
        video = cv2.VideoWriter('C:\Users\Markus\AppData\Local\Temp\\steg_video.avi',-1,fps ,(width,height))
        print 'Collecting frames'
        for i in xrange(count-1):
            print 'C:\Users\Markus\AppData\Local\Temp\\frame%d.png'%i
            video.write( cv2.imread('C:\Users\Markus\AppData\Local\Temp\\frame%d.png'%i))
            srm('C:\Users\Markus\AppData\Local\Temp\\frame%d.png'%i)
                        
        cv2.destroyAllWindows()
        video.release()

        try:
            print subprocess.check_output('ffmpeg -i %s -ab 160k -ac 2 -ar 44100 -vn %s -y'%(self.source, 'C:\Users\Markus\AppData\Local\Temp\\steg_audio.wav'), stderr = subprocess.STDOUT, shell = True)        
            print subprocess.check_output('ffmpeg -i %s -i %s -codec copy -shortest %s -y'%('C:\Users\Markus\AppData\Local\Temp\\steg_video.avi', 'C:\Users\Markus\AppData\Local\Temp\\steg_audio.wav', os.path.abspath(self.target)), stderr = subprocess.STDOUT, shell = True)
        except subprocess.CalledProcessError as e:
            sys.stderr.write('Warning: Could not transfer audiodata from original video. %s Did you install ffmpeg properly?\n' %e.output)
            copyfile('C:\Users\Markus\AppData\Local\Temp\\steg_video.avi', self.target)

        try:
            srm('C:\Users\Markus\AppData\Local\Temp\\steg_audio.wav')
            srm('C:\Users\Markus\AppData\Local\Temp\\steg_video.avi')
        except  IOError:
            pass


    def write_file(self, src_path, key=""):
        print '[Write file]'
        txt = file_to_txt(src_path)
        txt = '{{{&&filename %s&&}}}%s'%(filename(src_path), txt)
        self.write_encrypted_txt(txt, key)
        print 'Done\n'

    def write_encrypted_txt(self, txt_msg, key=""):
        c = AESCipher(key)
        print 'Encrypting...'
        encrypted_msg = c.encrypt(txt_msg)
        self.write_txt(encrypted_msg)


class ImageWriter(object):
    def __init__(self, source, target):
        self.source = source
        self.target = target
        
    def write_txt(self, txt_msg, header=True):            #header only false for video
        im = Image.open(self.source)
        im = im.convert('RGB')
        width, height = im.size
        pix = im.load()
        pixels = []
        index_dict = {}
        print 'Reading pixels...'
        pixels = [item for row in im.getdata() for item in row]
        print 'Adding message...'
        if header:
            txt_msg = '%d:%s'%(len(txt_msg)*8, txt_msg)
        pixels = apply_bytes(pixels, str_to_bytes(txt_msg))
        print 'Converting to RGB...'
        altered_generator = chunks(pixels, 3)
        print 'Writing image...'
        pixels = []
        for item in altered_generator:
            pixels.append(tuple(item))
        im.putdata(pixels)
        print 'Saving image...'
        im.save(self.target)
        print 'Saved'

    def write_encrypted_txt(self, txt_msg, key=""):
        c = AESCipher(key)
        print 'Encrypting...'
        encrypted_msg = c.encrypt(txt_msg)
        self.write_txt(encrypted_msg)


    def write_file(self, src_path, key=""):
        print '[Write file]'
        txt = file_to_txt(src_path)
        txt = '{{{&&filename %s&&}}}%s'%(filename(src_path), txt)
        self.write_encrypted_txt(txt, key)
        print 'Done\n'

    def delete_msg(self):
        print '[Delete message]'
        im = Image.open(self.target)
        im = im.convert('RGB')
        width, height = im.size
        pix = im.load()
        pixels = []
        index_dict = {}
        print 'Reading pixels...'
        pixels = [item for row in im.getdata() for item in row]
        print 'Adding random bits..'
        pixels = apply_bytes(pixels, [ord(c) for c in os.urandom(len(pixels)/8)])
        pixel_generator = chunks(pixels, 3)
        print 'Writing image...'
        pixels = []
        for item in pixel_generator:
            pixels.append(tuple(item))
        im.putdata(pixels)
        print 'Saving image...'
        im.save(self.target)
        print 'Done\n'

    

    
class ImageReader(object):
    def __init__(self, source):
        self.source = source

    def read_txt(self):
        print 'Opening image...'
        im = Image.open(self.source)
        im = im.convert('RGB')
        width, height = im.size
        pix = im.load()
        pixels = []
        index_dict = {}
        print 'Reading pixels...'
        pixels = [item for row in im.getdata() for item in row]
        chunked_pixels = chunks(pixels,8)
        pixels = None
        tot = 0
        message = ''
        receiving = False
        print 'Looking for message...'
        for i, encoded_byte in enumerate(chunked_pixels):
            for n, byte in enumerate(encoded_byte):
                tot += (2**n)*last_bit(byte)
            if chr(tot) == ':' and not receiving:
                try:
                    following = int(message)
                except ValueError as e:
                    print 'No message'
                    break
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


    def read_encrypted_txt(self, key=""):
        encrypted_msg = self.read_txt()
        c = AESCipher(key)
        print 'Decrypting...'
        return c.decrypt(encrypted_msg)


    def read_file_content(self, key=""):
        txt = self.read_encrypted_txt(key)
        if txt.find('{{{&&filename ') == -1:
            raise Exception('The message found is no file')
        else:
            end = txt.find('&&}}}')
            target_file_name = txt[len('{{{&&filename '):end]
            encoded_content = txt[end+len('&&}}}'):]
            return encoded_content, target_file_name
        
    def read_file(self, target_directory, key=""):
        print '[Read file]'
        encoded_content, target_file_name = self.read_file_content(key)
        target_path = os.path.join(target_directory, target_file_name)
        txt_to_file(encoded_content, target_path)
        print 'Done\n'

    #For debugging only
    def show_image(self, key=""):
        print '[Show image]'
        encoded_content, file_name = self.read_file_content(key)
        content = encoded_content.decode('base64')
        encoded_content = None
        txt_to_image(content, name=file_name)
        print 'Done\n'



@contextlib.contextmanager
def silent_print():
    actual_stdout = sys.stdout
    sys.stdout = StringIO.StringIO()
    yield
    sys.stdout = actual_stdout
    
def txt_to_image(content, name='figure'):
        buff = StringIO.StringIO()
        buff.write(content)
        buff.seek(0)
        im = Image.open(buff)
        imgplot = plt.imshow(im)
        plt.title(name)
        plt.show()

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

def srm(path, reps = 3):
    with open(path, 'rb') as f:
        l = len(f.read())
    for _ in xrange(reps):
        with open(path, 'wb') as f:
            f.write(os.urandom(l))
    os.remove(path)


if __name__ == '__main__':              #Do some testing
    try:
        print 'Testing VideoWriter:'
        writer = VideoWriter("SampleVideo_1280x720_1mb.mp4", 'altered_media/video_altered.avi')
        writer.write_file('small_galaxy.jpg', 'pass')
        print 'Testing VideoReader:'
        reader = VideoReader('altered_media/video_altered.avi')
        reader.read_file('test_outputs', 'pass')
        count = 0
        while not os.path.isfile('test_outputs/small_galaxy.jpg'):
            count += 1
            time.sleep(1)
            if count>10:
                count = 0
                raise Exception('No Output was created')
        with open('small_galaxy.jpg', 'rb') as f_original:
            with open('test_outputs/small_galaxy.jpg', 'rb') as f_altered:
                if not f_original.read() == f_altered.read():
                    raise Exception('Test Input not equal to output')
        print 'Test passed!\n'
    except Exception as e:
        sys.stderr.write('Test failed with exception: %s\n'%(e))
        sys.stderr.write('Did you install OpenCV properly?\n')
    

    try:
        print 'Testing ImageWriter'
        with open('HumanRights.txt', 'r') as f:
            rights = f.read()
        writer = ImageWriter('images.png', 'altered_media/images_altered.png')
        writer.write_file('HumanRights.txt', 'pass')
        print 'Testing ImageReader:'
        reader = ImageReader('altered_media/images_altered.png')
        reader.read_file('test_outputs', 'pass')
        while not os.path.isfile('test_outputs/HumanRights.txt'):
            count += 1
            time.sleep(1)
            if count>10:
                count = 0
                raise Exception('No Output was created')
        with open('test_outputs/HumanRights.txt') as f:
            if not f.read() == rights:
                raise Exception('Test Input not equal to output')
        print "Testing ImageWriter's delete function:"
        writer.delete_msg()
        try:
            reader.read_file('', 'pass')
            sys.stderr.write('Could not delete message\n')
        except:                                                     #It is supposed to fail
            print 'Test passed!\n'
    except Exception as e:
        sys.stderr.write('Test failed with exception: %s\n'%(e))


    try:
        print 'Testing AudioWriter'
        writer = AudioWriter('alcohol.wav', 'altered_media/alcohol_altered.wav')
        writer.write_file('quote.rar', 'pass')
        print 'Testing AudioReader'
        reader = AudioReader('altered_media/alcohol_altered.wav')
        reader.read_file('test_outputs', 'pass')
        with open('quote.rar', 'r') as f:
            archive = f.read()
        while not os.path.isfile('test_outputs/quote.rar'):
            count += 1
            time.sleep(1)
            if count>10:
                count = 0
                raise Exception('No Output was created')
        with open('test_outputs/quote.rar') as f:
            if not f.read() == archive:
                raise Exception('Test Input not equal to output')
        print 'Test passed!\n'
    except Exception as e:
        sys.stderr.write('Test failed with exception: %s\n'%(e))
