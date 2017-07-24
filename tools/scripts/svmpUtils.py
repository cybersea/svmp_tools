__author__ = 'Allison Bailey, Sound GIS'
# svmpUtils.py
# 7/20/2017
# Developed in ArcGIS provided Python 2.7, NumPy 1.9.3, Pandas 0.16.1
# ArcGIS version 10.4.1

# This module contains shared functions and constants that are used
# with the SVMP Site Transect Analysis Tools

import arcpy
#---------------------------- CONSTANTS -----------------------------------#
# Columns
vegcodeCol = 'veg_code'
visityearCol = 'visit_year'
sampselCol = 'samp_sel'
studycodeCol = 'study_code'
sitevisitidCol = 'site_visit_id'

#Tables
vegcodesTbl = 'veg_codes'
sitevisitsTbl = 'site_visits'
sitesamplesTbl = 'site_samples'
studyassociationsTbl = 'study_associations'
transectsTbl = 'transects'
surveysTbl = 'surveys'
vegoccurTbl = 'veg_occur'

#Feature Classes
samppolyFC = 'samp_polygons'


def unique_values(table, field):
    # Get list of all unique values in a field
    # search cursor wrapped in list generator creating list of all values
    values = (row[0] for row in arcpy.da.SearchCursor(table, (field)))
    # pass list into set to get only unique values and return the result
    return sorted(set(values))

def tables_list(gdb):
    # Get list of tables in a geodatabase
    #Save initial state of workspace
    initial_ws = arcpy.env.workspace

    #change workspace to input geodatabase
    arcpy.env.workspace = gdb
    tables = arcpy.ListTables()
    #reset workspace back to original
    arcpy.env.workspace = initial_ws

    return tables

def fcs_list(gdb):
    # Get list of tables in a geodatabase
    #Save initial state of workspace
    initial_ws = arcpy.env.workspace

    #change workspace to input geodatabase
    arcpy.env.workspace = gdb
    fcs = arcpy.ListFeatureClasses()
    #reset workspace back to original
    arcpy.env.workspace = initial_ws

    return fcs