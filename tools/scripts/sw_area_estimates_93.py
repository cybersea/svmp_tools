""" Calculates annual Soundwide Zostera marina area estimates """

""" 
Tool Name:  SWAreaEstimates
Tool Label: SW Area Estimates
Source Name: sw_area_estimates_93.py
Version: ArcGIS 9.3
Author: Allison Bailey, Sound GIS
For: Washington DNR, Submerged Vegetation Monitoring Program (SVMP)
Date: December 2009 -- Updated January 2010 for Arc 9.3 geoprocessor
Requires: Python 2.5.1

This script calculates soundwide Zostera marina area estimates
for a single survey year.

# Parameters:
INPUT
(1) siteTable -- Site statistics geodatabase table (full path)
(2) allsitesFC -- Feature Class containing point locations for all sites (full path)
(3) flatsFC -- ArcGIS feature class for flats sites (full path)
(4) fringeFC -- ArcGIS feature class for fringe sites (full path)
(5) surveyYear -- Survey year for data to be processed
(6) sample_group -- soundwide or other data grouping.  soundwide is only option currently implemented
OUTPUT
(7) outFileStratum -- Output file name for Area Estimates by Stratum (full path)
(8) outFileAll -- Ouptut file name for Area Estimates for All Strata Combined (full path)

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
#-----------------------------------------------------------

#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
#MAIN

if __name__ == "__main__":

    try:
        #---- Create the Geoprocessing Object, v.9.3 ----------------------
        gp = arcgisscripting.create(9.3)
        gp.OverWriteOutput = True
        
        #----- Create the Custom Error Object ----------------------
        e = SvmpToolsError(gp)
        # Set some basic defaults for error handling
        e.debug = True
        e.full_tb = True
        
        def msg(msg):
            gp.AddMessage(msg)
        
        # ----------- PARAMETERS ----------------------------------
        # Temporary stand-ins for parameters - hard-coded
        # Input
        #dbPath = "c:/projects/dnr_svmp/output/eelgrass_monitoring/"
        #blPath = "c:/projects/dnr_svmp/output/eelgrass_monitoring/base_layers/"
        #outPath = "c:/projects/dnr_svmp/output/eelgrass_monitoring/ab_out/"
        #siteTable = dbPath  + "svmp_sitesdb_2009_12_21.mdb/all_years_sites"  #"svmp_sitesdb_lf.mdb/2007sites"
        #allsitesFC = blPath + "svmp_all_sites_041309_samptype.shp"
        #flatsFC = blPath + "flats.shp"
        #fringeFC = blPath + "fringe.shp"
        #surveyYear = 2007
        #sample_group = "soundwide"   # placeholder -- may be implemented as a parameter later (for soundwide, focus and other sites)
        
        ### output
        #outFileStratum = outPath
        #outFileStratum += "%s_swarea_stratum.csv" % (surveyYear)
        #outFileAll = outPath
        #outFileAll += "%s_swarea_all.csv" % (surveyYear)
        
        # Get parameters from ArcToolbox input or command line        
        siteTable = gp.GetParameterAsText(0)
        allsitesFC = gp.GetParameterAsText(1)
        flatsFC = gp.GetParameterAsText(2)
        fringeFC = gp.GetParameterAsText(3)
        surveyYear = int(gp.GetParameterAsText(4))
        sample_group = gp.GetParameterAsText(5)
        outFileStratum = gp.GetParameterAsText(6)
        outFileAll = gp.GetParameterAsText(7)
        
        unit_convert = "sf2m"   # unit conversion flag  -- survey feet to meters
        
        
        #----- Get  site list and strata from svmp_all_sites feature class
        #---------------------------------------------------------------------------
        
        if sample_group == "soundwide":
            ##----------Construct Query: Soundwide sites for the specified year ---
            query_field = "Y%s" % surveyYear
            # -- Should look like this: "Y2008" = 1 or "Y2008" = 8
            samp_type_qry = "%s = 1 or %s = 8" % (query_field,query_field)
        else:
            errtext = "Sample groups other than 'soundwide' are not implemented"
            e.call(errtext)
        
        # Query the All Sites feature class
        def site_query():
            return spatial.TableQuery(gp,allsitesFC,samp_type_qry)
        
        msg("Querying the All Sites Feature Class:\n  %s" % allsitesFC)
        site_characteristics = site_query()
        
        #----- Query All Sites Table for geomorph stratum, and sampling stratum with siteid as key
        def site_characteristics_query():
            flds_c = [utils.siteGeoStratCol,utils.siteSampStratCol]
            return site_characteristics.field_results(flds_c,utils.sitePtIDCol)
            
        site_characteristics_data = site_characteristics_query()
        
        ##-- List of sites sampled that year
        sites_sampled = sorted(site_characteristics_data.keys())
        ### same thing as a string w/single quotes separated by commas
        sites_sampled_string = "'" + "\',\'".join(sites_sampled) + "'" 
        
        
        #---------------------------------------------------------------------------- 
        #---------- DATA QUERIES and GROUPING --------------------------------------   
        #----------------------------------------------------------------------------
        
        #----- Get specified sites and year from the Sites database table
        #----------------------------------------------------------------------------
        
        #-------------- Construct Query: List of Sites and Year ----------------------
        def site_stats_query():
            # First part of query -- is the site in the list of sites sampled, 
            # query will look something like this: site_code in ('site1','site2','site5')
            site_stats_qry = "%s in (%s)" % (utils.siteCol, sites_sampled_string)
            # Combine that with a limit on the date to get only data from the specific year
            # For example:  date_samp_start >= #01-01-2007# and date_samp_start <= #12-31-2007#
            site_stats_qry = "%s and %s >= #01-01-%i# and %s <= #12-31-%i#" % (site_stats_qry, utils.samplestartdateCol, surveyYear, utils.samplestartdateCol, surveyYear)
            return spatial.TableQuery(gp,siteTable,site_stats_qry)
        
        msg("Querying the Sites Statistics Table:\n  %s" % siteTable)
        site_stats = site_stats_query()
        
        #------ Query the Sites Database Table for site id, Zm area, Zm variance with siteid as key
        flds_stats = (utils.siteCol,utils.est_basalcovCol,utils.estvar_basalcovCol)
        site_stats_data = site_stats.field_results(flds_stats, utils.siteCol)
        
        #----- List of all sites in the Sites DB table meeting the criteria
        sites_in_stats_tbl = sorted(site_stats_data.keys())
        
        #---Check for missing sites in the Sites DB table
        msg("Comparing site list from All Sites Feature Class and Sites Database Table")
        missing_sites = set(sites_sampled).difference(sites_in_stats_tbl)
        if missing_sites:
            err_text = "The sites database table, %s, is missing site(s)\n" % siteTable
            err_text += ",".join(missing_sites)
            err_text += "\nfor the year, %s" % surveyYear
            e.call(err_text)
        
        
        #--- Determine Analysis Stratum & Extrapolation Type (using geo and sampling strata lookup)
        site_extrap = {}
        for (siteid,data) in site_characteristics_data.items():
            site_extrap[siteid] = svmp.sw_Stratum4AreaCalcs[tuple(data)]
        #--- Create a dictionary of extrapolation types that groups sites
        extrap_site = invert_dict(site_extrap)
        
        # Group the site data into lists according to analysis stratum and extrapolation type
        core_dat = group_data_by_extrap(extrap_site,svmp.core_extrap,site_stats_data)
        pfl_dat = group_data_by_extrap(extrap_site,svmp.pfl_extrap,site_stats_data)
        fl_dat = group_data_by_extrap(extrap_site,svmp.fl_extrap,site_stats_data)
        fr_dat = group_data_by_extrap(extrap_site,svmp.fr_extrap,site_stats_data)
        frw_dat = group_data_by_extrap(extrap_site,svmp.frw_extrap,site_stats_data)
        
        # Get the sample area (from flats shapefile) for each rotational flats site sampled 
        fl_sites = extrap_site[svmp.fl_extrap]
        # same thing as a string w/single quotes separated by commas
        fl_sites_string = "'" + "\',\'".join(fl_sites) + "'" 
        # query will look something like this: NAME in ('site1','site2','site5')
        fl_sites_qry = "%s in (%s)" % (utils.sitePtIDCol, fl_sites_string)
        
        msg("Querying flats shapefile for sample area:\n  %s" % flatsFC)
        flats_sampled = spatial.FeatureQuery(gp,flatsFC,fl_sites_qry)
        
        # Dictionary of rotational flats sites with their sample area from flats.shp
        flats_a2j = flats_sampled.field_results([flats_sampled.shape_field],utils.sitePtIDCol)
        #print flats_a2j
        # Append the sample area to the rest of the site data (rotational flats only)
        for site in fl_dat:
            a2j = flats_a2j[site[0]][0]
            site.append(a2j)
        
        
        #---------------------------------------------------------------------------- 
        #---------- AREA ESTIMATE CALCULATIONS --------------------------------------   
        #----------------------------------------------------------------------------
        
        
        print "*** Soundwide Area Estimates for: %s ***" % surveyYear
        
        #-- Core Stratum
        def core_sample_calc():
            msg("Calculating Area Estimates for Core stratum, %s" % surveyYear)
            coreStratum = svmp.BaseStratum(svmp.core_extrap[0],svmp.core_extrap[1])
            coreSamp = svmp.SampleStats(core_dat,coreStratum,unit_convert)
            for site in sorted(coreSamp.site_ids):
                msg("  %s" % site)
            return coreSamp
        
        # -- Persistent Flats Stratum
        def persistant_flats_sample_calc():
            msg("Calculating Area Estimates for Persistent Flats stratum, %s" % surveyYear)
            pflStratum = svmp.BaseStratum(svmp.pfl_extrap[0],svmp.pfl_extrap[1])
            pflSamp = svmp.SampleStats(pfl_dat,pflStratum,unit_convert)
            for site in sorted(pflSamp.site_ids):
                msg("  %s" % site)
            return pflSamp
        
        # -- Rotational Flats Stratum
        def rotational_flats_sample_calc():
            msg("Calculating Area Estimates for Rotational Flats stratum, %s" % surveyYear)
            flStratum = svmp.FlatsStratum(svmp.fl_extrap[0],svmp.fl_extrap[1],gp,flatsFC,unit_convert)
            flSamp = svmp.SampleStats(fl_dat,flStratum,unit_convert)
            for site in sorted(flSamp.site_ids):
                msg("  %s" % site)
            return flSamp
                
        # -- Fringe Stratum
        def fringe_sample_calc():
            msg("Calculating Area Estimates for Fringe stratum, %s" % surveyYear)
            frStratum = svmp.FringeStratum(svmp.fr_extrap[0],svmp.fr_extrap[1],gp,fringeFC,unit_convert)
            frSamp = svmp.SampleStats(fr_dat,frStratum,unit_convert)
            for site in sorted(frSamp.site_ids):
                msg("  %s" % site)
            return frSamp
        
        # -- Wide Fringe Stratum    
        def wide_fringe_sample_calc():
            msg("Calculating Area Estimates for Wide Fringe stratum, %s" % surveyYear)
            frwStratum = svmp.FringeStratum(svmp.frw_extrap[0],svmp.frw_extrap[1],gp,fringeFC,unit_convert)
            frwSamp = svmp.SampleStats(frw_dat,frwStratum,unit_convert)
            for site in sorted(frwSamp.site_ids):
                msg("  %s" % site)
            return frwSamp
        
        # Do the calculations for all strata
        coreSamp = core_sample_calc()        
        pflSamp = persistant_flats_sample_calc()
        flSamp = rotational_flats_sample_calc()
        frSamp = fringe_sample_calc()
        frwSamp = wide_fringe_sample_calc()
        
        
        # Creates the comma-delimited output string 
        #  using formatting based on object type 
        # - Better way to do this?    what happens if only one value?
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
        
        
        coreString = output_string(surveyYear,coreSamp.stratum.analysis,coreSamp.stratum.extrapolation,sample_group,
                            coreSamp.zm_area,coreSamp.zm_area_var,coreSamp.se,coreSamp.cv,coreSamp.ni,
                            coreSamp.ni,"","","","","")
        pflString = output_string(surveyYear,pflSamp.stratum.analysis,pflSamp.stratum.extrapolation,sample_group,
                            pflSamp.zm_area,pflSamp.zm_area_var,pflSamp.se,pflSamp.cv,pflSamp.ni,
                            pflSamp.ni,"","","","","")
        flString = output_string(surveyYear,flSamp.stratum.analysis,flSamp.stratum.extrapolation,sample_group,
                            flSamp.zm_area,flSamp.zm_area_var,flSamp.se,flSamp.cv,flSamp.ni,
                            flSamp.stratum.Ni,flSamp.stratum.A2,flSamp.Aij,flSamp.R,"","")
        frString = output_string(surveyYear,frSamp.stratum.analysis,frSamp.stratum.extrapolation,sample_group,
                            frSamp.zm_area,frSamp.zm_area_var,frSamp.se,frSamp.cv,frSamp.ni,
                            frSamp.stratum.Ni,"","","",frSamp.stratum.LT,frSamp.stratum.LN)
        frwString = output_string(surveyYear,frwSamp.stratum.analysis,frwSamp.stratum.extrapolation,sample_group,
                            frwSamp.zm_area,frwSamp.zm_area_var,frwSamp.se,frwSamp.cv,frwSamp.ni,
                            frwSamp.stratum.Ni,"","","",frwSamp.stratum.LT,frwSamp.stratum.LN)
        
        msg("Writing stratum area results to output file:\n %s" % outFileStratum)
        
        try:
            # Open the file for output
            outFile = open(outFileStratum,'w')
            # Column names
            colnames_text = ",".join(utils.swAreaStratumCols)
            outFile.write(colnames_text + "\n")
            outFile.write(coreString)
            outFile.write(pflString)
            outFile.write(flString)
            outFile.write(frString)
            outFile.write(frwString)
            outFile.close()         
        except:
            errtext = "There was an error while opening or writing to the output file:"
            errtext += "%s" % outFileStratum
            e.call(errtext)
        
        # -- Soundwide (All Strata) Calculations
        def annual_sample_calc():
            #print coreSamp.zm_area
            msg("Calculating Area Estimates for all strata combined")
            annual = svmp.AnnualEstimate((coreSamp,pflSamp,flSamp,frSamp,frwSamp))
            return annual
        
        annualCalc = annual_sample_calc()
        annualString = output_string(surveyYear,sample_group,
                            annualCalc.zm_area,annualCalc.zm_area_var,annualCalc.se,annualCalc.cv)
        
        # Open the file for output
        msg("Writing combined area results to output file:\n %s" % outFileAll)
        try:
            outFile = open(outFileAll,'w')
            # Column names
            colnames_text = ",".join(utils.swAreaAllCols)
            outFile.write(colnames_text + "\n")        
            outFile.write(annualString)
            outFile.close() 
        except:
            errtext = "There was an error while opening or writing to the output file:"
            errtext += "%s" % outFileAll
            e.call(errtext)
            
        
    except SystemExit:
        pass
    except:
        e.call()
        del gp
