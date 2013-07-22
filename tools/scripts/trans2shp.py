#--------------------------------------------------------------------------
# Tool Name:  ConvertTransectDatatoShapefiles
# Tool Label: Convert Transect Data to Shapefiles
# Source Name: trans2shp.py
# Version: ArcGIS 10.0
# Author: Allison Bailey, Sound GIS and Greg Corradini, ChopShop Geospatial
# For: Washington DNR, Submerged Vegetation Monitoring Program (SVMP)
# Date: February 2007, Modified June 2007, Modified March 2013
# Requires: Python 2.6+
#
# This script converts a set of text files (.csv) containing
# submerged vegetation survey transect data to point shapefiles
# for Washington DNR's Submerged Vegetation Monitoring Program

# Parameters:
# (0) inParentDir -- Parent directory for input files
# (1) inSpatRef -- Spatial Reference for input data
# (2) siteFile -- Full path of text file containing list of sites
# (3) outGDB -- Geodatabase for output point feature classes
# (4) outSpatRef -- Coordinate system for output shapefiles
# (5) veg_code_lookup -- Table that lists all valid veg codes
# (6) sampOccasion_lookup -- Table that includes sampling occasion field
# (7) sampOccasion -- Selected value for sampling occasion

# Directory Structure Notes --
# This script is expecting a directory structure that is
# specific to Washington DNR's SVMP for input.
# The only room for naming changes is 
# the geodatabase name for the output.
# Here are some examples:
#
# Sample input data directory (one folder for each site within a year):
# J:\AQR\DATA\NEARSHOR\VegMon\2006_Field_Season\Site Folders\core006
#
# Sample output data geodatabase ( file or personal geodatabase ):
# (all transect featureclasses stored in one geodatabase, named by year)
# \\Snarf\bss3\work\svmp\fieldwork\site_folders\<geodatabase_name>.gdb\core001_2011_transect_pt

#--------------------------------------------------------------------------

#--------------------------------------------------------------------------
#Imports
#--------------------------------------------------------------------------
import os
import sys
import csv
import re
import arcpy

# Import constants and Utility Functions for SVMP processing
import svmpUtils as utils

# Import the custom Exception class for handling errors
from svmp_exceptions import SvmpToolsError

# Import worker classes
from transect_datasource import TransectDatasource
from transect_csv import TransectCSV

# General message accumulator
def msg(msg):
    arcpy.AddMessage(msg)

    
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
#MAIN

if __name__ == "__main__":
    

    try:
        #  make overwriteOutput ENV = True
        arcpy.env.overwriteOutput = True
        # Create the custom error class
        # and associate it with the arcpy
        e = SvmpToolsError( arcpy )
        # Set some basic defaults for error handling
        e.debug = True
        e.full_tb = True

        #-- Get parameters -----
        # Input Data Parent Directory 
        # Transect ASCII files are located in subdirectories below here
        # Parameter Data Type: Folder, Default: Environment - current workspace
        inParentDir = arcpy.GetParameterAsText(0)
        # Input Data Coordinate System.  Default:  GCS_WGS_1984
        # Parameter Data Type: Spatial Reference
        inSpatRef = arcpy.GetParameter(1)
        # siteFile: Full Path of text file containing list of sites to process
        # Parameter Data Type: File
        siteFile = arcpy.GetParameterAsText(2)
        # outGDB: Output Geodatabase for transect point feature classes. 
        # Parameter Data Type:  Workspace, Filter: Workspace - geodatabases only
        outGDB = arcpy.GetParameterAsText(3) 
        # Ouput Data Coordinate System.  Default:  Default: NAD_1983_HARN_StatePlane_Washington_South_FIPS_4602_Feet
        # Parameter Data Type: Spatial Reference
        outSpatRef = arcpy.GetParameter(4)
        # veg_code_lookup is full path to veg_code table
        # Parameter Data Type: Table
        veg_code_lookup = arcpy.GetParameterAsText(5)
        # sampOccasion_lookup is the table that contains samp_occasion column
        # Only used to derive sampling occasion list for user to select from in parameters box
        # Parameter Data Type: Table
        sampOccasion_lookup = arcpy.GetParameterAsText(6)
        # Sampling occasion for data to be processed
        # Parameter Data Type:  String
        sampOccasion = arcpy.GetParameterAsText(7)
        
        # This section should all be taken care of in the ToolValidator script now
        ##----------------------------------------------------------------------------------
        ##--- CHECK TO MAKE SURE SAMP OCCASION VALUE IS SITE_STATUS.SAMP_OCCASION ----------
        ##----------------------------------------------------------------------------------
        ##
        ##
        ##  user can still submit form when [ ERROR ]: text is set
        ##  in situation where Veg Code table is pointed somewhere where
        ##  site_status table does not exist. So we check for it here
        ## 
        ##
        #if sampOccasion.startswith("[ ERROR ]:"):
            #errtext = "You need to select a sampling occasion from dropdown list"
            #e.call( errtext )
            

        
        ##
        ##
        ##  keep this here for double extra juicy QC
        ##  the user can still change the text value 
        ##  once it's been set so just to make sure, check it
        ##
        ##
        #gdb_lookup = os.path.dirname( veg_code_lookup )
        #sites_status_table = os.path.join( gdb_lookup, 'sites_status' )
        #sites_status_exists = arcpy.Exists( sites_status_table )
        #if sites_status_exists:
            #delimited_field = arcpy.AddFieldDelimiters( sites_status_table, 'samp_occasion' )
            #where_clause = delimited_field + " = " + "'%s'" % sampOccasion
            ##rows = arcpy.SearchCursor( sites_status_table, where_clause="[samp_occasion] = '%s'" % sampOccasion )
            ## Arc 10.0 cannot used named args in SearchCursor
            #rows = arcpy.SearchCursor( sites_status_table, where_clause)
            #row = rows.next()
            #if not row:
                #errtext = "The table %s has no samp_occasion = '%s'\n...Please enter a new sampling occasion" % ( sites_status_table, sampOccasion )
                #e.call( errtext ) 
        #else:
            #errtext = "The sites_status table does not exist at path %s" % sites_status_table
            #e.call( errtext ) 
            
                

        #----------------------------------------------------------------------------------
        #--- END MAKE SURE SAMP OCCASION VALUE IS IN SITE_STATUS.SAMP_OCCASION ------------
        #----------------------------------------------------------------------------------

        #-------------------------------------------------------------------
        #--- CHECK FOR PRESENCE OF INPUT/OUTPUT DIRECTORIES AND FILES ------
        #-------------------------------------------------------------------
        
        # Get list of subdirectories within input data parent directory
        inSubDirList = utils.make_subDirList(inParentDir)           
        # Get site list from input text file
        siteList = utils.make_siteList(siteFile)
        
        # Create list of output transect files and output feature classes
        # and check for existence of input file
        msg('List of sites to process:\n%s' % '\n'.join(siteList))
        msg('Checking for input directories and transect files')
        sites_to_process = []
        missingTransFile = []
        for site in siteList:      
            # Construct input dirs
            inDir = os.path.join(inParentDir, site)
            # Input transect file names is unique site ID plus suffix/extension of TD.csv
            fullTransFile = os.path.join(inDir, '%s%s' % (site,utils.transFileSuffix))
            # Validate table/fc name, incase there are funky characters in input
            outFC = arcpy.ValidateTableName('%s_%s%s' % (site, sampOccasion,utils.ptFCSuffix ))
            # Make list of transect files, output directories, output feature class, and site name
            sites_to_process.append([fullTransFile,outGDB,outFC,site])
            # Validate presence of input transect file
            if not os.path.isfile(fullTransFile):
                missingTransFile.append(fullTransFile)
        
        # Compare site list to directory lists (in and out) to check for folder and file existence
        missingInDir = [d for d in siteList if d not in inSubDirList]
        errtext = ""
        if missingInDir or missingTransFile:
            if missingInDir:
                errtext += "INPUT directory(ies) not found:\n%s\n%s\n" % ('/'.join((inParentDir,"*")),'\n'.join(missingInDir)) 
            if missingTransFile:
                errtext += "TRANSECT file(s) not found:\n%s" % '\n'.join(missingTransFile)
            e.call(errtext)
            
        #-----------------------------------------------------------------------
        #--- END CHECK FOR PRESENCE OF INPUT/OUTPUT DIRECTORIES AND FILES ------
        #-----------------------------------------------------------------------
        
        msg("Processing %s site(s) requested in '%s'" % (len(siteList),siteFile))
        # Now loop through and process sites
        for path in sites_to_process:
            fullTransFile,outGDB,outFC,site  = path[0],path[1],path[2],path[3]
            msg("-------- SITE ID: %s --------" % site)
            try:
                transect_csv = TransectCSV( fullTransFile, inSpatRef, veg_code_lookup )
                msg("Converting Site: '%s'" % site)              
                datasource = TransectDatasource( outGDB, outFC, outSpatRef, transect_csv )         
                datasource.write_output()
            except Exception, err:
                #
                #
                #  this catches all errors in general
                #  and prints out the error message
                #  because we aren't doing anything
                #  specific with errors such as 
                #  MissingFields when caught
                #  although we could
                #
                #
                e.call( err )
    except SystemExit:
        pass
    except:
        e.call()