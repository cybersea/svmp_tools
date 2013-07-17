#
#
#  sys imports
#
#
import os, sys, re
import copy
import arcpy
import csv



#
#
#  app imports
#
#
from transect_csv import TransectCSV
import svmpUtils as utils

def msg(msg):
    arcpy.AddMessage(msg)

#--------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------
#---------------------------   ERROR CLASSES   ----------------------------------------------
#--------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------

class CreateFeatureClassError( Exception ):
    def __init__(self, message):
        super( self.__class__ , self ).__init__( message )
    def __str__(self):
        return repr(self)
    
class SetValueError( Exception ):
    def __init__(self, message):
        super( self.__class__, self ).__init__( message )
    def __str__(self):
        return repr(self)
    
class InsertRowError( Exception ):
    def __init__(self, message):
        super( self.__class__ , self ).__init__( message )
    def __str__(self):
        return repr(self)

class DecimalDegreesConversionError( Exception ):
    def __init__(self, message):
        super( self.__class__ , self ).__init__( message )
    def __str__(self):
        return repr(self)


class TransectDatasource( object ):
    
    def __init__( self, target_path, target_name, output_spatial_ref, transect_csv_object ):
        '''
        a geo datasource class that hasA TransetCSV object
        it can read the TransectCSV 
        and write it to a datasource
        ----------------------------------------------------
        < target_path >  : datasource dirname() for target_name ( featureclass )
        < target_name >  : name of the featureclass
        < output_spatial_ref > : the arcpy.SpatialReference of the target datasource
        < transect_csv_object > : an instance of TransectCSV
        '''
        
        self.target_path = target_path  # dirname( target_name )
        self.target_name = target_name  # featureclass name 
        self.output_spatial_ref = output_spatial_ref
        self.full_output_path = os.path.join( self.target_path, self.target_name )
        self.transect_csv = transect_csv_object
        
        #
        #
        #  DYNAMIC Attributes
        #
        #
        self.insert_fields = None # this holds all fields that will be created in output datasource
        self.field_mapping = None # this is field mapping hash between target fields and csv fields
        self.fkey_cache = {} # a hash that cache's trktype_code lookups so we don't have to use SearchCursor
        
        #
        #
        #  FEATURECLASS FIELDS
        #
        #
        self.site_code = utils.site_code
        self.trkCol = utils.trkCol # to match final database column name, changed from trk to tran_num  
        self.shpDepCol = utils.shpDepCol # Interpolated Biosonics Depth column
        self.shpDateCol = utils.shpDateCol # Column with date of survey       
        self.time24hr = utils.time24hr
        self.bsdepth = utils.bsdepth
        self.videoCol = utils.videoCol # Column for video data quality (0,1)
        self.trktype = utils.trktype
        
        #
        #
        #  on instantiation we will:
        #  1) create the needed fields for
        #  featureclass creation and cache them
        #  2) setup the mapping of
        #  TransectCSV fields to 
        #  TransectDatasource fields
        #  3) create the featureclass
        #  4) add featureclass fields
        #
        #  
        self._add_veg_code_fields()
        self._create_field_mapping()
        self._create_featureclass()
        
    
    def _get_fields( self ):
        '''
        note this data structure also preserves field order
        there is an assumption that this order
        mirrors the TransectCSV._expected_columns() order
        '''
        return utils.trkPtShpCols
        
    def _create_field_mapping( self ):
        #
        #
        #  first step: create a dictionary where
        #  our TransectDatasource fields are KEY
        #  to our TransectCSV field VALUE
        #  this is based on intial class values
        #  which means we'll need to update the hash
        #  with the dynamic veg_code fieldnames after
        #
        #
        self.field_mapping = dict( zip( [ i[0] for i in self._get_fields() if i ],
                                        self.transect_csv._expected_columns() ) )
        
        #
        #
        #  udpate with our dynamic
        #  veg_codes 
        #  from TransectCSV
        #
        #
        self.field_mapping.update( dict( [ (fld[0],fld[0]) for fld in self.transect_csv.veg_code_fields ] ) )
        
    def _add_veg_code_fields( self ):
        '''
        TransectCSV will determine what columns
        in the CSV are veg_code columns dynamically.
        Here we use this informaiton to create our
        self.insert_fields that will be used
        to create output featurelcass columns
        in _add_featureclass_fields
        
        TODO:
        1) move veg_code template fields to utils and reference that
        '''
        
        #
        #
        #  we only want to run this 
        #  code *once* because
        #  it can be cached in class attribute
        #  self.insert_fields to save time
        #
        #
        if not self.insert_fields:               
            #
            #
            #  cache the field names in self.insert_fields
            #  we will need to dynamically add veg_code
            #  fields derived from TransectCSV to them
            #  before creating the output datasource
            #
            #
            self.insert_fields = copy.deepcopy( self._get_fields() )
                      
            #
            #
            #  add veg_code fields 
            #  to this TransectDatasource
            #  we insert them before
            #  'video' column here
            #  because we do not have
            #  any other option yet
            #   
            #
            for field in self.transect_csv.veg_code_fields:  
                # Question -- why is the whole field definition here?
                insert_indx = self.insert_fields.index( [ self.videoCol ,'SHORT','#','#','#' ] )
                self.insert_fields.insert( insert_indx, field )
                
                
    def _create_featureclass( self ):
        try:
            arcpy.CreateFeatureclass_management( self.target_path, self.target_name, "POINT","#","#","#", self.output_spatial_ref )
            msg( "Created Feature Class: '%s'" % self.full_output_path )
            self._add_featureclass_fields()
        except arcpy.ExecuteError:
            errtext = "Unable to create feature class: '%s' or unable to add fields" % self.full_output_path
            errtext += "\nTry closing ArcMap, or other applications that may be accessing these data."
            errtext += "\nIf you are viewing the data in ArcCatalog, change directories and choose 'Refresh' under the 'View' menu."
            #errtext += "\nYou can also try deleting the existing shapefile manually from the file system."
            raise CreateFeatureClassError( errtext )
        
    def _add_featureclass_fields( self ):
        """
        take everything stored in self.insert_fields
        and create columns in the output featureclass
        """
        fnames = []
        for col in self.insert_fields:
            if col:
                fname = col[0]
                ftype = col[1]
                fprecision = col[2]
                fscale = col[3]
                flength = col[4]
                arcpy.AddField_management( self.full_output_path, fname,ftype, fprecision, fscale, flength )
                fnames.append(fname)
        return fnames   
    
    def _get_fkey( self, path, lookup_key, lookup_value ):
        """
        this generic functions assumes that the path being passed
        in is to a featureclass inside a geodatabase of some kind
        """
        
        #
        #
        #  check the self.fkey_cache
        #  to see if lookup_value has already been looked up
        #
        #
        if self.fkey_cache.get( lookup_value, False ):
            return self.fkey_cache.get( lookup_value )
        
        #
        #
        #  format search_string based on lookup_value Python type
        #  then this function will be general enough
        #  to be resused later if needed
        #
        #
        delimited_field = arcpy.AddFieldDelimiters( path, lookup_key )
        search_string = delimited_field + " = " + "'%s'" %( str( lookup_value ) )
      
      
        scurse = arcpy.SearchCursor( path, search_string )
        row = scurse.next()
        if not row:
            errtext = "You tried FKEY lookup '%s' on table [ %s ] and it query returned nothing" % ( search_string, self.full_output_path )
            raise Exception( errtext )         
        fkey = row.getValue( "trktype_code" )
        del row, scurse
        #
        #  add it to the cache
        #
        self.fkey_cache[ lookup_value ] = fkey
        return fkey
         

    def write_output( self ):
            reader = csv.DictReader( open(self.transect_csv.file_path,'rbU') )  
            icurse = arcpy.InsertCursor( self.full_output_path, self.transect_csv.input_spatial_ref )
            pnt = arcpy.CreateObject("Point")
            msg("Populating data table of '%s'" % self.full_output_path)
            for idx, row in enumerate(reader):
                # Convert and create the geometries
                csv_row = idx + 2
                pnt.ID = idx + 1
                lon,lat = row[ self.transect_csv.sourceLonCol ],row[ self.transect_csv.sourceLatCol ]
                # convert lat/long values in csv file to decimal degrees
                try:         
                    pnt.X = utils.dm2dd(lon)
                except Exception:
                    errtext = "Unable to convert source longitude, %s, to decimal degree format" % lon
                    errtext += "\nCSV file, %s\nrow: %s" % ( self.full_output_path, csv_row )  
                    raise DecimalDegreesConversionError( errtext )
                                
                try:               
                    pnt.Y = utils.dm2dd(lat)
                except Exception:
                    errtext = "Error converting source latitude, %s, to decimal degree format" % lat
                    errtext += "\nCSV file, %s\nrow: %s" % ( self.full_output_path, csv_row )
                    raise DecimalDegreesConversionError( errtext )
                    
                # assign the point to the shape attribute
                feat = icurse.newRow()
                feat.shape = pnt
                for target_field, source_field in self.field_mapping.items():
                    value = row.get( source_field )
                    
                    #
                    #  if this is TrkType, do a lookup
                    #  because TryType in output featureclass
                    #  is now a SHORT integer Fkey
                    #  so we override it here
                    #  --- Do not need this foreign key look up at the moment ----  
                    #
                    # if source_field == 'TrkType':
                        # override value with lookup
                        # value = self._get_fkey( self.trktype_path, "trktype_code", value )
                        
                    # Convert null values to a nonsense number for dbf file
                    if not value:
                        value = utils.nullDep

                    # set it
                    try:
                        feat.setValue( target_field, value )
                    except Exception:
                        errtext = "Error in input CSV file, row: %s and column: %s" % ( csv_row, target_field )
                        raise SetValueError( errtext )
                        
                try:
                    icurse.insertRow( feat )
                except Exception:
                    errtext = "Error in input CSV file, row: %s" % ( csv_row )
                    raise InsertRowError( errtext )
                    
            del icurse
        