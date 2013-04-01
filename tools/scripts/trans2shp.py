#--------------------------------------------------------------------------
# Tool Name:  ConvertTransectDatatoShapefiles
# Tool Label: Convert Transect Data to Shapefiles
# Source Name: trans2shp.py
# Version: ArcGIS 10.x
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
# (1) inCoordSys -- Coordinate system for input data
# (2) siteFile -- Full path of text file containing list of sites
# (3) outGDB -- Parent directory for output files
# (4) outCoordSys -- Coordinate system for output shapefiles
# (5) veg_code -- Table path that points to veg_code for lookups
# (6) surveyYear -- Survey year for data to be processed

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

# Wrapper for GetParametersAsText
def get(idx):
    return arcpy.GetParameterAsText(idx)
          
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
        #  Default: Environment - current workspace
        # outGDB: Output Geodatabase.  Default: Environment - scratch workspace
        # siteFile: Full Path of text file containing list of sites to process
        inParentDir,siteFile,outGDB = get(0),get(2),get(3) 
        # Input Data Coordinate System.  Default:  GCS_WGS_1984
        # Ouput Data Coordinate System.  Default:  Default: NAD_1983_HARN_StatePlane_Washington_South_FIPS_4602_Feet
        inCoordSys,outCoordSys = arcpy.GetParameter(1),arcpy.GetParameter(4)
        # veg_code_lookup is full path to veg_code table
        # Survey Year for data to be processed
        veg_code_lookup,surveyYear = get(5),get(6)
        
        #----------------------------------------------------------------------------------
        #--- CHECK TO MAKE SURE SAMP OCCASION VALUE IS SITE_STATUS.SAMP_OCCASION ----------
        #----------------------------------------------------------------------------------
        gdb_lookup = os.path.dirname( veg_code_lookup )
        sites_status_table = os.path.join( gdb_lookup, 'sites_status' )
        sites_status_exists = arcpy.Exists( sites_status_table )
        if sites_status_exists:
            rows = arcpy.SearchCursor( sites_status_table, where_clause="[samp_occasion] = '%s'" % surveyYear )
            row = rows.next()
            if not row:
                errtext = "The table %s has no samp_occasion year = '%s'...please submit a new samp occasion year" % ( sites_status_table, surveyYear )
                e.call( errtext ) 
        else:
            errtext = "The sites_status table does not exist at path %s" % sites_status_table
            e.call( errtext ) 
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
            outFC = '%s_%s%s' % (site, surveyYear,utils.ptShpSuffix )
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
                transect_csv = TransectCSV( fullTransFile, inCoordSys, veg_code_lookup )
                msg("Converting Site: '%s'" % site)              
                datasource = TransectDatasource( outGDB, outFC, outCoordSys, transect_csv )         
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