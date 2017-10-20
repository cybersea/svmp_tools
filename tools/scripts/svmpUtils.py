__author__ = 'Allison Bailey, Sound GIS'
# svmpUtils.py
# 7/20/2017
# Developed in ArcGIS provided Python 2.7, NumPy 1.9.3, Pandas 0.16.1
# ArcGIS version 10.4.1

# This module contains shared functions and constants that are used
# with the SVMP Site Transect Analysis Tools

import arcpy
import numpy as np
#---------------------------- CONSTANTS -----------------------------------#
# Columns
vegcodeCol = 'veg_code'
visityearCol = 'visit_year'
sampselCol = 'samp_sel'
sampstatCol = 'samp_status'
studycodeCol = 'study_code'
sitevisitidCol = 'site_visit_id'
sitecodeCol = 'site_code'
sampidCol = 'site_samp_id'
datesampCol = 'date_samp_start'
transectidCol = 'transect_id'
surveyidCol = 'survey_id'
surveystatCol = 'survey_status'
maxdepflagCol = 'tran_maxd_qual'
mindepflagCol = 'tran_mind_qual'
datetimesampCol = 'date_time_samp'
depInterpCol = 'depth_interp'
videoCol = 'video'
ptidCol = 'ID'

#Tables
vegcodesTbl = 'veg_codes'
sitevisitsTbl = 'site_visits'
sitesamplesTbl = 'site_samples'
studyassociationsTbl = 'study_associations'
transectsTbl = 'transects'
surveysTbl = 'surveys'
vegoccurTbl = 'veg_occur'
segmentsTbl = 'segments'

#Feature Classes
samppolyFC = 'samp_polygons'

NULL_DEPTH = -9999
NULL_VEG = -9999
NULL_VIDEO = -9999


# Spatial Reference
sr = arcpy.SpatialReference(2927) # NAD_1983_HARN_StatePlane_Washington_South_FIPS_4602_Fee

# Filter for Sample Status -- only these are used for statistics calcs
sampstat4stats = ["sampled","exception"]


def unique_values(table, field):
    # Get list of all unique values in a field
    # search cursor wrapped in list generator creating list of all values
    values = (row[0] for row in arcpy.da.SearchCursor(table, (field)))
    # pass list into set to get only unique values and return the result
    return sorted(set(values))

def unique_values_np(table, field):
    data = arcpy.da.TableToNumPyArray(table, [field])
    return np.unique(data[field])

def tables_fcs_list(gdb):
    # Get list of tables and feature classes in a geodatabase
    #Save initial state of workspace
    initial_ws = arcpy.env.workspace

    #change workspace to input geodatabase
    arcpy.env.workspace = gdb
    tables = arcpy.ListTables()
    fcs = arcpy.ListFeatureClasses()
    #reset workspace back to original
    arcpy.env.workspace = initial_ws

    return {"tables":tables,"fcs":fcs,"both":tables + fcs}


def fieldExists(dataset, field_name):
    if field_name in [field.name for field in arcpy.ListFields(dataset)]:
        return True