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
import timeit



def create_template_ln(gdb, field_names, field_types, field_lengths):
    """ Create a template feature class for the line features"""
    fc_name = "template_ln"
    fc_full = os.path.join(gdb, fc_name)
    if arcpy.Exists(fc_full):
        # remove feature class if it exists
        arcpy.Delete_management(fc_full)
    # Create a temporary feature class
    tmp_fc = arcpy.CreateFeatureclass_management('in_memory', fc_name, "POLYLINE", spatial_reference = utils.sr)
    # Add all the fields
    for fname, typ, leng in zip(field_names, field_types, field_lengths):
        if leng is not None:
            arcpy.AddField_management(tmp_fc, field_name=fname, field_type=typ, field_length=leng)
        else:
            arcpy.AddField_management(tmp_fc, field_name=fname, field_type=typ)
    # Create final feature class by using temporary feature class as template
    arcpy.CreateFeatureclass_management(gdb, fc_name, template=tmp_fc)
    arcpy.Delete_management(tmp_fc)
    return fc_full

def timeStamped(fname, fmt='{fname}_%Y%m%d_%H%M%S.csv'):
    """ Create time stamped filename
    :param fname: base file name
    :param fmt: time-stamped filename as a format string (with a default of csv)
    :return: time-stamped filenaame
    """
    return datetime.datetime.now().strftime(fmt).format(fname=fname)

def make_sitelist(sites_file):
    """ Get all lines from input file without leading or trailing whitespace
        and omit lines that are just whitespace
    """
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
        atnsnt - veg type is absent/trace, samp_sel <> SUBJ, no transects
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
        """ List of sample ids associated with the sample"""
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
            my_sample = Sample(s)
            my_sample.importTransects(ts_dict)
            self._addSample(my_sample)

    def _get_transects_list(self, s_id):
        """ get list of transects for a sample.  Requires dataframe with samples and transects
        :param s_id: sample identifier
        :return: list of transects
        """
        return self.ts_df.loc[self.ts_df[utils.sampidCol] == s_id][utils.transectidCol].unique().tolist()

    def _get_surveys_dict(self, t_id):
        """ get dictionary of surveys and attributes for a transect.
        Requires dataframe with transects, surveys, max/min dep flags, site visit id
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
    transects -- a list of transect objects associated with the sample
    transect_ids -- a list of transect ids associated with the sample
    lnfc -- feature class name for line feature class
    lnfc_clipped -- feature class name for clipped line feature class
    sample_poly -- sample polygon
    """

    def __init__(self, id):
        self.id = id
        # individual transect objects
        self.transects = [] # list of associated sample objects

    def __repr__(self):
        return repr((self.id, self.transect_ids))

    @property
    def transect_ids(self):
        """ List of transect ids associated with the sample"""
        return self._transect_attrs('id')

    @property
    def lnfc(self):
        """ Feature class name for line feature class"""
        return self.id

    @property
    def lnfc_clipped(self):
        """ Feature class name for clipped line feature class"""
        return self.lnfc + "_clipped"

    def _transect_attrs(self, attr):
        """ Fetch attributes from the transects in the group """
        return [getattr(transect, attr) for transect in self.transects]

    def importTransects(self, ts_dict):
        """ Create Transect objects from a list of transects
         Add surveys to the transect objects using dictionary of transects and associated surveys

        Append these transect objects to a sample
        """
        for t in ts_dict.keys():
            my_transect = Transect(t, self.id)
            my_transect.importSurveys(ts_dict[t])
            self._addTransect(my_transect)

    def _addTransect(self, transect):
        """ Adds individual transect objects to the sample"""
        self.transects.append(transect)

    def make_line_fc(self, template_fc, gdb="in_memory" ):
        lnfc_path = os.path.join(gdb, self.lnfc)
        del_fc(lnfc_path)
        arcpy.CreateFeatureclass_management(gdb, self.lnfc, "Polyline", template_fc, spatial_reference = utils.sr)
        return lnfc_path

    def clip_line_fc(self, poly_layer, gdb="in_memory" ):
        lnfc_path = os.path.join(gdb, self.lnfc)
        lnfc_clip_path = os.path.join(gdb, self.lnfc_clipped)
        del_fc(lnfc_clip_path)
        arcpy.Clip_analysis(lnfc_path, poly_layer, lnfc_clip_path)

class Transect(object):
    """ Represents an individual Transect

    Properties:
    id -- transect identifier (transect_id)
    sample_id -- associated sample identifier (site_samp_id)
    surveys -- list of survey objects that make up the transect
    survey_ids -- list of survey ids that make up the transect
    maxdepflag -- maximum depth flag (maximum of maxdepflag values for associated surveys)
    mindepflag -- minimum depth flag (maximum of mindepflag values for associated surveys)

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
    veg_code -- veg_code for the statistics for the survey
    ptfc -- the name of the point feature class that contains the survey points
    ptfc_full -- full path to the point feature class containing the survey points
    ptfc_array -- Numpy array with survey points and attributes
    ptfc_list -- the numpy array as a list of lists (each internal list corresponds to a row in the source data)

    """
    def __init__(self, id, maxdepflag, mindepflag, sitevisit):
        self.id = id
        self.maxdepflag = maxdepflag
        self.mindepflag = mindepflag
        self.sitevisit = sitevisit
        self.fc_name = "_".join((self.sitevisit,"transect","pt"))
        self.veg_code = ""
        self.ptfc = ""
        self.ptfc_path = ""
        self.ptfc_array = None
        self.ptfc_df = None


    def __repr__(self):
        repr((self.id, self.maxdepflag, self.mindepflag))

    def set_ptfc_array(self, pt_field_names):
        """ Create a numpy array of point locations and specified attributes
            and set the ptfc_array property to that array
        """
        delimited_svyidcol = arcpy.AddFieldDelimiters(self.ptfc_path, utils.surveyidCol)
        where_clause = "{0} = '{1}'".format(delimited_svyidcol, self.id)
        # Get data from the point feature class as a NumPy array
        points_array = arcpy.da.FeatureClassToNumPyArray(self.ptfc_path, pt_field_names, where_clause)
        # Sort data by surveyid and date/time stamp
        self.ptfc_array = np.sort(points_array, order=[utils.surveyidCol, utils.datetimesampCol])

    def set_ptfc_df(self, pt_field_names):
        """ Create a numpy array of point locations and specified attributes
            and set the ptfc_array property to that array
        """
        delimited_svyidcol = arcpy.AddFieldDelimiters(self.ptfc_path, utils.surveyidCol)
        where_clause = "{0} = '{1}'".format(delimited_svyidcol, self.id)
        df = pd.DataFrame([row for row in arcpy.da.SearchCursor(self.ptfc_path, pt_field_names, where_clause, )],
                          columns=pt_field_names)
        # Sort the dataframe by surveyid number and time stamp
        # Note:  in later versions of pandas (0.17.0), this is deprecated and replaced by sort_values
        df.sort([utils.surveyidCol, utils.datetimesampCol], inplace=True)
        self.ptfc_df = df

    @property
    def ptfc_list(self):
        """ Returns the point feature array as a list"""
        if self.ptfc_array is not None:
            return self.ptfc_array.tolist()
        else:
            return []

    @property
    def maxdep(self):
        """ Maximum (i.e., deepest) depth on the survey line, prior to clipping
            Must have video = 1, and not be the null depth value (-9999)
        """
        if self.ptfc_df is not None:
            df = self.ptfc_df[(self.ptfc_df[utils.videoCol] == 1) & (self.ptfc_df[utils.depInterpCol] != utils.NULL_DEPTH)]
            return df[utils.depInterpCol].min()
        else:
            return None

    @property
    def mindep(self):
        """ Minimum depth (i.e. shallowest) on the survey line, prior to clipping
            Must have video = 1, and not be the null depth value (-9999)
        """
        if self.ptfc_df is not None:
            df = self.ptfc_df[(self.ptfc_df[utils.videoCol] == 1) & (self.ptfc_df[utils.depInterpCol] != utils.NULL_DEPTH)]
            return df[utils.depInterpCol].max()
        else:
            return None

    @property
    def maxdep_veg(self):
        """ Maximum (i.e., deepest) depth of selected veg_cod the survey line, prior to clipping
            Must have video = 1, and not be the null depth value (-9999)
        """
        if self.ptfc_df is not None:
            df = self.ptfc_df[(self.ptfc_df[utils.videoCol] == 1) & (self.ptfc_df[utils.depInterpCol] != utils.NULL_DEPTH)
                              & (self.ptfc_df[veg_code] == 1)]
            return df[utils.depInterpCol].min()
        else:
            return None

    @property
    def mindep_veg(self):
        """ Maximum (i.e., deepest) depth of selected veg_cod the survey line, prior to clipping
            Must have video = 1, and not be the null depth value (-9999)
        """
        if self.ptfc_df is not None:
            df = self.ptfc_df[(self.ptfc_df[utils.videoCol] == 1) & (self.ptfc_df[utils.depInterpCol] != utils.NULL_DEPTH)
                              & (self.ptfc_df[veg_code] == 1)]
            return df[utils.depInterpCol].max()
        else:
            return None

    def make_line_feature_df(self, lnfc_path, ln_field_names):
        """ Create a line feature from the point feature data frame """
        # Open cursor for line feature class
        cursor_ln = arcpy.da.InsertCursor(lnfc_path, ln_field_names)
        # Initialize variables
        first_point = True
        from_point = arcpy.Point()
        to_point = arcpy.Point()
        pt_attributes = ()

        for index, row in self.ptfc_df.iterrows():
            if first_point:
                from_point.X, from_point.Y = row['SHAPE@XY']
                from_point.ID = int(row[utils.ptidCol])
                dtsamp = row[utils.datetimesampCol].replace(microsecond=0)
                pt_attributes = (row[utils.ptidCol], row[utils.surveyidCol], dtsamp,
                                 row[utils.depInterpCol], row[utils.videoCol], row[veg_code])
                # print pt_attributes
                # print("X: {0}, Y: {1}".format(from_point.X, from_point.Y))
                first_point = False
            else:
                to_point.X, to_point.Y = row['SHAPE@XY']
                to_point.ID = int(row[utils.ptidCol])
                array = arcpy.Array([from_point, to_point])
                line_segment = arcpy.Polyline(array)
                line_attributes = (from_point.ID, line_segment) + pt_attributes
                # Insert a new row with the line segment and associated attributes into the feature class
                cursor_ln.insertRow(line_attributes)
                # The previous "to" point becomes the "from" point
                from_point.X = to_point.X
                from_point.Y = to_point.Y
                from_point.ID = to_point.ID
                # store the attributes for the current point to be used on next line segment
                dtsamp = row[utils.datetimesampCol].replace(microsecond=0)
                pt_attributes = (row[utils.ptidCol], row[utils.surveyidCol], dtsamp,
                                 row[utils.depInterpCol], row[utils.videoCol], row[veg_code])
                # print pt_attributes
                # print("X: {0}, Y: {1}".format(to_point.X, to_point.Y))


    def make_line_feature(self, lnfc_path, ln_field_names):
        """ Create a line feature from the point feature array (as a list) """
        # Open cursor for line feature class
        cursor_ln = arcpy.da.InsertCursor(lnfc_path, ln_field_names)
        # Initialize variables
        first_point = True
        from_point = arcpy.Point()
        to_point = arcpy.Point()
        pt_attributes = ()

        # Loop through array of survey points
        # for row in np.nditer(self.ptfc_array, order="C"):
        # Couldn't figure out how to manipulate the timestamp value from the array, so had to use list instead
        for row in self.ptfc_list:
            if first_point:
                # from_point.X, from_point.Y = row['SHAPE@XY']
                # from_point.ID = int(row[utils.ptidCol])
                # pt_attributes = (row[utils.ptidCol], row[utils.surveyidCol], row[utils.datetimesampCol],
                #                  row[utils.depInterpCol], row[utils.videoCol], row[veg_code])
                from_point.X, from_point.Y = row[1]
                from_point.ID = int(row[0])
                ptid = row[2]
                surveyid = row[3]
                # Microseconds in some timestamps throwing errors in insert cursor, so set to zero
                dtsamp = row[4].replace(microsecond=0)
                dep = row[5]
                vid = row[6]
                veg = row[7]
                pt_attributes = (ptid, surveyid, dtsamp, dep, vid, veg)
                # print pt_attributes
                # print("X: {0}, Y: {1}".format(from_point.X, from_point.Y))
                first_point = False
            else:
                # to_point.X, to_point.Y = row['SHAPE@XY']
                # to_point.ID = int(row[utils.ptidCol])
                to_point.X, to_point.Y = row[1]
                to_point.ID = int(row[0])
                array = arcpy.Array([from_point, to_point])
                line_segment = arcpy.Polyline(array)
                line_attributes = (from_point.ID, line_segment) + pt_attributes
                # Insert a new row with the line segment and associated attributes into the feature class
                cursor_ln.insertRow(line_attributes)
                # The previous "to" point becomes the "from" point
                from_point.X = to_point.X
                from_point.Y = to_point.Y
                from_point.ID = to_point.ID
                # store the attributes for the current point to be used on next line segment
                # print row[utils.datetimesampCol].replace(microsecond=0)
                # pt_attributes = (row[utils.ptidCol], row[utils.surveyidCol], row[utils.datetimesampCol],
                #                  row[utils.depInterpCol], row[utils.videoCol], row[veg_code])
                ptid = row[2]
                surveyid = row[3]
                dtsamp = row[4].replace(microsecond=0)
                dep = row[5]
                vid = row[6]
                veg = row[7]
                pt_attributes = (ptid, surveyid, dtsamp, dep, vid, veg)
                # print pt_attributes
                # print("X: {0}, Y: {1}".format(to_point.X, to_point.Y))

        del cursor_ln


class SurveyFCPtGroup(object):
    """ Represents a group of Survey Point Feature Classes within a geodatabase for a particular year

    Properties:
    gdb -- geodatabase with transect point feature classes
    year -- year of interest
    fcs -- list of all feature classes in geodatabase for that year
    survey_fc -- dictionary of survey ids (key) and feature class (value)

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


class SamplePoly(object):
    """ Represents an individual sample polygon

    Properties:
    id -- sample polygon identifier (site_samp_id)
    fc -- feature class full path
    gdb -- geodatabase containing the feature class
    feat_lyr -- an in-memory feature layer of the sample polygon


    """
    def __init__(self, id, gdb):
        self.id = id
        self.fc = os.path.join(gdb, utils.samppolyFC)
        self.gdb = gdb
        self.feat_lyr = self._make_feature_layer()

    def _make_feature_layer(self):
        """ Returns a feature layer of the sample polygon"""
        poly_layer = self.id + "_fl"
        # Select sample polygon for that sample
        try:
            delimited_sampidcol = arcpy.AddFieldDelimiters(self.fc, utils.sampidCol)
            where_clause = "{0} = '{1}'".format(delimited_sampidcol, self.id)
            arcpy.MakeFeatureLayer_management(self.fc, poly_layer, where_clause)
            return poly_layer
        except:
            return None



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

def paramstr2list(param, delim=";"):
    """ Convert an ESRI multichoice parameter value to a list"""
    if param:
        return param.split(delim)
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

def del_fc(fc):
    if arcpy.Exists(fc):
        arcpy.Delete_management(fc)


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
    msg("Generating list of samples based on user parameters")
    msg(filter)
    samples_filtered_df = filter_samples(svmp_tables, filter)

    # # ------- List of available point feature classes and associated survey_ids -------
    #  NOTE:  This is quite slow -- may be able to improve by re-writing with da.Walk approach
    # msg("Generating list of point transect features in {0}".format(transect_gdb))
    # surveypt_fcs = SurveyFCPtGroup(transect_gdb, survey_year)
    # # print surveypt_fcs.fcs
    # # print surveypt_fcs.survey_fc

    # -----------------  Fields for Transect Line feature classes
    # Base Field names (without Object ID and Shape fields), field types, and lengths
    base_field_names = [utils.ptidCol, utils.surveyidCol, utils.datetimesampCol, utils.depInterpCol, utils.videoCol,
                        veg_code]
    base_field_types = ["LONG", "TEXT", "DATE", "DOUBLE", "LONG", "LONG"]
    base_field_lengths = [None, 25, None, None, None, None]
    # Field names specific to point and line data sets
    pt_field_names = ['OID@', 'SHAPE@XY'] + base_field_names
    ln_field_names = ['OID@', 'SHAPE@'] + base_field_names

    #----- Create the template feature class for the temporary transect lines
    template_ln = create_template_ln(transect_gdb, base_field_names, base_field_types, base_field_lengths)

    # ------- Create groups of samples and associated transects/surveys for processing --------

    # Veg present
    msg("Grouping samples for processing and calculation of results")
    samp_vegp = SampleGroup(samples_filtered_df, svmp_tables, veg_code, "p")
    # # print samp_vegp
    # # print samp_vegp.samples
    # # print samp_vegp.sample_ids
    for sample in samp_vegp.samples:
        # print sample.id
        # print sample.transect_ids
        # Create an empty line feature class for the sample transects/surveys
        lnfc_path = sample.make_line_fc(template_ln, transect_gdb)
        for transect in sample.transects:
            print transect.id
            # print transect.maxdepflag, transect.mindepflag
            # print transect.survey_ids
            for survey in transect.surveys:
                print survey.id
                survey.veg_code = veg_code
                # print survey.maxdepflag, survey.mindepflag
                # survey.pointfc = transect_gdb
                # Get survey points from feature class
                # ptfc = surveypt_fcs.survey_fc[survey.id] # feature class name for specified survey.id
                # ptfc_path = os.path.join(surveypt_fcs.gdb, ptfc) # full path to survey point feature class
                #----- for testing ONLY, specify input point feature class ---------------
                # ptfc = "core004_2014_01_transect_pt"
                # ptfc_path = os.path.join(transect_gdb, ptfc) # full path to survey point feature class
                survey.ptfc = "core004_2014_01_transect_pt"
                survey.ptfc_path = os.path.join(transect_gdb, survey.ptfc)
                #---------------------

                # Get pandas data frame of the survey's points and specified attributes
                # start_time = timeit.default_timer()
                survey.set_ptfc_df(pt_field_names)
                print "Max depth: {}".format(survey.maxdep)
                print "Min depth: {}".format(survey.mindep)
                print "Max Veg depth: {}".format(survey.maxdep_veg)
                print "Min Veg depth: {}".format(survey.mindep_veg)

                # elapsed = timeit.default_timer() - start_time
                # print "DataFrame creation time: {}".format(elapsed)
                # Get the NumPy array of the survey's points and specified attributes
                # start_time = timeit.default_timer()
                # survey.set_ptfc_array(pt_field_names)
                # # elapsed = timeit.default_timer() - start_time
                # # print "Numpy array creation time: {}".format(elapsed)
                # # print survey.ptfc_df
                # # print survey.ptfc_df.describe()

                # print survey.ptfc_df.to_dict('list')

                # # Create a line feature from the survey points
                # start_time = timeit.default_timer()
                # survey.make_line_feature(lnfc_path, ln_field_names)
                # elapsed = timeit.default_timer() - start_time
                # print "Line from Numpyarray creation time: {}".format(elapsed)

                # start_time = timeit.default_timer()
                survey.make_line_feature_df(lnfc_path, ln_field_names)
                # elapsed = timeit.default_timer() - start_time
                # print "Line from dataframe creation time: {}".format(elapsed)

        # Get the associated sample polygon
        sample_poly = SamplePoly(sample.id, svmp_gdb)
        # Clip the line segments
        sample.clip_line_fc(sample_poly.feat_lyr, transect_gdb)








    # print samp_vegp.sample_ids
    # print samp_vegp.df.describe()
    # print samp_vegp.df
    # print samp_vegp.stats
    # print samp_vegp.ts_df

    # # Vegetation absent/trace, samp_sel = 'SUBJ'
    # samp_vegats = SampleGroup(samples_filtered_df, svmp_tables, veg_code, "ats")
    # # print samp_vegats.ts_df
    # # print samp_vegats.df
    # # print samp_vegats.stats
    #
    # # Veg absent/trace, samp_sel <> 'SUBJ', transects
    # samp_vegatnst = SampleGroup(samples_filtered_df, svmp_tables, veg_code, "atnst")
    # # print samp_vegatnst.ts_df
    # # print samp_vegatnst.df
    # # print samp_vegatnst.stats
    #
    # # Veg absent/trace, samp_sel <> 'SUBJ', no transects
    # samp_vegatnsnt = SampleGroup(samples_filtered_df, svmp_tables, veg_code, "atnsnt")
    # # print samp_vegatnsnt.ts_df
    # # print samp_vegatnsnt.df
    # # print samp_vegatnsnt.stats


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
    # sites_file = ""
    # sites_file = "Y:/projects/dnr_svmp2016/data/2014_test/sites2process_all.txt"
    sites_file = "Y:/projects/dnr_svmp2016/data/sitefiles/sites2014core004.txt"

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