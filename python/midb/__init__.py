#!/bin/env python

"""MyImageDB python package
"""
import os
import sys
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
    
def makeMosaicImage(filename, tilesInXorY, outputResInX, outfile,
                    noRepeatingImages=True, imageQueryLimit=16):
    """Create the mosaic matching the input image.
    NOTE: For now we only use mipLevel0
    """
    resolutions = [(tilesInXorY,tilesInXorY),
                   (tilesInXorY*2,tilesInXorY*2),
                   (tilesInXorY*4,tilesInXorY*4)]
    
    imageInfo = ImageInfo(filename, resolutions, thumbSize=tilesInXorY)

    frameAspect = imageInfo['frame_aspect']
    
    infiles = []
    usedImageIDClusters = {}
    allUsedImageIDs = set()

    n = 0
    
    for y in range(tilesInXorY):
        for x in range(tilesInXorY):
            n += 1
            pixelsForRes = []
            
            print 'Target Pixel: (%d, %d)' % (x, y)
            
            for w, h in resolutions:
                scale = w / tilesInXorY
                pixelsForRes.append(imageInfo.getPixels((w, h),
                                                        x*scale,
                                                        y*scale,
                                                        (x+1)*scale,
                                                        (y+1)*scale))
                #print 'Resolution: (%d, %d), %d pixels' % (w, h, len(pixelsForRes[-1]))
                                    
            rgbCluster = tuple([int(x * 24 + 0.5) for x in pixelsForRes[0]])

            print 'Looking up image %d of %d matching color %s...' % \
                    (n, tilesInXorY*tilesInXorY, `pixelsForRes[0]`)
        
            if noRepeatingImages:
                excludeIDs = allUsedImageIDs
                imageQueryLimit = 1
            else:
                excludeIDs = usedImageIDClusters.get(rgbCluster)
        
            distsAndImages = []
            
            for pixels in pixelsForRes:
                i = 0
                for ift in ImageFilesTable.findByClosestColors(pixels,
                                                            frameAspect,
                                                            aspectTolerance=0.1,
                                                            limit=imageQueryLimit,
                                                            excludeImageIDs=excludeIDs):
                    maxDist = ift.maxDistance(pixels) / (len(pixels) / 3)
                    distsAndImages.append((maxDist, ift))
                    if i == 0:
                        print 'MaxDistance: %g for the best match by %d sample(s)' % \
                                    (maxDist, len(pixels) / 3)
                    i += 1
                
            distsAndImages.sort(cmp=lambda *arg: cmp(arg[0][0], arg[1][0]))
            bestImageCandidates = [b for a, b in distsAndImages]
            
            # Try to pick an image that was not yet used:
            for ift in bestImageCandidates:
                if ift.id not in allUsedImageIDs:
                    break
            else:
                # All images returned by the query have been already used. Let's pick
                # one of them anyways. Use random but deterministic selection:
                randIdx = hash(str(n)) % len(bestImageCandidates)
                #print randIdx, len(ifTables)
                ift = bestImageCandidates[randIdx]
                print 'Re-using image %s' % ift.path
            
            infiles.append(ift.abspath())
            print 'Image found: id: %d, %s' % (ift.id, ift.abspath())
            sys.stdout.flush()
            
            if rgbCluster in usedImageIDClusters:
                usedImageIDClusters[rgbCluster].add(ift.id)
            else:
                usedImageIDClusters[rgbCluster] = set([ift.id])
            
            allUsedImageIDs.add(ift.id)
            
    #return ifniles
    outputResInY = int(outputResInX / frameAspect + 0.5)
    tileSizeX = outputResInX / tilesInXorY
    tileSizeY = outputResInY / tilesInXorY
    
    tfiles = []

    for i, infile in enumerate(infiles):
        print 'Resizing image %d of %d...' % (i+1, len(infiles))
        sys.stdout.flush()
        
        tfile = tempfile.mktemp(prefix='myImgDBMosaicIn',
                                suffix=os.path.splitext(outfile)[-1])
        tfiles.append(tfile)
        cmd = ['oiiotool', infile, '--resize', '%dx%d' % (tileSizeX, tileSizeY),
               '-o', tfile]
        subprocess.check_call(cmd)
        
    print 'Building mosaic...'
    
    cmd = ['oiiotool'] + \
           tfiles + \
           ['--mosaic', '%dx%d' % (tilesInXorY, tilesInXorY), '-o', outfile]
    subprocess.check_call(cmd)
    
    print 'Cleaning up...'
    for f in tfiles:
        os.unlink(f)
    print 'Done: ', outfile 
    
if __name__ == '__main__':
    #fname = '/run/media/alex/Seagate Expansion Drive/backup.rsync.win/Pictures/2018/2018Sep02(Grouse)/JPEG/P1034001.jpg'
    #fname = '/run/media/alex/Seagate Expansion Drive/backup.rsync.win/Pictures/2009/2009June13/DSC_6311.jpg'
    #fname = '/run/media/alex/Seagate Expansion Drive/backup.rsync.win/Pictures/2010/2010April18/DSC_8886.jpg'
    fname = '/var/tmp/DSC_9041.jpg'
    print makeMosaicImage(fname, 48, 8192, '/var/tmp/mosaic_yasha03.png')
    #processImageDir()