#--------------------------------------------------------------------------
# Tool Name:  ConvertTransectDatatoShapefiles
# Tool Label: Convert Transect Data to Shapefiles
# Source Name: trans2shp.py
# Version: ArcGIS 9.2
# Author: Allison Bailey, Sound GIS
# For: Washington DNR, Submerged Vegetation Monitoring Program (SVMP)
# Date: February 2007, Modified June 2007
# Requires: Python 2.4
#
# This script converts a set of text files (.csv) containing
# submerged vegetation survey transect data to point shapefiles
# for Washington DNR's Submerged Vegetation Monitoring Program

# Parameters:
# (1) inParentDir -- Parent directory for input files
# (2) inCoordSys -- Coordinate system for input data
# (3) siteFile -- Full path of text file containing list of sites
# (4) outParentDir -- Parent directory for output files
# (5) outCoordSys -- Coordinate system for output shapefiles
# (6) surveyYear -- Survey year for data to be processed

# Directory Structure Notes --
# This script is expecting a directory structure that is
#   specific to Washington DNR's SVMP it looks as follows:
# Sample input data directory (one folder for each site within a year):
# J:\AQR\DATA\NEARSHOR\VegMon\2006_Field_Season\Site Folders\core006
# Sample output data directory:
# (all transect shapefiles stored in one directory, named by year)
# \\Snarf\bss3\work\svmp\fieldwork\site_folders\core006\video_transect_data

#--------------------------------------------------------------------------

#--------------------------------------------------------------------------
#Imports
#--------------------------------------------------------------------------
import os
import sys
import csv
import arcgisscripting

# Import constants and Utility Functions for SVMP processing
import svmpUtils as utils

# Import the custom Exception class for handling errors
from svmp_exceptions import SvmpToolsError

STEP = 1
def msg(msg):
    global STEP
    #msg = 'Step %s: %s...' % (STEP,msg)
    gp.AddMessage(msg)
    STEP += 1

#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Add Data Fields to Feature Class
# Assumes order of field definitions same as AddField geoprocessing tool
# Requires a list of lists with field definitions
def addDatFields(cols,FC):
    fnames = []
    for col in cols:
        if col:
            fname = col[0]
            ftype = col[1]
            fprecision = col[2]
            fscale = col[3]
            flength = col[4]
            gp.addfield(FC,fname,ftype,fprecision,fscale,flength)
            fnames.append(fname)
    return fnames

def test_csv(csv_input):
    """Test opening a CSV File
    """
    csv_file = open(csv_input,'rbU')
    csv_reader = csv.DictReader(csv_file)  # use this instead
    cols = csv_reader.reader.next()
    
    # Compare CSV column headers to list of required headers
    # to identify missing fields
    missingFields = [f for f in utils.sourceCols if f not in cols] 
    if missingFields:
        errtext = "The CSV file, '%s' is missing columns:\n%s" % (os.path.basename(csv_input), '\n'.join(missingFields))
        e.call(errtext)
        
    csv_file.close()

        
def get(idx):
    return gp.GetParameterAsText(idx)
          
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
#MAIN

if __name__ == "__main__":

    try:

        # Create the geoprocessing object
        gp = arcgisscripting.create()
        # Overwrite existing output data (for testing only?)
        gp.OverWriteOutput = 1

        # Create the custom error class
        # and associate it with the gp
        e = SvmpToolsError(gp)
        # Set some basic defaults for error handling
        e.debug = True
        e.full_tb = True

        #-- Get parameters -----
        # Input Data Parent Directory 
        # Transect ASCII files are located in subdirectories below here
        #  Default: Environment - current workspace
        # outParentDir: Output Data Parent Directory.  Default: Environment - scratch workspace
        # siteFile: Full Path of text file containing list of sites to process
        inParentDir,siteFile,outParentDir = get(0),get(2),get(3)  
        # Input Data Coordinate System.  Default:  GCS_WGS_1984
        # Ouput Data Coordinate System.  Default:  Default: NAD_1983_HARN_StatePlane_Washington_South_FIPS_4602_Feet
        # Survey Year for data to be processed
        inCoordSys,outCoordSys, surveyYear = get(1),get(4),get(5)

        #--- CHECK FOR PRESENCE OF INPUT/OUTPUT DIRECTORIES AND FILES ------
        #-------------------------------------------------------------------
        # Get list of subdirectories within input data parent directory
        inSubDirList = utils.make_subDirList(inParentDir)
        # Get list of subdirectories in output parent directory
        outSubDirList = utils.make_subDirList(outParentDir)
        # Find out if the output site directories have the subdirectory for transect data
        outSubDirList[:] = [d for d in outSubDirList if os.path.isdir(os.path.join(outParentDir,d,utils.ptShpSubDir))]
                      
        # Get site list from input text file
        siteList = utils.make_siteList(siteFile)
        
        # Create list of output transect files and output feature classes
        # and check for existence of input file
        msg('List of sites to process:\n%s' % '\n'.join(siteList))
        msg('Checking for input directories, transect files, and output directories')
        sites_to_process = []
        missingTransFile = []
        for site in siteList:      
            # Construct input dirs
            inDir = os.path.join(inParentDir, site)
            # Construct output dirs
            outDir = os.path.join(outParentDir,site,utils.ptShpSubDir)
            # Input transect file names is unique site ID plus suffix/extension of TD.csv
            fullTransFile = os.path.join(inDir, '%s%s' % (site,'TD.csv'))
            outFC = '%s_%s%s' % (surveyYear,site,utils.ptShpSuffix)
            # Make list of transect files, output directories, output feature class, and site name
            sites_to_process.append([fullTransFile,outDir,outFC,site])
            # Validate presence of input transect file
            if not os.path.isfile(fullTransFile):
                missingTransFile.append(fullTransFile)
        
        # Compare site list to directory lists (in and out) to check for folder and file existence
        missingInDir = [d for d in siteList if d not in inSubDirList]
        missingOutDir = [d for d in siteList if d not in outSubDirList]  
        errtext = ""
        if missingInDir or missingOutDir or missingTransFile:
            if missingInDir:
                errtext += "INPUT directory(ies) not found:\n%s\n%s\n" % ('/'.join((inParentDir,"*")),'\n'.join(missingInDir)) 
            if missingOutDir:
                errtext += "OUTPUT directory(ies) not found:\n%s\n%s\n" % ('/'.join((outParentDir,"*",utils.ptShpSubDir)),'\n'.join(missingOutDir))
            if missingTransFile:
                errtext += "TRANSECT file(s) not found:\n%s" % '\n'.join(missingTransFile)
            e.call(errtext)
        #--- END CHECK FOR PRESENCE OF INPUT/OUTPUT DIRECTORIES AND FILES ------
        #-----------------------------------------------------------------------
            
        # Create input Spatial Reference for use in Cursor
        msg('Fetching Spatial Reference')
        inSpatialRef = utils.make_spatRef(gp,outParentDir,inCoordSys)
        
        msg("Processing %s site(s) requested in '%s'" % (len(siteList),siteFile))
        # Now loop through and process sites
        for path in sites_to_process:
            fullTransFile,outDir,outFC,site  = path[0],path[1],path[2],path[3]
            msg("-------- SITE ID: %s --------" % site)
            outFCFull = os.path.join(outDir,outFC)
            
            if os.path.exists(fullTransFile):
                # Test opening with lightwight validation
                test_csv(fullTransFile)
                msg("CSV file, '%s', found and opened successfully" % os.path.basename(fullTransFile))
            else:
                e.call("CSV file '%s' cannot be found" % fullTransFile)

            msg("Converting Site: '%s'" % site)
            
            # Now let's truly open the file for processing
            reader = csv.DictReader(open(fullTransFile,'rbU'))  
            
            # Create an empty feature class for the shapefile
            
            # in 9.2, TestSchemaLock returns a string ('TRUE','FALSE','ERROR'), not a true Boolean
            # Also, in 9.2, there is a bug, so it works outside ArcCatalog/ArcMap, but not within
            # In 9.2, it just dies without any sort of error indication -- says it was successful - Yuck
            # This workaround didn't work: http://forums.esri.com/Thread.asp?c=93&f=1729&t=251511#774023
            #gp.workspace = os.path.dirname(outFCFull)
            #schemaTest = 'TRUE'
            #if os.path.exists(outFCFull):
                #msg("Feature class already exists")
                ##schemaTest = gp.TestSchemaLock(outFCFull)
                #schemaTest = gp.TestSchemaLock(outFC)
            #if schemaTest == 'TRUE':
            # Can't use schema Lock test in 9.2, therefore, if it can't create out FC, just give suggestions
            # This section would be further indented within an if/else for Schema Lock test if it worked
            try: 
                # Create Feature class and add fields
                fc = gp.CreateFeatureClass(outDir,outFC,"POINT","#","#","#",outCoordSys)
                # Add Fields to the feature class
                fieldnames = addDatFields(utils.trkPtShpCols,outFCFull)
                msg("Created Feature Class: '%s'" % outFC)
            except:
                # <class 'pywintypes.com_error'>: (-2147467259, 'Unspecified error', None, None)
                # schema lock error shows up automatically
                errtext = "Unable to create feature class: '%s' or unable to add fields" % outFCFull
                #errtext = "Unable to obtain schema lock for:\n%s" % outFCFull
                errtext += "\nTry closing ArcMap, or other applications that may be accessing these data."
                errtext += "\nIf you are viewing the data in ArcCatalog, change directories and choose 'Refresh' under the 'View' menu."
                errtext += "\nYou can also try deleting the existing shapefile manually from the file system."
                e.call(errtext)
            #else:
                #errtext = "Unable to obtain schema lock for:\n%s" % outFCFull
                #errtext += "\nTry closing ArcMap, or other applications that may be accessing these data."
                #errtext += "\nIf you are viewing the data in ArcCatalog, \nchange directories and choose 'Refresh' under the 'View' menu."
                #e.call(errtext)

            # Create Update Cursor, with input spatial reference info
            # Allows projection on the fly from source data to output shapefile
            cur = gp.InsertCursor(outFCFull,inSpatialRef)
            pnt = gp.CreateObject("Point")

            msg("Populating data table of '%s'" % outFC)
            for idx, row in enumerate(reader):
                # Convert and create the geometries
                csv_row = idx + 2
                pnt.Id = idx + 1
                lon,lat = row[utils.sourceLonCol],row[utils.sourceLatCol]
                # convert lat/long values in csv file to decimal degrees
                try:
                    pnt.x = utils.dm2dd(lon)
                except:
                    errtext = "Unable to convert source longitude, %s, to decimal degree format" % lon
                    errtext += "\nCSV file, %s\nrow: %s" % (fullTransFile, csv_row)
                    e.call(errtext)
                try:                  
                    pnt.y = utils.dm2dd(lat)
                except:
                    errtext = "Error converting source latitude, %s, to decimal degree format" % lat
                    errtext += "\nCSV file, %s\nrow: %s" % (fullTransFile, csv_row)
                    e.call(errtext)                    
                # Create the features
                feat = cur.NewRow()
                # Assign the point to the shape attribute
                feat.shape = pnt
                feat.Id = idx + 1
                # Collect and assign Feature attributes
                for field in fieldnames:
                    csv_field_name = utils.mapping[field]
                    value = row.get(csv_field_name)
                    # Convert null values to a nonsense number for dbf file
                    if not value:
                        value = utils.nullDep
                    # Catch erroneous data types here (string in a numeric type)
                    try:
                        feat.SetValue(field,value)
                    except:
                        errtext = "Error in input CSV file, row: %s and column: %s" % (csv_row,field)
                        e.call(errtext)
                try:
                    cur.InsertRow(feat)
                except:
                    errtext = "Error in input CSV file row: %s" % (csv_row)
                    e.call(errtext)
            del cur         

    except SystemExit:
        pass
    except:
        e.call()
        del gp