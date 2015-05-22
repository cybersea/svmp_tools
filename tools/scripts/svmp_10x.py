__author__ = 'Allison Bailey, Sound GIS'

"""
Major Classes and Data Structures for SVMP Tools Module

"""

import sys
import os
import svmpUtils as utils
import arcpy
import numpy


class Site:
    """ Represents the SVMP data for an individual site

    Properties
    id -- individual site identifier
    sampling_occasion -- sampling occasion (for example, year)
    sitestat_id -- unique identifier for site and sampling occasion combination
    veg_col -- vegetation column of interest
    veg_col_exists -- Flag for existence of vegetation column in transect_pt_fc
    transect_gdb -- geodatabase containing transect point feature classes
    transect_pt_fc -- Transect point feature class (full path)
    transect_pt_fc_exists -- Flag for existence of transect point feature class
    sample_poly_fc -- Feature Class containing all sample polygons
    sample_poly_exists -- Flag for existence of sample polygon
    sample_poly -- Sample polygon feature
    ctl_file -- Control file name (full path)
    ctl_file_exists -- Flag for existence of control file
    transects -- list of transects at the site

    """


    def __init__(self, id, sampling_occasion, veg_col, transect_gdb, sample_poly_fc, ctl_directory):
        self.id = id
        self.sampling_occasion = sampling_occasion
        self.veg_col = veg_col
        self.sitestat_id = "".join((self.id, "_", self.sampling_occasion))
        self.site_results_id = "".join((self.id, "_", self.sampling_occasion, "_", veg_col))
        self.transect_gdb = transect_gdb
        self.sample_poly_fc = sample_poly_fc
        self.ctl_directory = ctl_directory
        # Create transect lines only based on validation/existence checks
        if self.ctl_file_exists and self.veg_exists and self.sample_poly_exists:
            self.make_line_fc(clip=True)

    @property
    def transect_pt_fc(self):
        """ Transect Point Feature class full path"""
        fc_name = "%s_%s%s" % (self.id, self.sampling_occasion, utils.ptFCSuffix)
        return os.path.join(self.transect_gdb, fc_name)

    @property
    def ctl_file(self):
        file_name = "".join((self.id, utils.ctlSuffix))
        return os.path.join(self.ctl_directory, self.id, file_name)

    @property
    def transect_pt_fc_exists(self):
        """ Flag for existence of transect point feature class """
        if arcpy.Exists(self.transect_pt_fc):
            return True
        else:
            return False

    @property
    def ctl_file_exists(self):
        """ Flag for existence of control file """
        if os.path.exists(self.ctl_file):
            return True
        else:
            return False

    @property
    def veg_col_exists(self):
        """ Flag for existence of vegetation column"""
        if self.transect_pt_fc_exists:
            field_name_list = [f.name for f in arcpy.ListFields(self.transect_pt_fc)]
            if self.veg_col in field_name_list:
                return True
            else:
                return False
        else:
            return False

    @property
    def veg_exists(self):
        """Flag for existence of specified vegetation"""
        if self.veg_col_exists:
            # Make NumPy Array from table and see if it returns a result
            results = arcpy.da.TableToNumPyArray(self.transect_pt_fc, self.veg_col)
            if results[self.veg_col].max() > 0:
                return True
            else:
                return False

        return False

    @property
    def sample_poly_exists(self):
        """ Flag for existence of sample polygon"""
        # Build where clause that looks this: [sitestat_id] = "hdc2334_2014"
        delimited_field = arcpy.AddFieldDelimiters(self.sample_poly_fc, utils.sitestatidCol)
        where_clause = delimited_field + " = " + "'%s'" % (self.sitestat_id)
        # Make NumPy Array from table and see if it returns a result
        results = arcpy.da.TableToNumPyArray(self.sample_poly_fc, utils.sitestatidCol, where_clause)
        # print results - for debugging
        if results:
            return True
        else:
            return False

    @property
    def transect_list(self):
        """ Returns a list of unique transects at the site """
        if self.transect_pt_fc_exists:
            results = arcpy.da.TableToNumPyArray(self.transect_pt_fc, utils.trkCol)
            # print results
            # print results.dtype.names
            # print results.dtype
            # print numpy.unique(results)
            # print numpy.unique(results).tolist()
            # print numpy.unique(results).ndim
            # print numpy.unique(results).shape
            # print results.ndim
            # print results.shape
            return numpy.unique(results)[utils.trkCol].tolist()

    @property
    def transect_ln_fc(self):
        """ Returns the the full path of a temporary feature class used to depict transect line segments """
        fc_name = "%s_%s_transect_line" % (self.id, self.sampling_occasion)
        return os.path.join(self.transect_gdb, fc_name)

    @property
    def transect_ln_clip_fc(self):
        """ Returns the the full path of a temporary feature class used to depict CLIPPED transect line segments """
        fc_name = "%s_%s_transect_line_clip" % (self.id, self.sampling_occasion)
        return os.path.join(self.transect_gdb, fc_name)

    def make_line_fc(self, clip=True):
        """
        Creates a line feature class from point feature class
        :rtype : object
        """
        # Get the spatial reference from the point feature class
        spatRef = arcpy.Describe(self.transect_pt_fc).spatialReference
        # Create an empty polyline feature class
        self.del_fc(self.transect_ln_fc)
        arcpy.CreateFeatureclass_management(os.path.dirname(self.transect_ln_fc), os.path.basename(self.transect_ln_fc),
                                            "Polyline", self.transect_pt_fc, spatial_reference=spatRef)
        # Base Field names (without Object ID and Shape fields)
        field_names = utils.get_fieldnames(self.transect_pt_fc, arcpy)
        pt_field_names = ['OID@', 'SHAPE@XY'] + field_names
        ln_field_names = ['OID@', 'SHAPE@'] + field_names
        # (u'OID@', u'SHAPE@', u'site_code', u'tran_num', u'date_samp', u'Time24hr', u'depth_obs', u'depth_interp',
        # u'Phyllo', u'Zm', u'Native_SG', u'Zj', u'undiff', u'video', u'TrkType')

        # Open a Cursor for populating the line feature class
        cursor = arcpy.da.InsertCursor(self.transect_ln_fc, ln_field_names)
        print cursor.fields

        expression = "ORDER BY %s, %s, %s" % (arcpy.AddFieldDelimiters(self.transect_pt_fc, utils.trkCol),
                                              arcpy.AddFieldDelimiters(self.transect_pt_fc, utils.shpDateCol),
                                              arcpy.AddFieldDelimiters(self.transect_pt_fc, utils.time24hrCol))
        with arcpy.da.SearchCursor(self.transect_pt_fc, pt_field_names, sql_clause=(None, expression)) as allpts:
            prev_transect = 0  # intialize transect counter
            from_point = arcpy.Point()
            to_point = arcpy.Point()
            pt_attributes = ()

            for pt in allpts:
                # Get the transect ID
                transect_id = pt[3]
                if transect_id != prev_transect:
                    # This is the first point in a transect
                    from_point.X, from_point.Y = pt[1]
                    from_point.ID = pt[0]
                    #print "%s first point: %s, %s, %s" % (transect_id, from_point.ID, from_point.X, from_point.Y)
                    prev_transect = transect_id
                    pt_attributes = pt[2:]
                    #print from_point, pt_attributes
                else:
                    # This is a point along the transect
                    to_point.X, to_point.Y = pt[1]
                    to_point.ID = pt[0]
                    array = arcpy.Array([from_point, to_point])
                    line_segment = arcpy.Polyline(array)
                    line_attributes = (from_point.ID, line_segment) + pt_attributes
                    # Insert a new row with the line segment and associated attributes into the feature class
                    cursor.insertRow(line_attributes)
                    # The previous "to" point becomes the "from" point
                    from_point.X = to_point.X
                    from_point.Y = to_point.Y
                    from_point.ID = to_point.ID
                    # store the attributes for the current point to be used on next line segment
                    pt_attributes = pt[2:]
                    #print line_segment.JSON, line_segment.length
        del cursor

        # If clip flag is true, clip the line with the sample polygon
        if clip:
            self.clip_line_fc()

    def clip_line_fc(self):
        if self.sample_poly_exists and arcpy.Exists(self.transect_ln_fc):
            self.del_fc(self.transect_ln_clip_fc)
            # Build where clause like this: [sitestat_id] = 'hdc2334_2014'
            where_clause = "%s = '%s'" % (arcpy.AddFieldDelimiters(self.sample_poly_fc, utils.sitestatidCol),
                                          self.sitestat_id)
            poly_fl = "sample_poly_feature"
            arcpy.MakeFeatureLayer_management(self.sample_poly_fc, poly_fl, where_clause)
            arcpy.Clip_analysis(self.transect_ln_fc, poly_fl, self.transect_ln_clip_fc)


    def del_fc(self, fc):
        if arcpy.Exists(fc):
            arcpy.Delete_management(fc)


class Transects:
    """ Represents the SVMP data for a set of transects at a Site

    Properties
    site -- Site object
    transect_list -- list of transect ids at the site
    transect_results_ids -- dictionary of transect id (key) and transect_results_id (value)
    trktypes -- dictionary of transect id (key) and track type code (value)
    maxflags -- dictionary of transect id (key) and flag indicating transect can be used for vegetation max depth
    minflags -- dictionary of transect id (key) and flag indicating transect can be used for vegetation min depth
    maxtransdeps -- dictionary of transect id (key) and maximum depth of transect (value)
    mintransdeps -- dictionary of transect id (key) and minimum depth of transect  (value)
    maxvegdeps -- dictionary of transect id (key) and maximum depth of vegetation on transect (value)
    minvegdeps -- dictionary of transect id (key) and minimum depth of vegetation on transect (value)
    trans_lengths -- dictionary of transect id (key) and total length of clipped transect (value)
    veg_lengths -- dictionary of transect id (key) and total length of veg on clipped transect (value)
    veg_fractions -- dictionary of transect id (key) and fraction of vegetation on clipped transect (value)
    date_sampled -- Date of site sampling
    trans_dates -- dictionary of transect id (key) and data of sampling (value)
    """

    def __init__(self, site):
        self.site = site
        self.transect_list = self.site.transect_list
        self.get_trans_results_ids()
        self.get_trkflags()
        self.get_transdeps()
        self.get_vegdeps()
        self.get_translengths()
        self.get_veglengths()
        self.get_dates()

    def get_trans_results_ids(self):
        self.transect_results_ids = {}
        for t in self.site.transect_list:
            self.transect_results_ids[t] = self.site.site_results_id + "_" + str(t).zfill(2)

    def get_trkflags(self):
        self.trktypes = {}
        self.maxflags = {}
        self.minflags = {}
        """ This method is highly dependent upon the assumed structure of the control file
        which has specific attributes and values listed line-by-line in sequential order.
        For example:
            Track, 1
            TrackType,  SLPR
            Perimeter,  Yes
            BasalArea,  Yes
            PatchIndex, Yes
            MinDepth,   Yes
            MaxDepth,   Yes
        """
        if self.site.ctl_file_exists:
            for line in open(self.site.ctl_file):
                line = line.strip()
                [att, val] = line.split(",")
                val = val.strip()
                # Get Track Number
                if att == utils.ctlTrkAtt:
                    trk = int(val)
                # Get Track Type
                if att == utils.ctlTrktypeAtt:
                    trktype = val
                    self.trktypes[trk] = trktype
                # Get Maximum Depth Flag
                if att == utils.ctlMaxAtt:
                    if val == utils.ctlYes:
                        maxflag = 1
                    else:
                        maxflag = 0
                    self.maxflags[trk] = maxflag
                # Get Minimum Depth Flag
                if att == utils.ctlMinAtt:
                    if val == utils.ctlYes:
                        minflag = 1
                    else:
                        minflag = 0
                    self.minflags[trk] = minflag

    def get_transdeps(self):
        self.maxtransdeps = {}
        self.mintransdeps = {}
        if self.site.transect_pt_fc_exists:
            delimited_field_dep = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, utils.shpDepCol)
            # Loop through all transect at the site
            for t in self.site.transect_list:
                # Build where clause that looks like this: [tran_num] = 3 and [depth_interp] <> -9999
                delimited_field_id = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, utils.trkCol)
                where_clause = delimited_field_id + " = %d and " % t
                where_clause += delimited_field_dep + " <> %d" % utils.nullDep
                """Get results and find max and min depths
                    NOTE: Comparisons for max and min look backward because
                    Depths below MLLW are recorded with negative numbers
                    So, a maximum depth is actually the lowest number
                    and minimum depth is the highest number
                """
                results = arcpy.da.TableToNumPyArray(self.site.transect_pt_fc, (utils.trkCol, utils.shpDepCol),
                                                     where_clause)
                # Might need some checks for null results here.
                maxdep = results[utils.shpDepCol].min()
                mindep = results[utils.shpDepCol].max()
                self.maxtransdeps[t] = maxdep
                self.mintransdeps[t] = mindep

    def get_vegdeps(self):
        self.maxvegdeps = {}
        self.minvegdeps = {}
        # Create Delimited Field Names
        if self.site.transect_pt_fc_exists and self.site.veg_exists:
            delimited_field_dep = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, utils.shpDepCol)
            delimited_field_veg = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, self.site.veg_col)
            delimited_field_video = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, utils.videoCol)
            # Loop through all transects and get associated max/min depths where veg is present
            for t in self.site.transect_list:
                #print t
                # Build where clause that looks like this (with proper field delimiters) :
                # [tran_num] = 3 and [Zm] = 1 and [video] = 1 and [depth_interp] <> -9999
                delimited_field_id = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, utils.trkCol)
                where_clause = delimited_field_id + " = %d and " % t
                where_clause += delimited_field_veg + " = 1 and "
                where_clause += delimited_field_video + " = 1 and "
                where_clause += delimited_field_dep + " <> %d" % utils.nullDep
                """ Get results and find max and min depths
                    NOTE: Comparisons for max and min look backward because
                    Depths below MLLW are recorded with negative numbers
                    So, a maximum depth is actually the lowest number
                    and minimum depth is the highest number
                """
                results = arcpy.da.TableToNumPyArray(self.site.transect_pt_fc, (utils.trkCol, utils.shpDepCol,
                                                                self.site.veg_col, utils.videoCol),where_clause)
                # print where_clause
                # print results
                # print results[utils.shpDepCol].any()
                # Check for null results here.  (or try: except ValueError:  ??)
                if results[utils.shpDepCol].any():
                    maxdep = results[utils.shpDepCol].min()
                    mindep = results[utils.shpDepCol].max()
                else:
                    maxdep = utils.nullDep
                    mindep = utils.nullDep
                self.maxvegdeps[t] = maxdep
                self.minvegdeps[t] = mindep

    def get_translengths(self):
        self.trans_lengths = {}
        if arcpy.Exists(self.site.transect_ln_clip_fc):
            delimited_field_trktype = arcpy.AddFieldDelimiters(self.site.transect_ln_clip_fc, utils.trktypeCol)
            delimited_field_video = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, utils.videoCol)
            inclTrkTypesString = "(\'" + "\',\'".join(utils.trkType4Stats) + "\')"
            length_field = arcpy.Describe(self.site.transect_ln_clip_fc).lengthFieldName
            #print length_field

            # Loop through all transects at the site
            for t in self.site.transect_list:
                # Build where clause that looks like this: [tran_num] = 1 and [video] = 1 and [TrkType] in ('SLPR')
                delimited_field_id = arcpy.AddFieldDelimiters(self.site.transect_ln_clip_fc, utils.trkCol)
                where_clause = "%s = %d and " % (delimited_field_id, t)
                where_clause += "%s = %d and " % (delimited_field_video, 1)
                where_clause += "%s in %s" % (delimited_field_trktype, inclTrkTypesString)
                # Get results and sum the total length of the transect meeting the criteria
                results = arcpy.da.TableToNumPyArray(self.site.transect_ln_clip_fc,
                                                     (utils.trkCol, utils.trktypeCol, length_field),
                                                     where_clause)
                # Might need some checks for null results here.
                #print t, results[length_field]
                trans_length = results[length_field].sum()
                self.trans_lengths[t] = trans_length

    def get_veglengths(self):
        self.veg_lengths = {}
        if self.site.veg_exists and arcpy.Exists(self.site.transect_ln_clip_fc):
            delimited_field_veg = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, self.site.veg_col)
            delimited_field_video = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, utils.videoCol)
            delimited_field_trktype = arcpy.AddFieldDelimiters(self.site.transect_ln_clip_fc, utils.trktypeCol)
            inclTrkTypesString = "(\'" + "\',\'".join(utils.trkType4Stats) + "\')"
            length_field = arcpy.Describe(self.site.transect_ln_clip_fc).lengthFieldName

            # Loop through all transect at the site
            for t in self.site.transect_list:
                # Build where clause that looks like this:
                #   [tran_num] = 3 and [Zm] = 1 and [video] = 1 and [TrkType] in ('SLPR')
                delimited_field_id = arcpy.AddFieldDelimiters(self.site.transect_ln_clip_fc, utils.trkCol)
                where_clause = "%s = %d and " % (delimited_field_id, t)
                where_clause += "%s = %d and " % (delimited_field_veg, 1)
                where_clause += "%s = %d and " % (delimited_field_video, 1)
                where_clause += "%s in %s" % (delimited_field_trktype, inclTrkTypesString)
                # Get results and sum the total length of the transect meeting the criteria
                results = arcpy.da.TableToNumPyArray(self.site.transect_ln_clip_fc,
                                                     (utils.trkCol, utils.trktypeCol, length_field),
                                                     where_clause)
                # Might need some checks for null results here.
                veg_length = results[length_field].sum()
                self.veg_lengths[t] = veg_length

    def calc_vegfractions(self):
        self.veg_fractions = {}
        if self.trans_lengths and self.veg_lengths:
            for t, trans_len in self.trans_lengths.items():
                veg_len  = self.veg_lengths[t]
                try:
                    veg_fraction = veg_len / trans_len
                except ZeroDivisionError:
                    veg_fraction = 0.0
                #print transect, trans_len, veg_len, veg_fraction
                self.veg_fractions[t] = veg_fraction

    def get_dates(self):
        self.date_sampled = None
        self.trans_dates = {}
        if self.site.transect_pt_fc_exists:
            # Get unique combination for transect id and date.
            delimited_field_id = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, utils.trkCol)
            delimited_field_date = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, utils.shpDateCol)
            expression_prefix  = "DISTINCT"
            expression_postfix = "ORDER BY %s, %s" % (delimited_field_id,delimited_field_date)
            cursor = arcpy.da.SearchCursor(self.site.transect_pt_fc,
                                                    (utils.trkCol, utils.shpDateCol)
                                                    ,sql_clause=(expression_prefix, expression_postfix))
            results = [[r[0],r[1]] for r in cursor]
            del cursor
            #valueDict = {r[0]:[r[1],r[2]] for r in arcpy.da.SearchCursor(myFC, ["OID@","ID","NAME"])}
            # print map(max, zip(*results)) -- gets max of both columns
            self.date_sampled = min(zip(*results)[1])
            for r in results:
                self.trans_dates[r[0]] = r[1]

class SiteStatistics:
    """ Represents the Site Level Statistics for SVMP site
    Properties
    transects -- Transects object
    siteid -- unique Site identifier
    sitestat_id -- unique identifier for site and sampling occasion combination
    site_results_id -- unique identifier for site, sampling occasion, veg combination
    sample_lengths -- A list of the site's individual transect lengths
    vegetation_lengths -- A list of the site's individual transect vegetation lengths
    max_deps_4stats -- A list of maximum depths passing criteria for use for mean stats
    min_deps_4stats -- A list of minimum depths passing criteria for use for mean stats
    veg_fraction -- estimated mean vegetation fraction
    n_area -- number of transects used in area calculations
    mean_transect_length -- mean transect length
    sample_area -- sample area
    veg_area -- vegetation area
    var_vegfraction -- variance of the vegetation fraction
    var_vegarea -- variance of the vegetation area
    se_vegarea -- standard error of the vegetation area

    """
    def __init__(self,transects):
        self.transects = transects
        self.siteid = self.transects.site.id
        self.sitestat_id = self.transects.site.sitestat_id
        self.site_results_id = self.transects.site.site_results_id
        self.sample_lengths = self.transects.trans_lengths.values()
        self.vegetation_lengths = self.transects.veg_lengths.values()
        self.max_deps_4stats = self.get_depths4stats(self.transects.maxvegdeps,self.transects.maxflags)
        self.min_deps_4stats = self.get_depths4stats(self.transects.minvegdeps,self.transects.minflags)

    @property
    def veg_fraction(self):
        """Estimated mean vegetation fraction (P Bar Hat) """
        # sum_samplelen = sum(self.sample_lengths)
        # sum_veglen = sum(self.vegetation_lengths)
        try:
            return sum(self.vegetation_lengths) / sum(self.sample_lengths)
        except ZeroDivisionError:
            return 0.0

    @property
    def n_area(self):
        """ Number of transects used in area calculations """
        return len(self.sample_lengths)

    @property
    def mean_transect_length(self):
        """Mean transect lengths (L bar) """
        try:
            return sum(self.sample_lengths) / self.n_area
        except ZeroDivisionError:
            return 0.0

    @property
    def sample_area(self):
        """ Area of the sample polygon """
        if self.transects.site.sample_poly_exists:
            sample_poly = self.transects.site.sample_poly_fc
            # Build where clause like this: [sitestat_id] = 'hdc2334_2014'
            delimited_field = arcpy.AddFieldDelimiters(sample_poly, utils.sitestatidCol)
            where_clause = delimited_field + " = " + "'%s'" % (self.sitestat_id)
            # Make NumPy Array from table and see if it returns a result
            results = arcpy.da.FeatureClassToNumPyArray(sample_poly, "SHAPE@AREA", where_clause)
            return results["SHAPE@AREA"].sum()

    @property
    def veg_area(self):
        """ Area of the vegetation at the site """
        try:
            return self.veg_fraction * self.sample_area
        except ZeroDivisionError:
            return 0.0

    @property
    def var_vegfraction(self):
        """ Estimated variance of the vegetation fraction """
        return utils.ratioEstVar(self.sample_lengths,self.vegetation_lengths,self.veg_fraction,
                                 self.n_area,self.mean_transect_length)

    @property
    def var_vegarea(self):
        """ Estimated variance of the vegetation area """
        return self.var_vegfraction * (self.sample_area ** 2)

    @property
    def se_vegarea(self):
        """ Standard error of the vegetation area """
        return self.var_vegarea ** 0.5

    def get_depths4stats(self,depth_dict,flag_dict):
        """ Return a list of depth values meeting criteria for use in stats calculations
            Must have Track type in the list of types used for stats (SLPR)
            And must have a depth flag = 1 (yes)
        """
        depths = []
        for t, trktype in self.transects.trktypes.items():
            if trktype in utils.trkType4Stats:
                if flag_dict[t] == 1:
                    depths.append(depth_dict[t])
        return depths

    @property
    def n_veg_mindep(self):
        """ Number of transects used for mean vegetation minimum depth """
        # n = 0
        # for t in self.transects.transect_list:
        #     try:
        #         if self.transects.minflags[t] == 1:
        #             if self.transects.trktypes[t] in utils.trkType4Stats:
        #                 n += 1
        #     except IndexError:
        #         pass
        return len(self.min_deps_4stats)


    @property
    def n_veg_maxdep(self):
        """ Number of transects used for mean vegetation maximum depth """
        # n = 0
        # for t in self.transects.transect_list:
        #     try:
        #         if self.transects.maxflags[t] == 1:
        #             if self.transects.trktypes[t] in utils.trkType4Stats:
        #                 n += 1
        #     except IndexError:
        #         pass
        return len(self.max_deps_4stats)

    @property
    def veg_mind_mean(self):
        """ Mean of minimum vegetation depth """
        # dep_sum = 0
        # # print self.transects.trktypes
        # # print self.transects.minflags
        # # print self.transects.minvegdeps
        # for t, trktype in self.transects.trktypes.items():
        #     if trktype in utils.trkType4Stats:
        #         if self.transects.minflags[t] == 1:
        #             dep_sum += self.transects.minvegdeps[t]
        # return dep_sum / self.n_veg_mindep
        return sum(self.min_deps_4stats) / self.n_veg_mindep

    @property
    def veg_maxd_mean(self):
        """ Mean of maximum vegetation depth """
        # dep_sum = 0
        # # print self.transects.trktypes
        # # print self.transects.maxflags
        # # print self.transects.maxvegdeps
        # for t, trktype in self.transects.trktypes.items():
        #     if trktype in utils.trkType4Stats:
        #         if self.transects.maxflags[t] == 1:
        #             dep_sum += self.transects.maxvegdeps[t]
        # return dep_sum / self.n_veg_mindep
        return sum(self.max_deps_4stats) / self.n_veg_maxdep

    @property
    def veg_mind_se(self):
        """ Standard error of the vegetation minimum depth """
        if self.n_veg_mindep > 1:
            stdev = utils.stdDev(self.min_deps_4stats)
            return utils.stdErr(stdev, self.n_veg_mindep)
        else:
            return utils.nullDep

    @property
    def veg_maxd_se(self):
        """ Standard error of the vegetation minimum depth """
        if self.n_veg_maxdep > 1:
            stdev = utils.stdDev(self.max_deps_4stats)
            return utils.stdErr(stdev, self.n_veg_maxdep)
        else:
            return utils.nullDep

    @property
    def veg_mind_shallowest(self):
        """ Site shallowest vegetation depth
        Note: Counter-intuitive use of max/min because depths below MLLW are negative
        Using all depth values, not certain Track Types (like for mean)
        """
        return max(self.transects.minvegdeps.values())

    @property
    def veg_maxd_deepest(self):
        """ Site deepest vegetation depth
        Note: Counter-intuitive use of max/min because depths below MLLW are negative
        Using all depth values, not certain Track Types (like for mean)
        """
        return min(self.transects.maxvegdeps.values())






class Transect:
    """ Represents the SVMP data for a transect

    Properties
    site -- Site object
    id -- transect id
    maxdep_flag -- Flag indicating transect can be used for vegetation max depth
    mindep_flag -- Flag indicating transect can be used for vegetation min depth
    track_type -- transect type
    maxdep -- maximum depth of transect
    mindep -- minimum depth of transect
    maxdep_veg -- maximum depth of vegetation on transect
    mindep_veg -- minimum depth of vegetation on transect


    """

    def __init__(self, site, id):
        """ Pass in a site object to initialize"""
        self.site = site
        self.id = id


class SiteGroup:
    """ Represents a group of SVMP sites to be processed together with common parameters

    Attributes
    sites -- a list of site objects
    sampling_occasion -- sampling occasion (for example, year)
    veg_type -- vegetation type to be summarized
    transect_gdb -- geodatabase containing transect point feature classes
    sample_poly_fc -- Sample polygon feature class
    ctl_directory -- Parent directory for control files
    site_db -- output database with template tables (sites, transects)
    """

    def __init__(self, sites_list, sampling_occasion, veg_type, transect_gdb, sample_poly_fc, ctl_directory, site_db):
        self.sites = []
        self.import_sites(sites_list)
        self.sampling_occasion = sampling_occasion
        self.veg_type = veg_type
        self.transect_gdb = transect_gdb
        self.sample_poly_fc = sample_poly_fc
        self.ctl_directory = ctl_directory
        self.site_db = site_db


    def import_sites(self, sites_list):
        """
        Create Site objects from a list of site data.
        Append these sites objects to a sample
        """

    def _addSite(self, site):
        """ Adds individual site objects to the sample. """
        self.sites.append(site)

    def _site_attrs(self, attr):
        return [getattr(site, attr) for site in self.sites]


if __name__ == '__main__':
    import doctest

    doctest.testmod(verbose=True, report=True)

