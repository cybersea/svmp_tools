__author__ = 'Allison Bailey, Sound GIS'
# statsdb.py
# 8/4/2017
# Calculate site and transect results and populate geodatabase tables
#   site_results, transect_results
# Developed in ArcGIS provided Python 2.7, NumPy 1.9.3, Pandas 0.16.1
# ArcGIS version 10.4.1

import numpy as np
import datetime
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

class SampleGroup(object):
    """ Represents a group of samples to be processed together



    """

    def __init__(self, in_df, veg_df, stats_group):
        self.in_df = in_df
        self.veg_df = veg_df
        self.stats_group = stats_group



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
    stats_group -- identifies the type of stats to be calculated
        site_transect - calculate site and transect stats
        transect - calculate transect stats only; assign site stats as zero/no data
        none - no transect results; assign site results as zero/no data


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
    surveystat -- survey status
    maxdepflag -- maximum depth flag
    mindepflag -- minimum depth flag

    """

class SamplePoly(object):
    """ Represents an individual sample polygon

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


def filter_samples(samp_df, stdy_df, filter):
    # Filter dataframe of samples using a dictionary of filtering criteria
    # filter for year to process
    samp_df = samp_df[samp_df[utils.datesampCol].dt.year == int(filter["year"])]
    # Filter for samp_status ("sampled" or "exception")
    samp_df = samp_df[samp_df[utils.sampstatCol].isin(filter["samp_status"])]
    # Filter for samp_sel (optional parameter)
    if filter["samp_sel"]:
        samp_df = samp_df[samp_df[utils.sampselCol].isin(filter["samp_sel"])]
    # Filter for study (optional parameter)
    if filter["study_code"]:
        # Filter studies data frame with list of studies
        stdy_df = stdy_df[stdy_df[utils.studycodeCol].isin(filter["study_code"])]
        #samp_df = pd.merge(samp_df, stdy_df, on=utils.sampidCol, how='left')  # example join - not used
        # Select samples that correspond to only those studies
        samp_df = samp_df[samp_df[utils.sampidCol].isin(stdy_df[utils.sampidCol])]
    # Filter for site_code (using optional list of sites file)
    if filter["site_code"]:
        samp_df = samp_df[samp_df[utils.sitecodeCol].isin(filter["site_code"])]

    return samp_df

def paramstr2list(param,delim=";"):
    if param:
        return param.split(";")
    else:
        return []

def make_sitelist(sites_file):
    # Get all lines from input file without leading or trailing whitespace
    # and omit lines that are just whitespace
    site_list = [line.strip() for line in open(sites_file,'r') if not line.isspace()]
    return site_list

# General message accumulator
def msg(msg):
    arcpy.AddMessage(msg)

def main(transect_gdb, svmp_gdb, stats_gdb, survey_year, veg_code, sites_file, study, samp_sel):
    # Main function to run code

    # For debugging -- print the input parameters
    # print_params([transect_gdb,svmp_gdb,stats_gdb,survey_year,veg_code,sites_file,study,samp_sel])

    # Attributes for SVMP source tables:
    # site_samples, study_associations, transects, segments, surveys, veg_occur
    svmp_table_info = {
        utils.sitesamplesTbl:
            {"fields": [
                utils.sampidCol,
                utils.sitecodeCol,
                utils.datesampCol,
                utils.sampselCol,
                utils.sampstatCol,
                utils.sitevisitidCol,
                ]
            },
        utils.studyassociationsTbl:
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
                utils.surveystatCol,
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

    #---------- Filtering Criteria -------------------------------
    # Create lists from optional input parameters
    study_list = paramstr2list(study)
    sampsel_list = paramstr2list(samp_sel)
    if sites_file:
        # Generate list of sites from text file
        site_codes = make_sitelist(sites_file)
    else:
        site_codes = []

    # Dictionary of filters used to select samples to process
    filter = {
        "year" : survey_year,
        "samp_status" : utils.sampstat4stats,
        "site_code" : site_codes,
        "study_code" : study_list,
        "samp_sel" : sampsel_list
    }

    #-----------  Create a dataframe of samples filtered based on User input parameters
    samples_df = filter_samples(svmp_tables[utils.sitesamplesTbl].df, svmp_tables[utils.studyassociationsTbl].df, filter)
    print samples_df

    #-----------  END Filtering based on User input parameters -------------------------------

    # ----------- Create groups of data for transect processing -------------
    vegoccur_df = svmp_tables[utils.vegoccurTbl].df

    samp_vegp = SampleGroup(samples_df, vegoccur_df,"ts")
    # #----------- present
    # # Records from veg_occur table that have the veg_code = "present"
    # vegp_df = vegoccur_df[(vegoccur_df[veg_code].isin(["present"]))]
    # # print vegp_df
    # # Records in samples dataframe that have veg present
    # samples_vegp_df = samples_df[samples_df[utils.sitevisitidCol].isin(vegp_df[utils.sitevisitidCol])]
    # # Narrow to samples that have veg present, and samp_sel <> "SUBJ"
    # samples_vegp_df = samples_vegp_df[~samples_vegp_df[utils.sampselCol].isin(["SUBJ"])]
    # #---------- absent/trace
    # # Records from veg_occur table that have veg_code = "absent" or "trace"
    # vegat_df = vegoccur_df[vegoccur_df[veg_code].isin(["absent","trace"])]
    # # Records from samples dataframe where veg is absent or trace
    # samples_vegat_df = samples_df[samples_df[utils.sitevisitidCol].isin(vegat_df[utils.sitevisitidCol])]
    # # Veg absent/trace and samp_sel = "SUBJ"
    # samples_vegat_subj_df = samples_vegat_df[samples_vegat_df[utils.sampselCol].isin(["SUBJ"])]
    # # print samples_vegat_subj_df
    # # Veg absent/trace and samp_sel <> "SUBJ"
    # samples_vegat_notsubj_df = samples_vegat_df[~samples_vegat_df[utils.sampselCol].isin(["SUBJ"])]
    # # print samples_vegat_notsubj_df
    # # Veg absent/trace and samp_sel <> "SUBJ" with transects
    # transects_df = svmp_tables[utils.transectsTbl].df
    # samples_vegat_notsubj_tsect_df = samples_vegat_notsubj_df[samples_vegat_df[utils.sampidCol].isin(transects_df[utils.sampidCol])]
    # # Veg absent/trace and samp_sel <> "SUBJ" without transects
    # samples_vegat_notsubj_notsect_df = samples_vegat_notsubj_df[~samples_vegat_df[utils.sampidCol].isin(transects_df[utils.sampidCol])]
    #
    # #---- Four groups of samples for stats calcs
    # print samples_vegp_df  # calc transect and site results
    # print samples_vegat_subj_df  # No calcs -- assign zero/no data values in site results
    # print samples_vegat_notsubj_tsect_df # calc transect results, no site results
    # print samples_vegat_notsubj_notsect_df # No calcs -- assign zero/no data values
    #
    # # ----------- END of sample grouping -------------
    #
    # # Grab transects and surveys needed for processing
    # transects_df = svmp_tables[utils.transectsTbl].df
    # segments_df = svmp_tables[utils.segmentsTbl].df
    # surveys_df = svmp_tables[utils.surveysTbl].df
    # # --- transects and surveys associated with veg present samples
    # transects_vegp_df = transects_df[transects_df[utils.sampidCol].isin(samples_vegp_df[utils.sampidCol])]
    # print transects_vegp_df
    # segments_vegp_df = segments_df[segments_df[utils.transectidCol].isin(transects_vegp_df[utils.transectidCol])]
    # print segments_vegp_df
    # surveys_vegp_df = surveys_df[surveys_df[utils.surveyidCol].isin(segments_vegp_df[utils.surveyidCol])]
    # print surveys_vegp_df
    # # remove survey_stats <> 'surveyed'
    # surveys_vegp_df = surveys_vegp_df[surveys_vegp_df[utils.surveystatCol].isin(["surveyed"])]
    # print surveys_vegp_df
    #
    # # ---- transects and surveys associated with veg absent, non-SUBJ samples
    # transects_vegat_notsubj_df = transects_df[transects_df[utils.sampidCol].isin(samples_vegat_notsubj_tsect_df[utils.sampidCol])]
    # print transects_vegat_notsubj_df
    # segments_vegat_notsubj_df = segments_df[segments_df[utils.transectidCol].isin(transects_vegat_notsubj_df[utils.transectidCol])]
    # print segments_vegat_notsubj_df
    # surveys_vegat_notsubj_df = surveys_df[surveys_df[utils.surveyidCol].isin(segments_vegat_notsubj_df[utils.surveyidCol])]
    # print surveys_vegat_notsubj_df
    # # remove survey_stats <> 'surveyed'
    # surveys_vegat_notsubj_df = surveys_vegat_notsubj_df[surveys_vegat_notsubj_df[utils.surveystatCol].isin(["surveyed"])]
    # print surveys_vegat_notsubj_df
    #
    #





    # Get Source Data Tables
    # samples_list = make_sampleList(svmp_gdb,survey_year,veg_code,sites_file,study,samp_sel)



if __name__ == '__main__':

    # Input parameter 1:  Geodatabase with individual transect point data -- REQUIRED
    # transect_gdb = "Y:/projects/dnr_svmp2016/data/svmp_pt_data/svmptoolsv4_td2fc_testing_11-15.mdb"
    transect_gdb = "Y:/projects/dnr_svmp2016/data/svmp_pt_data/svmptoolsv4_td2fc_testing_2014_2015.mdb"

    # Input parameter 2:  SVMP Geodatabase with Base Tables -- REQUIRED
    svmp_gdb = "Y:/projects/dnr_svmp2016/db/SVMP_DB_v5.2_20170815_AB.mdb"

    # Input parameter 3: Site Statistics Geodatabase with Template results tables -- REQUIRED
    #stats_gdb = "Y:/projects/dnr_svmp2016/svmp_tools/tools/svmp_db/svmp_sitesdb.mdb"
    stats_gdb = "Y:/projects/dnr_svmp2016/data/out/svmp_sitesdb_test.mdb"

    # Input parameter 4: Survey Year to be Processed -- REQUIRED
    survey_year = "2014" # "2015"

    # Input parameter 5: Vegetation Type to be Processed -- REQUIRED
    veg_code = "nativesg"

    # Input parameter 6: List of Sites file -- OPTIONAL
    sites_file = ""
    # sites_file = "Y:/projects/dnr_svmp2016/data/2014_test/sites2process_all.txt"

    # Input parameter 7: Study or Studies to Be Processed -- OPTIONAL
    # Returned from ArcToolbox as a semi-colon separated string "CityBham;DNRparks;Elwha"
    # study = "SVMPsw;Stressor"
    study = ""

    # Input parameter 8: Vegetation Type to be Processed -- OPTIONAL
    # Returned from ArcToolbox as a semi-colon separated string "SRS;STR;SUBJ"
    # samp_sel = "SRS;STR;SUBJ"
    samp_sel = ""

    main(transect_gdb, svmp_gdb, stats_gdb, survey_year, veg_code, sites_file, study, samp_sel)

    # t1 = time.time()
    #
    # print ("Total time elapsed is: %s seconds" %str(t1-t0))