#--------------------------------------------------------------------------
# Tool Name:  SiteStatisticsDatabase
# Tool Label: Site Statistics Database
# Source Name: sitestatsdb.py
# Version: ArcGIS 10.0
# Author: Allison Bailey, Sound GIS and Greg Corradini Chop Shop Geospatial
# For: Washington DNR, Submerged Vegetation Monitoring Program (SVMP)
# Date: April 2007, modified June 2007, Feb 2008, Dec 2008, March-July 2013
# Requires: Python 2.6+
#
# This script calculates summary statistics for
# all transects and all sites for a specified sampling occasion.
# These statistics are stored in two data tables
# within an existing MS Access personal geodatabase
# If the tables exist, they will be repopulated with
# a full set of data

# Parameters:
# (0) ptTransectGDB -- Geodatabase for site point feature classes
# (1) sampPyFC -- Sample Polygon Feature Class
# (2) ctlParentDir -- Parent directory for site control files
# (3) siteFile -- Full path of text file containing list of all sites for year
# (4) siteDB -- Full path to database to store site and transect statistic tables
# (5) sampOccasion_lookup -- Table that includes sampling occasion field
# (6) sampOccasion -- Selected value for sampling occasion
# (7) veg_code_lookup -- Table that lists all valid veg codes
# (8) veg_code -- The Veg Code to run statistics on

# This script is expecting a directory structure and feature class naming convention
#   specific to Washington DNR's SVMP 
# Sample input control file directory
#  J:\AQR\DATA\NEARSHOR\VegMon\2006_Field_Season\Site Folders\core006
#--------------------------------------------------------------------------

#--------------------------------------------------------------------------
#Imports
#--------------------------------------------------------------------------
import sys
import os 
from datetime import datetime
import arcpy
# Import functions used for SVMP scripts
import svmpUtils as utils
# Import the custom Exception class for handling errors
from svmp_exceptions import SvmpToolsError


STEP = 1
def msg(msg):
    global STEP
    #msg = 'Step %s: %s...' % (STEP,msg)
    arcpy.AddMessage(msg)
    STEP += 1
    
#--------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------
#---------------------------   ERROR CLASSES   ----------------------------------------------
#--------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------

class SamplePolygonNotFound( Exception ):
    def __init__(self, message):
        super( self.__class__ , self ).__init__( message )
    def __str__(self):
        return repr(self)

#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Create a dictionary with the site name and featureclass
# Assumes shapefiles are prefixed with site_year_
#  and the appropriate suffix is passed in as a parameter
def make_ptShpDict(siteList,transectGDB,yr,shpSuffix):
    siteShpDict = {}
    for site in siteList:
        shp = site + "_" + yr + shpSuffix
        shpPath = os.path.join(transectGDB,shp)
        siteShpDict[site] = shpPath
    return siteShpDict
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Create a dictionary with the site name and in-memory feature_layer
# Assumes featureclass are prefixed with site_year_
#  and the appropriate suffix is passed in as a parameter
#
def make_pyFCDict(siteList,sample_poly_path,sampOcc,fcSuffix):
    siteFCDict = {}
    missingPolygons = []
    #msg("In make_pyFCDict")
    for site in siteList:
        site_stat_poly_id = site + "_" + sampOcc
        fl_output_name = site + "_" + sampOcc + fcSuffix
        sample_poly_fc = sample_poly_path
        #
        #
        #  this creates a global temporary feature_layer
        #  we can reference it later just with it's name
        #  especially if we are using it in another arcpy
        #  Geoprocessing tool that takes a FeatureLayer as input
        #  such as a SearchCursor( < feature_layer> ) or SelectLayerByLocation
        #  the call to MakeFeatureLayer *will not* bomb if the
        #  the select statement is bad -- a null layer will exist
        #
        #  Check for layers with no rows to find sites with missing sample polygons
        #
        # Arc 10.0 cannot use named args
        delimited_field = arcpy.AddFieldDelimiters( sample_poly_fc, utils.sitestatidCol )
        where_clause= delimited_field + " = " + "'%s'" % (site_stat_poly_id)
        arcpy.MakeFeatureLayer_management( sample_poly_fc, fl_output_name, where_clause )
        row_count = int(arcpy.GetCount_management(fl_output_name).getOutput(0))
        # msg("%s has %s rows" % (fl_output_name,row_count))
        if row_count:
            siteFCDict[site] = fl_output_name
        else:
            missingPolygons.append( site )

    return ( siteFCDict, missingPolygons )
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Convert transect point shapefiles to line files
# Assign point attributes to the line ahead of it
def trans_pt2line(ptFC,lnFC,transID):
    try: 
        spatRef = arcpy.Describe(ptFC).SpatialReference
        #msg( "Creating line featureclass = %s" % lnFC )
        arcpy.CreateFeatureclass_management(os.path.dirname(lnFC),os.path.basename(lnFC),"Polyline",ptFC,"#","#",spatRef)
        # Open a cursor for the ouput line shapefile
        cur = arcpy.InsertCursor(lnFC)
        # Get a list of fields in the input point feature class
        pt_fields = utils.get_fieldnames(ptFC,arcpy)
        # Cursor for iterating through Point Feature class
        objidCol = arcpy.Describe(ptFC).OIDFieldName
        allpts = arcpy.SearchCursor(ptFC,"","","",objidCol)
        pt = allpts.next()
        lastTrk = 0   # Initialize the transect counter
        lineArray = arcpy.CreateObject("Array")  # Make an array object for the line
        fromPt = arcpy.CreateObject("Point") # Make an array object for the "From" point
        toPt = arcpy.CreateObject("Point") # Make an array object for the "To" point

        while pt:
            # Get the current Transect ID
            trkID = pt.getValue(transID)
            # IF it's a new transect, store the coordinates
            # and the attributes of this point
            if trkID != lastTrk:
                # Get the coordinates and Transect ID
                fromPt.X = pt.shape.getPart().X
                fromPt.Y = pt.shape.getPart().Y
                fromPt.ID = trkID
                lastTrk = trkID
                # List to contain the attributes
                pt_attributes = {}
                # Get the attributes
                for fld in pt_fields:
                    pt_attributes[fld] = pt.getValue(fld)
            # Otherwise, this point is the end point
            # of a two point line, starting with the previous point
            else:
                # Get the coordinates of the end point of line
                toPt.X = pt.shape.getPart().X
                toPt.Y = pt.shape.getPart().Y
                toPt.ID = trkID
                # Create a new row in the feature class
                lineArray.removeAll()
                # Add the To/From points
                lineArray.add(fromPt)
                lineArray.add(toPt)
                # Create a new feature
                feat = cur.newRow()
                # Set the new feature's shape to the Line Array
                feat.shape = lineArray
                for fld in pt_fields:
                    feat.setValue(fld, pt_attributes[fld])
                # Insert this Row into the feature class
                cur.insertRow(feat)

                # Then, save these coordinates for
                # the start coordinates of the next line
                fromPt.X = toPt.X
                fromPt.Y = toPt.Y
                # And the associated attributes go with the next line
                for fld in pt_fields:
                    pt_attributes[fld] = pt.getValue(fld)

                # Get the next point from the transect point file   
            pt = allpts.next()
            # Get rid of cursors
        del cur
        del allpts
    except:
        e.call("Problem creating Line Feature Class from: " + ptFC)
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Get Transect Max/Min Depth Flags and Track Type from Control File
# These are the attributes which will control output eelgrass statistics
# Assumes format is two columns separated by commas (and some extra whitespace)
#  first column is the attribute name and second column is the value 
# Change Yes/No values to numeric: 1 or 0 for database input
def get_Flags(site,ctlFile):

    # initialize Track ID comparison
    trk = 0
    trkFlagDict = {}

    for line in open(ctlFile):
        # Get rid of white space at beginning and end of line 
        line = line.strip()
        [att,val] = line.split(',')
        val = val.strip()

        # Get Track Number
        if att == utils.ctlTrkAtt:
            # After the first track, output track and 
            # max/min flags from previous track
            if trk > 0:
                trkFlagDict[trk] = [maxFlag,minFlag,trkType]
            # Convert Track Number to an integer
            trk = int(val)
        # Get Track Type
        if att == utils.ctlTrktypeAtt:
            trkType = val
        # Get Maximum Depth Flag
        if att == utils.ctlMaxAtt:
            if val == utils.ctlYes:  
                maxFlag = 1
            elif val == utils.ctlNo:  
                maxFlag = 0
        # Get Minimum Depth Flag
        if att == utils.ctlMinAtt:
            if val == utils.ctlYes:  
                minFlag = 1
            elif val == utils.ctlNo:  
                minFlag = 0

    # Get info from final track        
    trkFlagDict[trk] = [maxFlag,minFlag,trkType]
    return trkFlagDict         

#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Calculate transect-based statistics
# Creates a list of lists containing attributes for each transect
# Attributes are ordered according to output data fields in transect table
def calc_transStats(site,lnFC,trkFlagDict, selected_veg_code):
    # Empty List to Store data for all transects at this site
    allTrkStats = []

    # List indexes for max/min/track types
    maxFlagIdx = 0
    minFlagIdx = 1
    trkTypeIdx = 2

    # String Version of this list for SQL IN statement
    inclTrkTypesString = "(\'" + "\',\'".join(utils.trkType4Stats) + "\')"
    # Feature Layer Name
    lnFL = "line_layer" 

    # Create list of all transects to be included in Stats Calculations  (right now, just SLPR)       
    tracks = [trk for trk in sorted(trkFlagDict) if trkFlagDict[trk][trkTypeIdx] in utils.trkType4Stats]
    
    startDate = 0 # initialize startDate

    # Loop through each transect
    if tracks:
        for trk in tracks:
            # Initialize values
            samplen = 0  # Sample length in meters
            zmlen = 0 # Zostera marina length in meters
    
            # Select lines from a particular track that have the correct track type (SLPR) for eelgrass area calculations
            # NOTE:  Don't need track type in SQL, because already filtered for that in creating list of tracks
            # Need to form a select statment like "tran_num" = 1
            #selStatement = '''"%s" = %s''' % (utils.trkCol,trk)
            delimited_field = arcpy.AddFieldDelimiters( lnFC, utils.trkCol)
            selStatement = delimited_field + " = " + "%s" % (trk)
            #msg(selStatement)
            # Create a search cursor for rows that meet the query's criteria
            rows = arcpy.SearchCursor(lnFC,selStatement)
            row = rows.next()
            # If records returned from query, do processing for that transect
            if row:   
                # Initialize Max and Min depth 
                # Can't use first row, because that may have the nonsense depth null value of -9999
                # So, use these extremely large and small values to initialize
                trk_maxdep_ft = zm_maxdep_ft = init_max = 10000
                zm_mindep_ft = trk_mindep_ft = init_min = -10000
                # Get date of first transect:
                if startDate == 0:
                    startDate = row.getValue(utils.shpDateCol)
                ## Loop through all rows for the transect
                while row:
                    feat = row.shape  # Get the Shape field
                    trkDate = row.getValue(utils.shpDateCol)
                    dep = row.getValue(utils.shpDepCol)
                    vidQual = row.getValue(utils.videoCol)
                    zmPresence = row.getValue(selected_veg_code)
                    # length of the current feature 
                    segLen = feat.length   
                    # Only use rows that have good video quality (good = 1, bad = 0)
                    if vidQual:
                        # This segment length gets added to total length of sample
                        samplen = samplen + segLen
                        # Comparisons for max and min look backward because
                        # Depths below MLLW are recorded with negative numbers
                        # So, a maximum depth is actually the lowest number
                        #  and minimum depth is the highest number
                        if dep != utils.nullDep:
                            if dep <  trk_maxdep_ft:
                                trk_maxdep_ft = dep
                            if dep > trk_mindep_ft:
                                trk_mindep_ft = dep                
                        # For eelgrass length, only use rows with 
                        #  good video quality and Zostera marina (Zm <> 0)
                        if zmPresence:
                            # This segment length is added to total length of Z.marina
                            zmlen = zmlen + segLen
                            # Max and min eelgrass depths, same caveat as track depths
                            if dep != utils.nullDep:
                                if dep < zm_maxdep_ft:
                                    zm_maxdep_ft = dep
                                if dep > zm_mindep_ft:
                                    zm_mindep_ft = dep
                    row = rows.next()
        
                # If the max/min depths are the same as the initialized value, 
                #    then, change it to the null value
                if trk_maxdep_ft == init_max:
                    trk_maxdep_ft = utils.nullDep
                if trk_mindep_ft == init_min:
                    trk_mindep_ft = utils.nullDep
                if zm_maxdep_ft == init_max:
                    zm_maxdep_ft = utils.nullDep
                if zm_mindep_ft == init_min:
                    zm_mindep_ft = utils.nullDep
        
                #msg("Z marina transect length: " + str(zmlen))
                #msg("transect sample length: " + str(samplen))    
                # Calculate eelgrass fraction for this Track
                if samplen > 0:
                    zm_fraction = zmlen / samplen
                else:
                    zm_fraction = 0
        
                #msg("Zm fraction: " + str(zm_fraction))
        
                # Get the flags (0,1) for max/min depth for this transect
                trkMaxDepFlag = trkFlagDict[trk][maxFlagIdx]
                trkMinDepFlag = trkFlagDict[trk][minFlagIdx]

                #----------------  SITE_RESULTS_ID ----------------------------  
                #
                site_results_id = site + "_" + startDate.strftime( "%Y%m%d" ) + "_" + selected_veg_code
                
                #----------------  TRAN_RESULTS_ID ----------------------------
                trk_string = str( trk ).zfill(2)                    
                tran_results_id = site_results_id + "_" + trk_string
                
               
                # return all values in a list in the same order as the output database table
                # for use in an InsertCursor
                trkStats = [ tran_results_id,site,startDate,trkDate,selected_veg_code,trk,samplen,zmlen,zm_fraction,
                            trk_maxdep_ft,zm_maxdep_ft,zm_mindep_ft,trk_mindep_ft,
                            trkMaxDepFlag,trkMinDepFlag, site_results_id ]
                allTrkStats.append(trkStats)
                
            # No rows returned for transect query.  Transect likely outside of sample polygon   
            else:
                errtext = "No transect data retrieved for Site %s, Transect %s, Transect Type: %s" % (site,trk,'or'.join(utils.trkType4Stats))
                #errtext += "\nIt has Z. marina, good video quality, and transect type: %s" % ('or'.join(utils.trkType4Stats))
                errtext += "\nThe transect may be located outside the sample polygon."
                e.call(errtext)

        del rows # Get rid of cursor
                
    else:
        errtext = "Site %s has Z. marina, a Sample Polygon, but No transects of Type: %s " % (site,'or'.join(utils.trkType4Stats))
        #
        #  No error needs to be thrown here. Just return
        #  the empty allTrkStats and append knowledge of this
        #  site to output to a warning
        #
        #e.call(errtext)

        
    return allTrkStats

#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
# Insert the calculated statistics data into the specified database table
# Assumes that the data are stored as a list of lists
# and they are in the same order as the output data table column list
def insert_stats(table,data,cols):
    cur = arcpy.InsertCursor(table)
    for line in data:
        # Create a New Row in the table
        row = cur.newRow()
        # Set all the attributes
        # Assumes data list is in the same order as column list
        for (col,val) in zip(cols,line):
            #msg( "col = %s , value = %s , type = %s" % ( col, val, type(val) ) )
            row.setValue(col,val)
        cur.insertRow(row)

    del cur  # Remove the cursor
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
# Calculate statistics for sites with selected vegetation, based on transect table
def calc_siteStats(sites,inTable,pyDirDict,selected_veg_code,samp_occasion):
    # Empty List to Store output data for all sites
    allSiteStats = []

    # Column Names
    siteCol = utils.siteCol  
    dateCol = utils.samplestartdateCol 
    samplenCol = utils.samplenCol 
    zmlenCol = utils.zmlenCol 
    zmmaxdepCol = utils.zmmaxdepCol 
    zmmindepCol = utils.zmmindepCol 
    maxdepflagCol = utils.maxdepflagCol  
    mindepflagCol = utils.mindepflagCol     

    for site in sites:
        # Initialize lists to hold transect data for site
        samplenList = []  # Sample length values
        veglenList = [] # Eelgrass length values
        maxdepList = [] # Maximum eelgrass depth values
        mindepList = [] # Minimum eelgrass depth values

        # full path for sample Polygon Feature Class
        pyFC = pyDirDict[site]
        # SQL statement for selecting site data
        # Fields are indicated by square brackets because it's a geodatabase
        delimited_field = arcpy.AddFieldDelimiters( inTable, siteCol )
        selStatement =  delimited_field + " = "  + "'%s'" % str(site)
        # Create Search Cursor for Input Transect Data Table
        #print inTable, selStatement
        rows = arcpy.SearchCursor(inTable,selStatement)
        row = rows.next()
        # Get date from first row 
        if row == None:
            print "No rows returned"
            e.call("site %s:  No data in table %s" % (site, inTable))

        startDate = row.getValue(dateCol)
        n = 0  # Counter for number of transects used in calculations
        # Gather necessary data from data table
        while row:
            # Add values to Sample Length and Eelgrass Length Lists
            samplenList.append(row.getValue(samplenCol))
            veglenList.append(row.getValue(zmlenCol))
            # If transect is Flagged for use in max eelgrass depth, add
            #  its maximum eelgrass depth value to the list
            maxDepZM = row.getValue(zmmaxdepCol)
            minDepZM = row.getValue(zmmindepCol)
            if row.getValue(maxdepflagCol):
                if maxDepZM <> utils.nullDep:
                    maxdepList.append(maxDepZM)
            if row.getValue(mindepflagCol):
                if minDepZM <> utils.nullDep:
                    mindepList.append(minDepZM)
            n = n + 1 # increment the transect counter 
            row = rows.next()
        del row
        del rows  # Get rid of cursor
        

        # Calculate the Site Statistics
        #----------------------- AREA STATISTICS --------------------------------
        # Sum of Sample and Vegetation Lengths for this site
        sum_samplen = sum(samplenList)
        sum_veglen = sum(veglenList)
        # Estimated mean vegetation fraction (P Bar Hat)
        estmean_vegfraction = sum_veglen / sum_samplen
        # Mean transect lengths (L bar)
        mean_translen = sum_samplen / n
        # Estimated Variance of eelgrass fraction
        estvar_vegfraction = utils.ratioEstVar(samplenList,veglenList,estmean_vegfraction,n,mean_translen)
        # Sampling area
        sample_area = sampPolyArea(pyFC)
        # Estimated basal area coverage (i.e. area of vegetation)
        est_basalcov = estmean_vegfraction * sample_area
        # Estimated variance of basal area coverage 
        estvar_basalcov = estvar_vegfraction * (sample_area ** 2)
        # standard error of eelgrass area
        se_basalcov = estvar_basalcov ** 0.5
        # coefficient of Variation of basal area coverage
        #cv_basalcov = se_basalcov / est_basalcov
        # 95% confidence interval of basal area coverage
        #ci95_basalcov = utils.ci95(se_basalcov)

        #-------------------- DEPTH STATISTICS --------------------------------
        # Number of samples for Max and Min Eelgrass Depth summaries
        n_maxdep = len(maxdepList)
        n_mindep = len(mindepList)
        # Sort the depth lists
        maxdepList.sort()
        mindepList.sort()
        # Range, Mean, Stdev, variance,SE, and 95% confidence interval
        #    for Maximum Depth Values
        if n_maxdep > 0: 
            # If there is at least one max depth transect, use the formulas
            max_maxdep = maxdepList[-1] # last value in sorted list
            min_maxdep = maxdepList[0] # first value in sorted list
            mean_maxdep = sum(maxdepList) / len(maxdepList)
        else:
            # If there is 0 max depth transects, fill with null values
            max_maxdep = utils.nullDep
            min_maxdep = utils.nullDep
            mean_maxdep = utils.nullDep
        if n_maxdep > 1:
            # If there are at least two max depth transects, you can calculate
            # calculate Standard deviation, variance, standard error and 95%CI
            std_maxdep = utils.stdDev(maxdepList)
            var_maxdep = utils.variance(std_maxdep)
            se_maxdep = utils.stdErr(std_maxdep,n_maxdep)
            #ci95_maxdep = utils.ci95(se_maxdep) 
        else:
            # Otherwise assign null values
            std_maxdep = utils.nullDep
            var_maxdep = utils.nullDep
            se_maxdep = utils.nullDep
            #ci95_maxdep = utils.nullDep
        # Range, Mean, StdDev, variance, SE, and 95% confidence interval
        #   for Minimum Depth Values
        if n_mindep > 0: 
            max_mindep = mindepList[-1] # last value in sorted list
            min_mindep = mindepList[0]  # first value in sorted list
            mean_mindep = sum(mindepList) / len(mindepList) 
        else:
            # If there are 0 min depth transects, fill with null values
            max_mindep = utils.nullDep
            min_mindep = utils.nullDep
            mean_mindep = utils.nullDep
        if n_mindep > 1:
            # If there are at least two min depth transects, you can 
            # calculate Standard deviation, variance, standard error and 95%CI        
            std_mindep = utils.stdDev(mindepList)
            var_mindep = utils.variance(std_mindep)
            se_mindep = utils.stdErr(std_mindep,n_mindep)
            #ci95_mindep = utils.ci95(se_mindep)
        else:
            # Otherwise assign null values
            std_mindep = utils.nullDep
            var_mindep = utils.nullDep
            se_mindep = utils.nullDep
            #ci95_mindep = utils.nullDep

        #-------------------- SITE_RESULTS_ID ------------------------
        site_results_id = site + "_" + startDate.strftime( "%Y%m%d" ) + "_" + selected_veg_code

        #-------------------- SITESTAT_ID ----------------------------
        ## -- This needs to be the sampling occasion field value, not necessarily year
        sitestat_id = site + "_" + samp_occasion #startDate.strftime( "%Y" )
      
        siteStats = [ site_results_id, site, startDate, selected_veg_code, n, estmean_vegfraction, 
                     sample_area, est_basalcov, se_basalcov,
                     n_mindep, mean_mindep, min_mindep, max_mindep, se_mindep,
                     n_maxdep, mean_maxdep, min_maxdep, max_maxdep, se_maxdep, sitestat_id]

        allSiteStats.append(siteStats)

    return allSiteStats

#--------------------------------------------------------------------------
# Calculate statistics for sites with Zostera marina, based on transect table
def calc_siteStats_noVeg(sites,ptShpDict,selected_veg_code,samp_occasion):
    # Empty List to Store output data for all sites
    allSiteStats = []
    
    # Sample Size
    n = 0
    # Veg Fraction
    estmean_vegfraction = 0
    # Areas and variability
    sample_area = est_basalcov = se_basalcov = 0
    # Null values for depths
    # Min and Max depth stats
    n_mindep = 0
    mean_mindep = max_mindep = min_mindep = se_mindep = utils.nullDep
    n_maxdep = 0
    mean_maxdep = max_maxdep = min_maxdep = se_maxdep = utils.nullDep
    
    for site in sites:
        #------------------- DATE -----------------------------------
        try:
            ptFC = ptShpDict.get(site)
            rows = arcpy.SearchCursor(ptFC,"","",utils.shpDateCol)
            row = rows.next()
            # Get date of first transect:
            startDate = row.getValue(utils.shpDateCol)
            del rows
            del row
        except:
            e.call("Problem accessing or querying %s" % ptFC)  
            
        #-------------------- SITE_RESULTS_ID ------------------------
        site_results_id = site + "_" + startDate.strftime( "%Y%m%d" ) + "_" + selected_veg_code
    
        #-------------------- SITESTAT_ID ----------------------------
        ## -- This needs to be the sampling occasion field value, not necessarily year
        sitestat_id = site + "_" + samp_occasion 
        
        
        siteStats = [ site_results_id, site, startDate, selected_veg_code, n, estmean_vegfraction, 
                     sample_area, est_basalcov, se_basalcov,
                     n_mindep, mean_mindep, max_mindep, min_mindep, se_mindep,
                     n_maxdep, mean_maxdep, max_maxdep, min_maxdep, se_maxdep, sitestat_id]
    
        allSiteStats.append(siteStats)

    return allSiteStats
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
# Calculate Area of Sample Polygon 
# Optional parameter to pass in a multiplier to convert 
# from units in the source shapefile to some other area unit
# Default is to return units from shapefile
def sampPolyArea(pyFC, areaConvConstant=1):
    # Create a search cursor on the sample polygon
    # Get Area, and convert from survey feet to square meters
    polys = arcpy.SearchCursor(pyFC)
    poly = polys.next()
    pyArea = 0 # initialize polygon area total
    # accumulate area from each polygon in the shapefile
    while poly:
        pyArea = pyArea + (poly.shape.area * areaConvConstant )
        poly = polys.next()
    del polys, poly
    return pyArea  

#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
# Get Location of Site in Decimal Degrees
# This info was extracted from the svmp_all_sites shapefile
def siteCoords(site,siteXYDict):
    x = siteXYDict[site][0]
    y = siteXYDict[site][1]
    return float(x),float(y)
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------


#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
#MAIN

if __name__ == "__main__":

    try:

        #  make overwriteOutput ENV = True
        arcpy.env.overwriteOutput = True

        # Create the custom error class
        # and associate it with the arcpy
        e = SvmpToolsError( arcpy )
        # Set some basic defaults for error handling
        e.debug = True
        e.full_tb = True
        #e.exit_clean = False
        #e.pdb = True

        #Get parameters
        # Input Transect Point Geodatabase 
        # Parameter Data Type: Workspace, Filter: Workspace - geodatabases only
        ptTransectGDB = arcpy.GetParameterAsText(0)  
        # Input Sample Polygon Feature Class 
        # Parameter Data Type:  Feature Class
        sampPyFC = arcpy.GetParameterAsText(1)
        # Control File Parent Directory
        # Parameter Data Type:  Folder
        ctlParentDir = arcpy.GetParameterAsText(2)
        # Full Path of text file containing list of sites to process
        # Parameter Data Type: File
        siteFile = arcpy.GetParameterAsText(3) 
        # Full Path to database to store site and transect statistic tables
        # Parameter Data Type: Workspace or Feature Dataset
        siteDB = arcpy.GetParameterAsText(4)   
        # Survey Year for data to be processed
        # Parameter Data Type: String
        sampOccasion = arcpy.GetParameterAsText(6)
        # Veg Code
        # Parameter Data Type: STring
        selected_veg_code = arcpy.GetParameterAsText(8)
        
        # Suffix for Transect Point Shapefiles
        ptSuffix = utils.ptFCSuffix  
        # Suffix for Sample Polygon shapefiles
        pySuffix = utils.sampPyShpSuffix  
        # Field name for Unique Transect Number within a site
        transID = utils.trkCol   
        # File suffix for control file
        ctlSuffix = utils.ctlSuffix 

        # Template table for sites statistics
        template_sites = utils.templateSites
        template_sites_fullpath = os.path.join(siteDB,template_sites)
        #msg("Template Sites:" + template_sites_fullpath)        
        # Template table for transect statistics
        template_transects = utils.templateTransects  
        template_transects_fullpath = os.path.join(siteDB,template_transects)
        # msg("Template Transects" + template_transects_fullpath)

        # Output Statistics Table Names -- use sampling occasion and vegetation code as suffix 
        site_table = template_sites + sampOccasion + "_" + selected_veg_code
        site_table_fullpath = os.path.join(siteDB,site_table)
        trans_table = template_transects + sampOccasion + "_" + selected_veg_code # sampOccasion + template_transects
        trans_table_fullpath = os.path.join(siteDB,trans_table)

        # Site and Transect Table Field Names
        siteCols = utils.siteTabCols
        transCols = utils.transTabCols

        # Get site list 
        siteList = utils.make_siteList(siteFile)
        msg("List of %s sites to calculate statistics:" % ( len(siteList) ))
        for site in siteList:
            msg(site)

        #
        # Initialize lists to hold site-wide presence or absence of selected veg_code
        #
        siteList_NoVeg = []
        siteList_Veg = []
        
        # 
        # Make a dictionary containing the sites and the 
        #  full path to transect feature classes
        #
        ptDirDict = make_ptShpDict(siteList,ptTransectGDB,sampOccasion,ptSuffix)
        
        #------------------------------------------------------------------------
        #  Multi-Site Validation for missing 
        #  Transect Point, Control Files, or veg_code columns
        #------------------------------------------------------------------------
        # check for missing transect point shapefiles 
        #  if transect point feature class exists, check for the veg_code column
        missingPtShapes = []
        missingVegCol = []
        for site in siteList:
            ptFeatureClass = ptDirDict.get(site)
            if not arcpy.Exists( ptFeatureClass ):
                # add to list of sites with missing transect shapefiles
                missingPtShapes.append(site)
            else:
                field_list = arcpy.ListFields( ptFeatureClass )
                field_name_list = [ i.name for i in field_list ]
                if selected_veg_code not in field_name_list:
                    missingVegCol.append( site )
                    
        # Check for missing control files
        missingCtlFiles = []
        for site in siteList:
            # construct control file name and full path
            ctlFile = "".join((site,ctlSuffix))
            ctlFileFull = os.path.join(ctlParentDir,site,ctlFile)
            if not os.path.exists(ctlFileFull):
                # add to list of sites with missing control files
                missingCtlFiles.append(site)

        errtext = ""
        if missingPtShapes or missingCtlFiles or missingVegCol:        
            if missingPtShapes:
                missingPtShapes.sort()
                errtext += "The following %s sites are missing transect point feature classes for %s:\n" % ( len(missingPtShapes), sampOccasion )
                errtext += '\n'.join(missingPtShapes)
            if missingCtlFiles:
                missingCtlFiles.sort()
                errtext += "\nThe following %s sites are missing control files for %s:\n" % ( len(missingCtlFiles), sampOccasion )
                errtext += '\n'.join(missingCtlFiles)
            if missingVegCol:
                missingVegCol.sort()
                errtext += "\nThe following %s sites are missing the selected vegetation column, %s, for %s\n" % (len(missingVegCol),selected_veg_code,sampOccasion)
                errtext += '\n'.join(missingVegCol)
            e.call(errtext)
        #------------------------------------------------------------------------
        #  END Multi-Site Validation for missing 
        #     Transect Point, Control Files, or veg_code columns
        #------------------------------------------------------------------------

        
        #
        # Loop through all sites and make a list of those 
        #   with and withouth the vegetation of interest
        # 
        for site, featureclass in ptDirDict.items():
            #msg("%s,%s" % (site,featureclass))
            try:
                # Create Search Cursor for Input Transect Data table
                # Sort on specified veg column, descending -- contains on zero or one for presence/absence
                rows = arcpy.SearchCursor(featureclass,"","",selected_veg_code,"%s D" % selected_veg_code)
                row = rows.next()
                ZmFlag = row.getValue(selected_veg_code)
            except Exception:
                e.call("Sorry, there was a problem accessing or querying feature class %s" % site)
                
            if ZmFlag:
                siteList_Veg.append(site)
            else:
                siteList_NoVeg.append(site)
                
        siteList_Veg.sort()
        siteList_NoVeg.sort()        
        msg("%s sites with %s:\n" % ( len(siteList_Veg), selected_veg_code ) +  '\n'.join(siteList_Veg))
        msg("%s sites without %s:\n" % ( len(siteList_NoVeg), selected_veg_code) + '\n'.join(siteList_NoVeg))

        #
        # Make a dictionary containing the sites (w/veg present) and the temp feature_layer name
        # this function will also hand back a list of problem polygons
        # that are not found in the target feature class 
        #
        pyDirDict, missingSamplePolys = make_pyFCDict(siteList_Veg,sampPyFC,sampOccasion,pySuffix)
        print pyDirDict
                
        if missingSamplePolys:
            errtext = "The following %s sites have %s, but are missing sample polygons for %s:\n" % ( len(missingSamplePolys), selected_veg_code, sampOccasion)
            errtext += '\n'.join(missingSamplePolys)
            e.call(errtext)

        # Create Tables for Annual Site and Transect Data Summary Statistics
        # NOte:  This will overwrite existing tables and replace them
        try:
            arcpy.CreateTable_management(siteDB,trans_table,template_transects_fullpath)
            arcpy.CreateTable_management(siteDB,site_table,template_sites_fullpath)
        except:
            errtext = ("Problem Creating Annual Stats Table(s): '%s' and/or '%s' in \n%s\n" % (trans_table,site_table,siteDB))
            errtext += ("Make sure that the database is not open in ArcGIS or MS Access")
            e.call(errtext)
            
        # Loop throught all sites with Vegetation of interest
        for site in siteList_Veg:
            msg("-------- SITE ID: %s --------" % site)
            msg("Calculating statistics for site: '%s'" % site)
            ptFC = ptDirDict[site]  # get point feature class name
            msg("The point feature class is: '%s'" % ptFC)
            
            # GDB location of temp files
            gdb_temp_dir_path = os.path.dirname(ptFC)
            # name for Line Feature Class (put in same directory as input points)
            shape_name = "_%s_%s_transect_line" % (site,sampOccasion)
            lnFC = os.path.join( gdb_temp_dir_path, shape_name)
            # full path for sample Polygon Feature Class
            pyFC = pyDirDict[site]
            # Output clipped Line Feature Class name
            shape_name = "_%s_%s_transect_line_clip" % (site,sampOccasion)
            cliplnFC = os.path.join( gdb_temp_dir_path, shape_name )
            # Control File Name
            ctlFile = "".join((site,ctlSuffix))
            ctlFileFull = os.path.join(ctlParentDir,site,ctlFile)


            # Create the Line Feature Class with same attributes as input points
            try:
                msg("Creating temporary line file")
                trans_pt2line(ptFC,lnFC,transID)                    
            except:
                e.call("Problem creating a line from:" + ptFC)

            # Clip the Line Feature Class with the sample polygon
            if arcpy.Exists(pyFC):  
                msg("Clipping the Line to the sample poly")             
                arcpy.Clip_analysis(lnFC,pyFC,cliplnFC)
            else:
                e.call("'%s' does not exist" % pyFC)

            # Extract Transect Max/Min Depth Flags from Site Control File
            trkFlagDict = get_Flags(site,ctlFileFull)

            # Calculate Transect Statistics 
            #Transect statistics (list of lists, in order by columns in output tables
            msg("Calculating transect statistics")
            transStats = calc_transStats(site,cliplnFC,trkFlagDict,selected_veg_code)

            # Insert Transect Statistics into annual Transects data table
            msg("Inserting transect statistics into data table")
            insert_stats(trans_table_fullpath,transStats,transCols)

            #if transStats:
                #insert_stats(trans_table_fullpath,transStats,transCols)
            #else:
                ##
                ## add this site to sites_no_slpr to drop a warning
                ## at the end of the script run
                ##
                #sites_no_slpr.append( site )

            # Delete the temporary line files:
            #arcpy.Delete_management(lnFC)
            #arcpy.Delete_management(cliplnFC)

        #
        # Calculate Site Statistics for Vegetation of interest sites
        # NOTE: we only want to run calc_siteStats on sites 
        # that 1) have a TrkType code SLPR ( cause only those were outputed in Transects<Year> table )
        # and  2) have the selected VegCode
        # 
        if siteList_Veg:
            # sites_minus_non_slpr = set(siteList_VegCode).difference( set( sites_no_slpr ) )
            msg("\n\nCalculating site statistics for sites with %s" % selected_veg_code )
            siteStats_veg = calc_siteStats(siteList_Veg,trans_table_fullpath,pyDirDict,selected_veg_code,sampOccasion)
            # Insert site Statistics into annual Sites data table
            msg("Inserting site statistics into data table")
            insert_stats(site_table_fullpath,siteStats_veg,siteCols)
            
        # Site statistics for sites without the selected vegetation type    
        if siteList_NoVeg:
            msg("\n\nCalculating site statistics for sites without %s" % selected_veg_code )
            siteStats_noVeg = calc_siteStats_noVeg(siteList_NoVeg,ptDirDict,selected_veg_code,sampOccasion)
            msg("Inserting site statistics into data table")
            insert_stats(site_table_fullpath,siteStats_noVeg,siteCols)
 

    except SystemExit:
        pass
    except:
        e.call()
        del arcpy