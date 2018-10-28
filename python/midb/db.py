#!/bin/env python

"""MyImageDB database module
"""
import os
import copy
import MySQLdb
import pprint
from config import Config

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
            print('Argument(s): %s do not correspond to the schema of the '
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
    def storeImagePath(cls, path, resampleSizes=((1,1), (2,2), (4,4)),
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
                             resampleSizes=resampleSizes)
        except Exception, e:
            print path, e
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
        print 'pixel_dumps[0]:', data['pixel_dumps'][0]
        MipLevel0Table.store(result.id, data['pixel_dumps'][0])
        MipLevel1Table.store(result.id, data['pixel_dumps'][1])
        MipLevel2Table.store(result.id, data['pixel_dumps'][2])
        
        # TODO: for some reason images stored in the BLOB column get truncated
        # at random sizes, usually around 60% of the actual size.
        # Looks like a MySQL bug to me...
        #ThumbnailTable.store(result.id, thumbFormat, data['thumbnail'], data['thumbnail_size'])
        
        return result

    @classmethod
    def traverseAndStore(cls, root=Config.IMG_ROOT):
        """Walk down the file system tree, adding images to the database table
        """
        exts = set(['.' + x.lower() for x in cls.listEnumOptions('format')])
        
        for root, dirs, files in os.walk(root, topdown=False):
            print 'Traversing %s...' % root
            for name in files:
                nm, ext = os.path.splitext(name)
                if ext.lower() in exts:
                    print name
                    cls.storeImagePath(os.path.join(root, name))

    @classmethod
    def findByClosestColors(cls, rgbs, frameAspect, aspectTolerance=0.1, limit=16,
                            excludeImageIDs=None):
        """Locate rows in the database and return as a list of instances of
        this class, that are the closest to the given rgb value(s). There can be either
        1, 4, or 16 [r,g,b] values to compare against.
        Returned list length is equal or shorter than limit, sorted "closest first"
        """
        def isRGB(rgb):
            return isinstance(rgb, (list, tuple)) and \
                   len(rgb) == 3 and \
                   all([isinstance(x, float) for x in rgb])
        
        if  isRGB(rgbs):
            pixels = [rgbs]
        elif (len(rgbs) == 1 and isRGB(rgbs[0])) or \
             (len(rgbs) in (4, 16) and all([isRGB(x) for x in rgbs])):
            pixels = rgbs
        else:
            raise ValueError('list/tuple of 1, 4, or 16 [float, float, float] ' \
                             'expected, got %s' % `rgbs`)
        
        if len(pixels) == 1:
            return MipLevel0Table.findClosest(pixels, frameAspect, aspectTolerance,
                                              limit, excludeImageIDs)
        elif len(pixels) == 4:
            return MipLevel1Table.findClosest(pixels, frameAspect, aspectTolerance,
                                              limit, excludeImageIDs)
        elif len(pixels) == 16:
            return MipLevel2Table.findClosest(pixels, frameAspect, aspectTolerance,
                                              limit, excludeImageIDs)

        raise ValueError('WTF?')
      
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
        
        if len(keys) != len(values):
            raise ValueError('%d keys vs %d values!' % (len(keys), len(values)))
        
        sql = 'INSERT INTO %s (%s) VALUES (%s)' % \
              (cls.table(),
               ','.join(keys + ['imageID']),
               ','.join([str(x) for x in (values + [imageID])]))

        updates = []
        for k, v in zip(keys, values):
            updates.append('%s=%s' % (k, str(v)))
        sql += ' ON DUPLICATE KEY UPDATE %s' % ','.join(updates)
        
        print sql
        cursor = Connection.cursor()
        cursor.execute(sql)

    @classmethod
    def sortOrder(cls, rgbs):
        return 'POW(mip_level0.red-%g, 2) + ' \
               'POW(mip_level0.green-%g, 2) + ' \
               'POW(mip_level0.blue-%g, 2)' % tuple(rgbs[0])
    
    @classmethod
    def findClosest(cls, rgbs, frameAspect, aspectTolerance=0.1, limit=16,
                    excludeImageIDs=None):
        """Find a few rows that are the closest to the given rgbs
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
               cls.sortOrder(rgbs),
               limit)
        
        cursor = Connection.cursor()
        cursor.execute(sql)
        imageIDs = [x['imageID'] for x in cursor.fetchall()]
        return [ImageFilesTable.findByID(x) for x in imageIDs]

    '''
    def distance(self, rgb, mode='average'):
        """Find the color space distance (either 'average', 'max', or 'min')
        between the rgb value and 
    '''
    
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

    @classmethod
    def sortOrder(cls, rgbs):
        assert(len(rgbs) == 4)
        result = []
        for i, rgb in enumerate(rgbs):
            result.append('POW(mip_level1.red%d-%g, 2)' % (i, rgb[0]))
            result.append('POW(mip_level1.green%d-%g, 2)' % (i, rgb[1]))
            result.append('POW(mip_level1.green%d-%g, 2)' % (i, rgb[2]))
        return '+'.join(result)
    
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

    @classmethod
    def sortOrder(cls, rgbs):
        assert(len(rgbs) == 16)
        result = []
        for i, rgb in enumerate(rgbs):
            result.append('POW(%s.red%02d-%g, 2)' % (cls.table(), i, rgb[0]))
            result.append('POW(%s.green%02d-%g, 2)' % (cls.table(), i, rgb[1]))
            result.append('POW(%s.green%02d-%g, 2)' % (cls.table(), i, rgb[2]))
        return '+'.join(result)

    
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

        print sql
        
        cursor = Connection.cursor()
        cursor.execute(sql, tuple(data.values() + data2.values()))
        

if __name__ == '__main__':
    pass
    #fname = '/run/media/alex/Seagate Expansion Drive/backup.rsync.win/Pictures/2018/2018Apr15/JPEG/DSC_1074.jpg'
    #fname = '/run/media/alex/Seagate Expansion Drive/backup.rsync.win/Pictures/2018/2018Apr15/JPEG/DSC_1104.jpg'
    fname = '/run/media/alex/Seagate Expansion Drive/backup.rsync.win/Pictures/2010/2010Dec11/CIMG0575.JPG'
    print ImageFilesTable.storeImagePath(fname)
    #ImageFilesTable.traverseAndStore("/run/media/alex/Seagate Expansion Drive/backup.rsync.win/Pictures/SchoolPhotos")
    #ImageFilesTable.traverseAndStore() # the total thing!
    #pprint.pprint(MipLevel0Table.findClosest([[0.145098, 0.266667, 0.356863]], 1.5))
    #pprint.pprint(MipLevel1Table.findClosest([[0.5, 0.5, 0.5], [0.5, 0.5, 0.5], [0.5, 0.5, 0.5], [0.5, 0.5, 0.5]], 1.5))
    #pprint.pprint(MipLevel2Table.findClosest([[0.5, 0.5, 0.5], [0.5, 0.5, 0.5], [0.5, 0.5, 0.5], [0.5, 0.5, 0.5],
    #                                          [0.5, 0.5, 0.5], [0.5, 0.5, 0.5], [0.5, 0.5, 0.5], [0.5, 0.5, 0.5],
    #                                          [0.5, 0.5, 0.5], [0.5, 0.5, 0.5], [0.5, 0.5, 0.5], [0.5, 0.5, 0.5],
    #                                          [0.5, 0.5, 0.5], [0.5, 0.5, 0.5], [0.5, 0.5, 0.5], [0.5, 0.5, 0.5]],
    #                                          1.5))