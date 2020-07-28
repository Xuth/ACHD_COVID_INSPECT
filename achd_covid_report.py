import urllib.request
import re
#import xml.etree.ElementTree as ET
import logging
from collections import defaultdict
import xmltodict
import csv

import dbm.gnu as gdbm



log = logging.getLogger("main")



def listify(v):
    if isinstance(v, (list, tuple)):
        return v
    return [v]
        

class ImportFail(Exception):
    pass

class Report:
    
    def __init__(self, xml):
        self.assessmentStats = {}
        
        if xml is not None:
            try:
                self.parseXml(xml)
            except RuntimeError:
                raise
            except:
                raise ImportFail()
            
        else:
            log.warning("nothing to import in report")
            raise ImportFail()

            
    def parseXml(self, xmlString):
        xml = xmltodict.parse(xmlString)
        xml = xml['INSP_SUMMARY_COVID']  # nothing above this point so move our root
        self.encounter = xml['LIST_G_1']['G_1']['ENCOUNTER']
        self.reportDate = xml['LIST_G_1']['G_1']['SYS_DATE']
        self.demo = self.parseDemographic(xml)
        self.ratings = self.parseRatings(xml)
        self.comments = self.parseComments(xml)
        
    def parseDemographic(self, xml):
        ret = {}
        tree = xml['LIST_G_1']['G_1']

        ret['name'] = tree['CLIENT_NAME']
        ret['addr'] = tree['ST_NAME']
        ret['city'] = tree['CITY']
        ret['municipality'] = tree['MUNICIPALITY']
        ret['zip'] = tree['ZIP']
        ret['desc'] = tree['DESCRIPTION']

        return ret

    def parseRatings(self, xml):
        ret = {}
        for node in listify(xml['LIST_G_CRITICAL']['G_CRITICAL']['LIST_G_DESCRIPTION_NEW1']['G_DESCRIPTION_NEW1']):
            desc = node['CF_DESCRIPTION']
            if node['SATISFY'] == 'x':
                ret[desc] = 'S'
            elif node['VIOLATION'] == 'x':
                ret[desc] = '** U **'
            elif node['NOT_APPLY'] == 'x':
                ret[desc] = 'N/A'
            elif node['NOT_OBSERV'] == 'x':
                ret[desc] = 'N/O'
            else:
                ret[desc] = node['RATING2']
                if ret[desc] == 'Not Rated':
                    ret[desc] = 'N/R'

        return ret

    def parseComments(self, xml):
        ret = {}
        try:
            nodeList = listify(xml['LIST_G_1']['G_1']['LIST_G_VIOLATION_CD1']['G_VIOLATION_CD1'])
            for node in nodeList:
                try:
                    desc = node['LONGDESC1']
                    comment = node['CF_V_CMT']
                    ret[desc] = comment
                except:
                    pass
        except:
            pass

        try:
            nodeList = listify(xml['LIST_G_1']['G_1']['LIST_G_NC_ENCOUNTER']['G_NC_ENCOUNTER'])
            for node in nodeList:
                try:
                    desc = node['NC_LONG_DESC']
                    comment = node['NC_COMMENTS']
                    ret[desc] = comment
                except:
                    pass

        except:
            pass

        foundNew = False
        try:
            nodeList = listify(xml['LIST_G_1']['G_1']['LIST_G_CMT_VIOL_ENCOUNTER']['G_CMT_VIOL_ENCOUNTER'])
            foundNew = True
        except:
            pass
            
        try:
            nodeList = listify(xml['LIST_G_1']['G_1']['LIST_EM_ENCOUNTER']['EM_ENCOUNTER'])
            foundNew = True
        except:
            pass

        if foundNew:
            raise RuntimeError("Found new information in %s"%self.encounter)
        
        return ret

        
    @classmethod
    def csvListHeaders(cls):
        return ['encounter',
                'date',
                'name',
                'addr',
                'city',
                'municipality',
                'zip',
                'description',
                
                '25% occupancy',
                'tables 6ft',
                'closed bar',
                'staff masks',
                'table service',
                'tobacco',
                '11pm close',
                
                'comments']

    def csvList(self):
        ret = [self.encounter,
               self.reportDate,
               self.demo['name'],
               self.demo['addr'],
               self.demo['city'],
               self.demo['municipality'],
               self.demo['zip'],
               self.demo['desc'],
               self.ratings['Indoor occupancy (25%)'],
               self.ratings['Tables 6 feet apart'],
               self.ratings['Closed bar seating'],
               self.ratings['Face coverings by staff'],
               self.ratings['Table service only'],
               self.ratings['Zero tobacco usage'],
               self.ratings['Closed by 11:00 pm']]

        for k,v in self.comments.items():
            ret.append("%s: %s"%(k,v))

        return ret
        

def wget(url):
    with urllib.request.urlopen(url) as f:
        html = f.read().decode('utf-8')
    return html

def getReportsAvailable():
    html = wget('https://eapps.alleghenycounty.us/cFips/cDashBoard.aspx')

    urlre = re.compile(r'href=\"http://appsrv\.alleghenycounty\.us/reports/rwservlet\?food_rep\&amp\;report=FoodINSP/insp_summary_COVID.jsp\&amp;desformat=PDF\&amp;P_ENCOUNTER=(\d+)\"')
    matches = urlre.findall(html)

    return list(matches)

def parseReport(xml):
    return None

def getReportXML(encounter):
    url = "http://appsrv.alleghenycounty.us/reports/rwservlet?food_rep&report=FoodINSP/insp_summary_COVID.jsp&desformat=XML&P_ENCOUNTER=%s"%encounter
    dbm = gdbm.open("reportDB.gdbm", 'c')

    try:
        xmlString = dbm[encounter]
        print("found %s"%encounter)
    except:
        try:
            print("getting %s"%encounter)
            xmlString = wget(url)
            dbm[encounter] = xmlString
        except:
            return None
    dbm.close()

    return xmlString

def getReport(encounter):
    xmlString = getReportXML(encounter)
    return Report(xml=xmlString)

def main():
    reportsAvailable = getReportsAvailable()
    print(reportsAvailable)
    rptDict = {}
    for encounter in reportsAvailable:
        try:
            rpt = getReport(encounter)
            rptDict[encounter] = rpt
        except ImportFail:
            pass
        
    with open('acr_summary.csv', 'w') as f:
        csvOut = csv.writer(f)
        csvOut.writerow(["ACHD COVID restaurant reports summary"])
        csvOut.writerow([""])
        csvOut.writerow(["","","","", "", "", "", "", "S = Satisfactory", "U = Unsatisfactory", "N/A = Not Applicable", "N/O = Not Observed", "N/R = Not Rated"])
        csvOut.writerow([""])
        csvOut.writerow(Report.csvListHeaders())
        for rpt in rptDict.values():
            csvOut.writerow(rpt.csvList())


if __name__ == "__main__":
    main()
