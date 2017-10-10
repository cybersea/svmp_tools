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
    """ Create time stamped filename
    :param fname: base file name
    :param fmt: time-stamped filename as a format string (with a default of csv)
    :return: time-stamped filenaame
    """
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
    sample_ids -- a list of sample ids for samples in the group
    """

    def __init__(self, samp_df, svmp_tables, veg_code, group):
        self.veg_code = veg_code
        self.group = group
        self.stats = "" # initialize stats type before setting it in _samp_group
        # create samples and transects dataframes based on group criteria
        self.df = self._samp_group(samp_df, svmp_tables)
        self.ts_df = None # initialize transects dataframe
        if "t" in self.stats:
            self.ts_df = self._get_ts_df(svmp_tables)

        # Import individual sample objects
        self.samples = [] # list of associated sample objects
        self.importSamples()
        # Properties of the samples

    def __repr__(self):
        return repr((self.sample_ids, self.group, self.stats, self.veg_code))

    @property
    def sample_ids(self):
        """ List of transect ids associated with the sample"""
        return self._sample_attrs('id')

    def _sample_attrs(self, attr):
        """ Fetch attributes from the samples in the group """
        return [getattr(sample, attr) for sample in self.samples]

    def _samp_group(self, samp_df, svmp_tables):
        """
        Filter samples according to the vegetation occurrence, sample selection, and existence of transects
        Requires the samples dataframe, veg_occur table and transect table

        :param samp_df:  pandas dataframe of site_samples table from svmp geodatabase
        :param svmp_tables:  dictionary of source svmp tables
        :return: pandas dataframe of samples in the group
        """

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

    def _get_ts_df(self, svmp_tables):
        """
        Get a dataframe with the transects and surveys associated with the sample group
        Requires the grouped samples dataframe, and transects, segments, and surveys tables

        :param svmp_tables: dictionary of source svmp tables
        :return: pandas dataframe with transects and surveys

        """
        tsect_df = svmp_tables[utils.transectsTbl].df
        seg_df = svmp_tables[utils.segmentsTbl].df
        svy_df = svmp_tables[utils.surveysTbl].df
        # Find all the transects that match the filtered set of samples
        transects = tsect_df[tsect_df[utils.sampidCol].isin(self.df[utils.sampidCol])]
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

        # If only need id, convert to list and iterate
        samples_list = self.df[utils.sampidCol].tolist()
        for s in samples_list:
            transects_list = []
            surveys_dict = {}
            ts_dict = {}
            # Get associated transects if they exist
            if self.ts_df is not None:
                transects_list = self._get_transects_list(s)
                for t in transects_list:
                    # Get surveys (and max/min dep flags) associated with each transect
                    surveys_dict = self._get_surveys_dict(t)  # survey id (key), min/max dep flags (value as list)
                    ts_dict[t] = surveys_dict # transect id (key), associated survey dictionary as value
            my_sample = Sample(s, ts_dict)
            my_sample.importTransects()
            self._addSample(my_sample)

    def _get_transects_list(self, s_id):
        """ get list of transects for a sample.  Requires dataframe with samples and transects
        :param s_id: sample identifier
        :return: list of transects
        """
        return self.ts_df.loc[self.ts_df[utils.sampidCol] == s_id][utils.transectidCol].unique().tolist()

    def _get_surveys_dict(self, t_id):
        """ get list of surveys for a transect.  Requires dataframe with transects, surveys, max/min dep flags, site visit id
        :param t_id: transect identifier
        :return: dictionary with survey id (key), and max/min depth flags (values as list)
        """
        surveys_depths_df = self.ts_df.loc[self.ts_df[utils.transectidCol] == t_id][
            [utils.surveyidCol, utils.maxdepflagCol, utils.mindepflagCol, utils.sitevisitidCol]]
        return surveys_depths_df.set_index(utils.surveyidCol).T.to_dict('list')

    def _addSample(self, sample):
        """ Adds individual sample objects to the sample group"""
        self.samples.append(sample)


class Sample(object):
    """ Represents an individual Site Sample

    Properties:
    id -- sample identifier (site_samp_id)
    transects_list -- list of transects to be associated with the sample
    transects -- a list of transect objects associated with the sample
    transect_ids -- a list of transect ids associated with the sample
    sample_poly -- sample polygon
    """

    def __init__(self, id, ts_dict):
        self.id = id
        self.transects_list = ts_dict.keys()
        self.ts_dict = ts_dict

        # individual transect objects
        self.transects = [] # list of associated sample objects

    def __repr__(self):
        return repr((self.id, self.transect_ids))

    @property
    def transect_ids(self):
        """ List of transect ids associated with the sample"""
        return self._transect_attrs('id')

    def _transect_attrs(self, attr):
        """ Fetch attributes from the transects in the group """
        return [getattr(transect, attr) for transect in self.transects]

    def importTransects(self):
        """ Create Transect objects from a list of transects
         Add surveys to the transect objects using dictionary of transects and associated surveys

        Append these transect objects to a sample
        """
        for t in self.transects_list:
            my_transect = Transect(t, self.id)
            my_transect.importSurveys(self.ts_dict[t])
            self._addTransect(my_transect)

    def _addTransect(self, transect):
        """ Adds individual transect objects to the sample"""
        self.transects.append(transect)


class Transect(object):
    """ Represents an individual Transect

    Properties:
    id -- transect identifier (transect_id)
    sample_id -- associated sample identifier (site_samp_id)
    surveys -- surveys that make up the transect
    maxdepflag -- maximum depth flag
    mindepflag -- minimum depth flag

    """
    def __init__(self, id, sample_id):
        self.id = id
        self.sample_id = sample_id
        self.surveys = []

    def __repr__(self):
        return repr(self.id)

    @property
    def survey_ids(self):
        return self._survey_attrs('id')

    @property
    def maxdepflag(self):
        return max(self._survey_attrs('maxdepflag'))

    @property
    def mindepflag(self):
        return max(self._survey_attrs('maxdepflag'))

    def _survey_attrs(self, attr):
        """ Fetch list of attributes from the surveys in the transect """
        return [getattr(survey, attr) for survey in self.surveys]

    def importSurveys(self, survey_dict):
        """
        Create survey objects from a dictionary of survey ids (key) and max/min depth flags
        Append surveys to transect object

        :param survey_dict: dictionary of survey ids (key) and list of max/min depth flags and site visit (value)
        :return:
        """
        for s, atts in survey_dict.items():
            my_survey = Survey(s, atts[0], atts[1], atts[2])
            self._addSurvey(my_survey)

    def _addSurvey(self, survey):
        """ Adds individual survey objects to the transect"""
        self.surveys.append(survey)


class Survey(object):
    """ Represents an individual Survey

    Properties:
    id -- survey identifier
    maxdepflag -- maximum depth flag
    mindepflag -- minimum depth flag
    sitevisit -- site visit id

    """
    def __init__(self, id, maxdepflag, mindepflag, sitevisit):
        self.id = id
        self.maxdepflag = maxdepflag
        self.mindepflag = mindepflag
        self.sitevisit = sitevisit
        self.fc_name = "_".join((self.sitevisit,"transect","pt"))


    def __repr__(self):
        repr((self.id, self.maxdepflag, self.mindepflag))

    # @property
    # def pointfc(self):
    #     """ The point feature class associated with the survey """
    #     fc_list = utils.tables_fcs_list(self.gdb)
    #     if self.fc_name in fc_list:
    #         return os.path.join(self.gdb, self.fc_name)
    #     else:
    #         return None


class SurveyFCPtGroup(object):
    """ Represents a group of Survey Point Feature Classes within a geodatabase

    """

    def __init__(self, gdb, year):
        self.gdb = gdb
        self.year = year
        self.fcs = self._get_fcs()
        self.survey_fc = self._get_surveys()

    def _get_fcs(self):
        """ Returns a list of point transect feature classes within the geodatabase"""
        fc_list = utils.tables_fcs_list(self.gdb)["fcs"]
        return [fc for fc in fc_list if fc.endswith("transect_pt") and self.year in fc]

    def _get_surveys(self):
        """ Returns a dictionary of survey_ids (key) and
            the feature class (value) the survey points are within
        """
        _survey_fc = {}
        for fc in self.fcs:
            survey_list = utils.unique_values(os.path.join(self.gdb, fc), utils.surveyidCol)
            for survey in survey_list:
                _survey_fc[survey] = fc
        return _survey_fc

class SurveyPts(object):
    """ Represents a set of points for a survey"""

    def __init__(self, gdb, fc, survey_id):
        self.gdb = gdb
        self.fc = fc
        self.survey_id = survey_id

    @property
    def exists(self):
        pass



class SamplePoly(object):
    """ Represents an individual sample polygon

    Properties:
    id -- sample polygon identifier (site_samp_id)

    """
    def __init__(self, id):
        self.id = id


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


def print_params(params):
    # Print out the the list of parameters
    for param in params:
        if param:
            msg(param)

def filter_samples(svmp_tables, filter):
    """ Filter dataframes to produce list of samples meeting the criteria

    :param svmp_tables: dictionary of source svmp tables
    :param filter: dictionary with filtering criteria for different elements or columns
    :return:  pandas dataframe of samples filtered with the criteria
    """

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
    """ Convert an ESRI multichoice parameter value to a list"""
    if param:
        return param.split(";")
    else:
        return []

def make_sitelist(sites_file):
    """ Create a list of sites from in input text file

    Get all lines from input file without leading or trailing whitespace
    and omit lines that are just whitespace

    :param sites_file: text file with sites listed one per line
    :return:  list of sites
    """

    site_list = [line.strip() for line in open(sites_file,'r') if not line.isspace()]
    return site_list

def msg(msg):
    """ General message accumulator"""
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

    # ------- List of available point feature classes and associated survey_ids -------
    surveypt_fcs = SurveyFCPtGroup(transect_gdb, survey_year)
    print surveypt_fcs.fcs
    print surveypt_fcs.survey_fc



    # ------- Create groups of samples and associated transects/surveys for processing --------

    # Veg present
    # samp_vegp = SampleGroup(samples_filtered_df, svmp_tables, veg_code, "p")
    # samp_vegp.importSamples()
    # # print samp_vegp
    # # print samp_vegp.samples
    # # print samp_vegp.sample_ids
    # for sample in samp_vegp.samples:
    #     print sample.id
    #     # print sample.transect_ids
    #     for transect in sample.transects:
    #         print transect.id
    #         print transect.maxdepflag, transect.mindepflag
    #         print transect.survey_ids
    #         for survey in transect.surveys:
    #             print survey.maxdepflag, survey.mindepflag
    #             # survey.pointfc = transect_gdb


    # print samp_vegp.sample_ids
    # print samp_vegp.df.describe()
    # print samp_vegp.df
    # print samp_vegp.stats
    # print samp_vegp.ts_df

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