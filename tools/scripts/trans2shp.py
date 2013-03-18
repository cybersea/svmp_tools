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
# (1) inParentDir -- Parent directory for input files
# (2) inCoordSys -- Coordinate system for input data
# (3) siteFile -- Full path of text file containing list of sites
# (4) outParentDir -- Parent directory for output files
# (5) outCoordSys -- Coordinate system for output shapefiles
# (6) surveyYear -- Survey year for data to be processed
# (7) veg_code -- Table path that points to veg_code
# (8) trktype_code -- Table path that points to trktype_code

# Directory Structure Notes --
# This script is expecting a directory structure that is
#   specific to Washington DNR's SVMP it looks as follows:
# Sample input data directory (one folder for each site within a year):
# J:\AQR\DATA\NEARSHOR\VegMon\2006_Field_Season\Site Folders\core006
# Sample output data geodatabase:
# (all transect featureclasses stored in one geodatabase, named by year)
# \\Snarf\bss3\work\svmp\fieldwork\site_folders\core006\video_transect_data

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

# our worker classes
from transect_datasource import TransectDatasource
from transect_csv import TransectCSV

def msg(msg):
    arcpy.AddMessage(msg)

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
        # outParentDir: Output Data Parent Directory.  Default: Environment - scratch workspace
        # siteFile: Full Path of text file containing list of sites to process
        inParentDir,siteFile,outParentDir = get(0),get(2),get(3) 
        # Input Data Coordinate System.  Default:  GCS_WGS_1984
        # Ouput Data Coordinate System.  Default:  Default: NAD_1983_HARN_StatePlane_Washington_South_FIPS_4602_Feet
        # Survey Year for data to be processed
        inCoordSys,outCoordSys, surveyYear = arcpy.GetParameter(1),arcpy.GetParameter(4),get(5)
        
        veg_code_lookup, trktype_code_lookup = get(6),get(7)

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
        msg('Checking for input directories, transect files, and output directories')
        sites_to_process = []
        missingTransFile = []
        for site in siteList:      
            # Construct input dirs
            inDir = os.path.join(inParentDir, site)
            # Construct output dirs
            outDir = os.path.join( outParentDir ) #os.path.join(outParentDir,site) #utils.ptShpSubDir)
            # Input transect file names is unique site ID plus suffix/extension of TD.csv
            fullTransFile = os.path.join(inDir, '%s%s' % (site,'TD.csv'))
            outFC = '_%s_%s%s' % (surveyYear,site, os.path.splitext( utils.ptShpSuffix )[0] )
            # Make list of transect files, output directories, output feature class, and site name
            sites_to_process.append([fullTransFile,outDir,outFC,site])
            # Validate presence of input transect file
            if not os.path.isfile(fullTransFile):
                missingTransFile.append(fullTransFile)
        
        # Compare site list to directory lists (in and out) to check for folder and file existence
        missingInDir = [d for d in siteList if d not in inSubDirList]
        missingOutDir = [] #[d for d in siteList if d not in outSubDirList]  
        errtext = ""
        if missingInDir or missingOutDir or missingTransFile:
            if missingInDir:
                errtext += "INPUT directory(ies) not found:\n%s\n%s\n" % ('/'.join((inParentDir,"*")),'\n'.join(missingInDir)) 
            if missingOutDir:
                errtext += "OUTPUT directory(ies) not found:\n%s\n%s\n" % ('/'.join((outParentDir,"*",utils.ptShpSubDir)),'\n'.join(missingOutDir))
            if missingTransFile:
                errtext += "TRANSECT file(s) not found:\n%s" % '\n'.join(missingTransFile)
            e.call(errtext)
            
        #-----------------------------------------------------------------------
        #--- END CHECK FOR PRESENCE OF INPUT/OUTPUT DIRECTORIES AND FILES ------
        #-----------------------------------------------------------------------
        
        msg("Processing %s site(s) requested in '%s'" % (len(siteList),siteFile))
        # Now loop through and process sites
        for path in sites_to_process:
            fullTransFile,outDir,outFC,site  = path[0],path[1],path[2],path[3]
            msg("-------- SITE ID: %s --------" % site)
            try:
                transect_csv = TransectCSV( fullTransFile, inCoordSys, veg_code_lookup )
                msg("Converting Site: '%s'" % site)              
                datasource = TransectDatasource( outDir, outFC, trktype_code_lookup, outCoordSys, transect_csv )         
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