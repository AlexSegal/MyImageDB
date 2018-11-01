#!/bin/env python

"""MyImageDB database module
"""
import os
import copy
import MySQLdb
import pprint
import math
import datetime
import logging
import traceback
from config import Config

log = logging.getLogger('midb.db')

class Connection(object):
    """Database connection class, with a couple static methods.
    """
    connection = None

    @classmethod
    def cursor(cls):
        if cls.connection is None:
            cls.connection = MySQLdb.connect(host=Config.DB_HOST,
                                             user=Config.USERNAME,
                                             passwd=Config.PASSWD)
            cls.connection.autocommit(True)
        cursor = cls.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('USE %s' % Config.DB_NAME)
        return cursor

    @classmethod
    def disconnect(cls):
        if cls.connection is not None:
            cls.connection.close()
            cls.connection = None


class DBTableBase(object):
    """Generic database table-related methods and data
    """
    # Cached database table description (contains all tables)
    # 1st level: table names are keys, data dicts are values
    # 2st level (data dicts): column names are keys, their description dictionaries
    # (as returned by the MySQL 'DESCRIBE <table>' query)
    _tableSchemaCache = None
    
    # Cached lists of each table's columns. We need this to preserve the order
    # of colums, lost in the _tableSchemaCache dictionary
    _tableColumnsCache = None

    @classmethod
    def _schema(cls, table=None):
        """Return the database table schema as a dictionary:
        column names are keys, their descriprion dictionaries, as returned by the
        MySQL DESCRIBE <table> query are values. Usually the keys in them are:
        'Field':    column name
        'Extra':    auto_increment, etc
        'Default':  default value or None
        'Key':      'PRI', etc
        'Null'      'YES' or 'NO'
        'Type'      type_name(size) unsigned
        """
        if not table:
            table = cls.table()

        if cls._tableSchemaCache is None:
            cls._tableSchemaCache = {}
            cls._tableColumnsCache = {}

        if table not in cls._tableSchemaCache:
            cursor = Connection.cursor()
            cursor.execute('DESCRIBE %s' % table, ())
            describeRowList = cursor.fetchall()
            colDict = {}
            colList = []
            for col in describeRowList:
                colDict[col['Field']] = col
                colList.append(col['Field'])
                
            cls._tableSchemaCache[table] = colDict
            cls._tableColumnsCache[table] = colList

        return cls._tableSchemaCache[table]

    @classmethod
    def columns(cls, table=None):
        """Return the database column names in the database table order.
        The same names can be used in the instance.column syntax to query their
        values.
        """
        cls._schema() # seed the cache
        return cls._tableColumnsCache[table if table else cls.table()]
        
    def __init__(self, **data):
        """Create the instance of the class. Names of arguments it expects
        should correspond to the names of the table columns in the database.
        """
        badKeys = set([x for x in data.keys() if x not in self._schema()])

        if badKeys:
            log.warning('Argument(s): %s do not correspond to the schema of the '
                        'database table %s' % (sorted(badKeys), self.table()))

        self.data = copy.deepcopy(data)

    @property
    def attributes(self):
        """Return a dictionary of all attributes known to the class.
        They all can be accessed (read-only) with classInstance.Attribute syntax
        """
        return copy.deepcopy(self.data)

    def getAttribute(self, attr):
        """Return a attribute value
        """
        return self.attributes[attr]

    def __getattribute__(self, attr):
        """Do the classInstance.attribute syntax support.
        NOTE: if there is a table row matching attr, this method would access
        its value, not a python attribute!
        """
        if attr not in ('_schema', 'data') and attr in self._schema():
            return self.data[attr]

        return super(DBTableBase, self).__getattribute__(attr)

    @classmethod
    def _notimplemented(cls):
        """A "pure virtual call" exception thing
        """
        import traceback
        caller = traceback.extract_stack(limit=2)[0][2]
        raise NotImplementedError('method %s of class %s not implemented' % \
                                  (caller, cls.__name__))

    @classmethod
    def table(cls):
        """Return table name in the database.
        Subclasses must re-implement.
        """
        cls._notimplemented()

    @classmethod
    def idColumn(cls):
        """Return the 'id' column name in the database table.
        Subclasses must re-implement.
        """
        cls._notimplemented()

    @classmethod
    def nameColumn(cls):
        """Return the 'name' column name in the database table.
        Subclasses must re-implement.
        """
        cls._notimplemented()

    @property
    def id(self):
        """Return database ID of the "self" record or None if cannot be detected
        """
        return self.data.get(self.idColumn())

    @property
    def name(self):
        """Return database name of the "self" record or None if cannot be detected
        """
        return self.data.get(self.nameColumn())

    def __repr__(self):
        return '%s(**%s)' % (type(self).__name__, self.data)

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash('%s_%d' % (self.table(), self.id))

    @classmethod
    def _findSQL(cls, sql='', args=None, asDict=False, asCount=False):
        """Find rows in the table and return them as a list of either the
        class instances (asDict=False) or python dictionaries (asDict=True).
        Alternatively, a count of found records can be returned if asCount=True.
        A WHERE clause for the query can be provided via the sql argument.
        """
        cursor = Connection.cursor()

        selWhat = 'COUNT(*)' if asCount else '*'

        try:
            cursor.execute('SELECT %s FROM %s %s' % (selWhat, cls.table(), sql), args)
        except Exception, e:
            log.error('MySQL error: %s.\nQuery was:\n%s' % (e, cursor._last_executed))
            raise

        #print cursor._last_executed

        result = cursor.fetchall()

        if asCount:
            return result[0].values()[0]

        if not asDict:
            result = [cls(**x) for x in result]

        return result

    def reread(self):
        """Force re-reading cached values from the database table
        """
        self.data = self._findSQL('WHERE %s = %d' % (self.idColumn(), self.id),
                                  asDict=True)[0]

    @classmethod
    def findByID(cls, id):
        """Return this class's instance corresponding to the ID value,
        or None if nothing is found
        """
        if id is None or not cls.idColumn():
            return None
        results = cls._findSQL('WHERE %s = %s' % (cls.idColumn(), id))
        return results[0] if results else None

    @classmethod
    def findByName(cls, name):
        """Return this class's instance corresponding to the name value,
        or None if nothing is found
        """
        if not cls.nameColumn():
            return None
        results = cls._findSQL('WHERE %s = %s' % (cls.nameColumn(), `str(name)`))
        return results[0] if results else None

    @classmethod
    def listEnumOptions(cls, column):
        """For an enum column: return a list of its enum options, or []
        if the column is not of type enum.
        """
        typeStr = cls._schema().get(column, {}).get('Type', '')

        if not typeStr.startswith('enum'):
            return []

        def enum(*args):
            """We need this to be able to eval MySQL strings like
            "enum('enumValue1', 'enumValue2')"
            """
            return args

        return eval(typeStr)


class ImageFilesTable(DBTableBase):
    @classmethod
    def table(cls):
        """Return table name in the database.
        """
        return 'image_files'

    @classmethod
    def idColumn(cls):
        """Return the 'id' column name in the database table.
        Subclasses must re-implement.
        """
        return 'imageID'

    @classmethod
    def nameColumn(cls):
        """Return the 'name' column name in the database table.
        Subclasses must re-implement.
        """
        return 'path'

    @classmethod
    def findByImagePath(cls, path):
        """Basically a tiny convenience wrapper around the "findByName" method,
        accepting absolute path to images and looking up records by path which
        is relative to Config.IMG_ROOT
        """
        if os.path.isabs(path) and path.startswith(Config.IMG_ROOT):
            path = os.path.relpath(path, Config.IMG_ROOT)
        return cls.findByName(path)

    def abspath(self):
        """Return absolute image path
        """
        return os.path.normpath(os.path.join(Config.IMG_ROOT, self.path))
    
    @classmethod
    def storeImagePath(cls, path, resolutions=((1,1), (2,2), (4,4)),
                       thumbSize=128, thumbFormat='png'):
        """Add a new row into the table given the absolute path to the image file.
        If the record for this path exists, update it (if necessary).
        Return the class instance for the newly added (or already existing and
        just updated) record.
        """
        if not os.access(path, os.R_OK):
            raise ValueError('%s: cannot be read' % path)
        
        from images import ImageInfo
        
        try:
            data = ImageInfo(path,
                             thumbSize=thumbSize,
                             thumbFormat=thumbFormat,
                             resolutions=resolutions)
        except Exception, e:
            log.exception(traceback.format_exc())
            return

        thisTableData = dict([(k, v) for k, v in data.items() if k in cls.columns()])
        
        sql = 'INSERT INTO %s (%s) VALUES (%s)' % \
              (cls.table(),
               ','.join(thisTableData.keys()),
               ','.join([`x` for x in thisTableData.values()]))
        
        updates = []
        for k, v in thisTableData.items():
            updates.append('%s=%s' % (k, `v`))

        sql += ' ON DUPLICATE KEY UPDATE %s' % ','.join(updates)
        
        cursor = Connection.cursor()
        cursor.execute(sql)
        
        result = cls.findByImagePath(path)
        
        # Now also update the mipmaps and the thumbnail:
        log.debug('pixel_dumps[(1,1)]: %s' % data['pixel_dumps'][(1,1)])
        MipLevel0Table.store(result.id, data['pixel_dumps'][(1,1)])
        MipLevel1Table.store(result.id, data['pixel_dumps'][(2,2)])
        MipLevel2Table.store(result.id, data['pixel_dumps'][(4,4)])
        
        # TODO: for some reason images stored in the BLOB column get truncated
        # at random sizes, usually around 60% of the actual size.
        # Looks like a MySQL bug to me...
        #ThumbnailTable.store(result.id, thumbFormat,
        #                     data.getThumbnail(), data.getThumbnailSize()])
        
        return result

    @classmethod
    def traverseAndStore(cls, rootDir=None, forceUpdateExisting=False):
        """Walk down the file system tree, adding images to the database table
        """
        exts = set(['.' + x.lower() for x in cls.listEnumOptions('format')])
        
        if rootDir is None:
            rootDir = Config.IMG_ROOT
            
        for root, dirs, files in os.walk(rootDir, topdown=False):
            log.info('Traversing %s...' % root)
            for name in files:
                nm, ext = os.path.splitext(name)
                if ext.lower() in exts:
                    fullpath = os.path.join(root, name)
                    if forceUpdateExisting or not cls.findByImagePath(fullpath):
                        log.info('Storing: %s' % name)
                        cls.storeImagePath(fullpath)
                    else:
                        log.info('%s skipped: already in the database' % name)

    @classmethod
    def findByClosestColors(cls, pixels, frameAspect, aspectTolerance=0.1, limit=16,
                            excludeImageIDs=None):
        """Locate rows in the database and return as a list of instances of
        this class, that are the closest to the given pixel (rgb) value(s).
        There can be either 1*3, 4*3, or 16*3 values to compare against.
        Returned list length is equal or shorter than limit, sorted "closest first"
        """
        if len(pixels) == 1*3:
            return MipLevel0Table.findClosest(pixels, frameAspect, aspectTolerance,
                                              limit, excludeImageIDs)
        elif len(pixels) == 4*3:
            return MipLevel1Table.findClosest(pixels, frameAspect, aspectTolerance,
                                              limit, excludeImageIDs)
        elif len(pixels) == 16*3:
            return MipLevel2Table.findClosest(pixels, frameAspect, aspectTolerance,
                                              limit, excludeImageIDs)

        raise ValueError('pixels: %d values not expected' % len(pixels))
      
    def distance(self, pixels):
        """Return color space distance from the float pixels RGBRGBRGB...
        to mip levels of this image.
        There can be either 1*3, 4*3, or 16*3 values in pixels to compare against.
        """
        if len(pixels) == 1*3:
            mipTable = MipLevel0Table.findByImageID(self.id)
        elif len(pixels) == 4*3:
            mipTable = MipLevel1Table.findByImageID(self.id)
        elif len(pixels) == 16*3:
            mipTable = MipLevel2Table.findByImageID(self.id)
        else:
            raise ValueError('pixels: %d values not expected' % len(pixels))

        return mipTable.distance(pixels) if mipTable else 1e+27
            
        
class MipLevel0Table(DBTableBase):
    @classmethod
    def table(cls):
        """Return table name in the database.
        """
        return 'mip_level0'

    @classmethod
    def idColumn(cls):
        """Return the 'id' column name in the database table.
        """
        return 'mip_level0ID'

    @classmethod
    def nameColumn(cls):
        """Return the 'name' column name in the database table.
        """
        return None

    @classmethod
    def findByImageID(cls, imageID):
        results = cls._findSQL('WHERE imageID = %s' % imageID)
        return results[0] if results else None

    @classmethod
    def colorColumns(cls):
        """Return the list of color columns this class stores in its database
        table
        """
        return [x for x in cls.columns() if \
                x.startswith('red') or \
                x.startswith('green') or \
                x.startswith('blue')]
        
    @classmethod
    def store(cls, imageID, values):
        """Create/update the record for the given imageID
        """
        keys = cls.colorColumns()
        
        assert(len(keys) == len(values))
        
        sql = 'INSERT INTO %s (%s) VALUES (%s)' % \
              (cls.table(),
               ','.join(keys + ['imageID']),
               ','.join([str(x) for x in (values + [imageID])]))

        updates = []
        for k, v in zip(keys, values):
            updates.append('%s=%s' % (k, str(v)))
        sql += ' ON DUPLICATE KEY UPDATE %s' % ','.join(updates)
        
        cursor = Connection.cursor()
        cursor.execute(sql)

    @classmethod
    def sortOrder(cls, values):
        assert(len(values) == len(cls.colorColumns()))
        s = []
        for column, value in zip(cls.colorColumns(), values):
            s.append('POW(%s.%s - %g, 2)' % (cls.table(), column, value))
        return '+'.join(s)

    @classmethod
    def findClosest(cls, pixels, frameAspect, aspectTolerance=0.1, limit=16,
                    excludeImageIDs=None):
        """Find a few rows that are the closest to the given rgb pixels
        """
        if not excludeImageIDs:
            excludeImageIDs = [-1]
            
        table = cls.table()
        
        sql = '''SELECT image_files.imageID 
FROM image_files
INNER JOIN 
    %s ON image_files.imageID = %s.imageID
WHERE ABS(image_files.frame_aspect - %g) < %g
      AND image_files.active = 1
      AND image_files.imageID NOT IN (%s)
ORDER BY %s ASC
LIMIT %d''' % (table,
               table,
               frameAspect,
               aspectTolerance,
               ','.join([str(x) for x in excludeImageIDs]),
               cls.sortOrder(pixels),
               limit)
        
        cursor = Connection.cursor()
        cursor.execute(sql)
        imageIDs = [x['imageID'] for x in cursor.fetchall()]
        return [ImageFilesTable.findByID(x) for x in imageIDs]

    def distance(self, pixels):
        """Find the max color space distance between the given pixel(s) and
        the one(s) stored in the table
        """
        assert(len(pixels) == len(self.colorColumns()))
        
        data = self.attributes
        result = 0
        
        resultVec = [0, 0, 0]
        
        for i in range(0, len(pixels), 3):
            red = data[self.colorColumns()[i]]
            green = data[self.colorColumns()[i+1]]
            blue = data[self.colorColumns()[i+2]]
            resultVec[0] += red - pixels[i]
            resultVec[1] += green - pixels[i+1]
            resultVec[2] += blue - pixels[i+2]
        
        return math.sqrt(resultVec[0]**2 + resultVec[1]**2 + resultVec[2]**2) / \
               (len(pixels) / 3)
    
class MipLevel1Table(MipLevel0Table):
    @classmethod
    def table(cls):
        """Return table name in the database.
        """
        return 'mip_level1'

    @classmethod
    def idColumn(cls):
        """Return the 'id' column name in the database table.
        """
        return 'mip_level1ID'

    
class MipLevel2Table(MipLevel0Table):
    @classmethod
    def table(cls):
        """Return table name in the database.
        """
        return 'mip_level2'

    @classmethod
    def idColumn(cls):
        """Return the 'id' column name in the database table.
        """
        return 'mip_level2ID'

    
class ThumbnailTable(DBTableBase):
    @classmethod
    def table(cls):
        """Return table name in the database.
        """
        return 'thumbnails'

    @classmethod
    def idColumn(cls):
        """Return the 'id' column name in the database table.
        """
        return 'thumbnailID'

    @classmethod
    def findByImageID(cls, imageID):
        results = cls._findSQL('WHERE imageID = %s' % imageID)
        return results[0] if results else None

    @classmethod
    def store(cls, imageID, thumbnailFormat, thumbnailDump, thumbnailSize):
        """Create/update the record for the given imageID
        """
        data = {
            'imageID': int(imageID),
            'thumbnail_format': thumbnailFormat,
            'thumbnail_image': thumbnailDump,
            'width': thumbnailSize[0],
            'height': thumbnailSize[1],
        }

        sql = 'INSERT INTO %s (%s) VALUES (%s)' % \
              (cls.table(),
               ','.join(data.keys()),
               ','.join(['%s'] * len(data)))

        data2 = dict(data)
        data2.pop('thumbnail_image')
        
        updates = []
        for k in data2.keys():
            updates.append('%s=%s' % (k, '%s'))
        sql += ' ON DUPLICATE KEY UPDATE %s' % ','.join(updates)

        cursor = Connection.cursor()
        cursor.execute(sql, tuple(data.values() + data2.values()))
