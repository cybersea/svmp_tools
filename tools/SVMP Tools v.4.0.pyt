import arcpy
import os

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "SVMP Tools v.4.0"
        self.alias = "svmp40"

        # List of tool classes associated with this toolbox
        self.tools = [TransectDatatoPtFC, TransectAndSiteStatistics]


class TransectDatatoPtFC(object):

    def __init__(self):
        """Tool to convert SVMP video survey point files (csv) to point feature classes"""
        self.label = "(1) Transect Data to Point Feature Class"
        self.description = "This tool converts SVMP video survey files from csv format to point feature classes"
        self.canRunInBackground = True

    def getParameterInfo(self):
        """Define parameter definitions"""

        # Input parameter 1:  Parent directory for site data folders and input csv files
        in_dir = arcpy.Parameter(
            displayName="Input Data Parent Directory",
            name="in_dir",
            datatype="Folder",
            parameterType="Required",
            direction="Input"
        )
        # Input parameter 2:  Text file with list of sites to process
        sites_file = arcpy.Parameter(
            displayName="List of Sites file",
            name="sites_file",
            datatype="File",
            parameterType="Required",
            direction="Input"
        )
        # Input parameter 3: Table with vegetation codes
        vegcode_table = arcpy.Parameter(
            displayName="Vegetation Code Table",
            name="vegcode_table",
            datatype="Table",
            parameterType="Required",
            direction="Input"
        )

        out_gdb = arcpy.Parameter(
            displayName="Output Geodatabase",
            name="out_gdb",
            datatype="Workspace",
            parameterType="Required",
            direction="Input"
        )
        out_gdb.filter.list = ['Local Database','Remote Database']

        err_dir = arcpy.Parameter(
            displayName="Output Error Log Directory",
            name="err_dir",
            datatype="Folder",
            parameterType="Required",
            direction="Input"
        )

        # Default values  -- Change or remove these for DNR paths
        in_dir.value = "Y:/projects/dnr_svmp2016/data/2014_test/site_folders"
        sites_file.value = os.path.join("Y:/projects/dnr_svmp2016/data/2014_test", "sites2process_all.txt")
        vegcode_table.value = "Y:/projects/dnr_svmp2016/db/SVMP_2000_2015_DB.v4_20170109/SVMP_DB_v4_20170109.mdb/veg_codes"
        out_gdb.value = "Y:/projects/dnr_svmp2016/data/2014_test/2014_test_pgdb.mdb"
        err_dir.value = "Y:/projects/dnr_svmp2016/data/2014_test/site_folders"

        params = [in_dir, sites_file, vegcode_table, out_gdb, err_dir]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[2].value:
            vegcode_table = parameters[2].value
            vegcode_field = 'veg_code'
            # table = arcpy.Describe(vegcode_path).baseName
            field_names = [f.name for f in arcpy.ListFields(vegcode_table)]
            if vegcode_field not in field_names:
                errtext = "[SVMP ERROR]: The selected table, {0}, has no field {1}.".format(vegcode_table, vegcode_field)
                errtext += "\nChoose a different table."
                parameters[2].setErrorMessage(errtext)
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        import csv2pt
        reload(csv2pt)  # Remove this after development

        # Input parameter 1:  Parent directory for site data folders and input csv files
        in_dir = parameters[0].valueAsText # "Y:/projects/dnr_svmp2016/data/2014_test/site_folders"

        # Input parameter 2:  Text file with list of sites to process
        sites_file = parameters[1].valueAsText # os.path.join("Y:/projects/dnr_svmp2016/data/2014_test", "sites2process_all.txt")

        # Input parameter 3: Table with vegetation codes
        vegcode_table = parameters[2].valueAsText # "Y:/projects/dnr_svmp2016/db/SVMP_2000_2015_DB.v4_20170109/SVMP_DB_v4_20170109.mdb/veg_codes"

        # Input parameter 4: Output Geodatabase to store point feature classes
        out_gdb = parameters[3].valueAsText # "Y:/projects/dnr_svmp2016/data/2014_test/2014_test_pgdb.mdb"

        # Input parameter 5: Error Log directory
        err_dir = parameters[4].valueAsText  # in_dir

        # Call the main function to process the csv point data
        csv2pt.main(in_dir, sites_file, vegcode_table, out_gdb, err_dir)

        return


class TransectAndSiteStatistics(object):
    def __init__(self):
        """Tool to calculate SVMP transect and site statistics from transect point features """
        self.label = "(2) Calculate Transect and Site Statistics"
        self.description = "This tool calculates SVMP transect and site statistics from transect point features"
        self.canRunInBackground = True

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = None
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        return
