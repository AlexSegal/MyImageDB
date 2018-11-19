#!/bin/env python

"""MyImageDB python package
"""
import os
import sys
import subprocess
import tempfile
import logging
import logging.handlers as handlers

from db import ImageFilesTable
from images import ImageInfo
from config import Config

log = logging.getLogger('midb')

h = logging.StreamHandler(stream=sys.stderr)
h.setFormatter(logging.Formatter('%(name)s [%(levelname)s]: %(message)s'))
log.addHandler(h)

h = handlers.RotatingFileHandler(Config.LOGFILE, maxBytes=10*1024*1024,
                                backupCount=10)
h.setFormatter(logging.Formatter('%(asctime)s %(name)s [%(levelname)s]: %(message)s'))
log.addHandler(h)
log.setLevel(logging.DEBUG)

def processImageDir(root=None, forceUpdateExisting=False):
    """Process all images in all subdirectories of the specified root,
    or Config.IMG_ROOT if root is None.
    Store their info in the database.
    If forceUpdateExisting is True, re-process images that are already in the
    database; otherwise skip them.
    """
    log.info('*** Process Image Directory: session begin ***')
    log.info('Log file: %s' % Config.LOGFILE)
    ImageFilesTable.traverseAndStore(root, forceUpdateExisting=forceUpdateExisting)
    log.info('Done')
    
def makeMosaicImage(filename, tilesInXorY, outputResInX, outfile,
                    noRepeatCount=200, imageQueryLimit=16):
    """Create the mosaic matching the input image.
    NOTE: For now we only use mipLevel0
    """
    log.info('*** Make Mosaic Image: session begin ***')
    log.info('Log file: %s' % Config.LOGFILE)
    log.info('Output file: %s' % outfile)
    
    resolutions = [(tilesInXorY,tilesInXorY),
                   (tilesInXorY*2,tilesInXorY*2),
                   (tilesInXorY*4,tilesInXorY*4)]
    
    imageInfo = ImageInfo(filename, resolutions, thumbSize=tilesInXorY)

    frameAspect = imageInfo['frame_aspect']
    
    infiles = []
    usedImageIDClusters = {}
    allUsedImageIDs = []

    n = 0
    
    for y in range(tilesInXorY):
        for x in range(tilesInXorY):
            n += 1
            pixelsForRes = []
            
            log.info('Target Pixel: (%d, %d)' % (x, y))
            
            for w, h in resolutions:
                scale = w / tilesInXorY
                pixelsForRes.append(imageInfo.getPixels((w, h),
                                                        x*scale,
                                                        y*scale,
                                                        (x+1)*scale,
                                                        (y+1)*scale))
                log.debug('Resolution: (%d, %d), %d pixels' % \
                          (w, h, len(pixelsForRes[-1])))
                                    
            rgbCluster = tuple([int(x * 24 + 0.5) for x in pixelsForRes[0]])

            log.info('Looking up image %d of %d matching color %s...' % \
                     (n, tilesInXorY*tilesInXorY, `pixelsForRes[0]`))
        
            if noRepeatCount > 0:
                excludeIDs = allUsedImageIDs[-noRepeatCount:]
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
                    dist = ift.distance(pixels)
                    distsAndImages.append((dist, ift))
                    if i == 0:
                        log.info('Distance: %g for the best match by %d sample(s)' % \
                                 (dist, len(pixels) / 3))
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
                ift = bestImageCandidates[randIdx]
                log.warning('Re-using image %s' % ift.path)
            
            infiles.append(ift.abspath())
            log.info('Image found: id: %d, %s' % (ift.id, ift.abspath()))
            
            if rgbCluster in usedImageIDClusters:
                usedImageIDClusters[rgbCluster].add(ift.id)
            else:
                usedImageIDClusters[rgbCluster] = set([ift.id])
            
            allUsedImageIDs.append(ift.id)
            
    #return ifniles
    outputResInY = int(outputResInX / frameAspect + 0.5)
    tileSizeX = outputResInX / tilesInXorY
    tileSizeY = outputResInY / tilesInXorY
    
    tfiles = []

    for i, infile in enumerate(infiles):
        log.info('Resizing image %d of %d...' % (i+1, len(infiles)))
        
        tfile = tempfile.mktemp(prefix='myImgDBMosaicIn',
                                suffix=os.path.splitext(outfile)[-1])
        tfiles.append(tfile)
        cmd = ['oiiotool', infile, '--resize', '%dx%d' % (tileSizeX, tileSizeY),
               '-o', tfile]
        subprocess.check_call(cmd)
        
    log.info('Building mosaic...')
    
    cmd = ['oiiotool'] + \
           tfiles + \
           ['--mosaic', '%dx%d' % (tilesInXorY, tilesInXorY), '-o', outfile]
    subprocess.check_call(cmd)
    
    log.info('Cleaning up...')
    for f in tfiles:
        os.unlink(f)
    log.info('Done: %s' % outfile)
    
