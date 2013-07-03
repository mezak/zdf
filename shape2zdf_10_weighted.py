# shape2zdf
# converts feature class to/from ZDF text file
# assumes NAD83 lat/lon spatial reference
# does not handle multiple stations per zone (only 1)
# does not handle tide average (only writes one station
# to each zone under the TIDE_AVERAGE section
#
# updated for ArcGIS 10
# to be updated to use Fiona and Shapely and remove ArcPy
# also an experiment with GitHub

import string, os, sys, locale, copy
import mzconstants
import arcpy
arcpy.env.overwriteOutput = True

##{'zone':'Zone',
## 'station1':'StationID',
##'station1type':'Sta_Type',
## 'rr1':'RRatio',
## 'to1':'TimeOffset',
## 'w1':'Weight_1',
## 'station2':'StationID2',
##'station2type':'Sta_Type2',
## 'rr2':'RRatio_2',
## 'to2':'TimeOff_2',
## 'w2':'Weight_2'} 


def writezdf(inputzoningpath,inputstationpath,outputzdfpath,zfields,stationfields):
    try:
        logfile = 0
        zdf_file = 0

        print 'begin writezdf...'
        
        #write logfile
        logfilepath = os.path.splitext(outputzdfpath)[0]+'.LOG'
        logfile = open(logfilepath,'w')
        logfile.write('Convert feature to ZDF.\n\n')
        logfile.write('input zoning feature class: '+os.path.split(inputzoningpath)[1]+'\n')
        logfile.write('input station feature class: '+os.path.split(inputstationpath)[1]+'\n')
        logfile.write('output zdf: '+os.path.split(outputzdfpath)[1]+'\n')
   
        # open zdf file
        zdf = open(outputzdfpath,'w')
        zdf.write('[ZONE_DEF_VERSION_2]\n')

        if not os.path.isfile(inputzoningpath):
            print 'Problem with path...EXITING.'
            print inputzoningpath
            return 0
        zdfDesc = arcpy.Describe(inputzoningpath)
        oidname = zdfDesc.OIDFieldName

        newstationlist =[]
        tideavglist = []
        cent_dict = {}

        zdfRows = arcpy.SearchCursor(inputzoningpath,"","",zfields['zone'],zfields['zone']+" A")
        zdfRow = zdfRows.next()
        
        logfile.write('Shape Type: ' + zdfDesc.ShapeType + "\n")

        while zdfRow:
            # Create the geometry object
            feat = zdfRow.getValue(zdfDesc.ShapeFieldName)

            #get centroid for later in case we want to use it for tide station coord
            cent_dict[zdfRow.getValue(zfields['zone'])] = feat.centroid
            
            # the current multipoint's ID
            logfile.write('Feature '+str(zdfRow.getValue(oidname))+':')
            zdf.write('\n[ZONE]\n')
            partcount = feat.partCount
            zonestr = str(zdfRow.getValue(zfields['zone']))
            zone_coords = []
            partnum = 0
            
            # Enter while loop for each part in the feature (if a singlepart feature
            # this will occur only once)
            pntcount = 0
            while partnum<partcount:
                logfile.write('Part '+str(partnum)+'\n')
                part = feat.getPart(partnum)
                pnt = part.next()
                pntcount = 0
                # Enter while loop for each vertex
                while pnt:
                    zone_coords.append([pnt.X,pnt.Y])
                    pnt = part.next()
                    pntcount += 1
                    if not pnt:
                        pnt = part.next()
                        if pnt:
                            logfile.write('Interior ring\n')
                partnum+=1
                
            zdf.write(str(zdfRow.getValue(zfields['zone']))+','+str(pntcount)+'\n')
            for coords in zone_coords:
                lat = '%9.6f' % coords[1]
                lon = '%9.6f' % coords[0]
                zdf.write(lat+','+lon+'\n')
            zdfRow = zdfRows.next()
            
        del zdfRow
        del zdfRows


        ########
        # TIDE ZONE
        ########

        zdf.write('\n[TIDE_ZONE]\n')

        weightedcombo = True
        # to qualify as a weighted combination zone, must have these
        # fields in the zfields dictionary
        checklist = ['station2','rr2','to2','w2'] 
        for item in checklist:
            if item not in zfields.keys():
                weightedcombo = False
        if not weightedcombo:
            print 'Not a weighted zoning shapefile'
                
        if weightedcombo:
            #verify these fields also exist in the shapefile
            fieldlist = arcpy.ListFields(inputzoningpath)
            for item in checklist:
                fndfld = False
                fldname = zfields[item]
                for afieldobj in fieldlist:
                    if afieldobj.name == fldname:
                        fndfld = True
                if not fndfld:
                    weightedcombo = False
                    print 'Did not find',fldname,'in this shapefile'
                    print 'Not a weighted zoning shapefile'

        if weightedcombo:
            print 'This shapefile may have weighted combination zones.'
            zdfRows = arcpy.SearchCursor(inputzoningpath,"","","",
                                         zfields['zone']+" A")
            zdfRow = zdfRows.next()

            while zdfRow:
                if ((not zdfRow.isNull(zfields['station2']) and
                    not zdfRow.isNull(zfields['to2']) and
                    not zdfRow.isNull(zfields['rr2']) and
                    not zdfRow.isNull(zfields['w2']) ) and 
                    (float(zdfRow.getValue(zfields['rr2']))!=0 and
                     float(zdfRow.getValue(zfields['w2']))!=0)):
                    # we have all the info we need for a weighted zone
                    logfile.write(str(zdfRow.getValue(zfields['zone']))+' = weighted zone\n')

                    wzonenum = zdfRow.getValue(zfields['zone']).strip('JOA')
                    newstation = str(9990000 + int(wzonenum))
                    #newstation = str(9990000 + int(zdfRow.getValue(oidname)))
                    newstationlist.append([newstation,cent_dict[zdfRow.getValue(zfields['zone'])]])
                    str_offset = '0'
                    str_ratio = '%4.3f' % 1.0
                    
                    #if weighted combination of different tide stations
                    # create new, unique station name (must also be used for name of tide data file)
                    # name is 9990000 + FID
                    # to = 0
                    # rr = 1
                    # stationtype = PRIM

                    # some shapefiles don't have a station type field
                    if zfields['station1type'] == None:
                        stationtype = 'PRIM'
                    else:
                        stationtype = zdfRow.getValue(zfields['station1type'])
                    zdf.write(str(zdfRow.getValue(zfields['zone']))+','+
                          newstation+','+
                          stationtype+','+
                          str_offset+','+
                          str_ratio+'\n')
                    tideavglist.append([str(zdfRow.getValue(zfields['zone'])),newstation])
                    zdfRow = zdfRows.next()
                    
                else:
                    #this is not a weighted zone 
                    str_offset = str(int(zdfRow.getValue(zfields['to1'])))
                    str_ratio = '%4.3f' % zdfRow.getValue(zfields['rr1'])
                    if float(str_ratio)==0:
                        print '***',zdfRow.getValue(zfields['zone']),'range ratio = 0 ***'

                    # some shapefiles don't have a station type field
                    if zfields['station1type'] == None:
                        stationtype = 'PRIM'
                    else:
                        stationtype = zdfRow.getValue(zfields['station1type'])
                    zdf.write(str(zdfRow.getValue(zfields['zone']))+','+
                              str(int(zdfRow.getValue(zfields['station1'])))+','+
                              stationtype+','+
                              str_offset+','+
                              str_ratio+'\n')
                    tideavglist.append([str(zdfRow.getValue(zfields['zone'])),
                                        str(zdfRow.getValue(zfields['station1']))])
                    zdfRow = zdfRows.next()
                
            del zdfRow
            del zdfRows
            

        else:   
            # if only one set of zoning parameters exist
            
            zdfRows = arcpy.SearchCursor(inputzoningpath,"","",
                                      zfields['zone']+';'+zfields['station1']+';'+
                                      zfields['to1']+';'+
                                      zfields['rr1'],zfields['zone']+" A")
            zdfRow = zdfRows.next()

            while zdfRow:
                str_offset = str(int(zdfRow.getValue(zfields['to1'])))
                str_ratio = '%4.3f' % zdfRow.getValue(zfields['rr1'])
                if float(str_ratio)==0:
                    print '***',zdfRow.getValue(zfields['zone']),'range ratio = 0 ***'
                # some shapefiles don't have a station type field
                if zfields['station1type'] == None:
                    stationtype = 'PRIM'
                else:
                    stationtype = zdfRow.getValue(zfields['station1type'])
                zdf.write(str(zdfRow.getValue(zfields['zone']))+','+
                          str(int(zdfRow.getValue(zfields['station1'])))+','+
                          stationtype+','+
                          str_offset+','+
                          str_ratio+'\n')
                tideavglist.append([str(zdfRow.getValue(zfields['zone'])),
                                        str(zdfRow.getValue(zfields['station1']))])
                zdfRow = zdfRows.next()
                
            del zdfRow
            del zdfRows

            
        
        ########
        # TIDE STATIONS
        ########

        zdf.write('\n[TIDE_STATION]\n')
        stationDesc = arcpy.Describe(inputstationpath)
        shapefieldname = stationDesc.ShapeFieldName
        stationRows = arcpy.SearchCursor(inputstationpath,"","",stationfields['station'],stationfields['station']+" A")
        stationRow = stationRows.next()
        # Create the geometry object
        while stationRow:
            feat = stationRow.getValue(shapefieldname)
            pnt = feat.getPart()
            zdf.write(str(stationRow.getValue(stationfields['station'])))
            lat = '%9.6f' % pnt.Y
            lon = '%9.6f' % pnt.X
            zdf.write(','+lat+','+lon+'\n')
            stationRow = stationRows.next()

        for newstation in newstationlist:
            lat = '%9.6f' % newstation[1].Y
            lon = '%9.6f' % newstation[1].X
            zdf.write(newstation[0]+','+lat+','+lon+'\n')
            
        del stationRow
        del stationRows
        
        ########
        # TIDE AVERAGE
        ########

        zdf.write('\n[TIDE_AVERAGE]\n')
        for azone in tideavglist:
            zdf.write(azone[0]+','+str(int(float(azone[1])))+','+str(int(float(azone[1])))+'\n')

        zdf.write('\n[OPTIONS]\n')
        zdf.write('Outage, 30\n')
        zdf.write('Interval, 360\n')
        

    finally:
        if logfile:
            logfile.close()
        if zdf_file:
            zdf_file.close()

if __name__ == '__main__':

    basepath = mzconstants.basepath+''
    
    inputpath = basepath + 'input\\'
    inputzoningname = 'K354KR2012CORP_JOAfinal_20130118.shp'
    inputzoningpath = inputpath+inputzoningname
    inputstationname = 'K354KR2011stations_revised20120501.shp'
    inputstationpath = inputpath + inputstationname

    outputpath = basepath+ 'output\\'
    outputzdfname = 'K354KR2012CORP_JOAfinal_20130118.zdf'
    outputzdfpath = outputpath + outputzdfname

##    zonefields = {'zone':'Zone',
##                  'station1':'StationID',
##                  'station1type':'Sta_Type',
##                  'rr1':'RRatio',
##                  'to1':'TimeOffset'}
   
    zonefields = {'zone':'ZONE',
                  'station1':'TS3',
                  'station1type':'TYPE',
                  'rr1':'R3',
                  'to1':'ATC3'}
    
##    zonefields = {'zone':'Zone',
##                  'station1':'StationID',
##                  'station1type':None, #'Sta_Type',
##                  'rr1':'RRatio',
##                  'to1':'TimeOffset',
##                  'w1':'Weight_1',
##                  'station2':'StationID2',
##                  'station2type':None, #'Sta_Type2',
##                  'rr2':'RRatio_2',
##                  'to2':'TimeOff_2',
##                  'w2':'Weight_2'}

    stationfields = {'station':'station'}

    writezdf(inputzoningpath,inputstationpath,outputzdfpath,zonefields,stationfields)
