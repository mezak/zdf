# -*- coding: utf-8 -*-
"""
Created on Fri Jul 18 15:04:22 2014

@author: mzieserl
trying github desktop

read Caris ZDF
returns geojson outputs
zones are polygon, tide stations are points
does not handle multiple stations per zone (only 1)
only puts one tide station per zone under the TIDE_AVERAGE section
assumes coordinates are NAD83 lat, lon

QC - not enforced!!!
checks that all polygons are closed
that each geometry has zoning attributes
that adjacent coordintates are the same, so there are no slivers or overlaps 
between zones
that there are no duplicate zone names or geometries

REQUIRES: geojson

"""
import json
import copy
from geojson import Point, Polygon, Feature, FeatureCollection
import shapefile as shp


# create the PRJ file
#prj = open("%s.prj" % filename, "w")
#epsg = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'
#prj.write(epsg)
#prj.close()


###############################################################################
#functions to support readzdf function

# get a section of the zdf into a list
def zdfsection(i,zdflines,sectiontype):
    
    numlinesadded = 0
    thelines = []
    
    firstline = zdflines[i].replace('\r\n', '').strip()
    i+=1 # move to next line
    if firstline == '[ZONE]':
        this_section = 'geometry'
    elif firstline == '[TIDE_ZONE]': 
        this_section = 'zoning factors'
    elif firstline == '[TIDE_STATION]':
        this_section = 'tide stations'
    elif firstline == '[TIDE_AVERAGE]':        
        this_section = 'tide average'       
    elif firstline == '[OPTIONS]':
        this_section = 'options'
    elif sectiontype:
        this_section = sectiontype 
        i-=1
    else:
        logmsg = 'Section type is missing:',firstline
        this_section = 'unknown'
        return {'lines added': 0,'current line':i,
        'readlines':[],'current section':this_section,'msg':logmsg}
    

    #stops at end of file or at a blank line, split on commas
    while i < len(zdflines) and zdflines[i].replace('\r\n', '').strip():
        thestring = zdflines[i].replace('\r\n', '').strip()
        strlist = thestring.split(',')
        for item in strlist:
            item.strip()
        thelines.append(strlist)
        numlinesadded+=1
        i+=1

    if numlinesadded==0:
        logmsg = 'Nothing read for this section: {}'.format(zdflines[i-1].replace('\r\n', '').strip())
    else:
        logmsg="Read {:.0f} lines from this section.".format(numlinesadded)
        
    #print logmsg

    return {'lines added':numlinesadded,'current line':i,
    'readlines':thelines,'current section':this_section,'msg':logmsg}
 
# read polygon geometry under ZONE into list  
def read_zone(thelines):
    azone = {}
    zonename = str(thelines[0][0])
    azone['point_number'] = int(thelines[0][1])
    thecoords=[]
    error = False
    
    for pnt in thelines[1:]:
        thecoords.append([float(pnt[1]),float(pnt[0])])   #lon,lat for geojson
    azone['coordinates'] = copy.copy(thecoords)

    logmsg = ''
    if len(thecoords)!=azone['point_number']:
        logmsg = '\r\n'+azone['name']+': given number of points ('+str(azone['point_number'])
        logmsg = logmsg+') does not equal list length: '+str(len(thecoords))+'\r\n'
        error = True

    if azone['coordinates'][0]!=azone['coordinates'][-1]:
        logmsg = logmsg + '\r\nFirst and last coordinates are not the same: \r\n'
        logmsg = logmsg+str(azone['coordinates'][0])+'   '
        logmsg = logmsg+str(azone['coordinates'][-1])+'\r\n'
        error = True
        
    return  {'zonename': zonename, 'readzone': azone, 'error' : error,'msg': logmsg}


# read in the zoning factors in TIDE_ZONE into dictionary
def read_tide_zone(thelines):
##    print thelines
    alltidezones= {}
    for oneline in thelines:
        zone_name = str(oneline[0])
        if not alltidezones.has_key(zone_name):
            alltidezones[zone_name] = {'TS1':int(oneline[1]), 
                                        #'STYPE':str(oneline[2]), # don't include this
                                        'ATC1':int(oneline[3]),
                                        'R1':float(oneline[4])}
        else:
            print 'Duplicate tide zones: {}'.format(zone_name)
            
    return alltidezones


#assumes 1 station per zone
def read_tide_station(thelines):
    allstations = []   
    for oneline in thelines:
        allstations.append({'coordinates':[float(oneline[2]),float(oneline[1])], # lon, lat for geojson
                                            'attributes':{'Station':oneline[0]}})
    return allstations


# assumes 2 stations numbers per zone
def read_tide_average(thelines):
    allaverages = []
    for oneline in thelines:
        allaverages.append([str(oneline[0]),int(oneline[1]),int(oneline[2])])
    return allaverages


def read_options(thelines):
    options={}
    options['Outage'] = thelines[0][1]
    options['Interval'] = thelines[1][1]
    
    return options



###############################################################################
#geojson functions (require geojson module)

#create geojson polygons
#geojson expects longitude first, then lat (x,y)
def create_zones(zones):
    
    featurelist = []
    i = 0
    for azonekey in sorted(zones):
        azone = zones[azonekey]
        g = Polygon(azone['coordinates'])
        a = azone['attributes']
        a['ZONE'] = str(azonekey)
        f = Feature(geometry = g, properties = a, id = i)
        i+=1
        featurelist.append(f)
    
    geozones = FeatureCollection(featurelist)
    
    return geozones

#create geojson points
def create_stations(tide_stations):
    
    featurelist = []
    i = 0
    for arec in tide_stations:
        a = arec['attributes']
        g = Point(arec['coordinates'])
        f = Feature(geometry = g, properties = a, id = i)
        i+=1
        featurelist.append(f)
    
    geostations = FeatureCollection(featurelist)   
    
    return geostations

# get boundary extents and center of geojson files
def geojson_bounds(gj):
    lat=[]
    lon=[]    
    
    for agj in gj:
        for f in agj['features']:
            if f['geometry']['type']=='Polygon':
                for c in f['geometry']['coordinates']: 
                    lon.append(c[0])
                    lat.append(c[1])
            elif f['geometry']['type']=='Point':
                lon.append(c[0])
                lat.append(c[1])
    
    bounds = {'latmax': max(lat),
              'latmin': min(lat),
              'lonmax': min(lon), #assume negative for west longitude
              'lonmin': max(lon),
              'center': [(max(lat)+min(lat))/2, (max(lon) + min(lon))/2]}
    
    return bounds

            
    
    
    
###############################################################################  
# readzdf
# read in zdf file (ZONE, TIDE_ZONE, TIDE_AVERAGE, TIDE_STATION, OPTIONS)
# create geojson polygons for zones and points for stations 
def zdf2geojson(zdfpath):
    zdf_file = 0
    try:
        zdf_file = open(zdfpath,'r')
        zone = {}
        unique_zonegeo = 0
        zone_attributes = 0
        tide_station = []
        tide_average = []
        options = {}
        valid_format = 0
        current_section = None
    
        # read in ZDF file
        #try:
        zdf_file = open(zdfpath,'r')
        zdflines = zdf_file.readlines()
        
        i = 0
        while i<len(zdflines):
            oneline = zdflines[i].replace('\r\n','').strip()
            if not oneline:
                pass 
            elif oneline == '[ZONE_DEF_VERSION_2]': #header
                valid_format = 2
                current_section = 'header'
            else:
                #read in a section of the file (ends at a blank line)
                section_return = zdfsection(i,zdflines,current_section)
                current_section = section_return['current section']
                #print section_return['msg']
                #print current_section
                
                if section_return['lines added'] > 0: #actually read something
                    
                    if current_section == 'geometry': # [ZONE]
                        zone_return = read_zone(section_return['readlines'])
                    
                        if zone_return['error']:
                            print zone_return['msg']
                    
                        if zone.has_key(zone_return['zonename']): #problem
                            msg = 'Duplicate zone defintions for '+zone_return['zonename']+'\r\n'
                            print msg
                        else:
                            zone[zone_return['zonename']] = zone_return['readzone']
                            unique_zonegeo +=1
                        
                    elif current_section == 'zoning factors': # [TIDE_ZONE]
                        tide_zone = read_tide_zone(section_return['readlines'])
                        zone_attributes = len(tide_zone)
    
                    elif current_section == 'tide stations': # [TIDE_STATION]
                        tide_station = read_tide_station(section_return['readlines'])
                        
                    elif current_section == 'tide average': # [TIDE_AVERAGE]
                        tide_average.append(read_tide_average(section_return['readlines']))
                        
                    elif current_section == 'options': # [OPTIONS]
                        options = read_options(section_return['readlines'])
                        
                    else:
                        print 'problem'
                    
                i = section_return['current line'] 
                #print i              
            i+=1
            #print i
            
        #combine zone geometry and zone attributes
        #loop through each attribute record in tide_zone list
        for attkey in tide_zone.keys():
            if zone.has_key(attkey):
                zone[attkey]['attributes'] = tide_zone[attkey]
            else:
                pass
                #error, there are attributes without geometry

        for akey in zone.keys():
            if not zone[akey].has_key('attributes'):
                print 'missing attributes for',akey
        
        # create zoning geojson
        geozones = create_zones(zone)
        #print geozones
        
        #create tide station point geojson
        geostations = create_stations(tide_station)
        #print geostations
        
        #determine bounds of geojson files
        bounds = geojson_bounds([geozones,geostations])
        
        #weird geojson fix for polygons, have to embed coordinates inside of another list
        for azone in geozones['features']:
            azone['geometry']['coordinates'] = [azone['geometry']['coordinates']]

#    except:
#        print 'ok'
    finally:
        if zdf_file:
            zdf_file.close()    
    return geozones,geostations,bounds
    
#if __name__ == '__main__':
#    zdfpath ='C:/WORK/python/git/zdf/tests/JOA Zoning 20131008b.zdf'
#    zdf2geojson(zdfpath)


###############################################################################
# create zdf from geojson (does not require geojson module)
# assumes NAD83 lat/lon spatial reference
# does not handle multiple stations per zone (only 1)
# does not handle tide average (only writes one station)
def writezdf(outputzdfpath,zones,zonecols,stations,stationcols):
    zdf=0
    try:    
        zdf = open(outputzdfpath,'w')
        
        #write header
        zdf.write('[ZONE_DEF_VERSION_2]\r\n')
        
        #write zones
        zdf.write('\r\n[ZONE]')
        for azone in zones['features']:
            c = azone['geometry']['coordinates']
            while len(c)==1: # coordinate list may be embedded inside of another list
                c = azone['geometry']['coordinates'][0]
            zdf.write('\r\n')
            zdf.write(','.join([str(azone['properties'][zonecols['zone']]),'{:.0f}'.format(len(c))+'\r\n']))
            for apair in c:
                zdf.write('{0:>.6f},{1:>.6f}\r\n'.format(apair[1],apair[0]))
        
        #write tide zones
        zdf.write('\r\n[TIDE_ZONE]\r\n')
        for azone in zones['features']:
            zprops = azone['properties']
            zdf.write(','.join([str(zprops[zonecols['zone']]),
                                str(zprops[zonecols['station']]),
                                'PRIM',
                                '{:.0f}'.format(zprops[zonecols['time']]),
                                '{:.2f}'.format(zprops[zonecols['range']])]))
            zdf.write('\r\n')
        
        #write tide stations
        zdf.write('\r\n[TIDE_STATION]\r\n')
        for astation in stations['features']:
            sprops = astation['properties']
            c = astation['geometry']['coordinates']
            zdf.write(','.join([str(sprops[stationcols['station']]),
                                '{:>.6f}'.format(c[1]),
                                '{:>.6f}'.format(c[0])]))
            zdf.write('\r\n')
        
        #write tide average (assume only 1 station per zone)
        zdf.write('\r\n[TIDE_AVERAGE]\r\n')
        for azone in zones['features']:
            zprops = azone['properties']
            zdf.write(','.join([str(zprops[zonecols['zone']]),
                                str(zprops[zonecols['station']]),
                                str(zprops[zonecols['station']])]))
            zdf.write('\r\n')
        
        zdf.write('\r\n[OPTIONS]\r\nOutage, 30\r\nInterval, 360\r\n')
    
    finally:
        if zdf:        
            zdf.close()
        return 1
    
#if __name__ == '__main__':
#    #grab sample json files
#    zf = open('C:/WORK/python/git/zdf/tests/zones.json','r')    
#    zonesgj = json.loads(zf.read())
#    sf = open('C:/WORK/python/git/zdf/tests/stations.json','r')    
#    stationsgj = json.loads(sf.read())
#    
#    outputzdfpath = 'C:/WORK/python/git/zdf/tests/testoutput.zdf'
#    #define the column or field names for each of the following items
#    zonecols={'zone':'ZONE','station':'TS1','time':'ATC1','range':'R1'}
#    stationcols={'station':'Station'}
#    writezdf(outputzdfpath,zonesgj,zonecols,stationsgj,stationcols)


###############################################################################
# write shapefiles from geojson

#utility function to create projection file
#assuming NAD83
def prjNAD83():
    
    prj = 'GEOGCS["GCS_North_American_1983", \
    DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137,298.257222101]], \
    PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]'    
    
    return prj

# write shapefile from geojson polygon
def writezoneshp(outputpath,zonesgj):
    
    w = shp.Writer(shp.POLYGON)
    
    w.field('ZONE','C','20')
    w.field('TS1','C','20')
    w.field('ATC1','N','20')
    w.field('R1','D','20')
    
    for afeature in zonesgj['features']:
        w.poly(parts=afeature['geometry']['coordinates'])
        rec=afeature['properties']
        w.record(rec['ZONE'],rec['TS1'],rec['ATC1'],rec['R1'])
    
    w.save(outputpath)
    
    #write prj file assuming NAD83
    prj = open(outputpath+'.prj','w')
    prj.write(prjNAD83())
    prj.close()
    
    return 1

#if __name__ == '__main__':
#    #grab sample json files
#    zf = open('C:/WORK/python/git/zdf/tests/zones.json','r')    
#    zonesgj = json.loads(zf.read())
#    #sf = open('C:/WORK/python/git/zdf/tests/stations.json','r')    
#    #stationsgj = json.loads(sf.read())
#    
#    outputpath = 'C:/WORK/python/git/zdf/tests/testzone'
#    #define the column or field names for each of the following items
#    writezoneshp(outputpath,zonesgj)
    

# write shapefile from geojson points
def writestationshp(outputpath,stationsgj):
    
    w = shp.Writer(shp.POINT)
    
    w.field('STATION','C','20')
    
    for afeature in stationsgj['features']:
        c = afeature['geometry']['coordinates']
        w.point(c[0],c[1])
        w.record(afeature['properties']['Station'])
    
    w.save(outputpath)
    
    #write prj file assuming NAD83
    prj = open(outputpath+'.prj','w')
    prj.write(prjNAD83())
    prj.close()
    
    return 1

#if __name__ == '__main__':
#    #grab sample json files
#    zf = open('C:/WORK/python/git/zdf/tests/stations.json','r')    
#    stationsgj = json.loads(zf.read())
#    #sf = open('C:/WORK/python/git/zdf/tests/stations.json','r')    
#    #stationsgj = json.loads(sf.read())
#    
#    outputpath = 'C:/WORK/python/git/zdf/tests/teststation'
#    #define the column or field names for each of the following items
#    writestationshp(outputpath,stationsgj)
    


###############################################################################
# read shapefile to geojson
def shp2geojson(shppath):
    # read the shapefile
    reader = shp.Reader(shppath)
    fields = reader.fields[1:]
    field_names = [field[0] for field in fields]
    buffer = []
    for sr in reader.shapeRecords():
        atr = dict(zip(field_names, sr.record))
        #print atr
        geom = sr.shape.__geo_interface__
        #print geom
        buffer.append(dict(type="Feature", geometry=geom, properties=atr))
   
    # write the GeoJSON file
    geojson = {"type": "FeatureCollection","features": buffer}

    return geojson
    
if __name__ == '__main__':
    #shapefile path
    shppath = "C:/WORK/python/git/zdf/tests/JOA Zoning 20131008b.shp"
    #zonecols={'zone':'ZONE','station':'TS1','time':'ATC1','range':'R1'}
    shp2geojson(shppath)