#
#
#  sys imports
#
#
import os, sys, re
import arcpy
import csv

#
#
#  app import
#
#
def msg(msg):
    arcpy.AddMessage(msg)


#--------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------
#---------------------------   ERROR CLASSES   ----------------------------------------------
#--------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------

class CsvFileNotFound( Exception ):
    def __init__(self, message):
        super( self.__class__.__name__ , self ).__init__( message )
    def __str__(self):
        return repr(self.code)

class MissingFields( Exception ):
    def __init__(self, message):
        super( self.__class__.__name__ , self ).__init__( message )
    def __str__(self):
        return repr(self.code)
    
    
    



class TransectCSV( object ):
    
    def __init__ ( self, transfile_path, input_spatial_ref, veg_code_table_path ):
        '''
        this class takes two args both of them paths 
        ---------------------------------------------
        < transfile_path > : path to site_area transect CSV
        < input_spatial_ref > : the arcpy.SpatialReference of the input CSV
        < veg_code_table_path > : path to the veg_code table
        '''
        self.file_path = transfile_path
        self.input_spatial_ref = input_spatial_ref
        self.existing_cols = None # the acutal columns that exist in csv
        self.valid_veg_codes = [] # a list of field names from the csv that are veg codes
        self.veg_code_fields = [] # this is updated in get_veg_codes() -- a list of new veg_code fields in this csv
        self.actual_cols_minus_expected = None # actual csv columns minus the expected onces
        self.veg_code_table_path = veg_code_table_path
        
        #
        #
        #  EXPECTED SOURCE CSV COLUMNS
        #
        #  
        self.site_code = 'Site'
        self.sourceLatCol = 'latitude'  # source ASCII data column name for latitude
        self.sourceLonCol = 'lon' # source ASCII data column name for longitude 
        self.sourceDateCol = 'date' # source ASCII data column name for data
        self.sourceTimeCol = 'time' # source ASCII data  column for time
        self.transFileSuffix = "TD.csv"  # suffix for input transect ASCII file  
        self.sourceTrkCol = 'trk' # column to identify a track/transect
        self.trkTypeCol = 'TrkType'  # Column listing type of track
        self.videoCol = 'video'  # Column for video data quality (0,1)    
        self.site_code = 'Site' # Column for site code e.g. core001
        self.depth_obs = 'BSdepth' # Column for depth
        self.depth_interp = 'BSdepth_interp' # Column for interp
        self.other =  'other' # Column other
        self.realtime = 'realtime'  # Column realtime video
        
        
        #
        #
        #  on instantiation, start QC
        #  and begin caching 
        #  the data we'll need
        #  to process the csv 
        #
        #
        self._verify_field_names()
        self._get_veg_codes()

        
    def _expected_columns( self ):
        '''
        note this data structure also preserves order
        there is an assumption that this order
        mirrors the TransectDatasource._get_fields() order
        '''
        
        return [
            
            self.site_code ,
            self.sourceTrkCol ,
            self.sourceDateCol ,
            self.sourceTimeCol ,
            self.depth_obs ,
            self.depth_interp ,
            self.other ,
            self.videoCol ,
            self.realtime ,
            self.trkTypeCol ,
            self.sourceLatCol ,
            self.sourceLonCol , 
                
        ]
        
    def _verify_field_names( self ):
        '''
        open the csv and make sure expected field names exist
        '''
        #
        #
        #  the first thing we do when we create a new CSV class
        #  is QC it to make sure:
        #  1) it exists
        #  2) it can be read
        #  3) that the columns we expect exist 
        #
        #
        if not os.path.exists( self.file_path ):
            raise CsvFileNotFound( "CSV file '%s' cannot be found" % self.file_path )   
        msg( "CSV file, '%s', found and opened successfully" % self.file_path )
        
        #
        #
        #  read the csv file
        #
        #
        csv_file = open( self.file_path ,'rbU' )
        csv_reader = csv.DictReader( csv_file )
        self.existing_cols = csv_reader.reader.next()
        
        #
        #  identify missing fields in the csv that are expected
        #
        #
        missingFields = [ f for f in self._expected_columns() if f not in self.existing_cols ] 
        if missingFields:
            raise MissingFields( "The CSV file, '%s' is missing columns:\n%s" % (os.path.basename( self.file_path ), '\n'.join( missingFields)) )
    
    
        #
        #
        #  get the difference between
        #  expected csv columns
        #  and
        #  csv read columns
        #  and cache it
        #
        #
        actual_csv_cols = frozenset( self.existing_cols )
        expected_csv_cols = frozenset( self._expected_columns() )
        self.actual_cols_minus_expected = actual_csv_cols.difference( expected_csv_cols )
            
        csv_file.close()
        
        
    def _get_veg_codes( self ):
        '''
        get all valid veg_codes from the veg_code table.
        these will be used to compare which fields in the csv
        are veg_codes and which are not for dynamic featureclass
        column creation in TransectDatasource class
        '''

        #
        #  we only want this cursor code
        #  to run once ( probably per site_code csv ) 
        #  and cache the valid
        #  veg_codes in the class attribute
        #  self.valid_veg_codes
        #
        if not self.valid_veg_codes:
            #
            #  get valid veg_codes
            #
            scurse = arcpy.SearchCursor( self.veg_code_table_path  )
            row = scurse.next()
            while row:
                self.valid_veg_codes.append( row.getValue( 'veg_code' ) )
                row = scurse.next()          
            del row, scurse
        
        
            #
            #
            #  for every csv column that is not an expected column
            #  see if it's a valid veg_code field name
            #
            #
            for source_veg_code in [ i for i in list( self.actual_cols_minus_expected ) if i in self.valid_veg_codes ]:         
                #
                #
                #  add it to our cached
                #  class attribute
                #  self.veg_code_fields
                #  this field for veg_code is a SHORT int
                #
                #     
                self.veg_code_fields.append( [ source_veg_code, 'SHORT', '#', '#', '#' ] )
