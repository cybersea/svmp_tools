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
        self.sitestat_id = "".join((self.id,"_",self.sampling_occasion))
        self.site_results_id = "".join((self.id,"_",self.sampling_occasion,"_",veg_col))
        self.transect_gdb = transect_gdb
        self.sample_poly_fc = sample_poly_fc
        self.ctl_directory = ctl_directory

    @property
    def transect_pt_fc(self):
        """ Transect Point Feature class full path"""
        fc_name = "".join((self.id, "_", self.sampling_occasion, utils.ptFCSuffix))
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
        # Build where clause like this: sitestat_id = "hdc2334_2014"
        delimited_field = arcpy.AddFieldDelimiters(self.sample_poly_fc, utils.sitestatidCol)
        where_clause = delimited_field + " = " + "'%s'" % (self.sitestat_id)
        # Make NumPy Array from table and see if it returns a result
        results = arcpy.da.TableToNumPyArray(self.sample_poly_fc, utils.sitestatidCol, where_clause)
        #print results - for debugging
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
    """

    def __init__(self,site):
        self.site = site
        self.transect_list = self.site.transect_list
        self.get_trans_results_ids()
        self.get_trkflags()
        self.get_transdeps()
        self.get_vegdeps()

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
                [att,val] = line.split(",")
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
                    elif val == utils.ctlNo:
                        maxflag = 0
                    self.maxflags[trk]= maxflag
                # Get Minimum Depth Flag
                if att == utils.ctlMinAtt:
                    if val == utils.ctlYes:
                        minflag = 1
                    elif val == utils.ctlNo:
                        minflag = 0
                    self.minflags[trk]= minflag

    def get_transdeps(self):
        self.maxtransdeps = {}
        self.mintransdeps = {}
        if self.site.transect_pt_fc_exists:
            delimited_field_dep = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, utils.shpDepCol)
            # Loop through all transect at the site
            for t in self.site.transect_list:
                # Build where clause that looks like this: tran_num = 1 and depth_interp <> -9999
                delimited_field_id = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, utils.trkCol)
                where_clause = delimited_field_id + " = %d and " % t
                where_clause += delimited_field_dep + " <> %d" % utils.nullDep
                """Get results and find max and min depths
                    NOTE: Comparisons for max and min look backward because
                    Depths below MLLW are recorded with negative numbers
                    So, a maximum depth is actually the lowest number
                    and minimum depth is the highest number
                """
                results = arcpy.da.TableToNumPyArray(self.site.transect_pt_fc, (utils.trkCol,utils.shpDepCol),
                                                     where_clause)
                # Might need some checks for null results here.
                maxdep = results[utils.shpDepCol].min()
                mindep = results[utils.shpDepCol].max()
                self.maxtransdeps[t] = maxdep
                self.mintransdeps[t] = mindep

    def get_vegdeps(self):
        self.maxvegdeps = {}
        self.minvegdeps = {}
        if self.site.transect_pt_fc_exists and self.site.veg_exists:
            delimited_field_dep = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, utils.shpDepCol)
            delimited_field_veg = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, self.site.veg_col)
            delimited_field_video = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, utils.videoCol)

            #results = arcpy.da.TableToNumPyArray(self.site.transect_pt_fc, (utils.trkCol,utils.shpDepCol,utils.videoCol))
            # print results
            for t in self.site.transect_list:
                # Build where clause that looks like this (with proper field delimiters) :
                # tran_num = 3 and Zm = 1 and video = 1 and depth_interp <> -9999
                delimited_field_id = arcpy.AddFieldDelimiters(self.site.transect_pt_fc, utils.trkCol)
                where_clause = delimited_field_id + " = %d and " % t
                where_clause += delimited_field_veg + " = 1 and "
                where_clause += delimited_field_video + " = 1 and "
                where_clause += delimited_field_dep + " <> %d" % utils.nullDep
                """Get results and find max and min depths
                    NOTE: Comparisons for max and min look backward because
                    Depths below MLLW are recorded with negative numbers
                    So, a maximum depth is actually the lowest number
                    and minimum depth is the highest number
                """
                results = arcpy.da.TableToNumPyArray(self.site.transect_pt_fc, (utils.trkCol,utils.shpDepCol,
                                                        self.site.veg_col,utils.videoCol),where_clause)
                # Might need some checks for null results here.
                maxdep = results[utils.shpDepCol].min()
                mindep = results[utils.shpDepCol].max()
                self.maxvegdeps[t] = maxdep
                self.minvegdeps[t] = mindep





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

