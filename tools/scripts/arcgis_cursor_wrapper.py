#--------------------------------------------------------------------------
#Imports
#--------------------------------------------------------------------------
import os, sys
import arcpy

#
#  if ArcGIS 10.1, defer to the Data Access module
#  from https://github.com/mattmakesmaps/335A_SoundGIS_DNR/blob/master/Python/Merge_Tool/Merge_Tool.py
#
def arcmodule_exists( module_name ):
    try:
        __import__( module_name )
    except ImportError:
        return False
    else:
        return True

#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
#--------------   Cursor Wrapper Errors  ----------------------------------
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
class BaseCursorError( Exception ):
    def __init__(self, message):
        super( BaseCursorError , self ).__init__( message )
    def __str__(self):
        return repr(self.code)

class BadCursorType( BaseCursorError ):
    def __init__(self, message):
        super( self.__class__.__name__, self ).__init__( message )
    
class NoneCursorType( BaseCursorError ):
    def __init__(self, message):
        super( self.__class__.__name__, self ).__init__( message )

class BadRowObject( BaseCursorError ):
    def __init__(self, message):
        super( self.__class__.__name__, self ).__init__( message )
        
class MissingCursorOptions( BaseCursorError ):
    def __init__(self, message):
        super( self.__class__.__name__, self ).__init__( message )


#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
#--------------   Cursor Wrapper  -----------------------------------------
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------     
class ArcGIS10xCursorWrapper( object ):
    
    def __init__( self, cursor_type_string, force_v100_cursor=True ):

        self.cursor_types = dict( 
                [ kv for kv in [ ( 'search', 'SearchCursor' ),
                                 ( 'insert', 'InsertCursor' ), 
                                 ( 'update', 'UpdateCursor' ) ] 
                ]
        )
        self.cursor_type_string = cursor_type_string
        self.cursor_ref = None
        self.cursor = None
             
        #
        #
        #  set property arcgis_version
        #  and setup appropriate
        #  cursor pointers -- select, insert, update
        #
        #
        self._arcgis_version = '10.0' # default
        if not force_v100_cursor and arcmodule_exists( 'arcpy.da' ):
            self._arcgis_version = '10.1'
        self._set_cursor_ref( self.cursor_type_string )
        
        
    @property
    def arcgis_version( self ):
        return self._arcgis_version
   
    def create( self, target_datasource=None, spatial_ref_obj=None, fields=None, where_sql=None ): 
        '''
        the right options need to be set for right arcgis_version cursor
        this takes all kwargs and does checking later
        
        '''
        
        #
        #
        #  check the options
        #
        #
        if self.arcgis_version == '10.0' and not target_datasource and not spatial_ref_obj:
            raise MissingCursorOptions( "you tried creating a 10.0 cursor " +
                "but you need to pass 1) target_datasource and 2) spatial_ref_obj ")
        elif self.arcgis_version == '10.1' and not target_datasource and not fields:
            raise MissingCursorOptions( "you tried creating a 10.1 cursor " +
                "but you need to pass 1) target_datasource and 2) fields ")
        
        #
        #
        #  instatiate the cursor
        #
        #
        if self.arcgis_version == '10.0':
            self.cursor = self.cursor_ref( target_datasource, spatial_ref_obj )
        elif self.arcgis_version == '10.1':
            self.cursor = self.cursor_ref( target_datasource, fields )
        
        if not self.cursor:
            raise NoneCursorType( "self.cursor is None")
        
        return self
        
    def _set_cursor_ref( self, cursor_type ):
        if cursor_type not in self.cursor_types.values():
            raise BadCursorType(
                "The cursor type you passed in [ %s ] is not one of the cursor types %s" % 
                ( cursor_type, str( self.cursor_types.values() ) )
            )
        if self.arcgis_version == '10.1':
            self.cursor_ref = getattr( arcpy.da , cursor_type )
        elif self.arcgis_version == '10.0':
            self.cursor_ref = getattr( arcpy , cursor_type )
            
    def new_row( self, ):
        """
        handles calls to newRow for version 10.0
        """
        if self.arcgis_version == '10.0':
            return self.cursor.newRow()
    
    def insert_row( self, row_object ):
        """
        handles calls to insertRow between 10.0 and 10.1
        ------------------------------------------------
        < row_object > : in 10.0 this is Cursor.row object
        < row_object > : in 10.1 this is a tuple
        """
        if self.arcgis_version == '10.0' and isinstance( row_object, arcpy.arcobjects.Row ):
            self.cursor.insertRow( row_object )
        elif self.arcgis_version == '10.1' and isinstance( row_object, tuple ):
            self.cursor.insertRow( row_object )
        else:
            raise BadRowObject( "The row_object = %s does not match arcgis_version = %s" % 
                                ( str( type( row_object ) ), self.arcgis_version ) )
    


        
        