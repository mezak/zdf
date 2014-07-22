

#read in zdf file, convert to geojson
def readzdf(zdfpath):
    reader = shapefile.Reader(zdfpath)
    fields = reader.fields[1:]
    field_names = [field[0] for field in fields]
    buffer = []
    for sr in reader.shapeRecords():
        atr = dict(zip(field_names, sr.record))
        geom = sr.shape.__geo_interface__
        buffer.append(dict(type="Feature", \
        geometry=geom, properties=atr)) 
   
    # write the GeoJSON file
    from json import dumps
    geojson = open("pyshp-demo.json", "w")
    geojson.write(dumps({"type": "FeatureCollection",\
        "features": buffer}, indent=2) + "\n")
    geojson.close()

#get a section of the zdf into a list
def zdfsection(i,entire_zdf):
    
    i+=1
    numlines = 0
    thelines = []
    
    while i < len(entire_zdf) and entire_zdf[i].replace('\n', '').strip():
        thestring = entire_zdf[i].replace('\n', '').strip()
        strlist = thestring.split(',')
        for item in strlist:
            item.strip()
        thelines.append(strlist)
        numlines+=1
        i+=1

    if numlines==0:
        logmsg = 'Nothing imported for this section: ' + entire_zdf[i-1].replace('\n', '').strip()
    else:
        logmsg=None

    outputlist = [numlines,i,thelines,logmsg]
    return outputlist

def read_zone(thelines):
    azone = {}
    zonename = str(thelines[0][0])
    azone['point_number'] = int(thelines[0][1])
    thecoords=[]
    for pnt in thelines[1:]:
        lat = float(pnt[0])
        lon = float(pnt[1])
        thecoords.append([lat,lon])
    azone['coordinates'] = copy.copy(thecoords)

    logmsg = ''
    if len(thecoords)!=azone['point_number']:
        logmsg = '\n'+azone['name']+': given number of points ('+str(azone['point_number'])
        logmsg = logmsg+') does not equal list length: '+str(len(thecoords))+'\n'

    if azone['coordinates'][0]!=azone['coordinates'][-1]:
        logmsg = logmsg + '\nFirst and last coordinates are not the same: \n'
        logmsg = logmsg+str(azone['coordinates'][0])+'   '
        logmsg = logmsg+str(azone['coordinates'][-1])+'\n'

    outputlist = [logmsg, zonename, azone]
        
    return outputlist



def read_tide_zone(thelines):
##    print thelines
    alltidezones= []
    onetidezone = [0,1,2,3,4]
    for oneline in thelines:
        onetidezone[0] = oneline[0]
        onetidezone[1] = int(oneline[1])
##        print onetidezone[1]
        onetidezone[2] = oneline[2]
        #assumes time offset in whole minutes
##        print oneline[3]
        onetidezone[3] = int(oneline[3])
        onetidezone[4] = float(oneline[4])
        alltidezones.append(copy.copy(onetidezone))

##    print alltidezones
    return alltidezones


#assumes 1 station per zone
def read_tide_station(thelines):
    allstations = []
    onestation = [0,1,2]
    for oneline in thelines:
        onestation[0] = int(oneline[0])
        onestation[1] = float(oneline[1])
        onestation[2] = float(oneline[2])
        allstations.append(copy.copy(onestation))
    return allstations


# assumes 2 stations numbers per zone
def read_tide_average(thelines):
    allaverages = []
    oneavg = [0,1,2]
    for oneline in thelines:
        oneavg[0] = oneline[0]
        oneavg[1] = int(oneline[1])
        oneavg[2] = int(oneline[2])
        allaverages.append(copy.copy(oneavg))
    return allaverages


def read_options(thelines):
    options={}
    
    options['Outage'] = thelines[0][1]
    options['Interval'] = thelines[1][1]
    
    return options

###################################
#
# START HERE
#
###################################


def convertzdf():
    print 'start convertzdf'
    try:
        row = rows = logfile = zdf_file = None

        basepath = mzconstants.basepath+'05-convert FPIzdf\\'
        print basepath
        
        # get the provided parameters
        zdfpath = basepath+'input\\OPRQ191KR2012_JOAZoning_20120911.zdf'
        outputFD = basepath+'output\\'
        outputZonesName = 'JOAZoning_20120911_FPI.shp'
        outputStationsName = 'OPRQ191KR2012_stations_20120911.shp'
        prjfile = basepath+'input\\NAD83.prj'
        spatial_reference = arcpy.SpatialReference(prjfile)
        logfilepath = basepath+'output\\OPRQ191KR2012_JOAZoning_20120911.LOG'
        
        outputZonesPath = outputFD+'\\'+outputZonesName
        outputStationsPath = outputFD+'\\'+outputStationsName
        
        #write logfile
        print 'open log file'
        
        logfile = open(logfilepath,'w')
        logfile.write('Convert ZDF to feature class.\n\n')
        logfile.write('zdf: '+zdfpath+'\n')
        logfile.write('output dataset: '+outputFD+'\n')
        logfile.write('output zoning feature class name: '+outputZonesName+'\n')
        logfile.write('output station feature class name: '+outputStationsName+'\n\n')

        # set toolbox
##        gp.toolbox = 'management'

        # read in ZDF file
        #test number of coords is correct
        #first coord = last coord
        ZONE = {}
        zone_count = 0
        zone_good = 0
    ##    TIDE_ZONE = []
        TIDE_STATION = []
        TIDE_AVERAGE = []
        OPTIONS = {}

        print 'read in zdf file'
        zdf_file = open(zdfpath,'r')

        valid_format = False
        
        entire_zdf = zdf_file.readlines()
        
        i = 0
        while i<len(entire_zdf):
            oneline = entire_zdf[i].replace('\n','').strip()
            if not oneline:
                current_status = ''
                i+=1
                
            elif oneline == '[ZONE_DEF_VERSION_2]':
                valid_format = True
                i+=1
                
            elif oneline == '[ZONE]' and valid_format:
                zone_count+=1
                section_return = zdfsection(i,entire_zdf)
                i = section_return[1]
                if section_return[0] > 0:
                    read_return = read_zone(section_return[2])
                    if read_return[0]:
                        logfile.write(read_return[0])
                    else:
                        if ZONE.has_key(read_return[1]):
                            #problem
                            logfile.write('Duplicate zone defintions for '+read_return[1]+'\n')
                        else:
                            ZONE[read_return[1]] = read_return[2]
                            zone_good+=1
                else:
                    logfile.write(section_return[3])
                    
            elif oneline == '[TIDE_ZONE]' and valid_format:
                section_return = zdfsection(i,entire_zdf)
                i = section_return[1]
                if section_return[0] > 0:
                    TIDE_ZONE = read_tide_zone(section_return[2])
##                    print section_return[2]
                else:
                    logfile.write(section_return[3])
                    
            elif oneline == '[TIDE_STATION]' and valid_format:
                section_return = zdfsection(i,entire_zdf)
##                print section_return
                i = section_return[1]
                if section_return[0] > 0:
                    TIDE_STATION = read_tide_station(section_return[2])
##                    print section_return[2]
                else:
                    logfile.write(section_return[3])
                    
            elif oneline == '[TIDE_AVERAGE]' and valid_format:
                section_return = zdfsection(i,entire_zdf)
                i = section_return[1]
                if section_return[0] > 0:
                    TIDE_AVERAGE.append(read_tide_average(section_return[2]))
                else:
                    logfile.write(section_return[3])
                    
            elif oneline == '[OPTIONS]' and valid_format:
                section_return = zdfsection(i,entire_zdf)
                i = section_return[1]
                if section_return[0] > 0:
                    OPTIONS = read_options(section_return[2])
                else:
                    logfile.write(section_return[3])
            else:
                #PROBLEM
                logfile.write('Problem with ZDF format.\n')
                logfile.write(oneline+'\n')

        ###############
        # a little QC
        ###############
        print 'check zdf file'
        if zone_count!=zone_good:
            logfile.write(str(zone_count)+' zone descriptions in file, but only ' +
                          str(zone_good)+' zone descriptions were valid.\n')
        else:
            logfile.write('All '+str(zone_good)+' zone descriptions are valid.\n')
        
        if len(ZONE) != len(TIDE_ZONE):
            logfile.write('The number of ZONE descriptions does not match the number ' +
                          'of TIDE ZONE records: '+
                          str(len(ZONE))+' vs. '+str(len(TIDE_ZONE))+'\n')

        zonename_list = ZONE.keys()
##        print zonename_list
        for atidezone in TIDE_ZONE:
            if not atidezone[0] in zonename_list:
                logfile.write('TIDE ZONE '+str(atidezone[0])+' not in ZONE list.\n')

        tidezonename_list = [atidezone[0] for atidezone in TIDE_ZONE]
##        print tidezonename_list
        for azone in ZONE.iterkeys():
            if not azone in tidezonename_list:
                logfile.write('ZONE '+azone+' not in TIDE ZONE list.\n')

        station_list = [astation[0] for astation in TIDE_STATION]
        for atidezone in TIDE_ZONE:
            if not atidezone[1] in station_list:
                logfile.write('TIDE ZONE station '+str(atidezone[1])+' not in TIDE STATION list.\n')

        ##########
        # combine all TIDE ZONE info into ZONE dictionary
        ##########
        print 'create zone dictionary'
        for atidezone in TIDE_ZONE:
            if ZONE.has_key(atidezone[0]):
                ZONE[atidezone[0]]['zoning factors'] = copy.copy(atidezone[1:])
##                print ZONE[atidezone[0]]
        

        ##########
        # create feature class
        ##########
        print 'create feature class'
        arcpy.overwriteOutput = True
        # need spatial ref from target dataset?

        # create the new featureclass
        arcpy.CreateFeatureclass_management(outputFD, outputZonesName,
                                            'POLYGON', '#','DISABLED',
                                            'DISABLED',spatial_reference)
        # create fields
        # file id, zone name, station number, station type,
        # time offset, range ratio, station list (semi-colon separated)
        
##        gp.addfield(outputZonesPath, 'File_ID', 'LONG')
        arcpy.AddField_management(outputZonesPath, 'Zone', 'TEXT')
        arcpy.AddField_management(outputZonesPath, 'StationID', 'LONG')
        arcpy.AddField_management(outputZonesPath, 'Sta_Type', 'TEXT')
        arcpy.AddField_management(outputZonesPath, 'TimeOffset', 'LONG')
        arcpy.AddField_management(outputZonesPath, 'RRatio', 'FLOAT')

        # get some information about the new featureclass for later use.
        ZonesDesc = arcpy.Describe(outputZonesPath)
        #need this to create and assign to shape field in feature class
        shapefield = ZonesDesc.ShapeFieldName
        
        # create the cursor and objects necessary for the geometry creation
        rows = arcpy.InsertCursor(outputZonesPath)
        polyArray = arcpy.Array()

        polycount = 1

        for azone in ZONE.keys():
            thiszone = ZONE[azone]
            newzone = rows.newRow()
##            newzone.id == polycount
            for coords in thiszone['coordinates']:
##                logfile.write(str(coords))
                pnt = arcpy.Point(coords[1],coords[0])
##                pnt.id = polycount
##                pnt.x = coords[1]
##                pnt.y = coords[0]
                polyArray.add(pnt)
                    
            newzone.shape = polyArray
            newzone.setValue('Zone',azone)
            newzone.setValue('StationID',thiszone['zoning factors'][0])
            newzone.setValue('Sta_Type',thiszone['zoning factors'][1])
            newzone.setValue('TimeOffset',thiszone['zoning factors'][2])
            newzone.setValue('RRatio',thiszone['zoning factors'][3])
            rows.insertRow(newzone)
            
            polyArray.removeAll()
            polycount +=1

        del newzone
        del rows
        del polyArray
        del pnt


        ###############
        # create the stations featureclass
        ################
        arcpy.CreateFeatureclass_management(outputFD, outputStationsName,
                                            'point', '#','DISABLED', 'DISABLED', spatial_reference)
        # create field
##        gp.addfield(outputZonesPath, 'File_ID', 'LONG')
        arcpy.AddField_management(outputStationsPath, 'StationID', 'LONG')

        # get some information about the new featureclass for later use.
        StationDesc = arcpy.Describe(outputStationsPath)
        #need this to create and assign to shape field in feature class
        shapefield = StationDesc.ShapeFieldName
        
        # create the cursor and objects necessary for the geometry creation
        rows = arcpy.InsertCursor(outputStationsPath)
        row = rows.newRow()
        
        station_count = 1
        for astation in TIDE_STATION:
            pnt = arcpy.Point(astation[2],astation[1])
                    
            row.setValue(shapefield, pnt)
            row.setValue('StationID', astation[0])
            rows.insertRow(row)

            station_count+=1


        del row
        del rows
        del pnt

        return 0
                    


    finally:
        if logfile:
            logfile.close()
        if zdf_file:
            zdf_file.close()
##        if row:
##            del row
##        if rows:
##            del rows

if __name__ == '__main__':

    convertzdf()
    
    
