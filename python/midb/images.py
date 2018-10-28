#!/usr/bin/env python

import os
import re
import subprocess
import datetime
import tempfile
import pprint
from config import Config

class ImageInfo(dict):
    def __init__(self, filename, resampleSizes=((1,1), (2,2), (4,4)),
                 thumbSize=128, thumbFormat='png'):
        super(ImageInfo, self).__init__()
        info = self.getGeneralInfo(filename)
        for k, v in info.items():
            self.setdefault(k, v)
        if resampleSizes:
            imgDumpDict = self.getImageDump(filename, resampleSizes,
                                            thumbSize, thumbFormat)
            for k, v in imgDumpDict.items():
                self.setdefault(k, v)
        
    @classmethod
    def getGeneralInfo(cls, filename):
        """
        Create and return a dictionary with keys:
            path
            format
            num_channels
            hash
            colorspace
            orig_timestamp
            pixel_type
            width
            height
            frame_aspect
        """
        assert(filename.startswith(Config.IMG_ROOT))
        
        cmd = ['iinfo', '--hash', '-v', filename]
        pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = pipe.communicate()
        
        resRegex = re.compile(r'^(\d+)\s*x\s*(\d+)$')
        nchanRegex = re.compile(r'^(\d+)\s+channel$')
        # this will match anything, so it should be queried last!
        typeFormatRegex = re.compile(r'^(.*?)\s+(.*?)$')
        
        result = {}

        # default orig_timestamp: file creation time, unless Exif data
        # overrides it (see below):
        #ctime = os.path.getctime(filename)
        #result['orig_timestamp'] = str(datetime.datetime.fromtimestamp(ctime))
        
        # Actually I prefer setting it to some old time...
        result['orig_timestamp'] = '2001-01-01 00:00:00.0'

        for line in stdout.splitlines():
            if ':' not in line:
                continue
            
            parts = [x.strip() for x in line.split(':', 2)]
            
            if parts[0] == 'Exif':
                parts = [parts[0] + ':' + parts[1], ':'.join(parts[2:])]
            
            if parts[0] == filename:
                result['path'] = os.path.relpath(parts[0], Config.IMG_ROOT)
                
                for subpart in [x.strip() for x in parts[1].split(',')]:
                    if resRegex.match(subpart):
                        found = resRegex.findall(subpart)
                        result['width'] = int(found[0][0])
                        result['height'] = int(found[0][1])
                        result['frame_aspect'] = float(result['width']) / \
                                                       result['height']
                    elif nchanRegex.match(subpart):
                        found = nchanRegex.findall(subpart)
                        result['num_channels'] = int(found[0])
                    elif typeFormatRegex.match(subpart):
                        found = typeFormatRegex.findall(subpart)
                        result['pixel_type'] = found[0][0]
                        result['format'] = found[0][1]
                        
            elif parts[0] == 'SHA-1':
                result['hash'] = parts[1]
            elif parts[0] == 'oiio:ColorSpace':
                result['colorspace'] = parts[1][1:-1]
            elif parts[0] == 'Exif:DateTimeOriginal':
                dt = datetime.datetime.strptime(parts[1][1:-1], '%Y:%m:%d %H:%M:%S')
                result['orig_timestamp'] = str(dt)
            
        if result['format'] == 'jpeg':
            result['format'] = 'jpg'
        elif result['format'] == 'tiff':
            result['format'] = 'tif'
        
        return result
    
    @classmethod
    def getImageDump(cls, filename, resampleSizes=((1,1), (2,2), (4,4)),
                     thumbSize=128, thumbFormat='png'):
        """Return a dictionary with keys:
        'pixel_dumps': list of len(resampleSizes) of float pixel values lists
        'thumbnail': binary string with the thumbnail image in the requested format
        'thumbnail_size': (width, height)
        """
        info = cls.getGeneralInfo(filename)
        scale = float(thumbSize) / max(info['width'], info['height'])
        thumbW = int(info['width'] * scale + 0.5)
        thumbH = int(info['height'] * scale + 0.5)

        result = {'thumbnail_size': (thumbW, thumbH)}
        
        rgbRegex = re.compile(r'^\s*Pixel \(\d+,\s+\d+\)\s*:\s*' \
                               '([0-9\.\-\+e]+)\s+([0-9\.\-\+e]+)\s+([0-9\.\-\+e]+)\s*$')
        floatRegex = re.compile(r'^\s*Pixel \(\d+,\s+\d+\)\s*:\s*' \
                               '([0-9\.\-\+e]+)\s*$')
        tfiles = []
        cmd = ['oiiotool', filename]

        sizes = list(resampleSizes)
        # Append order indices to widths, heights list to restore the original
        # order later on. For now we have to sort the sized from the largest
        # to the smallest, since this is what oiiotool is expecting to execute
        # multiple resizes in one command:
        sizes = [[w, h, i] for i, (w, h) in enumerate(sizes)]
        sizes.sort(cmp=lambda *arg: cmp(max(arg[1][0], arg[1][1]),
                                        max(arg[0][0], arg[0][1])))
        # thumbnail is expected to be the largest, so it should come first:
        sizes.insert(0, (thumbW, thumbH, -1))
        
        for w, h, i in sizes:
            tfile = tempfile.mktemp(prefix='myImgDBResamp',
                                    suffix=os.path.splitext(filename)[-1])
    
            if os.path.exists(tfile):
                os.unlink(tfile)
        
            cmd.extend(['--resize', '%dx%d' % (w,h), '-o', tfile])
            tfiles.append(tfile)
            
        #print cmd
        subprocess.check_call(cmd)
        
        result['pixel_dumps'] = []
        
        # Resize the result['pixel_dumps'] list for random access to its elements:
        for i in range(len(resampleSizes)):
            result['pixel_dumps'].append([])
        
        for (w, h, i), tfile in zip(sizes, tfiles):
            if not os.path.exists(tfile):
                raise RumtimeError('%s not found after being saved' % tfile)
            
            if i == -1:
                # thumbnail!
                f = file(tfile, 'rb')
                result['thumbnail'] = f.read(os.path.getsize(tfile))
                f.close()
                continue
            
            cmd = ['oiiotool', '--dumpdata', tfile]
            pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = pipe.communicate()
            pixels = []
            for line in stdout.splitlines():
                if rgbRegex.match(line):
                    found = rgbRegex.findall(line)
                    rgb = [float(x) for x in found[0]]
                    pixels.extend(rgb)
                elif floatRegex.match(line):
                    found = floatRegex.findall(line)
                    rgb = [float(found[0])] * 3
                    pixels.extend(rgb)
            result['pixel_dumps'][i] = pixels
                
            os.unlink(tfile)
        
        return result
    
if __name__ == '__main__':
    #fn = '/run/media/alex/Seagate Expansion Drive/backup.rsync.win/Pictures/2018/2018Apr15/JPEG/DSC_1074.jpg'
    #fn = '/run/media/alex/Seagate Expansion Drive/backup.rsync.win/Pictures/RMC_25_years/FromKayumov/rmc20.jpg'
    fn = '/run/media/alex/Seagate Expansion Drive/backup.rsync.win/Pictures/2018/2018Sep02(Grouse)/JPEG/P1034001.jpg'
    tilesInX = 8
    imgInfo = ImageInfo(fn, resampleSizes=((tilesInX,tilesInX),), thumbSize=tilesInX)
    imgInfo.pop('thumbnail')
    pprint.pprint(dict(imgInfo))
    #dump = ImageInfo.getImageDump(fn, thumbSize=16)
    #pprint.pprint(dump)
