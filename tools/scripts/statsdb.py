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

    veg_code -- vegetation code for analysis
    group -- grouping criteria used
        p - veg type is present
        ats - veg type is absent or trace, samp_sel = SUBJ
        atnst - veg type is absent or trace, samp_sel <> SUBJ, transects exist
        atnsnt - veg type is absent/trace, samp_sel <> SUBJ, transects exist
    stats -- type of stats to be calculated
        ts - calculate transect and site stats
        t - calculate transect stats only; assign site stats as zero/no data
        s - no transect results; assign site results as zero/no data
    df -- dataframe of the samples in the group with attributes
    ts_df -- data frame of the associated transects and surveys
    samples -- a list of sample objects
    """

    def __init__(self, samp_df, svmp_tables, veg_code, group):
        self.veg_code = veg_code
        self.group = group
        self.stats = "" # initialize stats type before setting it in _samp_group
        # create samples and transects dataframes based on group criteria
        self.df = self._samp_group(samp_df, svmp_tables)
        self.ts_df = None # initialize transects dataframe
        if "t" in self.stats:
            self.ts_df = self._get_transects(svmp_tables)

        # Import individual sample objects
        self.samples = [] # list of associated sample objects
        self.importSamples()
        # Properties of the samples
        self.sample_ids = self._sample_attrs('id')


    def _sample_attrs(self, attr):
        return [getattr(sample, attr) for sample in self.samples]

    def _samp_group(self, samp_df, svmp_tables):
        # Group the samples according to the vegetation occurrence, sample selection, and existence of transects
        # Need the samples dataframe, veg_occur table and transect table
        veg_df = svmp_tables[utils.vegoccurTbl].df
        tsect_df = svmp_tables[utils.transectsTbl].df
        # Vegetation Present
        if self.group == "p":
            # Select all records in veg_occur dataframe where the veg type is present
            vegp_df = veg_df[(veg_df[self.veg_code].isin(["present"]))]
            df = samp_df[samp_df[utils.sitevisitidCol].isin(vegp_df[utils.sitevisitidCol])]
            # Remove any samples where samp_sel is SUBJ
            df = df[~df[utils.sampselCol].isin(["SUBJ"])]
            # set the stats type -- transects and site calcs
            self.stats = "ts"  # set stats calc type to transect & site
            return df
        # Vegetation is absent/trace and samp_sel = "SUBJ"
        elif self.group == "ats":
            # vegetation absent/trace
            vegat_df = veg_df[veg_df[veg_code].isin(["absent","trace"])]
            df = samp_df[samp_df[utils.sitevisitidCol].isin(vegat_df[utils.sitevisitidCol])]
            # samp_sel = SUBJ
            df = df[df[utils.sampselCol].isin(["SUBJ"])]
            self.stats = "s" # set stats calc type to site (zero/no data)
            return df
        # Vegetation is absent/trace, samp_sel <> "SUBJ", transects exist
        elif self.group == "atnst":
            # vegetation absent/trace
            vegat_df = veg_df[veg_df[veg_code].isin(["absent", "trace"])]
            df = samp_df[samp_df[utils.sitevisitidCol].isin(vegat_df[utils.sitevisitidCol])]
            # samp_sel <> 'SUBJ'
            df = df[~df[utils.sampselCol].isin(["SUBJ"])]
            # sample has an associated record in transects table
            df = df[df[utils.sampidCol].isin(tsect_df[utils.sampidCol])]
            self.stats = "t"  # set stats calc type to transect
            return df
        # Vegetation is absent/trace, samp_sel <> "SUBJ", no transects
        elif self.group == "atnsnt":
            # vegetation absent/trace
            vegat_df = veg_df[veg_df[veg_code].isin(["absent", "trace"])]
            df = samp_df[samp_df[utils.sitevisitidCol].isin(vegat_df[utils.sitevisitidCol])]
            # samp_sel <> 'SUBJ'
            df = df[~df[utils.sampselCol].isin(["SUBJ"])]
            # sample has no associated record in transects table
            df = df[~df[utils.sampidCol].isin(tsect_df[utils.sampidCol])]
            self.stats = "s"  # set stats calc type to transect
            return df

    def _get_transects(self, svmp_tables):
        # Get a dataframe with the transects and surveys associated with the sample group
        # Need the grouped samples dataframe, and transects, segments, and surveys tables
        tsect_df = svmp_tables[utils.transectsTbl].df
        seg_df = svmp_tables[utils.segmentsTbl].df
        svy_df = svmp_tables[utils.surveysTbl].df
        # Find all the transects that match the filtered set of samples
        transects = tsect_df[tsect_df[utils.sampidCol].isin(self.df[utils.sampidCol])]
        # Find matching segments and surveys --- not used
        # segments = seg_df[seg_df[utils.transectidCol].isin(transects[utils.transectidCol])]
        # surveys = svy_df[svy_df[utils.surveyidCol].isin(segments[utils.surveyidCol])]
        # Merge join selected transects with segments to get associated surveys
        df = transects.merge(seg_df, on=utils.transectidCol).merge(svy_df, on=utils.surveyidCol)
        # Filter for survey_status = 'surveyed'
        df = df[df[utils.surveystatCol].isin(["surveyed"])]
        return df

    def importSamples(self):
        """  Create Sample objects from a data frame of samples and associated attributes

        Append these sample objects to a sample group

        """
        # # this approach will be helpful if need the other attributes
        # for idx, row in self.df.iterrows():
        #     id = row[utils.sampidCol]
        #     my_sample = Sample(id)
        #     self._addSample(my_sample)

        # If only need id, convert to list and iterate
        samples_list = self.df[utils.sampidCol].tolist()
        # print samples_list
        for s in samples_list:
            transects_list = []
            if self.ts_df is not None:
                print s
                transects_list = self.ts_df.loc[self.ts_df[utils.sampidCol] == s][utils.sampidCol].tolist()
                print transects_list
                # print self.ts_df.loc[self.ts_df[utils.sampidCol].isin([s])].all()
            my_sample = Sample(s, transects_list)
            self._addSample(my_sample)

    def _addSample(self, sample):
        """ Adds individual sample objects to the sample group"""
        self.samples.append(sample)


class Sample(object):
    """ Represents an individual Site Sample

    Properties:
    id -- sample identifier (site_samp_id)
    site_code -- site code
    site_visit_id -- identifier for the site visit (site_visit_id)
    samp_sel -- sample selection method for the sample
    sample_poly -- sample polygon
    transects -- transects associated with the sample

    """

    def __init__(self, id, transects_list):
        self.id = id
        self.transects_list = transects_list


class Transect(object):
    """ Represents an individual Transect

    Properties:
    id -- transect identifier (transect_id)
    sample_id -- associated sample identifier (site_samp_id)
    surveys -- surveys that make up the transect
    maxdepflag -- maximum depth flag
    mindepflag -- minimum depth flag

    """
    def __init__(self, id, sample_id, surveys_list=[]):
        self.id = id
        self.sample_id = sample_id
        self.surveys_list = surveys_list


class Survey(object):
    """ Represents an individual Survey

    Properties:
    id -- survey identifier
    surveystat -- survey status
    maxdepflag -- maximum depth flag
    mindepflag -- minimum depth flag

    """
    def __init__(self, id):
        self.id = id

class SamplePoly(object):
    """ Represents an individual sample polygon

    Properties:
    id -- sample polygon identifier (site_samp_id)

    """
    def __init__(self, id):
        self.id = id

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


def filter_samples(svmp_tables, filter):
    # Filter dataframes to produce list of samples meeting the criteria

    # Source data Tables
    samp_df = svmp_tables[utils.sitesamplesTbl].df
    stdy_df = svmp_tables[utils.studyassociationsTbl].df

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
    # Final filtered dataframe
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
    samples_filtered_df = filter_samples(svmp_tables, filter)
    # print samples_df
    #-----------  END Filtering based on User input parameters -------------------------------

    # ----------- Create groups of samples and associated transects/surveys for processing -------------

    # Veg present
    samp_vegp = SampleGroup(samples_filtered_df, svmp_tables, veg_code, "p")
    # print samp_vegp.sample_ids
    # print samp_vegp.df.describe()
    # print samp_vegp.df
    # print samp_vegp.stats
    # print samp_vegp.ts_df

    # for idx, row in samp_vegp.ts_df.iterrows():
    #     print row[utils.sampidCol],row[utils.transectidCol],row[utils.surveyidCol], row[utils.maxdepflagCol],row[utils.mindepflagCol]

    # Vegetation absent/trace, samp_sel = 'SUBJ'
    samp_vegats = SampleGroup(samples_filtered_df, svmp_tables, veg_code, "ats")
    # print samp_vegats.ts_df
    # print samp_vegats.df
    # print samp_vegats.stats

    # Veg absent/trace, samp_sel <> 'SUBJ', transects
    samp_vegatnst = SampleGroup(samples_filtered_df, svmp_tables, veg_code, "atnst")
    # print samp_vegatnst.ts_df
    # print samp_vegatnst.df
    # print samp_vegatnst.stats

    # Veg absent/trace, samp_sel <> 'SUBJ', no transects
    samp_vegatnsnt = SampleGroup(samples_filtered_df, svmp_tables, veg_code, "atnsnt")
    # print samp_vegatnsnt.ts_df
    # print samp_vegatnsnt.df
    # print samp_vegatnsnt.stats


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