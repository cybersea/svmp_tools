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
#  app imports
#
#
from transect_csv import TransectCSV
import svmpUtils as utils


class TransectDatasource( object ):
    
    def __init__( self, target_path, target_name, trktype_path, output_spatial_ref, transect_csv_object ):
        '''
        a geo datasource class that hasA TransetCSV object
        it can read the TransectCSV 
        and write it to a datasource
        ----------------------------------------------------
        < target_path >  : datasource dirname() for target_name ( featureclass )
        < target_name >  : name of the featureclass
        < trktype_path > : full path to the trktype_code table
        < transect_csv_object > : an instance of TransectCSV
        < output_spatial_ref > : the arcpy.SpatialReference of the target datasource
        '''
        
        self.target_path = target_path  # dirname( target_name )
        self.target_name = target_name  # featureclass name 
        self.trktype_path = trktype_path 
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
        self.trkCol = 'tran_num' # to match final database column name, changed from trk to tran_num
        self.ptShpSubDir = 'video_transect_data'  # output subdirectory for point shapefile
        self.ptShpSuffix = '_transect_data.shp'  # suffix for output point shapefile     
        self.shpDepCol = 'BSdepIntrp' # Interpolated Biosonics Depth column
        self.shpDateCol = 'date_samp'  # Column with date of survey       
        self.time24hr = 'Time24hr'
        self.bsdepth = 'BSdepth'
        self.other = 'other'
        self.videoCol = 'video'  # Column for video data quality (0,1)
        self.realtime = 'realtime'
        self.trktype = 'TrkType'
        
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
        self._add_featureclass_fields()
        
    
    def _get_fields( self ):
        '''
        note this data structure also preserves field order
        '''
        return [ 
                
            [ self.trkCol,'LONG','#','#','#' ],
            [ self.shpDateCol,'DATE','#','#','#' ],
            [ self.time24hr,'TEXT','#','#','11' ],
            [ self.bsdepth,'DOUBLE','9','2','#' ],
            [ self.shpDepCol,'DOUBLE','9','2','#' ],
            [ self.other,'SHORT','#','#','#' ],
            [ self.videoCol,'SHORT','#','#','#' ],
            [ self.realtime,'SHORT','#','#','#' ],
            [ self.trktype,'SHORT','#','#','#' ],
            [],
            []
            
        ]
        
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
        Here we use this informaiton 
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
            self.insert_fields = self._get_fields()
                      
            #
            #
            #  add veg_code fields 
            #  to this TransectDatasource
            #  we insert them before
            #  'other' column here
            #  because we do not have
            #  any other option yet
            #   
            #
            for field in self.transect_csv.veg_code_fields:               
                insert_indx = self.insert_fields.index( ['other','SHORT','#','#','#'] )
                self.insert_fields.insert( insert_indx, field )
                
                
    def _create_featureclass( self ):
        arcpy.CreateFeatureclass_management( self.target_path, self.target_name, "POINT","#","#","#", self.output_spatial_ref )
        
    def _add_featureclass_fields( self ):
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
        search_string = ""
        if isinstance( lookup_value, int ):
            search_string = "[%s] = %s"
        elif isinstance( lookup_value, str ):
            search_string = "[%s] = '%s'"
        search_string = search_string %( lookup_key, str( lookup_value ) )
      
      
        scurse = arcpy.SearchCursor( path, where_clause=search_string )
        row = scurse.next()
        if not row:
            errtext = "You tried to do a Fkey lookup '%s' on table [ %s ] and it does not exist" % ( self.full_output_path, search_string )
            raise Exception( errtext )         
        fkey = row.getValue( "OBJECTID" )
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
            for idx, row in enumerate(reader):
                # Convert and create the geometries
                #csv_row = idx + 2
                pnt.ID = idx + 1
                lon,lat = row[ self.transect_csv.sourceLonCol ],row[ self.transect_csv.sourceLatCol ]
                # convert lat/long values in csv file to decimal degrees            
                pnt.X = utils.dm2dd(lon)                 
                pnt.Y = utils.dm2dd(lat)
                feat = icurse.newRow()
                # assign the point to the shape attribute
                feat.shape = pnt
                for target_field, source_field in self.field_mapping.items():
                    value = row.get( source_field )
                    
                    #
                    #  if this is TrkType, do a lookup
                    #  because TryType in output featureclass
                    #  is now a SHORT integer Fkey
                    #  so we override it here
                    #
                    if source_field == 'TrkType':
                        # override value with lookup
                        value = self._get_fkey( self.trktype_path, "trktype_code", value )
                        
                    # Convert null values to a nonsense number for dbf file
                    if not value:
                        value = utils.nullDep

                    # set it
                    feat.setValue( target_field, value )

                icurse.insertRow( feat )
            del icurse
        