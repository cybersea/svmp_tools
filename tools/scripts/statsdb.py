__author__ = 'Allison Bailey, Sound GIS'
# statsdb.py
# 8/4/2017
# Calculate site and transect results and populate geodatabase tables
#   site_results, transect_results
# Developed in ArcGIS provided Python 2.7, NumPy 1.9.3, Pandas 0.16.1
# ArcGIS version 10.4.1

import numpy as np
import pandas as pd
import svmpUtils as utils
import arcpy
import os

def timeStamped(fname, fmt='{fname}_%Y%m%d_%H%M%S.csv'):
    # Create time stamped filename
    return datetime.datetime.now().strftime(fmt).format(fname=fname)

def make_sitelist(sites_file):
    # Get all lines from input file without leading or trailing whitespace
    # and omit lines that are just whitespace
    site_list = [line.strip() for line in open(sites_file,'r') if not line.isspace()]
    return site_list

# General message accumulator
def msg(msg):
    arcpy.AddMessage(msg)

class Sample(object):
    """ Represents an individual Site Sample

    Properties:
    id -- sample identifier (site_samp_id)
    site_code -- site code
    site_visit_id -- identifier for the site visit (site_visit_id)
    study_codes -- list of study codes that a sample is associated with (study_code)
    samp_sel -- sample selection method for the sample
    sample_poly -- sample polygon
    transects -- transects associated with the sample

    """

    def __init__(self, id):
        self.id = id

class Transect(object):
    """ Represents an individual Transect

    Properties:
    id -- transect identifier (transect_id)
    sample_id -- associated sample identifier (site_samp_id)
    surveys -- surveys that make up the transect
    maxdepflag -- maximum depth flag
    mindepflag -- minimum depth flag

    """

class Survey(object):
    """ Represents an individual Survey

    Properties:
    id -- survey identifier
    maxdepflag -- maximum depth flag
    mindepflag -- minimum depth flag

    """

class SamplePoly(object):
    """ Represents and individual sample polygon

    Properties:
    id -- sample polygon identifier (site_samp_id)

    """

def print_params(params):
    # Print out the the list of parameters
    for param in params:
        if param:
            msg(param)

class Table(object):
    """ Represents a source SVMP data table
    table -- the table as full geodatabase path
    fields -- list of fields included in data frame of table
    query -- optional query from table when creating data frame
    df -- the table as dataframe
    exists -- flag for existence of the table
    """

    def __init__(self, gdb, tbl, flds, qry=""):
        self.table = os.path.normpath(os.path.join(gdb, tbl))
        self.fields = flds
        self.query = qry
        self.df = self._create_df()

    @property
    def exists(self):
        if arcpy.Exists(self.table):
            return True
        else:
            return False

    def _create_df(self):
        if self.exists:
            nparray = arcpy.da.TableToNumPyArray(self.table, self.fields, self.query)
            return pd.DataFrame(nparray)
        else:
            return None


def make_sampleList(svmp_gdb, survey_year, sites_file, study, samp_sel):
    pass


def main(transect_gdb, svmp_gdb, stats_gdb, survey_year, veg_code, sites_file, study, samp_sel):
    # Main function to run code

    # For debugging -- print the input parameters
    # print_params([transect_gdb,svmp_gdb,stats_gdb,survey_year,veg_code,sites_file,study,samp_sel])

    # Attributes for SVMP source tables:
    # site_samples, study_associations, transects, segments, surveys, veg_occur
    svmp_table_info = {
        utils.sitesamplesTbl :
            {"fields": [
                utils.sampidCol,
                utils.sitecodeCol,
                utils.datesampCol,
                utils.sampselCol,
                utils.sampstatCol,
                utils.sitevisitidCol,
                ]
            },
        utils.studyassociationsTbl :
            {"fields": [
                utils.sampidCol,
                utils.studycodeCol,
                ]
            },
        utils.transectsTbl:
            {"fields": [
                utils.transectidCol,
                utils.sampidCol,
                utils.sitevisitidCol,
                ]
            },
        utils.segmentsTbl:
            {"fields": [
                utils.transectidCol,
                utils.surveyidCol,
                ]
            },
        utils.surveysTbl:
            {"fields": [
                utils.surveyidCol,
                utils.maxdepflagCol,
                utils.mindepflagCol,
                ]
            },
        utils.vegoccurTbl:
            {"fields": [
                utils.sitevisitidCol,
                veg_code,
                ]
            },
    }


    svmp_tables = {} # Dictionary to hold all the source table objects
    # Create the table objects for each table in the dictionary
    missing_tables = [] # List to identify tables that are missing from the geodatabase
    for table, atts in svmp_table_info.items():
        # Create Table object for each source table in the svmp geodatabase
        svmp_tables[table] = Table(svmp_gdb, table, atts["fields"])
        # If table is missing from geodatabase, add to missing tables list
        if not svmp_tables[table].exists:
            missing_tables.append(table)
        # print svmp_tables[table].table
        # print svmp_tables[table].fields
        # print svmp_tables[table].query
        # print svmp_tables[table].exists
        # print svmp_tables[table].df

    # Error check for missing tables
    if not arcpy.Exists(os.path.normpath(os.path.join(svmp_gdb, utils.samppolyFC))):
        missing_tables.append(utils.samppolyFC)
    if missing_tables:
        print ",".join(missing_tables)

    samples_df = svmp_tables[utils.sitesamplesTbl].df
    print samples_df.describe()
    print samples_df.dtypes
    print samples_df[utils.datesampCol]
    print samples_df[survey_year]
    # print samples_df[samples_df[utils.datesampCol].year]
    # print samples_df[(samples_df.site_visit_id.str.contains(survey_year))]
    # samples_df = samples_df[(samples_df.site_visit_id.str.contains('2015'))]
    # print svmp_tables[utils.sitesamplesTbl].df






    # Get Source Data Tables
    # samples_list = make_sampleList(svmp_gdb,survey_year,veg_code,sites_file,study,samp_sel)



if __name__ == '__main__':

    # Input parameter 1:  Geodatabase with individual transect point data -- REQUIRED
    transect_gdb = "Y:/projects/dnr_svmp2016/data/svmp_pt_data/svmptoolsv4_td2fc_testing_11-15.mdb"

    # Input parameter 2:  SVMP Geodatabase with Base Tables -- REQUIRED
    svmp_gdb = "Y:/projects/dnr_svmp2016/db/SVMP_DB_v5.2_20170815_AB.mdb"

    # Input parameter 3: Site Statistics Geodatabase with Template results tables -- REQUIRED
    stats_gdb = "Y:/projects/dnr_svmp2016/svmp_tools/tools/svmp_db/svmp_sitesdb.mdb"

    # Input parameter 4: Survey Year to be Processed -- REQUIRED
    survey_year = "2015"

    # Input parameter 5: Vegetation Type to be Processed -- REQUIRED
    veg_code = "nativesg"

    # Input parameter 6: List of Sites file -- OPTIONAL
    sites_file = ""

    # Input parameter 7: Study or Studies to Be Processed -- OPTIONAL
    # Returned from ArcToolbox as a semi-colon separated string "CityBham;DNRparks;Elwha"
    study = ""

    # Input parameter 8: Vegetation Type to be Processed -- OPTIONAL
    # Returned from ArcToolbox as a semi-colon separated string "SRS;STR;SUBJ"
    samp_sel = ""

    main(transect_gdb, svmp_gdb, stats_gdb, survey_year, veg_code, sites_file, study, samp_sel)

    # t1 = time.time()
    #
    # print ("Total time elapsed is: %s seconds" %str(t1-t0))