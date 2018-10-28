#!/bin/env python

"""MyImageDB python package
"""
import os
import subprocess
import tempfile
from db import ImageFilesTable
from images import ImageInfo
from config import Config

def processImageDir(root=None):
    """Process all images in all subdirectories of the specified root,
    or Config.IMG_ROOT if root is None.
    Store their info in the database.
    """
    ImageFilesTable.traverseAndStore()
    
def makeMosaicImage(filename, tilesInX, outputResInX, outfile):
    """Create the mosaic matching the input image.
    NOTE: For now we only use mipLevel0
    """
    from images import ImageInfo
    imageInfo = ImageInfo(filename, resampleSizes=((tilesInX,tilesInX),),
                          thumbSize=tilesInX)
    floats = imageInfo['pixel_dumps'][0]
    rgbs = []
    for i in range(0, len(floats), 3):
        rgbs.append([floats[i], floats[i+1], floats[i+2]])
    
    frameAspect = imageInfo['frame_aspect']
    
    infiles = []
    usedImageIDClusters = {}
    allUsedImageIDs = set()
    
    for i, rgb in enumerate(rgbs):
        rgbCluster = tuple([int(x * 32 + 0.5) for x in rgb])

        print 'Looking up image %d of %d matching color %s...' % \
                (i+1, len(rgbs), `rgb`)
        
        excludeIDs = usedImageIDClusters.get(rgbCluster)
        
        ifTables = ImageFilesTable.findByClosestColors(rgb, frameAspect,
                                                       aspectTolerance=0.1,
                                                       limit=32,
                                                       excludeImageIDs=excludeIDs)
        # Try to pick an image that was not yet used in this rgb cluster:
        for ift in ifTables:
            if ift.id not in allUsedImageIDs:
                break
        else:
            # All images returned by the query have been already used. Let's pick
            # one of them anyways. Use deterministic selection:
            randIdx = hash(i) % len(ifTables)
            #print randIdx, len(ifTables)
            ift = ifTables[randIdx]
            print 'Re-using image %s' % ift.path
        
        infiles.append(ift.abspath())
        print 'Image found: id: %d, %s' % (ift.id, ift.abspath())
        
        if rgbCluster in usedImageIDClusters:
            usedImageIDClusters[rgbCluster].add(ift.id)
        else:
            usedImageIDClusters[rgbCluster] = set([ift.id])
        
        allUsedImageIDs.add(ift.id)
        
    #return ifniles
    outputResInY = int(outputResInX / frameAspect + 0.5)
    tileSizeX = outputResInX / tilesInX
    tileSizeY = outputResInY / tilesInX
    
    tfiles = []

    for i, infile in enumerate(infiles):
        print 'Resizing image %d of %d...' % (i+1, len(rgbs))
        
        tfile = tempfile.mktemp(prefix='myImgDBMosaicIn',
                                    suffix=os.path.splitext(outfile)[-1])
        tfiles.append(tfile)
        cmd = ['oiiotool', infile, '--resize', '%dx%d' % (tileSizeX, tileSizeY),
               '-o', tfile]
        subprocess.check_call(cmd)
        
    print 'Building mosaic...'
    
    cmd = ['oiiotool'] + \
           tfiles + \
           ['--mosaic', '%dx%d' % (tilesInX, tilesInX), '-o', outfile]
    subprocess.check_call(cmd)
    
    print 'Cleaning up...'
    for f in tfiles:
        os.unlink(f)
    print 'Done: ', outfile 
    
if __name__ == '__main__':
    #fname = '/run/media/alex/Seagate Expansion Drive/backup.rsync.win/Pictures/2018/2018Sep02(Grouse)/JPEG/P1034001.jpg'
    #print makeMosaicImage(fname, 8, 2048, '/var/tmp/mosaic01.png')
    processImageDir()