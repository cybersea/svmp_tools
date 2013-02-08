""" Calculates Soundwide Zostera marina 2-year area change and error estimates """

""" 
Tool Name:  SWAreaChange
Tool Label: SW Area Change
Source Name: sw_area_change_93.py
Version: ArcGIS 9.3
Author: Allison Bailey, Sound GIS
For: Washington DNR, Submerged Vegetation Monitoring Program (SVMP)
Date: December 2009 -- Updated January 2010 for Arc 9.3 geoprocessor
Requires: Python 2.5.1

This script calculates soundwide Zostera marina area change estimates
between two (usually) consecutive survey years.
Calculates Monte Carlo 95% Confidence Intervals (20,000 iterations)

# Parameters:
INPUT
(1) siteTable -- Site statistics geodatabase table (full path)
(2) allsitesFC -- Feature Class containing point locations for all sites (full path)
(3) flatsFC -- ArcGIS feature class for flats sites (full path)
(4) fringeFC -- ArcGIS feature class for fringe sites (full path)
(5) year1 -- First Survey year for data to be processed
(6) year2 -- Second survey year for the data to be processed
OUTPUT
(7) outFileStratum -- Output file name for Area Estimates by Stratum (full path)
(8) outFileAll -- Output file name for Area Estimates for All Strata Combined (full path)
(9) outFileRC -- Output file name for Monte Carlo Relative Change values (full path) -- not currently being used



"""

import sys
import arcgisscripting
import svmp_93 as svmp 
import svmp_spatial_93 as spatial
import svmpUtils as utils
from svmp_exceptions import SvmpToolsError

#-------------- FUNCTIONS ---------------------------------
# Function for inverting a dictionary
def invert_dict(dict):
    inverse = {}
    for (key, value) in dict.items():
        if value not in inverse:
            inverse[value] = []
        inverse[value].append(key)
    return inverse

# Get List of Site data, corresponding to the specified extrapolation type
def group_data_by_extrap(extrap_site_dict,extrap,site_stats_dict):
    # get list of sites for the specified analysis stratum and extrapolation
    site_list = extrap_site_dict[extrap]
    
    # Extract the specified site data from the site statistics dictionary
    dat = []    
    for s in site_list:
        vals = site_stats_dict[s]
        dat.append(vals)
        
    return dat

def query_results(gp,fc,return_fields,query_string,key_field = None):
    """ Generic function for creating ArcGIS query object and returning results """
    query = spatial.TableQuery(gp,fc,query_string)
    results = query.field_results(return_fields,key_field)
    return results

def sites_strata(gp,fc,group,year1,year2=None):
    """ Create dictionary of sites sampled in a single year or 
        matching sites sampled in both years
        from a particular "group" (soundwide being the only implemented option)
    """
    return_fields = [utils.siteGeoStratCol,utils.siteSampStratCol]   # STRATA_GEO, STRATUM
    key_field = utils.sitePtIDCol   # NAME    
    if group == "soundwide":
        #------ Query String: Soundwide sites for the specified years ---
        # -- Should look like this: ("Y2008" = 1 or "Y2008" = 8) and ("Y2009" = 1 or "Y2009" = 8)
        yr1_field = "Y%s" % year1
        query_string = "(%s = 1 or %s = 8)" % (yr1_field,yr1_field)
        if year2 is not None:
            yr2_field = "Y%s" % year2
            query_string += " and (%s = 1 or %s = 8)" % (yr2_field,yr2_field)
            
    results = query_results(gp,fc,return_fields,query_string,key_field)
    return results
    
##--Extract data from sites statistics database using site ID and date query
def sites_data(gp,sites,year,table):
    """ Create a dictionary of sites and their associated Zm area and variance """
    siteid_field = utils.siteCol   # site_code
    date_field = utils.samplestartdateCol
    return_fields = (utils.siteCol,utils.est_basalcovCol,utils.estvar_basalcovCol) 
    #------ Query String: List of sites within the specified year ---
    #  Example:  site_code in ('core001','core002','core005')
    query_string = "%s in (%s)" % (siteid_field, sites)
    # Example: date_samp_start >= #01-01-2007# and date_samp_start <= #12-31-2007#
    query_string += " and %s >= #01-01-%i# and %s <= #12-31-%i#" % (date_field, year, date_field, year)   
    results = query_results(gp,table,return_fields,query_string,siteid_field)
    return results

def missing_site_check(master_list,sites2check,table,year):
    """ Checks for missing sites based on a master list 
        Generates error text and calls error object if missing
    """
    missing_sites = set(master_list).difference(sites2check)
    if missing_sites:
        err_text = "The sites database table, %s, is missing site(s)\n" % table
        err_text += ",".join(missing_sites)
        err_text += "\nfor the year, %s" % year
        e.call(err_text)

def strata_lookup(sites_strata,lookup_dict):
    """Create dictionary of extrapolation type by site id
       using lookup from analysis/geo stratum to 
       determine analysis and extrapolation type
    """
    site_extrap = {}
    for (siteid,data) in sites_strata.items():
        site_extrap[siteid] = lookup_dict[tuple(data)]
    # invert this dictionary to get sites by extrapolation/analysis stratum
    extrap_site = invert_dict(site_extrap)
    return extrap_site
#------------------------------------------------------------

#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
#MAIN

if __name__ == "__main__":

    try:

        #---- Create the Geoprocessing Object ----------------------
        gp = arcgisscripting.create(9.3)
        
        #----- Create the Custom Error Object ----------------------
        e = SvmpToolsError(gp)
        # Set some basic defaults for error handling
        e.debug = True
        e.full_tb = True
        
        #-------- unit conversion flag --------------------
        unit_convert = "sf2m"
        
        def msg(msg):
            gp.AddMessage(msg)
        
            
        # ----------- PARAMETERS ----------------------------------
        # Temporary stand-ins for parameters
        #dbPath = "c:/projects/dnr_svmp/output/eelgrass_monitoring/"
        #blPath = "c:/projects/dnr_svmp/output/eelgrass_monitoring/base_layers/"
        #outPath = "c:/projects/dnr_svmp/output/eelgrass_monitoring/ab_out/"
        #siteTable = dbPath  + "svmp_sitesdb_2009_12_21.mdb/all_years_sites"  #"svmp_sitesdb_2009_12_21.mdb/2007sites"
        ##siteTable2 = dbPath  + "svmp_sitesdb_2009_12_21.mdb/all_years_sites"  #"svmp_sitesdb_2009_12_21.mdb/2008sites"
        #allsitesFC = blPath + "svmp_all_sites_041309_samptype.shp"
        #flatsFC = blPath + "flats.shp"
        #fringeFC = blPath + "fringe.shp"
        #year1 = 2007
        #year2 = 2008
        #outFileStratum = "areachg_20072008_stratum.csv"
        #outFileAll = "areachg_20072008_all.csv"
        #outFileRC = "mc_rc_20072008.csv"
        ## placeholder -- may be implemented as a parameter later 
        ##    (for soundwide, focus and other sites)
        #sample_group = "soundwide" 
        
        # Get parameters from ArcToolbox input or command line        
        siteTable = gp.GetParameterAsText(0)
        allsitesFC = gp.GetParameterAsText(1)
        flatsFC = gp.GetParameterAsText(2)
        fringeFC = gp.GetParameterAsText(3)
        year1 = int(gp.GetParameterAsText(4))
        year2 = int(gp.GetParameterAsText(5))
        
        sample_group = gp.GetParameterAsText(6)
        outFileStratum = gp.GetParameterAsText(7)
        outFileAll = gp.GetParameterAsText(8)
        #outFileRC = gp.GetParameterAsText(9)   #not being used currently
        

        unit_convert = "sf2m"   # unit conversion flag  -- survey feet to meters
        
        #------- Delete output files if they already exist -----------------
        #def outfile_exists(file):
            #if gp.Exists(file):
                #gp.Delete(file)            
        #outfile_exists(outFileStratum)
        #outfile_exists(outFileAll)
        # Produces this: ERROR: Geoprocessing Error: ERROR 000601: Cannot delete areachg_20072008_all.csv.  May be locked by another application.
        
        #------------------   DATA QUERIES AND GROUPING --------------------------------
        #-------------------------------------------------------------------------------
        #----------------- MATCHING SITES sampled in YEARS 1 & 2 -----------------------
        #-------------------------------------------------------------------------------
        # Get list of sites sampled in both years and their strata
        msg("-- Matching Sites Queries for %s and %s" % (year1,year2))
        msg(" Querying the All Sites Feature Class:\n  %s" % allsitesFC)
        sites_strata_2yr = sites_strata(gp,allsitesFC,sample_group,year1,year2)
        sites2yr = sorted(sites_strata_2yr.keys())
        # For use in query strings
        sites2yr_string = "'" + "\',\'".join(sites2yr) + "'" 
        
        # Get data from site stats database table for the matching sites
        msg(" Querying the Sites Statistics Table:\n  %s" % siteTable)
        data_y1m = sites_data(gp,sites2yr_string,year1,siteTable)
        data_y2m = sites_data(gp,sites2yr_string,year2,siteTable)
        
        # Check for missing sites in sites stats DB query results
        msg(" Comparing site list from All Sites Feature Class and Sites Database Table")
        missing_site_check(sites2yr,data_y1m.keys(),siteTable,year1)
        missing_site_check(sites2yr,data_y2m.keys(),siteTable,year2)
        
        ## Sites grouped by extrapolation type
        extrap_sites2yr = strata_lookup(sites_strata_2yr,svmp.sw_Stratum4AreaChgCalcs)
        
        # Group matching site data into lists by analysis/extrapolation type
        core_y1m = group_data_by_extrap(extrap_sites2yr,svmp.core_extrap,data_y1m)
        fl_y1m = group_data_by_extrap(extrap_sites2yr,svmp.fl_extrap,data_y1m)
        fr_y1m = group_data_by_extrap(extrap_sites2yr,svmp.fr_extrap,data_y1m)
        frw_y1m = group_data_by_extrap(extrap_sites2yr,svmp.frw_extrap,data_y1m)
        
        core_y2m = group_data_by_extrap(extrap_sites2yr,svmp.core_extrap,data_y2m)
        fl_y2m = group_data_by_extrap(extrap_sites2yr,svmp.fl_extrap,data_y2m)
        fr_y2m = group_data_by_extrap(extrap_sites2yr,svmp.fr_extrap,data_y2m)
        frw_y2m = group_data_by_extrap(extrap_sites2yr,svmp.frw_extrap,data_y2m)
        
        # Get the sample area (from flats shapefile) for rotational flats sites
        # and append to rotational flats data
        def add_samplearea(flats_data,extrap_sites):
            fl_sites = extrap_sites[svmp.fl_extrap]
            fl_sites_string = "'" + "\',\'".join(fl_sites) + "'" 
            siteid_field = utils.sitePtIDCol   # NAME    
            # query will look something like this: NAME in ('site1','site2','site5')
            query_string = "%s in (%s)" % (siteid_field, fl_sites_string)
            flats_query = spatial.FeatureQuery(gp,flatsFC,query_string)
            # Dictionary of rotational flats sites with their sample area from flats.shp
            flats_a2j = flats_query.field_results([flats_query.shape_field],siteid_field)
            
            # Append the sample area to the rest of the site data (rotational flats only)
            for site in flats_data:
                a2j = flats_a2j[site[0]][0]
                site.append(a2j)
                
            return flats_data
        
        msg(" Querying flats shapefile for sample area:\n  %s" % flatsFC)
        fl_y1m = add_samplearea(fl_y1m,extrap_sites2yr)
        fl_y2m = add_samplearea(fl_y2m,extrap_sites2yr)
        
        #--------------------- End MATCHING SITES --------------------------------------
            
        #----------------------- ALL SITES sampled in YEAR 1 ---------------------------
        # Get list of sites from Year 1 and associated strata
        msg("-- Year 1 Queries for %s" % year1)
        msg(" Querying the All Sites Feature Class:\n  %s" % allsitesFC)
        
        sites_strata_y1 = sites_strata(gp,allsitesFC,sample_group,year1)
        sites_y1 = sorted(sites_strata_y1.keys())
        # For use in query strings
        sites_y1_string = "'" + "\',\'".join(sites_y1) + "'" 
        
        # Get data from site stats database table
        msg(" Querying the Sites Statistics Table:\n  %s" % siteTable)
        data_y1 = sites_data(gp,sites_y1_string,year1,siteTable)
        
        # Check for missing sites in sites stats DB query results
        msg(" Comparing site list from All Sites Feature Class and Sites Database Table")
        missing_site_check(sites_y1,data_y1.keys(),siteTable,year1)
        
        # Sites grouped by extrapolation type
        extrap_sites_y1 = strata_lookup(sites_strata_y1,svmp.sw_Stratum4AreaChgCalcs)
        
        # Group site data into lists by analysis/extrapolation type
        core_y1 = group_data_by_extrap(extrap_sites_y1,svmp.core_extrap,data_y1)
        fl_y1 = group_data_by_extrap(extrap_sites_y1,svmp.fl_extrap,data_y1)
        fr_y1 = group_data_by_extrap(extrap_sites_y1,svmp.fr_extrap,data_y1)
        frw_y1 = group_data_by_extrap(extrap_sites_y1,svmp.frw_extrap,data_y1)
        
        msg(" Querying flats shapefile for sample area:\n  %s" % flatsFC)
        fl_y1 = add_samplearea(fl_y1,extrap_sites_y1)
        
        #----------------------- End SITES sampled in YEAR 1 ---------------------------
        
        #------------------   End DATA QUERIES AND GROUPING ----------------------------
        #-------------------------------------------------------------------------------
        
        #-------------------------------- CALCULATIONS ---------------------------------
        #---------------------------------- Strata -------------------------------------
        # Performs Sample Calculations for 
        # Year 1 matching sites, Year 2 matching sites, and Year 1 all sites
        # This is necessary input to Change Analysis Calculations
        
        def core_sample_calc(data):
            coreStratum = svmp.BaseStratum(svmp.core_extrap[0],svmp.core_extrap[1])
            coreSamp = svmp.SampleStats(data,coreStratum,unit_convert)
            return coreSamp
        msg("Calculating Area Change for Core stratum, %s to %s" % (year1,year2))
        coreSamp_y1m = core_sample_calc(core_y1m)
        coreSamp_y2m = core_sample_calc(core_y2m)
        coreSamp_y1 = core_sample_calc(core_y1)
        coreChange = svmp.ChangeStats(coreSamp_y1m,coreSamp_y2m,coreSamp_y1)
        
        def flats_sample_calc(data):
            flatsStratum = svmp.FlatsStratum(svmp.fl_extrap[0],svmp.fl_extrap[1],gp,flatsFC,unit_convert)
            flatsSamp = svmp.SampleStats(data,flatsStratum,unit_convert)
            return flatsSamp
        msg("Calculating Area Change for Rotational Flats stratum, %s to %s" % (year1,year2))
        flSamp_y1m = flats_sample_calc(fl_y1m)
        flSamp_y2m = flats_sample_calc(fl_y2m)
        flSamp_y1 = flats_sample_calc(fl_y1)
        flChange = svmp.ChangeStats(flSamp_y1m,flSamp_y2m,flSamp_y1)
        
        def fringe_sample_calc(data):
            fringeStratum = svmp.FringeStratum(svmp.fr_extrap[0],svmp.fr_extrap[1],gp,fringeFC,unit_convert)
            fringeSamp = svmp.SampleStats(data,fringeStratum,unit_convert)
            return fringeSamp
        msg("Calculating Area Change for Fringe stratum, %s to %s" % (year1,year2))
        frSamp_y1m = fringe_sample_calc(fr_y1m)
        frSamp_y2m = fringe_sample_calc(fr_y2m)
        frSamp_y1 = fringe_sample_calc(fr_y1)
        frChange = svmp.ChangeStats(frSamp_y1m,frSamp_y2m,frSamp_y1)
        
        def wide_fringe_sample_calc(data):
            fringewideStratum = svmp.FringeStratum(svmp.frw_extrap[0],svmp.frw_extrap[1],gp,fringeFC,unit_convert)
            fringewideSamp = svmp.SampleStats(data,fringewideStratum,unit_convert)
            return fringewideSamp
        msg("Calculating Area Change for Wide Fringe stratum, %s to %s" % (year1,year2))
        frwSamp_y1m = wide_fringe_sample_calc(frw_y1m)
        frwSamp_y2m = wide_fringe_sample_calc(frw_y2m)
        frwSamp_y1 = wide_fringe_sample_calc(frw_y1)
        frwChange = svmp.ChangeStats(frwSamp_y1m,frwSamp_y2m,frwSamp_y1)
        
        #--------------------------- Totals ALL STRATA Combined ------------------------
        #-------------------------------------------------------------------------------
        def annual_sample_calc(samples):
            annual = svmp.AnnualEstimate(samples)
            #print "****** Annual Estimate, Year 1 *********"
            #print "Area: %r" % annual.zm_area
            #print "Variance: %r" % annual.zm_area_var
            #print "s.e.: %r" % annual.se
            #print "cv: %r" % annual.cv
            return annual
        
        # Annual Estimate for Year 1, All strata combined
        msg("Calculating Area Change for all strata combined, %s to %s" % (year1,year2))
        y1annualCalc = annual_sample_calc((coreSamp_y1,flSamp_y1,frSamp_y1,frwSamp_y1))
        # Area Change for all strata combined, Year 1 to Year 2
        zmChangeAll = svmp.ChangeStatsTotal((coreChange,flChange,frChange,frwChange),y1annualCalc)
        
        #------------------------------ End CALCULATIONS -------------------------------
        #-------------------------------------------------------------------------------

        
        #------------------------------ MONTE CARLO CI ---------------------------------
        #-------------------------------------------------------------------------------
        
        def mc_stratum(y1_data,y1match_data,y2match_data,stratum,unit_convert=None):
            """ 
            Perform sampling error (bootstrap) and measurement error simulations
            to calculate area change statistics with simulated data from a single stratum
            """
            # Bootstrap Sample (Sampling Error)
            # Don't do bootstrap for core sites (non-subsampled) or strata with < 8 sites 
            if len(y1_data) < 8 or stratum.analysis == "core":
                y1 = y1_data[:]
                y1m = y1match_data[:]
                y2m = y2match_data[:]
            else:
                y1 = svmp.bootstrap(y1_data)
                y1m = svmp.bootstrap(y1match_data)
                y2m = svmp.match_sites(y1m,y2match_data)
            # Measurement Error - Simulated Zm area
            me1 = svmp.measurement_error(y1)
            me1m = svmp.measurement_error(y1m)
            me2m = svmp.measurement_error(y2m)
            # Printng for DEBUG only
            #for d in me1:
                #yr1_string = ','.join(["%s" % i for i in d[0:2]])
                #yr1_string = "%s,%s" % ("Y1",yr1_string)
                ## print yr1_string  # for debug only
            #for c,d in zip(me1m,me2m):
                #yr1m_string = ','.join(["%s" % i for i in c[0:2]])
                #yr1m_string = "%s,%s" % ("Y1m",yr1m_string)
                #yr2m_string = ','.join(["%s" % i for i in d[0:2]])
                #yr2m_string = "%s,%s" % ("Y2m",yr2m_string)
                #allmatch_string = "%s,%s" % (yr1m_string,yr2m_string)
                ## print allmatch_string # for debug only
                
             # Calculate Change Analysis stats with Simulated Data
            y1Samp  = svmp.SampleStats(me1,stratum,unit_convert)
            y1mSamp = svmp.SampleStats(me1m,stratum,unit_convert)
            y2mSamp = svmp.SampleStats(me2m,stratum,unit_convert)  
            change = svmp.ChangeStats(y1mSamp,y2mSamp,y1Samp)
            # Relative Change
            return (y1Samp,y1mSamp,y2mSamp,change)
        
        # For debugging only
        def mc_sites_out(i,label,changeObj):
            for s1,s2,a1,a2 in zip(changeObj.y1m.site_ids,changeObj.y2m.site_ids,changeObj.y1m.zm_areas,changeObj.y2m.zm_areas):
                # iteration, stratum, Year1 site, Year2 site, Year1 simulated Zm area, Year2 simulated Zm area
                print "%i,%s,%s,%s,%r,%r" % (i,label,s1,s2,a1,a2)

        
        def mc_relative_change(iterations,outFile=None):
            """
            Calculates relative change values using Monte Carlo analysis
            iterations -- number of Monte Carlo iterations (usually 20,000)
            outFile -- optional output file for list of Relative change values
            """
                
            if outFile:
                output = open(outFile,'w')
                output.write("run,RC\n")
                
            rel_changes = []
            for i in range(iterations):
                #--------- Monte Carlo Change calculations by Stratum
                # Core
                (core_y1_mcSamp,core_y1m_mcSamp,core_y2m_mcSamp,core_mcChange) = mc_stratum(core_y1,core_y1m,core_y2m,coreSamp_y1.stratum,unit_convert)
                # Rotational Flats
                (fl_y1_mcSamp,fl_y1m_mcSamp,fl_y2m_mcSamp,fl_mcChange) = mc_stratum(fl_y1,fl_y1m,fl_y2m,flSamp_y1.stratum,unit_convert)        
                # Fringe Sites
                (fr_y1_mcSamp,fr_y1m_mcSamp,fr_y2m_mcSamp,fr_mcChange) = mc_stratum(fr_y1,fr_y1m,fr_y2m,frSamp_y1.stratum,unit_convert)
                # Wide Fringe
                (frw_y1_mcSamp,frw_y1m_mcSamp,frw_y2m_mcSamp,frw_mcChange) = mc_stratum(frw_y1,frw_y1m,frw_y2m,frwSamp_y1.stratum,unit_convert)
                
                # For debugging
                #mc_sites_out(i,"Core",core_mcChange)
                #mc_sites_out(i,"Flats",fl_mcChange)
                #mc_sites_out(i,"Fringe",fr_mcChange)
                #mc_sites_out(i,"Wide Fringe",frw_mcChange)
                
                #-- Monte Carlo All strata calculations - annual estimate and area change
                # Annual Estimate for Year 1, All strata combined
                y1_mcAnnualCalc = annual_sample_calc((core_y1_mcSamp,fl_y1_mcSamp,fr_y1_mcSamp,frw_y1_mcSamp))
                # Area Change for all strata combined, Year 1 to Year 2
                mc_zmChangeAll = svmp.ChangeStatsTotal((core_mcChange,fl_mcChange,fr_mcChange,frw_mcChange),y1_mcAnnualCalc)
                rc = mc_zmChangeAll.change_prop
                
                #--- Store Relative Change value for each iteration
                rel_changes.append(rc)
                
                if outFile:
                    out_string = "%i,%r\n" % (i,rc)
                    output.write(out_string) 
                
            if outFile:
                output.close()
                
            return rel_changes

        
        msg("Calculating Monte Carlo Confidence Intervals.  This may take a couple minutes...")
        # Calculate Relative Change list - 20,000 iterations
        #rel_changes = mc_relative_change(20000,outFileRC)
        rel_changes = mc_relative_change(20000)
        # Calculate Monte Carlo 95% confidence interval
        mc_ci = svmp.conf_int(rel_changes,0.95)
                
        #------------------------------ End MONTE CARLO CI -----------------------------
        #-------------------------------------------------------------------------------
        
        
        #-----------------------------------   OUTPUT ----------------------------------
        #-------------------------------------------------------------------------------
        
        def output_strata(label,changeObj):
            msg("******  %s *********" % label)
            msg("Year 1 Area: %r" % changeObj.y1.zm_area)
            msg("Year 1 Variance: %r" % changeObj.y1.zm_area_var)
            msg("Matching Sites")
            for site in sorted(changeObj.y1m.site_ids):
                msg("  %s" % site)
            #print "Year 1 Site Count: %i" % changeObj.y1.ni
            #print "Matching Site Count: %i" % changeObj.y1m.ni
            #print "Slope: %r" % changeObj.m
            #print "S.E. of Slope: %r" % changeObj.m_se
            #print "Proportion Change: %r" % changeObj.change_prop
            #print "Percent Change: %r" % (changeObj.change_prop * 100)
            #print "Area Change (m2): %r" % changeObj.area_change
            #print "S.E. of Area Change: %r" % changeObj.area_change_se
        
        #msg("Zostera marina Soundwide Change Stats for %i to %i" % (year1,year2))
        output_strata("Core",coreChange)
        output_strata("Flats",flChange)
        output_strata("Fringe",frChange)
        output_strata("Wide Fringe",frwChange)
        
        def output_sw(label,changeObj):
            print "******  %s *********" % label
            print "Proportion Change: %r" % changeObj.change_prop
            print "Percent Change: %r" % (changeObj.change_prop * 100)
            print "Area Change (m2): %r" % changeObj.area_change
            print "S.E. of Area Change: %r" % changeObj.area_change_se
        
        #output_sw("Soundwide",zmChangeAll)
        
        # Used for Debugging
        def sites_out(label,changeObj):
            print "%s" % label
            for s1,s2,a1,a2 in zip(changeObj.y1m.site_ids,changeObj.y2m.site_ids,changeObj.y1m.zm_areas,changeObj.y2m.zm_areas):
                print "%s,%s,%r,%r" % (s1,s2,a1,a2)
        
        #sites_out("Core",coreChange)
        #sites_out("Flats",flChange)
        #sites_out("Fringe",frChange)
        #sites_out("Wide Fringe",frwChange)
                
        # Creates the comma-delimited output string 
        #  using formatting based on object type 
        def output_string(v1,*vals):
            out_string = "%s" % v1
            for v in vals:
                if type(v) == str or type(v) == unicode:
                    out_string = out_string + ",%s" % v
                elif type(v) == int:
                    out_string = out_string + ",%i" % v
                else:
                    out_string = out_string + ",%r" % v
            out_string = out_string + "\n"
            return out_string
        
        # ----------------------- Text File OUTPUT ------------------------------------
        coreString = output_string(year1,year2,coreChange.y1m.stratum.analysis,sample_group,
                                   coreChange.y1m.ni,coreChange.m,coreChange.m_se,
                                   coreChange.change_prop,coreChange.area_change,coreChange.area_change_se)
        flString =output_string(year1,year2,flChange.y1m.stratum.analysis,sample_group,
                                flChange.y1m.ni,flChange.m,flChange.m_se,
                                flChange.change_prop,flChange.area_change,flChange.area_change_se)
        frString = output_string(year1,year2,frChange.y1m.stratum.analysis,sample_group,
                                 frChange.y1m.ni,frChange.m,frChange.m_se,
                                 frChange.change_prop,frChange.area_change,frChange.area_change_se)
        frwString = output_string(year1,year2,frwChange.y1m.stratum.analysis,sample_group,
                                  frwChange.y1m.ni,frwChange.m,frwChange.m_se,
                                  frwChange.change_prop,frwChange.area_change,frwChange.area_change_se)

        
        # Stratum calcs - populate Output File
        msg("Writing stratum area change results to output file:\n %s" % outFileStratum)
        try:
            outFile = open(outFileStratum,'w')
            colnames_text = ",".join(utils.swAreaChgStratumCols)
            outFile.write(colnames_text + "\n")
            outFile.write(coreString)
            outFile.write(flString)
            outFile.write(frString)
            outFile.write(frwString)
            outFile.close()
        except:
            errtext = "There was an error while opening or writing to the output file:"
            errtext += "%s" % outFileStratum
            e.call(errtext)
            
        
        
        allStrataString = output_string(year1,year2,sample_group,zmChangeAll.change_prop,
                                        zmChangeAll.area_change,zmChangeAll.area_change_se,mc_ci)
        
        # All sites calcs - populate Output File
        msg("Writing soundwide area change results to output file:\n %s" % outFileAll)
        try:
            outFile = open(outFileAll,'w')
            colnames_text = ",".join(utils.swAreaChgAllCols)
            outFile.write(colnames_text + "\n")
            outFile.write(allStrataString)
            outFile.close()   
        except:
            errtext = "There was an error while opening or writing to the output file:"
            errtext += "%s" % outFileAll
            e.call(errtext)
        
        
        #--------------------------------- End  OUTPUT ---------------------------------
        #-------------------------------------------------------------------------------
    except SystemExit:
        pass
    except:
        e.call()
        del gp
