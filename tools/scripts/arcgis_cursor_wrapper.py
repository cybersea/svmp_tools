import os, sys, string
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
#--------------   Cursor Wrapper  -----------------------------------------
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
class BadCursorType(Exception):
    def __init__(self, message):
        super( BadCursorType , self ).__init__( message )
    def __str__(self):
        return repr(self.code)
        
class ArcGIS10xCursorWrapper( object ):
    
    def __init__( self, cursor_type_string, force_v100_cursor=True ):

        self.cursor_types = dict( 
                [ kv for kv in [ ( 'search', 'SearchCursor' ),
                                 ( 'insert', 'InsertCursor' ), 
                                 ( 'update', 'UpdateCursor' ) ] 
                ]
        )
        self.cursor_type_string = cursor_type_string
        self.cursor = None
        self.arcgis_version = None
             
        #
        #
        #  check arcgis version
        #  and setup appropriate
        #  cursors -- select, insert, update
        #
        #
        self.arcgis_version = '10.0' # default
        if not force_v100_cursor and arcmodule_exists( 'arcpy.da' ):
            self.arcgis_version = '10.1'
        self._set_cursor( self.cursor_type_string )
        
    def _get_cursor( self ):
        """
        in the future this method will
        not be available because self.cursor
        will not be returned, but used internally
        """
        return self.cursor
        
    def _set_cursor( self, cursor_type ):
        if cursor_type not in self.cursor_types.values():
            raise BadCursorType(
                "The cursor you passed in [ %s ] is not one of the cursor types %s" % 
                ( cursor_type, str( self.cursor_types.values() ) )
            )
        if self.arcgis_version == '10.1':
            self.cursor = getattr( arcpy.da , cursor_type )
        elif self.arcgis_version == '10.0':
            self.cursor = getattr( arcpy , cursor_type )
    
#    def insert_v100( self, **options ):
#        """
#        insert for 10.0 version:
#        """
#        print "stub"
#    
#    def insert_v101( self, **options ):
#        """
#        insert for 10.1 version:
#        """
#        print "stub"
#            
#    def insert( self, target_gdb, target_object, fields, records, **kwargs ):
#        """
#        TODO: list needed kwargs here
#        <destination_gdb>
#        <fields>
#        <records>
#        """
#        if self.cursor.__class__.__name__ != self.cursor_types['insert']:
#            raise BadCursorType(
#                "The method insert() cannot operate with cursor type of %s" % 
#                ( self.cursor.__class__.__name__ )
#            )
#    
#        if self.arcgis_version == '10.0':
#            pass
#            # call self.insert_v10.0
#        elif self.arcgis_version == '10.1':
#            pass
#            # call self.insert_v10.1
#        
        
        
        