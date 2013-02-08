#--------------------------------------------------------------------------
# svmpUtils.py
# Version: ArcGIS 9.2
# Author: Allison Bailey, Sound GIS
# For: Washington DNR, Submerged Vegetation Monitoring Program (SVMP)
# Date: April 2007, modified June 2007
# Requires: Python 2.4

# This module contains shared functions and constants that are used
# with the SVMP Site Transect Analysis Tools
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
#  Imports
#--------------------------------------------------------------------------
import sys
import os

#--------------------------------------------------------------------------
#------------- CONSTANTS, Column LISTS and Dictionaries -------------------
#--------------------------------------------------------------------------

#--------------VARIABLES for Conversions, Spatial Reference ---------------
sf_m = 0.304800609601219 # multiplier for survey feet to meters conversion
#### Not sure if any of these other ones are used......
#sf2_m2 = 0.09290341161327470000   # 0.092903411613274728  #0.092903411613274825 # multiplier for sq survey feet to sq meters conversion
#f_m = 0.3048 # multiplier for feet to meters conversion
#m2_ha = 0.0001 # multiplier for square meters to hectares conversion
#sf2_ha = 0.000009290341  # multiplier for square survey feet to hectares
#sf4_ha2 = 0.0000000000863104 # multiplier for survey feet to the fourth to hectares squared

wgs84Code = '4326' # ArcGIS spatial reference code for Geographic, WGS-84

#------------- VARIABLES Related to Source ASCII data files -------------#
## Source ASCII data are provided by MRC in a standard comma-delimited format
# The first row contains the column names, 
# but the order of columns within the file may vary

sourceLatCol = 'latitude'  # source ASCII data column name for latitude
sourceLonCol = 'lon' # source ASCII data column name for longitude 
sourceDateCol = 'date' # source ASCII data column name for data
sourceTimeCol = 'time' # source ASCII data  column for time
transFileSuffix = "TD.csv"  # suffix for input transect ASCII file

sourceTrkCol = 'trk' # column to identify a track/transect
trkTypeCol = 'TrkType'  # Column listing type of track
zmCol = 'Zm'  # Column indicating presence of Zostera marina (0,1)
videoCol = 'video'  # Column for video data quality (0,1)



# List of Source Column Names needed for data conversion/processing
sourceCols = [sourceTrkCol,
            sourceDateCol,
            sourceTimeCol,
            'BSdepth',
            'BSdepth_interp',
            zmCol,
            'Zj',
            'other',
            videoCol,
            'realtime',
            trkTypeCol,
            sourceLatCol,
            sourceLonCol]


#------------- VARIABLES Related to Output Point Shapefiles -------------#

nullDep = -9999 #-999.99 # Nonsense value to for null depth values in shapefile
ptShpSubDir = 'video_transect_data'  # output subdirectory for point shapefile
ptShpSuffix = '_transect_data.shp'  # suffix for output point shapefile

shpDepCol = 'BSdepIntrp' # Interpolated Biosonics Depth column
shpDateCol = 'date_samp'  # Column with date of survey

trkCol = 'tran_num' # to match final database column name, changed from trk to tran_num

            
# Column names and definitions for output transect point shapefile
# Number of items in list must match the input ascii file columns
# and be in the same order for dictionary to set relationship
trkPtShpCols = [[trkCol,'LONG','#','#','#'],
         [shpDateCol,'DATE','#','#','#'],
         ['Time24hr','TEXT','#','#','11'],
         ['BSdepth','DOUBLE','9','2','#'],
         [shpDepCol,'DOUBLE','9','2','#'],
         [zmCol,'SHORT','#','#','#'],
         ['Zj','SHORT','#','#','#'],
         ['other','SHORT','#','#','#'],
         [videoCol,'SHORT','#','#','#'],
         ['realtime','SHORT','#','#','#'],
         ['TrkType','TEXT','#','#','8'],
         [],
         []]

# Combine input output column lists into a dictionary
ptColDict = dict(zip(sourceCols,trkPtShpCols))

# Create a super simple dictionary mapping the new name to original csv name
# for all fields except the long lat fields
mapping = {}
for k, v in ptColDict.items():
  if v:
    mapping[v[0]] = k


#------------- VARIABLES Related to Sample Polygon Shapefiles -------------#

sampPyShpDir = "sample_polygons"  # subdirectory containing sample polygons
sampPyShpSuffix = "_sample_poly.shp"  # suffix for sample polygon shapefiles

#---------------------- VARIABLES Related to Control Files -----------------#

# Control files are provided by MRC and contain the transect type 
# and flags indicating usage of transects for Max/Min Depth
ctlSuffix = "ctl.txt"   # suffix for each site's control file
ctlMinAtt = 'MinDepth'
ctlMaxAtt = 'MaxDepth'
ctlTrkAtt = 'Track'
ctlTrktypeAtt = 'TrackType'
ctlYes = 'Yes'
ctlNo = 'No'


#-------------- VARIABLES Related to Statistics Data Tables ----------------#

# Template Database tables are provided for copying to annual stats tables
templateSites = 'sites' #'site_samp'  # Table for attributes about each site
templateTransects = 'transects' #'transect' # Table for attributes about each transect

# Only certain track types are included in statistics processing
# Right now only using SLPR transects, but could add to list
trkType4Stats = ['SLPR']

# Some individual column names are needed for processing
siteCol = 'site_code' # 'site'
samplenCol = 'tran_len_ft'  # 'samplen_m'
zmlenCol = 'zm_len_ft' #'zmlen_m'
zmfractionCol = 'tran_zm_frac'  # 'zm_fraction'
zmmaxdepCol = 'tran_zm_maxd_ft' #'zm_maxdep_ft'
zmmindepCol = 'tran_zm_mind_ft' #'zm_mindep_ft'
maxdepflagCol = 'tran_maxd_good' #'maxdep_flag'
mindepflagCol = 'tran_mind_good' #'mindep_flag'  
trkmaxdepCol = 'tran_maxd_ft' #'trk_maxdep_ft'
trkmindepCol = 'tran_mind_ft' #'trk_mindep_ft'

trandateCol = 'transect_date'
samplestartdateCol = 'date_samp_start'


estmean_zmfractionCol = 'zm_frac' #'estmean_zmfraction'
estvar_zmfractionCol = 'zm_frac_var' #'estvar_zmfraction'
samp_areaCol = 'samp_area_ft2' #'samp_area_m2'
est_basalcovCol = 'zm_area_ft2' #'est_basalcov_m2'
estvar_basalcovCol = 'zm_area_var_ft4' # 'estvar_basalcov_m2'
cv_basalcovCol = 'zm_area_cv' #'cv_basalcov'
num_transectsCol = 'zm_area_n_tran' # 'num_transects'
num_maxzmdepCol = 'zm_maxd_n_tran' #'num_maxzmdep'
num_minzmdepCol = 'zm_mind_n_tran' #'num_minzmdep'
min_maxzmdepCol = 'zm_maxd_shallowest_ft' #'min_maxzmdep_ft'
min_minzmdepCol = 'zm_mind_shallowest_ft' #'min_minzmdep_ft'
max_maxzmdepCol = 'zm_maxd_deepest_ft' #'max_maxzmdep_ft'
max_minzmdepCol = 'zm_mind_deepest_ft' #'max_minzmdep_ft'
mean_maxzmdepCol = 'zm_maxd_mean_ft' #'mean_maxzmdep_ft'
mean_minzmdepCol = 'zm_mind_mean_ft' #'mean_minzmdep_ft'
std_maxzmdepCol = 'zm_maxd_std'  #'std_maxzmdep' # 
std_minzmdepCol = 'zm_mind_std' # 'std_minzmdep' # 
se_maxzmdepCol = 'zm_maxd_se_ft' #'se_maxzmdep'
se_minzmdepCol = 'zm_mind_se_ft' #'se_minzmdep'
# added
var_maxzmdepCol = 'zm_maxd_var_ft2'
var_minzmdepCol = 'zm_mind_var_ft2'
zmareaSECol = 'zm_area_se_ft2'
ci95_zmareaCol = 'zm_area_95_ci_ft'
ci95_maxzmdepCol = 'zm_maxd_95_ci_ft'
ci95_minzmdepCol = 'zm_mind_95_ci_ft'

approx_latCol = 'approx_lat'
approx_lonCol = 'approx_lon'

# Here is the whole list of column names for the data tables, in order
# These must match exactly the column names in the table
# If the table column names are changed, this list must be changed too.
# Site and Transect Table Field Names
siteTabCols = [
siteCol,
samplestartdateCol,
num_transectsCol,
estmean_zmfractionCol,
estvar_zmfractionCol,
samp_areaCol,
est_basalcovCol,
estvar_basalcovCol,
cv_basalcovCol,
zmareaSECol,
ci95_zmareaCol,
num_minzmdepCol,
mean_minzmdepCol,
max_minzmdepCol,
min_minzmdepCol,
std_minzmdepCol,
var_minzmdepCol,
se_minzmdepCol,
ci95_minzmdepCol,
num_maxzmdepCol,
mean_maxzmdepCol,
max_maxzmdepCol,
min_maxzmdepCol,
std_maxzmdepCol,
var_maxzmdepCol,
se_maxzmdepCol,
ci95_maxzmdepCol,
approx_latCol,
approx_lonCol,
]

transTabCols = [
siteCol,
samplestartdateCol,
trandateCol,
trkCol,
samplenCol,
zmlenCol,
zmfractionCol,
trkmaxdepCol,
zmmaxdepCol,
zmmindepCol,
trkmindepCol,
maxdepflagCol,
mindepflagCol,
]

#-------------- VARIABLES Related to Soundwide Area Data Tables ----------------#
svyyrCol = "survey_year"
stratumanalysisCol = "stratum_analysis"
extrapolationCol = "extrapolation"
samplegroupCol = "sample_group"
swareaCol = "zm_area_m2"
swvarCol = "zm_var_m4"
swseCol = "se_m2"
swcvCol = "cv"
niCol = "ni"
NiCol = "Ni"
A2Col = "A2"
AijCol = "Aij"
RCol = "R"
LTCol = "LT"
LNCol = "LN"

svyyrCol1 = "survey_year1"
svyyrCol2 = "survey_year2"
sitecountCol = "site_count"
slopeCol = "slope"
seCol = "se_slope"
propChgCol = "prop_change"
zmAreaChgCol = "zm_area_chg_m2"
zmAreaChgSECol = "se_zm_area_chg"
zmAreaChgCI = "mc_95ci"


swAreaStratumCols = [
svyyrCol,
stratumanalysisCol,
extrapolationCol,
samplegroupCol,
swareaCol,
swvarCol,
swseCol,
swcvCol,
niCol,
NiCol,
A2Col,
AijCol,
RCol,
LTCol,
LNCol
]

swAreaAllCols = [
svyyrCol,
samplegroupCol,
swareaCol,
swvarCol,
swseCol,
swcvCol
]

swAreaChgStratumCols = [
svyyrCol1,
svyyrCol2,
stratumanalysisCol,
samplegroupCol,
sitecountCol,
slopeCol,
seCol,
propChgCol,
zmAreaChgCol,
zmAreaChgSECol
]

swAreaChgAllCols = [
svyyrCol1,
svyyrCol2,
samplegroupCol,
propChgCol,
zmAreaChgCol,
zmAreaChgSECol,
zmAreaChgCI
]


#------------ VARIABLES Related to All Sites Point Shapefile -------#
sitePtIDCol = 'NAME'
siteTypeCol = 'TYPE'
siteLocnCol = 'sitename' #'Location'
siteGeoStratCol = 'STRATA_GEO'
siteSampStratCol = 'STRATUM'
siteFocusAreaCol = 'FOCUS_AREA'
siteFocusStratCol = 'FOCUS_STRA'

sitePtCols = [
sitePtIDCol,
siteTypeCol,
siteLocnCol
]


#-------------- VARIABLES Related to Site Summaries ----------------#
# Site Description Dictionary
sitetypeDict = {
'cor':'Core',
'fl':'Flats', 
'fr':'Narrow Fringe',
'frw':'Wide Fringe'
}

sitetypeList = sitetypeDict.keys()
sitetypeList.sort()

#--------------------------------------------------------------------------
#------------- End of CONSTANTS, Column LISTS and Dictionaries ------------
#--------------------------------------------------------------------------

#--------------------------------------------------------------------------
#------------- FUNCTIONS to BUILD LISTS and DICTIONARIES ------------------
#---------- Generally used for sites and associated directories ------------
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Create a list of sites from input text file
# Assumes it is a text file, with one site listed per line
def make_siteList(inFileName):
    # Get all lines from input file without leading or trailing whitespace
    # and omit lines that are just whitespace
    siteList = [line.strip() for line in open(inFileName,'r') if not line.isspace()]
    return siteList
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Create a list of subdirectories in the Parent Directory
def make_subDirList(parentDir):
    # List everything in subdirectory, and filter based on the item being a directory
    subDirList = [x for x in os.listdir(parentDir) if os.path.isdir(os.path.join(parentDir,x))]
    return subDirList
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Create a dictionary with the site name and associated subdirectory
# Have to look for site id within subdirectory name, because it can have a suffix
# Assumes there is only one subdirectory for each site
def make_siteDirDict(siteList, subDirList):
    siteDirDict = {}
    for site in siteList:
        for d in subDirList:
            if site in d:
                siteDirDict[site] = d               
    return siteDirDict
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Get a list of field names from a feature class, excluding FID and Shape
def get_fieldnames(FC,gp):
    fieldnames = []
    fieldlist = gp.ListFields(FC,'*','all')
    field = fieldlist.Next()
    while field:
        if field.Name != 'FID' and field.Name != 'Shape':
            fieldnames.append(field.Name)
        field = fieldlist.Next()
    return fieldnames 

#--------------------------------------------------------------------------
#------------------------ CONVERSION FUNCTIONS -----------------------------
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Convert separate date/time columns to one value in format for database
# Assumes Date in mm/dd/yyyy format and 
# time in hh:mm:ss AM/PM format
def convert_DateTime(survDate,survTime):
    # Convert to 24-hour time
    [hms,ampm] = survTime.split(' ')
    [h,m,s] = hms.split(':')
    if ampm == 'PM' and int(h) < 12:
    # Add 12 hours to get 24 hour time
        h = str(int(h) + 12)
    if int(h) < 10 and len(h) < 2:
    # Add leading zero to hour if missing
        h = '0' + h
    # if it's in the 12 A.M. hour, need to change to 00
    if ampm == 'AM' and int(h) == 12:
        h = '00'
    time24hr = ':'.join([h,m,s])
    date_time = ' '.join([survDate,time24hr])
    return (date_time, time24hr) 
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Convert Degree/minute format to Decimal Degrees
# Assumes input in format ##d##.####' Dir  (i.e. 48d33.8342' N)
def dm2dd(coordDegMin):
    [deg,minDir] = coordDegMin.split('d')
    [minute,Dir] = minDir.split("' ")
    coordDD = int(deg) + (float(minute) / 60)
    if Dir in ['W','S']:
        coordDD = coordDD * (-1)
    return coordDD
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Make a COM version of Input Coordinate System as a Spatial Reference Object
# Due to a peculiarity with the Cursors in ArcGIS, InsertCursor
# will only accept a COM Object version of the Spatial Reference
# Which is only available when doing a describe on a feature class
def make_spatRef(gp,aDir,coordSys):
    tempName = 'tmp4sr.shp'
    tempFC = gp.CreateFeatureClass(aDir,tempName,"POINT","#","#","#",coordSys)
    desc = gp.describe(tempFC)
    spatRef = desc.SpatialReference
    gp.delete(tempFC)
    return spatRef
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
#------------------------ STATISTICS FUNCTIONS -----------------------------
#--------------------------------------------------------------------------
# Calculate Ratio estimator of variance for eelgrass fraction
# Variable names follow DNR SVMP nomenclature from 
# "Puget Sound Vegetation Monitoring Project:  2000 - 2002 Monitoring Report"
#  See Appendix L, Page 3
def ratioEstVar(L_list,l_list,pBarHat,m,LBar):
    numerator = 0
    # Loop through list of eelgrass and sample lengths in parallel
    for l,L in zip(l_list,L_list):
        numerator = ((l - (pBarHat * L)) ** 2) + numerator
    
    denominator = (m - 1) * m * (LBar ** 2)
   
    estvar = numerator / denominator
   
    return estvar        
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------  
# Calculate Standard Deviation of a sample
def stdDev(sample):
    N = len(sample)  # number of samples
    # Can't calculate if number if samples is 0 or 1
    mean = float(sum(sample)) / N    # mean of the samples
    sum_sqdif = 0  # initialize sum of squared differences
    # Calculate sum of squared differences
    for val in sample:
        sqdif = (val - mean) ** 2
        sum_sqdif = ((val - mean) ** 2) + sum_sqdif
    
    # Standard Deviation
    s = ( (1 / ( float(N) - 1 )) * sum_sqdif ) ** 0.5
    return s
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------  
# Calculate Variance of a sample
# Paramter is standard deviation
def variance(stdDev):
    var = stdDev ** 2
    return var
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------  
# Calculate Standard Error of a sample
# Parameters are Standard Deviation and number samples
def stdErr(s,N):
    SE = s / (float(N) ** 0.5)
    return SE
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
# Calculate 95% confidence interval
# Parameter is Standard Error (se)
def ci95(SE):
    confint95 = 1.96 * SE
    return confint95
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------


#------------------------ DATA EXTRACTION FUNCTIONS -----------------------------
#--------------------------------------------------------------------------

#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Extract the data from the table using a select statement and column list
def get_Data(dataTable,selStatement,colList,gp):
    print dataTable,selStatement,colList
    # initalize list to hold extracted data
    allData = []
    # Search Cursor with the selection statement
    rows = gp.SearchCursor(dataTable,selStatement)
    row = rows.Next()
    while row:
        # initialize list to hold data for the row
        rowData = []
        # Get the data from each desired column and put in list
        for col in colList:
            rowData.append(row.GetValue(col))
        # Append row data list, to list of lists for all data
        allData.append(rowData)
        row = rows.Next()
    del rows
    print allData
    return allData
        
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
