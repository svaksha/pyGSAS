# -*- coding: utf-8 -*-
########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################
'''
*GSASIIstrIO: structure I/O routines*
-------------------------------------

'''
import sys
import os
import os.path as ospath
import time
import math
import copy
import random
import cPickle
import numpy as np
import numpy.ma as ma
import numpy.linalg as nl
import scipy.optimize as so
import GSASIIpath
GSASIIpath.SetVersionNumber("$Revision$")
import GSASIIElem as G2el
import GSASIIgrid as G2gd
import GSASIIlattice as G2lat
import GSASIIspc as G2spc
import GSASIIobj as G2obj
import GSASIImapvars as G2mv
import GSASIImath as G2mth

sind = lambda x: np.sin(x*np.pi/180.)
cosd = lambda x: np.cos(x*np.pi/180.)
tand = lambda x: np.tan(x*np.pi/180.)
asind = lambda x: 180.*np.arcsin(x)/np.pi
acosd = lambda x: 180.*np.arccos(x)/np.pi
atan2d = lambda y,x: 180.*np.arctan2(y,x)/np.pi
    
ateln2 = 8.0*math.log(2.0)

def GetControls(GPXfile):
    ''' Returns dictionary of control items found in GSASII gpx file

    :param str GPXfile: full .gpx file name
    :return: dictionary of control items
    '''
    Controls = copy.copy(G2obj.DefaultControls)
    fl = open(GPXfile,'rb')
    while True:
        try:
            data = cPickle.load(fl)
        except EOFError:
            break
        datum = data[0]
        if datum[0] == 'Controls':
            Controls.update(datum[1])
    fl.close()
    return Controls
    
def GetConstraints(GPXfile):
    '''Read the constraints from the GPX file and interpret them

    called in :func:`ReadCheckConstraints`, :func:`GSASIIstrMain.Refine`
    and :func:`GSASIIstrMain.SeqRefine`. 
    '''
    fl = open(GPXfile,'rb')
    while True:
        try:
            data = cPickle.load(fl)
        except EOFError:
            break
        datum = data[0]
        if datum[0] == 'Constraints':
            constList = []
            for item in datum[1]:
                if item.startswith('_'): continue
                constList += datum[1][item]
            fl.close()
            constDict,fixedList,ignored = ProcessConstraints(constList)
            if ignored:
                print ignored,'Constraints were rejected. Was a constrained phase, histogram or atom deleted?'
            return constDict,fixedList
    fl.close()
    raise Exception,"No constraints in GPX file"
    
def ProcessConstraints(constList):
    """Interpret the constraints in the constList input into a dictionary, etc.
    All :class:`GSASIIobj.G2VarObj` objects are mapped to the appropriate
    phase/hist/atoms based on the object internals (random Ids). If this can't be
    done (if a phase has been deleted, etc.), the variable is ignored.
    If the constraint cannot be used due to too many dropped variables,
    it is counted as ignored.
    
    :param list constList: a list of lists where each item in the outer list
      specifies a constraint of some form, as described in the :mod:`GSASIIobj`
      :ref:`Constraint definition <Constraint_definitions_table>`.

    :returns:  a tuple of (constDict,fixedList,ignored) where:
      
      * constDict (list of dicts) contains the constraint relationships
      * fixedList (list) contains the fixed values for each type
        of constraint.
      * ignored (int) counts the number of invalid constraint items
        (should always be zero!)
    """
    constDict = []
    fixedList = []
    ignored = 0
    for item in constList:
        if item[-1] == 'h':
            # process a hold
            fixedList.append('0')
            var = str(item[0][1])
            if '?' not in var:
                constDict.append({var:0.0})
            else:
                ignored += 1
        elif item[-1] == 'f':
            # process a new variable
            fixedList.append(None)
            D = {}
            varyFlag = item[-2]
            varname = item[-3]
            for term in item[:-3]:
                var = str(term[1])
                if '?' not in var:
                    D[var] = term[0]
            if len(D) > 1:
                # add extra dict terms for input variable name and vary flag
                if varname is not None:                    
                    if varname.startswith('::'):
                        varname = varname[2:].replace(':',';')
                    else:
                        varname = varname.replace(':',';')
                    D['_name'] = '::' + varname
                D['_vary'] = varyFlag == True # force to bool
                constDict.append(D)
            else:
                ignored += 1
            #constFlag[-1] = ['Vary']
        elif item[-1] == 'c': 
            # process a contraint relationship
            D = {}
            for term in item[:-3]:
                var = str(term[1])
                if '?' not in var:
                    D[var] = term[0]
            if len(D) >= 1:
                fixedList.append(str(item[-3]))
                constDict.append(D)
            else:
                ignored += 1
        elif item[-1] == 'e':
            # process an equivalence
            firstmult = None
            eqlist = []
            for term in item[:-3]:
                if term[0] == 0: term[0] = 1.0
                var = str(term[1])
                if '?' in var: continue
                if firstmult is None:
                    firstmult = term[0]
                    firstvar = var
                else:
                    eqlist.append([var,firstmult/term[0]])
            if len(eqlist) > 0:
                G2mv.StoreEquivalence(firstvar,eqlist)
            else:
                ignored += 1
        else:
            ignored += 1
    return constDict,fixedList,ignored

def ReadCheckConstraints(GPXfile):
    '''Load constraints and related info and return any error or warning messages'''
    # init constraints
    G2mv.InitVars()    
    # get variables
    Histograms,Phases = GetUsedHistogramsAndPhases(GPXfile)
    if not Phases:
        return 'Error: No Phases!',''
    if not Histograms:
        return 'Error: no diffraction data',''
    constrDict,fixedList = GetConstraints(GPXfile) # load user constraints before internally generated ones
    rigidbodyDict = GetRigidBodies(GPXfile)
    rbIds = rigidbodyDict.get('RBIds',{'Vector':[],'Residue':[]})
    rbVary,rbDict = GetRigidBodyModels(rigidbodyDict,Print=False)
    Natoms,atomIndx,phaseVary,phaseDict,pawleyLookup,FFtables,BLtables,maxSSwave = GetPhaseData(Phases,RestraintDict=None,rbIds=rbIds,Print=False) # generates atom symmetry constraints
    hapVary,hapDict,controlDict = GetHistogramPhaseData(Phases,Histograms,Print=False)
    histVary,histDict,controlDict = GetHistogramData(Histograms,Print=False)
    varyList = rbVary+phaseVary+hapVary+histVary
    errmsg, warnmsg = G2mv.CheckConstraints(varyList,constrDict,fixedList)
    if errmsg:
        # print some diagnostic info on the constraints
        print('Error in constraints:\n'+errmsg+
              '\nRefinement not possible due to conflict in constraints, see below:\n')
        print G2mv.VarRemapShow(varyList,True)
    return errmsg, warnmsg
def GetRestraints(GPXfile):
    '''Read the restraints from the GPX file.
    Throws an exception if not found in the .GPX file
    '''
    fl = open(GPXfile,'rb')
    while True:
        try:
            data = cPickle.load(fl)
        except EOFError:
            break
        datum = data[0]
        if datum[0] == 'Restraints':
            restraintDict = datum[1]
    fl.close()
    return restraintDict
    
def GetRigidBodies(GPXfile):
    '''Read the rigid body models from the GPX file
    '''
    fl = open(GPXfile,'rb')
    while True:
        try:
            data = cPickle.load(fl)
        except EOFError:
            break
        datum = data[0]
        if datum[0] == 'Rigid bodies':
            rigidbodyDict = datum[1]
    fl.close()
    return rigidbodyDict
        
def GetFprime(controlDict,Histograms):
    'Needs a doc string'
    FFtables = controlDict['FFtables']
    if not FFtables:
        return
    histoList = Histograms.keys()
    histoList.sort()
    for histogram in histoList:
        if histogram[:4] in ['PWDR','HKLF']:
            Histogram = Histograms[histogram]
            hId = Histogram['hId']
            hfx = ':%d:'%(hId)
            if 'X' in controlDict[hfx+'histType']:
                keV = controlDict[hfx+'keV']
                for El in FFtables:
                    Orbs = G2el.GetXsectionCoeff(El.split('+')[0].split('-')[0])
                    FP,FPP,Mu = G2el.FPcalc(Orbs, keV)
                    FFtables[El][hfx+'FP'] = FP
                    FFtables[El][hfx+'FPP'] = FPP
                    
def PrintFprime(FFtables,pfx,pFile):
    print >>pFile,'\n Resonant form factors:'
    Elstr = ' Element:'
    FPstr = " f'     :"
    FPPstr = ' f"     :'
    for El in FFtables:
        Elstr += ' %8s'%(El)
        FPstr += ' %8.3f'%(FFtables[El][pfx+'FP'])
        FPPstr += ' %8.3f'%(FFtables[El][pfx+'FPP'])
    print >>pFile,Elstr
    print >>pFile,FPstr
    print >>pFile,FPPstr
            
def GetPhaseNames(GPXfile):
    ''' Returns a list of phase names found under 'Phases' in GSASII gpx file

    :param str GPXfile: full .gpx file name
    :return: list of phase names
    '''
    fl = open(GPXfile,'rb')
    PhaseNames = []
    while True:
        try:
            data = cPickle.load(fl)
        except EOFError:
            break
        datum = data[0]
        if 'Phases' == datum[0]:
            for datus in data[1:]:
                PhaseNames.append(datus[0])
    fl.close()
    return PhaseNames

def GetAllPhaseData(GPXfile,PhaseName):
    ''' Returns the entire dictionary for PhaseName from GSASII gpx file

    :param str GPXfile: full .gpx file name
    :param str PhaseName: phase name
    :return: phase dictionary
    '''        
    fl = open(GPXfile,'rb')
    General = {}
    Atoms = []
    while True:
        try:
            data = cPickle.load(fl)
        except EOFError:
            break
        datum = data[0]
        if 'Phases' == datum[0]:
            for datus in data[1:]:
                if datus[0] == PhaseName:
                    break
    fl.close()
    return datus[1]
    
def GetHistograms(GPXfile,hNames):
    """ Returns a dictionary of histograms found in GSASII gpx file

    :param str GPXfile: full .gpx file name
    :param str hNames: list of histogram names
    :return: dictionary of histograms (types = PWDR & HKLF)

    """
    fl = open(GPXfile,'rb')
    Histograms = {}
    while True:
        try:
            data = cPickle.load(fl)
        except EOFError:
            break
        datum = data[0]
        hist = datum[0]
        if hist in hNames:
            if 'PWDR' in hist[:4]:
                PWDRdata = {}
                PWDRdata.update(datum[1][0])        #weight factor
                PWDRdata['Data'] = ma.array(ma.getdata(datum[1][1]))          #masked powder data arrays/clear previous masks
                PWDRdata[data[2][0]] = data[2][1]       #Limits & excluded regions (if any)
                PWDRdata[data[3][0]] = data[3][1]       #Background
                PWDRdata[data[4][0]] = data[4][1]       #Instrument parameters
                PWDRdata[data[5][0]] = data[5][1]       #Sample parameters
                try:
                    PWDRdata[data[9][0]] = data[9][1]       #Reflection lists might be missing
                except IndexError:
                    PWDRdata['Reflection Lists'] = {}
                PWDRdata['Residuals'] = {}
    
                Histograms[hist] = PWDRdata
            elif 'HKLF' in hist[:4]:
                HKLFdata = {}
                HKLFdata.update(datum[1][0])        #weight factor
#patch
                if 'list' in str(type(datum[1][1])):
                #if isinstance(datum[1][1],list):
                    RefData = {'RefList':[],'FF':{}}
                    for ref in datum[1][1]:
                        RefData['RefList'].append(ref[:11]+[ref[13],])
                    RefData['RefList'] = np.array(RefData['RefList'])
                    datum[1][1] = RefData
#end patch
                datum[1][1]['FF'] = {}
                HKLFdata['Data'] = datum[1][1]
                HKLFdata[data[1][0]] = data[1][1]       #Instrument parameters
                HKLFdata['Reflection Lists'] = None
                HKLFdata['Residuals'] = {}
                Histograms[hist] = HKLFdata           
    fl.close()
    return Histograms
    
def GetHistogramNames(GPXfile,hType):
    """ Returns a list of histogram names found in GSASII gpx file

    :param str GPXfile: full .gpx file name
    :param str hType: list of histogram types
    :return: list of histogram names (types = PWDR & HKLF)

    """
    fl = open(GPXfile,'rb')
    HistogramNames = []
    while True:
        try:
            data = cPickle.load(fl)
        except EOFError:
            break
        datum = data[0]
        if datum[0][:4] in hType:
            HistogramNames.append(datum[0])
    fl.close()
    return HistogramNames
    
def GetUsedHistogramsAndPhases(GPXfile):
    ''' Returns all histograms that are found in any phase
    and any phase that uses a histogram. This also
    assigns numbers to used phases and histograms by the
    order they appear in the file. 

    :param str GPXfile: full .gpx file name
    :returns: (Histograms,Phases)

     * Histograms = dictionary of histograms as {name:data,...}
     * Phases = dictionary of phases that use histograms

    '''
    phaseNames = GetPhaseNames(GPXfile)
    histoList = GetHistogramNames(GPXfile,['PWDR','HKLF'])
    allHistograms = GetHistograms(GPXfile,histoList)
    phaseData = {}
    for name in phaseNames: 
        phaseData[name] =  GetAllPhaseData(GPXfile,name)
    Histograms = {}
    Phases = {}
    for phase in phaseData:
        Phase = phaseData[phase]
        if Phase['Histograms']:
            if phase not in Phases:
                pId = phaseNames.index(phase)
                Phase['pId'] = pId
                Phases[phase] = Phase
            for hist in Phase['Histograms']:
                if 'Use' not in Phase['Histograms'][hist]:      #patch
                    Phase['Histograms'][hist]['Use'] = True         
                if hist not in Histograms and Phase['Histograms'][hist]['Use']:
                    try:
                        Histograms[hist] = allHistograms[hist]
                        hId = histoList.index(hist)
                        Histograms[hist]['hId'] = hId
                    except KeyError: # would happen if a referenced histogram were
                        # renamed or deleted
                        print('For phase "'+str(phase)+
                              '" unresolved reference to histogram "'+str(hist)+'"')
    G2obj.IndexAllIds(Histograms=Histograms,Phases=Phases)
    return Histograms,Phases
    
def getBackupName(GPXfile,makeBack):
    '''
    Get the name for the backup .gpx file name
    
    :param str GPXfile: full .gpx file name
    :param bool makeBack: if True the name of a new file is returned, if
      False the name of the last file that exists is returned
    :returns: the name of a backup file
    
    '''
    GPXpath,GPXname = ospath.split(GPXfile)
    if GPXpath == '': GPXpath = '.'
    Name = ospath.splitext(GPXname)[0]
    files = os.listdir(GPXpath)
    last = 0
    for name in files:
        name = name.split('.')
        if len(name) == 3 and name[0] == Name and 'bak' in name[1]:
            if makeBack:
                last = max(last,int(name[1].strip('bak'))+1)
            else:
                last = max(last,int(name[1].strip('bak')))
    GPXback = ospath.join(GPXpath,ospath.splitext(GPXname)[0]+'.bak'+str(last)+'.gpx')
    return GPXback    
        
def GPXBackup(GPXfile,makeBack=True):
    '''
    makes a backup of the current .gpx file (?)
    
    :param str GPXfile: full .gpx file name
    :param bool makeBack: if True (default), the backup is written to
      a new file; if False, the last backup is overwritten
    :returns: the name of the backup file that was written
    '''
    import distutils.file_util as dfu
    GPXback = getBackupName(GPXfile,makeBack)
    dfu.copy_file(GPXfile,GPXback)
    return GPXback

def SetUsedHistogramsAndPhases(GPXfile,Histograms,Phases,RigidBodies,CovData,makeBack=True):
    ''' Updates gpxfile from all histograms that are found in any phase
    and any phase that used a histogram. Also updates rigid body definitions.


    :param str GPXfile: full .gpx file name
    :param dict Histograms: dictionary of histograms as {name:data,...}
    :param dict Phases: dictionary of phases that use histograms
    :param dict RigidBodies: dictionary of rigid bodies
    :param dict CovData: dictionary of refined variables, varyList, & covariance matrix
    :param bool makeBack: True if new backup of .gpx file is to be made; else use the last one made

    '''
                        
    import distutils.file_util as dfu
    GPXback = GPXBackup(GPXfile,makeBack)
    print 'Read from file:',GPXback
    print 'Save to file  :',GPXfile
    infile = open(GPXback,'rb')
    outfile = open(GPXfile,'wb')
    while True:
        try:
            data = cPickle.load(infile)
        except EOFError:
            break
        datum = data[0]
#        print 'read: ',datum[0]
        if datum[0] == 'Phases':
            for iphase in range(len(data)):
                if data[iphase][0] in Phases:
                    phaseName = data[iphase][0]
                    data[iphase][1].update(Phases[phaseName])
        elif datum[0] == 'Covariance':
            data[0][1] = CovData
        elif datum[0] == 'Rigid bodies':
            data[0][1] = RigidBodies
        try:
            histogram = Histograms[datum[0]]
#            print 'found ',datum[0]
            data[0][1][1] = histogram['Data']
            data[0][1][0].update(histogram['Residuals'])
            for datus in data[1:]:
#                print '    read: ',datus[0]
                if datus[0] in ['Background','Instrument Parameters','Sample Parameters','Reflection Lists']:
                    datus[1] = histogram[datus[0]]
        except KeyError:
            pass
        try:                        
            cPickle.dump(data,outfile,1)
        except AttributeError:
            print 'ERROR - bad data in least squares result'
            infile.close()
            outfile.close()
            dfu.copy_file(GPXback,GPXfile)
            print 'GPX file save failed - old version retained'
            return
            
    print 'GPX file save successful'
    
def SetSeqResult(GPXfile,Histograms,SeqResult):
    '''
    Needs doc string
    
    :param str GPXfile: full .gpx file name
    '''
    GPXback = GPXBackup(GPXfile)
    print 'Read from file:',GPXback
    print 'Save to file  :',GPXfile
    infile = open(GPXback,'rb')
    outfile = open(GPXfile,'wb')
    while True:
        try:
            data = cPickle.load(infile)
        except EOFError:
            break
        datum = data[0]
        if datum[0] == 'Sequential results':
            data[0][1] = SeqResult
        # reset the Copy Next flag, since it should not be needed twice in a row
        if datum[0] == 'Controls':
            data[0][1]['Copy2Next'] = False
        try:
            histogram = Histograms[datum[0]]
            data[0][1][1] = list(histogram['Data'])
            for datus in data[1:]:
                if datus[0] in ['Background','Instrument Parameters','Sample Parameters','Reflection Lists']:
                    datus[1] = histogram[datus[0]]
        except KeyError:
            pass
                                
        cPickle.dump(data,outfile,1)
    infile.close()
    outfile.close()
    print 'GPX file save successful'
                        
def ShowBanner(pFile=None):
    'Print authorship, copyright and citation notice'
    print >>pFile,80*'*'
    print >>pFile,'   General Structure Analysis System-II Crystal Structure Refinement'
    print >>pFile,'              by Robert B. Von Dreele & Brian H. Toby'
    print >>pFile,'                Argonne National Laboratory(C), 2010'
    print >>pFile,' This product includes software developed by the UChicago Argonne, LLC,' 
    print >>pFile,'            as Operator of Argonne National Laboratory.'
    print >>pFile,'                          Please cite:'
    print >>pFile,'   B.H. Toby & R.B. Von Dreele, J. Appl. Cryst. 46, 544-549 (2013)'

    print >>pFile,80*'*','\n'

def ShowControls(Controls,pFile=None,SeqRef=False):
    'Print controls information'
    print >>pFile,' Least squares controls:'
    print >>pFile,' Refinement type: ',Controls['deriv type']
    if 'Hessian' in Controls['deriv type']:
        print >>pFile,' Maximum number of cycles:',Controls['max cyc']
    else:
        print >>pFile,' Minimum delta-M/M for convergence: ','%.2g'%(Controls['min dM/M'])
    print >>pFile,' Initial shift factor: ','%.3f'%(Controls['shift factor'])
    if SeqRef:
        print >>pFile,' Sequential refinement controls:'
        print >>pFile,' Copy of histogram results to next: ',Controls['Copy2Next']
        print >>pFile,' Process histograms in reverse order: ',Controls['Reverse Seq']
    
def GetPawleyConstr(SGLaue,PawleyRef,im,pawleyVary):
    'needs a doc string'
#    if SGLaue in ['-1','2/m','mmm']:
#        return                      #no Pawley symmetry required constraints
    eqvDict = {}
    for i,varyI in enumerate(pawleyVary):
        eqvDict[varyI] = []
        refI = int(varyI.split(':')[-1])
        ih,ik,il = PawleyRef[refI][:3]
        dspI = PawleyRef[refI][4+im]
        for varyJ in pawleyVary[i+1:]:
            refJ = int(varyJ.split(':')[-1])
            jh,jk,jl = PawleyRef[refJ][:3]
            dspJ = PawleyRef[refJ][4+im]
            if SGLaue in ['4/m','4/mmm']:
                isum = ih**2+ik**2
                jsum = jh**2+jk**2
                if abs(il) == abs(jl) and isum == jsum:
                    eqvDict[varyI].append(varyJ) 
            elif SGLaue in ['3R','3mR']:
                isum = ih**2+ik**2+il**2
                jsum = jh**2+jk**2+jl**2
                isum2 = ih*ik+ih*il+ik*il
                jsum2 = jh*jk+jh*jl+jk*jl
                if isum == jsum and isum2 == jsum2:
                    eqvDict[varyI].append(varyJ) 
            elif SGLaue in ['3','3m1','31m','6/m','6/mmm']:
                isum = ih**2+ik**2+ih*ik
                jsum = jh**2+jk**2+jh*jk
                if abs(il) == abs(jl) and isum == jsum:
                    eqvDict[varyI].append(varyJ) 
            elif SGLaue in ['m3','m3m']:
                isum = ih**2+ik**2+il**2
                jsum = jh**2+jk**2+jl**2
                if isum == jsum:
                    eqvDict[varyI].append(varyJ)
            elif abs(dspI-dspJ)/dspI < 1.e-4:
                eqvDict[varyI].append(varyJ) 
    for item in pawleyVary:
        if eqvDict[item]:
            for item2 in pawleyVary:
                if item2 in eqvDict[item]:
                    eqvDict[item2] = []
            G2mv.StoreEquivalence(item,eqvDict[item])
                    
def cellVary(pfx,SGData): 
    'needs a doc string'
    if SGData['SGLaue'] in ['-1',]:
        return [pfx+'A0',pfx+'A1',pfx+'A2',pfx+'A3',pfx+'A4',pfx+'A5']
    elif SGData['SGLaue'] in ['2/m',]:
        if SGData['SGUniq'] == 'a':
            return [pfx+'A0',pfx+'A1',pfx+'A2',pfx+'A5']
        elif SGData['SGUniq'] == 'b':
            return [pfx+'A0',pfx+'A1',pfx+'A2',pfx+'A4']
        else:
            return [pfx+'A0',pfx+'A1',pfx+'A2',pfx+'A3']
    elif SGData['SGLaue'] in ['mmm',]:
        return [pfx+'A0',pfx+'A1',pfx+'A2']
    elif SGData['SGLaue'] in ['4/m','4/mmm']:
        G2mv.StoreEquivalence(pfx+'A0',(pfx+'A1',))
        return [pfx+'A0',pfx+'A1',pfx+'A2']
    elif SGData['SGLaue'] in ['6/m','6/mmm','3m1', '31m', '3']:
        G2mv.StoreEquivalence(pfx+'A0',(pfx+'A1',pfx+'A3',))
        return [pfx+'A0',pfx+'A1',pfx+'A2',pfx+'A3']
    elif SGData['SGLaue'] in ['3R', '3mR']:
        G2mv.StoreEquivalence(pfx+'A0',(pfx+'A1',pfx+'A2',))
        G2mv.StoreEquivalence(pfx+'A3',(pfx+'A4',pfx+'A5',))
        return [pfx+'A0',pfx+'A1',pfx+'A2',pfx+'A3',pfx+'A4',pfx+'A5']                       
    elif SGData['SGLaue'] in ['m3m','m3']:
        G2mv.StoreEquivalence(pfx+'A0',(pfx+'A1',pfx+'A2',))
        return [pfx+'A0',pfx+'A1',pfx+'A2']
        
def modVary(pfx,SSGData):
    vary = []
    for i,item in enumerate(SSGData['modSymb']):
        if item in ['a','b','g']:
            vary.append(pfx+'mV%d'%(i))
    return vary
        
################################################################################
##### Rigid Body Models and not General.get('doPawley')
################################################################################
        
def GetRigidBodyModels(rigidbodyDict,Print=True,pFile=None):
    'needs a doc string'
    
    def PrintResRBModel(RBModel):
        atNames = RBModel['atNames']
        rbRef = RBModel['rbRef']
        rbSeq = RBModel['rbSeq']
        print >>pFile,'Residue RB name: ',RBModel['RBname'],' no.atoms: ',len(RBModel['rbTypes']), \
            'No. times used: ',RBModel['useCount']
        print >>pFile,'    At name       x          y          z'
        for name,xyz in zip(atNames,RBModel['rbXYZ']):
            print >>pFile,'  %8s %10.4f %10.4f %10.4f'%(name,xyz[0],xyz[1],xyz[2])
        print >>pFile,'Orientation defined by:',atNames[rbRef[0]],' -> ',atNames[rbRef[1]], \
            ' & ',atNames[rbRef[0]],' -> ',atNames[rbRef[2]]
        if rbSeq:
            for i,rbseq in enumerate(rbSeq):
                print >>pFile,'Torsion sequence ',i,' Bond: '+atNames[rbseq[0]],' - ', \
                    atNames[rbseq[1]],' riding: ',[atNames[i] for i in rbseq[3]]
        
    def PrintVecRBModel(RBModel):
        rbRef = RBModel['rbRef']
        atTypes = RBModel['rbTypes']
        print >>pFile,'Vector RB name: ',RBModel['RBname'],' no.atoms: ',len(RBModel['rbTypes']), \
            'No. times used: ',RBModel['useCount']
        for i in range(len(RBModel['VectMag'])):
            print >>pFile,'Vector no.: ',i,' Magnitude: ', \
                '%8.4f'%(RBModel['VectMag'][i]),' Refine? ',RBModel['VectRef'][i]
            print >>pFile,'  No. Type     vx         vy         vz'
            for j,[name,xyz] in enumerate(zip(atTypes,RBModel['rbVect'][i])):
                print >>pFile,'  %d   %2s %10.4f %10.4f %10.4f'%(j,name,xyz[0],xyz[1],xyz[2])
        print >>pFile,'  No. Type      x          y          z'
        for i,[name,xyz] in enumerate(zip(atTypes,RBModel['rbXYZ'])):
            print >>pFile,'  %d   %2s %10.4f %10.4f %10.4f'%(i,name,xyz[0],xyz[1],xyz[2])
        print >>pFile,'Orientation defined by: atom ',rbRef[0],' -> atom ',rbRef[1], \
            ' & atom ',rbRef[0],' -> atom ',rbRef[2]
    rbVary = []
    rbDict = {}
    rbIds = rigidbodyDict.get('RBIds',{'Vector':[],'Residue':[]})
    if len(rbIds['Vector']):
        for irb,item in enumerate(rbIds['Vector']):
            if rigidbodyDict['Vector'][item]['useCount']:
                RBmags = rigidbodyDict['Vector'][item]['VectMag']
                RBrefs = rigidbodyDict['Vector'][item]['VectRef']
                for i,[mag,ref] in enumerate(zip(RBmags,RBrefs)):
                    pid = '::RBV;'+str(i)+':'+str(irb)
                    rbDict[pid] = mag
                    if ref:
                        rbVary.append(pid)
                if Print:
                    print >>pFile,'\nVector rigid body model:'
                    PrintVecRBModel(rigidbodyDict['Vector'][item])
    if len(rbIds['Residue']):
        for item in rbIds['Residue']:
            if rigidbodyDict['Residue'][item]['useCount']:
                if Print:
                    print >>pFile,'\nResidue rigid body model:'
                    PrintResRBModel(rigidbodyDict['Residue'][item])
    return rbVary,rbDict
    
def SetRigidBodyModels(parmDict,sigDict,rigidbodyDict,pFile=None):
    'needs a doc string'
    
    def PrintRBVectandSig(VectRB,VectSig):
        print >>pFile,'\n Rigid body vector magnitudes for '+VectRB['RBname']+':'
        namstr = '  names :'
        valstr = '  values:'
        sigstr = '  esds  :'
        for i,[val,sig] in enumerate(zip(VectRB['VectMag'],VectSig)):
            namstr += '%12s'%('Vect '+str(i))
            valstr += '%12.4f'%(val)
            if sig:
                sigstr += '%12.4f'%(sig)
            else:
                sigstr += 12*' '
        print >>pFile,namstr
        print >>pFile,valstr
        print >>pFile,sigstr        
        
    RBIds = rigidbodyDict.get('RBIds',{'Vector':[],'Residue':[]})  #these are lists of rbIds
    if not RBIds['Vector']:
        return
    for irb,item in enumerate(RBIds['Vector']):
        if rigidbodyDict['Vector'][item]['useCount']:
            VectSig = []
            RBmags = rigidbodyDict['Vector'][item]['VectMag']
            for i,mag in enumerate(RBmags):
                name = '::RBV;'+str(i)+':'+str(irb)
                mag = parmDict[name]
                if name in sigDict:
                    VectSig.append(sigDict[name])
            PrintRBVectandSig(rigidbodyDict['Vector'][item],VectSig)    
        
################################################################################
##### Phase data
################################################################################        
                    
def GetPhaseData(PhaseData,RestraintDict={},rbIds={},Print=True,pFile=None,seqRef=False):
    'needs a doc string'
            
    def PrintFFtable(FFtable):
        print >>pFile,'\n X-ray scattering factors:'
        print >>pFile,'   Symbol     fa                                      fb                                      fc'
        print >>pFile,99*'-'
        for Ename in FFtable:
            ffdata = FFtable[Ename]
            fa = ffdata['fa']
            fb = ffdata['fb']
            print >>pFile,' %8s %9.5f %9.5f %9.5f %9.5f %9.5f %9.5f %9.5f %9.5f %9.5f' %  \
                (Ename.ljust(8),fa[0],fa[1],fa[2],fa[3],fb[0],fb[1],fb[2],fb[3],ffdata['fc'])
                
    def PrintBLtable(BLtable):
        print >>pFile,'\n Neutron scattering factors:'
        print >>pFile,'   Symbol   isotope       mass       b       resonant terms'
        print >>pFile,99*'-'
        for Ename in BLtable:
            bldata = BLtable[Ename]
            isotope = bldata[0]
            mass = bldata[1]['Mass']
            if 'SL' in bldata[1]:
                blen = bldata[1]['SL'][0]
                bres = []
            else:
                blen = 0
                bres = bldata[1]['BW-LS']
            line = ' %8s%11s %10.3f %8.3f'%(Ename.ljust(8),isotope.center(11),mass,blen)
            for item in bres:
                line += '%10.5g'%(item)
            print >>pFile,line
            
    def PrintRBObjects(resRBData,vecRBData):
        
        def PrintRBThermals():
            tlstr = ['11','22','33','12','13','23']
            sstr = ['12','13','21','23','31','32','AA','BB']
            TLS = RB['ThermalMotion'][1]
            TLSvar = RB['ThermalMotion'][2]
            if 'T' in RB['ThermalMotion'][0]:
                print >>pFile,'TLS data'
                text = ''
                for i in range(6):
                    text += 'T'+tlstr[i]+' %8.4f %s '%(TLS[i],str(TLSvar[i])[0])
                print >>pFile,text
                if 'L' in RB['ThermalMotion'][0]: 
                    text = ''
                    for i in range(6,12):
                        text += 'L'+tlstr[i-6]+' %8.2f %s '%(TLS[i],str(TLSvar[i])[0])
                    print >>pFile,text
                if 'S' in RB['ThermalMotion'][0]:
                    text = ''
                    for i in range(12,20):
                        text += 'S'+sstr[i-12]+' %8.3f %s '%(TLS[i],str(TLSvar[i])[0])
                    print >>pFile,text
            if 'U' in RB['ThermalMotion'][0]:
                print >>pFile,'Uiso data'
                text = 'Uiso'+' %10.3f %s'%(TLS[0],str(TLSvar[0])[0])           
            
        if len(resRBData):
            for RB in resRBData:
                Oxyz = RB['Orig'][0]
                Qrijk = RB['Orient'][0]
                Angle = 2.0*acosd(Qrijk[0])
                print >>pFile,'\nRBObject ',RB['RBname'],' at ',      \
                    '%10.4f %10.4f %10.4f'%(Oxyz[0],Oxyz[1],Oxyz[2]),' Refine?',RB['Orig'][1]
                print >>pFile,'Orientation angle,vector:',      \
                    '%10.3f %10.4f %10.4f %10.4f'%(Angle,Qrijk[1],Qrijk[2],Qrijk[3]),' Refine? ',RB['Orient'][1]
                Torsions = RB['Torsions']
                if len(Torsions):
                    text = 'Torsions: '
                    for torsion in Torsions:
                        text += '%10.4f Refine? %s'%(torsion[0],torsion[1])
                    print >>pFile,text
                PrintRBThermals()
        if len(vecRBData):
            for RB in vecRBData:
                Oxyz = RB['Orig'][0]
                Qrijk = RB['Orient'][0]
                Angle = 2.0*acosd(Qrijk[0])
                print >>pFile,'\nRBObject ',RB['RBname'],' at ',      \
                    '%10.4f %10.4f %10.4f'%(Oxyz[0],Oxyz[1],Oxyz[2]),' Refine?',RB['Orig'][1]           
                print >>pFile,'Orientation angle,vector:',      \
                    '%10.3f %10.4f %10.4f %10.4f'%(Angle,Qrijk[1],Qrijk[2],Qrijk[3]),' Refine? ',RB['Orient'][1]
                PrintRBThermals()
                
    def PrintAtoms(General,Atoms):
        cx,ct,cs,cia = General['AtomPtrs']
        print >>pFile,'\n Atoms:'
        line = '   name    type  refine?   x         y         z    '+ \
            '  frac site sym  mult I/A   Uiso     U11     U22     U33     U12     U13     U23'
        if General['Type'] == 'macromolecular':
            line = ' res no residue chain'+line
        print >>pFile,line
        if General['Type'] in ['nuclear','modulated','magnetic']:
            print >>pFile,135*'-'
            for i,at in enumerate(Atoms):
                line = '%7s'%(at[ct-1])+'%7s'%(at[ct])+'%7s'%(at[ct+1])+'%10.5f'%(at[cx])+'%10.5f'%(at[cx+1])+ \
                    '%10.5f'%(at[cx+2])+'%8.3f'%(at[cx+3])+'%7s'%(at[cs])+'%5d'%(at[cs+1])+'%5s'%(at[cia])
                if at[cia] == 'I':
                    line += '%8.5f'%(at[cia+1])+48*' '
                else:
                    line += 8*' '
                    for j in range(6):
                        line += '%8.5f'%(at[cia+2+j])
                print >>pFile,line
        elif General['Type'] == 'macromolecular':
            print >>pFile,135*'-'            
            for i,at in enumerate(Atoms):
                line = '%7s'%(at[0])+'%7s'%(at[1])+'%7s'%(at[2])+'%7s'%(at[ct-1])+'%7s'%(at[ct])+'%7s'%(at[ct+1])+'%10.5f'%(at[cx])+'%10.5f'%(at[cx+1])+ \
                    '%10.5f'%(at[cx+2])+'%8.3f'%(at[cx+3])+'%7s'%(at[cs])+'%5d'%(at[cs+1])+'%5s'%(at[cia])
                if at[cia] == 'I':
                    line += '%8.4f'%(at[cia+1])+48*' '
                else:
                    line += 8*' '
                    for j in range(6):
                        line += '%8.4f'%(at[cia+2+j])
                print >>pFile,line
                
    def PrintWaves(General,Atoms):
        cx,ct,cs,cia = General['AtomPtrs']
        print >>pFile,'\n Modulation waves'
        names = {'Sfrac':['Fsin','Fcos','Fzero','Fwid'],'Spos':['Xsin','Ysin','Zsin','Xcos','Ycos','Zcos','Tzero','Xslope','Yslope','Zslope'],
            'Sadp':['U11sin','U22sin','U33sin','U12sin','U13sin','U23sin','U11cos','U22cos',
            'U33cos','U12cos','U13cos','U23cos'],'Smag':['MXsin','MYsin','MZsin','MXcos','MYcos','MZcos']}
        print >>pFile,135*'-'
        for i,at in enumerate(Atoms):
            AtomSS = at[-1]['SS1']
            for Stype in ['Sfrac','Spos','Sadp','Smag']:
                Waves = AtomSS[Stype]
                if len(Waves):
                    print >>pFile,' atom: %s, site sym: %s, type: %s wave type: %s:'    \
                        %(at[ct-1],at[cs],Stype,AtomSS['waveType'])
                    line = ''
                    for item in names[Stype]:
                        line += '%8s '%(item)
                    print >>pFile,line
                for wave in Waves:                    
                    line = ''
                    for item in wave[0]:
                        line += '%8.4f '%(item)
                    line += ' Refine? '+str(wave[1])
                    print >>pFile,line
        
    def PrintTexture(textureData):
        topstr = '\n Spherical harmonics texture: Order:' + \
            str(textureData['Order'])
        if textureData['Order']:
            print >>pFile,topstr+' Refine? '+str(textureData['SH Coeff'][0])
        else:
            print >>pFile,topstr
            return
        names = ['omega','chi','phi']
        line = '\n'
        for name in names:
            line += ' SH '+name+':'+'%12.4f'%(textureData['Sample '+name][1])+' Refine? '+str(textureData['Sample '+name][0])
        print >>pFile,line
        print >>pFile,'\n Texture coefficients:'
        SHcoeff = textureData['SH Coeff'][1]
        SHkeys = SHcoeff.keys()
        nCoeff = len(SHcoeff)
        nBlock = nCoeff/10+1
        iBeg = 0
        iFin = min(iBeg+10,nCoeff)
        for block in range(nBlock):
            ptlbls = ' names :'
            ptstr =  ' values:'
            for item in SHkeys[iBeg:iFin]:
                ptlbls += '%12s'%(item)
                ptstr += '%12.4f'%(SHcoeff[item]) 
            print >>pFile,ptlbls
            print >>pFile,ptstr
            iBeg += 10
            iFin = min(iBeg+10,nCoeff)
        
    def MakeRBParms(rbKey,phaseVary,phaseDict):
        rbid = str(rbids.index(RB['RBId']))
        pfxRB = pfx+'RB'+rbKey+'P'
        pstr = ['x','y','z']
        ostr = ['a','i','j','k']
        for i in range(3):
            name = pfxRB+pstr[i]+':'+str(iRB)+':'+rbid
            phaseDict[name] = RB['Orig'][0][i]
            if RB['Orig'][1]:
                phaseVary += [name,]
        pfxRB = pfx+'RB'+rbKey+'O'
        for i in range(4):
            name = pfxRB+ostr[i]+':'+str(iRB)+':'+rbid
            phaseDict[name] = RB['Orient'][0][i]
            if RB['Orient'][1] == 'AV' and i:
                phaseVary += [name,]
            elif RB['Orient'][1] == 'A' and not i:
                phaseVary += [name,]
            
    def MakeRBThermals(rbKey,phaseVary,phaseDict):
        rbid = str(rbids.index(RB['RBId']))
        tlstr = ['11','22','33','12','13','23']
        sstr = ['12','13','21','23','31','32','AA','BB']
        if 'T' in RB['ThermalMotion'][0]:
            pfxRB = pfx+'RB'+rbKey+'T'
            for i in range(6):
                name = pfxRB+tlstr[i]+':'+str(iRB)+':'+rbid
                phaseDict[name] = RB['ThermalMotion'][1][i]
                if RB['ThermalMotion'][2][i]:
                    phaseVary += [name,]
        if 'L' in RB['ThermalMotion'][0]:
            pfxRB = pfx+'RB'+rbKey+'L'
            for i in range(6):
                name = pfxRB+tlstr[i]+':'+str(iRB)+':'+rbid
                phaseDict[name] = RB['ThermalMotion'][1][i+6]
                if RB['ThermalMotion'][2][i+6]:
                    phaseVary += [name,]
        if 'S' in RB['ThermalMotion'][0]:
            pfxRB = pfx+'RB'+rbKey+'S'
            for i in range(8):
                name = pfxRB+sstr[i]+':'+str(iRB)+':'+rbid
                phaseDict[name] = RB['ThermalMotion'][1][i+12]
                if RB['ThermalMotion'][2][i+12]:
                    phaseVary += [name,]
        if 'U' in RB['ThermalMotion'][0]:
            name = pfx+'RB'+rbKey+'U:'+str(iRB)+':'+rbid
            phaseDict[name] = RB['ThermalMotion'][1][0]
            if RB['ThermalMotion'][2][0]:
                phaseVary += [name,]
                
    def MakeRBTorsions(rbKey,phaseVary,phaseDict):
        rbid = str(rbids.index(RB['RBId']))
        pfxRB = pfx+'RB'+rbKey+'Tr;'
        for i,torsion in enumerate(RB['Torsions']):
            name = pfxRB+str(i)+':'+str(iRB)+':'+rbid
            phaseDict[name] = torsion[0]
            if torsion[1]:
                phaseVary += [name,]
                    
    if Print:
        print  >>pFile,'\n Phases:'
    phaseVary = []
    phaseDict = {}
    phaseConstr = {}
    pawleyLookup = {}
    FFtables = {}                   #scattering factors - xrays
    BLtables = {}                   # neutrons
    Natoms = {}
    AtMults = {}
    AtIA = {}
    maxSSwave = {}
    shModels = ['cylindrical','none','shear - 2/m','rolling - mmm']
    SamSym = dict(zip(shModels,['0','-1','2/m','mmm']))
    atomIndx = {}
    for name in PhaseData:
        General = PhaseData[name]['General']
        pId = PhaseData[name]['pId']
        pfx = str(pId)+'::'
        FFtable = G2el.GetFFtable(General['AtomTypes'])
        BLtable = G2el.GetBLtable(General)
        FFtables.update(FFtable)
        BLtables.update(BLtable)
        Atoms = PhaseData[name]['Atoms']
        if Atoms and not General.get('doPawley'):
            cx,ct,cs,cia = General['AtomPtrs']
            AtLookup = G2mth.FillAtomLookUp(Atoms,cia+8)
        PawleyRef = PhaseData[name].get('Pawley ref',[])
        SGData = General['SGData']
        SGtext,SGtable = G2spc.SGPrint(SGData)
        cell = General['Cell']
        A = G2lat.cell2A(cell[1:7])
        phaseDict.update({pfx+'A0':A[0],pfx+'A1':A[1],pfx+'A2':A[2],
            pfx+'A3':A[3],pfx+'A4':A[4],pfx+'A5':A[5],pfx+'Vol':G2lat.calc_V(A)})
        if cell[0]:
            phaseVary += cellVary(pfx,SGData)       #also fills in symmetry required constraints 
        SSGtext = []    #no superstructure
        im = 0
        if General['Type'] in ['modulated','magnetic']:
            im = 1      #refl offset
            Vec,vRef,maxH = General['SuperVec']
            phaseDict.update({pfx+'mV0':Vec[0],pfx+'mV1':Vec[1],pfx+'mV2':Vec[2]})
            SSGData = General['SSGData']
            SSGtext,SSGtable = G2spc.SSGPrint(SGData,SSGData)
            if vRef:
                phaseVary += modVary(pfx,SSGData)        
        resRBData = PhaseData[name]['RBModels'].get('Residue',[])
        if resRBData:
            rbids = rbIds['Residue']    #NB: used in the MakeRB routines
            for iRB,RB in enumerate(resRBData):
                MakeRBParms('R',phaseVary,phaseDict)
                MakeRBThermals('R',phaseVary,phaseDict)
                MakeRBTorsions('R',phaseVary,phaseDict)
        
        vecRBData = PhaseData[name]['RBModels'].get('Vector',[])
        if vecRBData:
            rbids = rbIds['Vector']    #NB: used in the MakeRB routines
            for iRB,RB in enumerate(vecRBData):
                MakeRBParms('V',phaseVary,phaseDict)
                MakeRBThermals('V',phaseVary,phaseDict)
                    
        Natoms[pfx] = 0
        maxSSwave[pfx] = {'Sfrac':0,'Spos':0,'Sadp':0,'Smag':0}
        if Atoms and not General.get('doPawley'):
            cx,ct,cs,cia = General['AtomPtrs']
            Natoms[pfx] = len(Atoms)
            for i,at in enumerate(Atoms):
                atomIndx[at[cia+8]] = [pfx,i]      #lookup table for restraints
                phaseDict.update({pfx+'Atype:'+str(i):at[ct],pfx+'Afrac:'+str(i):at[cx+3],pfx+'Amul:'+str(i):at[cs+1],
                    pfx+'Ax:'+str(i):at[cx],pfx+'Ay:'+str(i):at[cx+1],pfx+'Az:'+str(i):at[cx+2],
                    pfx+'dAx:'+str(i):0.,pfx+'dAy:'+str(i):0.,pfx+'dAz:'+str(i):0.,         #refined shifts for x,y,z
                    pfx+'AI/A:'+str(i):at[cia],})
                if at[cia] == 'I':
                    phaseDict[pfx+'AUiso:'+str(i)] = at[cia+1]
                else:
                    phaseDict.update({pfx+'AU11:'+str(i):at[cia+2],pfx+'AU22:'+str(i):at[cia+3],pfx+'AU33:'+str(i):at[cia+4],
                        pfx+'AU12:'+str(i):at[cia+5],pfx+'AU13:'+str(i):at[cia+6],pfx+'AU23:'+str(i):at[cia+7]})
                if 'F' in at[ct+1]:
                    phaseVary.append(pfx+'Afrac:'+str(i))
                if 'X' in at[ct+1]:
                    try:    #patch for sytsym name changes
                        xId,xCoef = G2spc.GetCSxinel(at[cs])
                    except KeyError:
                        Sytsym = G2spc.SytSym(at[cx:cx+3],SGData)[0]
                        at[cs] = Sytsym
                        xId,xCoef = G2spc.GetCSxinel(at[cs])
                    xId,xCoef = G2spc.GetCSxinel(at[cs])
                    names = [pfx+'dAx:'+str(i),pfx+'dAy:'+str(i),pfx+'dAz:'+str(i)]
                    equivs = [[],[],[]]
                    for j in range(3):
                        if xId[j] > 0:                               
                            phaseVary.append(names[j])
                            equivs[xId[j]-1].append([names[j],xCoef[j]])
                    for equiv in equivs:
                        if len(equiv) > 1:
                            name = equiv[0][0]
                            coef = equiv[0][1]
                            for eqv in equiv[1:]:
                                eqv[1] /= coef
                                G2mv.StoreEquivalence(name,(eqv,))
                if 'U' in at[ct+1]:
                    if at[cia] == 'I':
                        phaseVary.append(pfx+'AUiso:'+str(i))
                    else:
                        try:    #patch for sytsym name changes
                            uId,uCoef = G2spc.GetCSuinel(at[cs])[:2]
                        except KeyError:
                            Sytsym = G2spc.SytSym(at[cx:cx+3],SGData)[0]
                            at[cs] = Sytsym
                            uId,uCoef = G2spc.GetCSuinel(at[cs])[:2]
                        uId,uCoef = G2spc.GetCSuinel(at[cs])[:2]
                        names = [pfx+'AU11:'+str(i),pfx+'AU22:'+str(i),pfx+'AU33:'+str(i),
                            pfx+'AU12:'+str(i),pfx+'AU13:'+str(i),pfx+'AU23:'+str(i)]
                        equivs = [[],[],[],[],[],[]]
                        for j in range(6):
                            if uId[j] > 0:                               
                                phaseVary.append(names[j])
                                equivs[uId[j]-1].append([names[j],uCoef[j]])
                        for equiv in equivs:
                            if len(equiv) > 1:
                                name = equiv[0][0]
                                coef = equiv[0][1]
                                for eqv in equiv[1:]:
                                    eqv[1] /= coef
                                G2mv.StoreEquivalence(name,equiv[1:])
                if General['Type'] in ['modulated','magnetic']:
                    AtomSS = at[-1]['SS1']
                    waveType = AtomSS['waveType']
                    phaseDict[pfx+'waveType:'+str(i)] = waveType    
                    for Stype in ['Sfrac','Spos','Sadp','Smag']:
                        Waves = AtomSS[Stype]
                        uId,uCoef = CSI[Stype]
                        for iw,wave in enumerate(Waves):
                            if not iw:
                                CSI = G2spc.GetSSfxuinel(waveType,at[cx:cx+3],SGData,SSGData)
                            else:
                                CSI = G2spc.GetSSfxuinel('Fourier',at[cx:cx+3],SGData,SSGData)
                            stiw = str(i)+':'+str(iw)
                            if Stype == 'Spos':
                                if waveType in ['ZigZag','Sawtooth'] and not iw:
                                    names = [pfx+'Tzero:'+stiw,pfx+'Xslope:'+stiw,pfx+'Yslope:'+stiw,pfx+'Zslope:'+stiw]
                                    equivs = [[], [],[],[]]
                                else:
                                    names = [pfx+'Xsin:'+stiw,pfx+'Ysin:'+stiw,pfx+'Zsin:'+stiw,
                                        pfx+'Xcos:'+stiw,pfx+'Ycos:'+stiw,pfx+'Zcos:'+stiw]
                                    equivs = [[],[],[], [],[],[]]
                            elif Stype == 'Sadp':
                                names = [pfx+'U11sin:'+stiw,pfx+'U22sin:'+stiw,pfx+'U33sin:'+stiw,
                                    pfx+'U12sin:'+stiw,pfx+'U13sin:'+stiw,pfx+'U23sin:'+stiw,
                                    pfx+'U11cos:'+stiw,pfx+'U22cos:'+stiw,pfx+'U33cos:'+stiw,
                                    pfx+'U12cos:'+stiw,pfx+'U13cos:'+stiw,pfx+'U23cos:'+stiw]
                                equivs = [[],[],[],[],[],[], [],[],[],[],[],[]]
                            elif Stype == 'Sfrac':
                                equivs = [[],[]]
                                if 'Crenel' in waveType and not iw:
                                    names = [pfx+'Fzero:'+stiw,pfx+'Fwid:'+stiw]
                                else:
                                    names = [pfx+'Fsin:'+stiw,pfx+'Fcos:'+stiw]
                            elif Stype == 'Smag':
                                equivs = [[],[],[], [],[],[]]
                                names = [pfx+'MXsin:'+stiw,pfx+'MYsin:'+stiw,pfx+'MZsin:'+stiw,
                                    pfx+'MXcos:'+stiw,pfx+'MYcos:'+stiw,pfx+'MZcos:'+stiw]
                            phaseDict.update(dict(zip(names,wave[0])))
                            if wave[1]:
                                for j in range(len(equivs)):
                                    if uId[j] > 0:                               
                                        phaseVary.append(names[j])
                                        equivs[uId[j]-1].append([names[j],uCoef[j]])
                                for equiv in equivs:
                                    if len(equiv) > 1:
                                        name = equiv[0][0]
                                        coef = equiv[0][1]
                                        for eqv in equiv[1:]:
                                            eqv[1] /= coef
                                        G2mv.StoreEquivalence(name,equiv[1:])
                            maxSSwave[pfx][Stype] = max(maxSSwave[pfx][Stype],iw+1)
            textureData = General['SH Texture']
            if textureData['Order'] and not seqRef:
                phaseDict[pfx+'SHorder'] = textureData['Order']
                phaseDict[pfx+'SHmodel'] = SamSym[textureData['Model']]
                for item in ['omega','chi','phi']:
                    phaseDict[pfx+'SH '+item] = textureData['Sample '+item][1]
                    if textureData['Sample '+item][0]:
                        phaseVary.append(pfx+'SH '+item)
                for item in textureData['SH Coeff'][1]:
                    phaseDict[pfx+item] = textureData['SH Coeff'][1][item]
                    if textureData['SH Coeff'][0]:
                        phaseVary.append(pfx+item)
                
            if Print:
                print >>pFile,'\n Phase name: ',General['Name']
                print >>pFile,135*'-'
                PrintFFtable(FFtable)
                PrintBLtable(BLtable)
                print >>pFile,''
                if len(SSGtext):    #if superstructure
                    for line in SSGtext: print >>pFile,line
                    if len(SSGtable):
                        for item in SSGtable:
                            line = ' %s '%(item)
                            print >>pFile,line   
                    else:
                        print >>pFile,' ( 1)    %s'%(SSGtable[0])
                else:
                    for line in SGtext: print >>pFile,line
                    if len(SGtable):
                        for item in SGtable:
                            line = ' %s '%(item)
                            print >>pFile,line   
                    else:
                        print >>pFile,' ( 1)    %s'%(SGtable[0])
                PrintRBObjects(resRBData,vecRBData)
                PrintAtoms(General,Atoms)
                if General['Type'] in ['modulated','magnetic']:
                    PrintWaves(General,Atoms)
                print >>pFile,'\n Unit cell: a = %.5f'%(cell[1]),' b = %.5f'%(cell[2]),' c = %.5f'%(cell[3]), \
                    ' alpha = %.3f'%(cell[4]),' beta = %.3f'%(cell[5]),' gamma = %.3f'%(cell[6]), \
                    ' volume = %.3f'%(cell[7]),' Refine?',cell[0]
                if len(SSGtext):    #if superstructure
                    print >>pFile,'\n Modulation vector: mV0 = %.4f'%(Vec[0]),' mV1 = %.4f'%(Vec[1]),   \
                        ' mV2 = %.4f'%(Vec[2]),' max mod. index = %d'%(maxH),' Refine?',vRef
                if not seqRef:
                    PrintTexture(textureData)
                if name in RestraintDict:
                    PrintRestraints(cell[1:7],SGData,General['AtomPtrs'],Atoms,AtLookup,
                        textureData,RestraintDict[name],pFile)
                    
        elif PawleyRef:
            if Print:
                print >>pFile,'\n Phase name: ',General['Name']
                print >>pFile,135*'-'
                print >>pFile,''
                if len(SSGtext):    #if superstructure
                    for line in SSGtext: print >>pFile,line
                    if len(SSGtable):
                        for item in SSGtable:
                            line = ' %s '%(item)
                            print >>pFile,line   
                    else:
                        print >>pFile,' ( 1)    %s'%(SSGtable[0])
                else:
                    for line in SGtext: print >>pFile,line
                    if len(SGtable):
                        for item in SGtable:
                            line = ' %s '%(item)
                            print >>pFile,line   
                    else:
                        print >>pFile,' ( 1)    %s'%(SGtable[0])
                print >>pFile,'\n Unit cell: a = %.5f'%(cell[1]),' b = %.5f'%(cell[2]),' c = %.5f'%(cell[3]), \
                    ' alpha = %.3f'%(cell[4]),' beta = %.3f'%(cell[5]),' gamma = %.3f'%(cell[6]), \
                    ' volume = %.3f'%(cell[7]),' Refine?',cell[0]
                if len(SSGtext):    #if superstructure
                    print >>pFile,'\n Modulation vector: mV0 = %.4f'%(Vec[0]),' mV1 = %.4f'%(Vec[1]),   \
                        ' mV2 = %.4f'%(Vec[2]),' max mod. index = %d'%(maxH),' Refine?',vRef
            pawleyVary = []
            for i,refl in enumerate(PawleyRef):
                phaseDict[pfx+'PWLref:'+str(i)] = refl[6+im]
                if im:
                    pawleyLookup[pfx+'%d,%d,%d,%d'%(refl[0],refl[1],refl[2],refl[3])] = i
                else:
                    pawleyLookup[pfx+'%d,%d,%d'%(refl[0],refl[1],refl[2])] = i
                if refl[5+im]:
                    pawleyVary.append(pfx+'PWLref:'+str(i))
            GetPawleyConstr(SGData['SGLaue'],PawleyRef,im,pawleyVary)      #does G2mv.StoreEquivalence
            phaseVary += pawleyVary
                
    return Natoms,atomIndx,phaseVary,phaseDict,pawleyLookup,FFtables,BLtables,maxSSwave
    
def cellFill(pfx,SGData,parmDict,sigDict): 
    '''Returns the filled-out reciprocal cell (A) terms and their uncertainties
    from the parameter and sig dictionaries.

    :param str pfx: parameter prefix ("n::", where n is a phase number)
    :param dict SGdata: a symmetry object
    :param dict parmDict: a dictionary of parameters
    :param dict sigDict:  a dictionary of uncertainties on parameters

    :returns: A,sigA where each is a list of six terms with the A terms 
    '''
    if SGData['SGLaue'] in ['-1',]:
        A = [parmDict[pfx+'A0'],parmDict[pfx+'A1'],parmDict[pfx+'A2'],
            parmDict[pfx+'A3'],parmDict[pfx+'A4'],parmDict[pfx+'A5']]
    elif SGData['SGLaue'] in ['2/m',]:
        if SGData['SGUniq'] == 'a':
            A = [parmDict[pfx+'A0'],parmDict[pfx+'A1'],parmDict[pfx+'A2'],
                0,0,parmDict[pfx+'A5']]
        elif SGData['SGUniq'] == 'b':
            A = [parmDict[pfx+'A0'],parmDict[pfx+'A1'],parmDict[pfx+'A2'],
                0,parmDict[pfx+'A4'],0]
        else:
            A = [parmDict[pfx+'A0'],parmDict[pfx+'A1'],parmDict[pfx+'A2'],
                parmDict[pfx+'A3'],0,0]
    elif SGData['SGLaue'] in ['mmm',]:
        A = [parmDict[pfx+'A0'],parmDict[pfx+'A1'],parmDict[pfx+'A2'],0,0,0]
    elif SGData['SGLaue'] in ['4/m','4/mmm']:
        A = [parmDict[pfx+'A0'],parmDict[pfx+'A0'],parmDict[pfx+'A2'],0,0,0]
    elif SGData['SGLaue'] in ['6/m','6/mmm','3m1', '31m', '3']:
        A = [parmDict[pfx+'A0'],parmDict[pfx+'A0'],parmDict[pfx+'A2'],
            parmDict[pfx+'A0'],0,0]
    elif SGData['SGLaue'] in ['3R', '3mR']:
        A = [parmDict[pfx+'A0'],parmDict[pfx+'A0'],parmDict[pfx+'A0'],
            parmDict[pfx+'A3'],parmDict[pfx+'A3'],parmDict[pfx+'A3']]
    elif SGData['SGLaue'] in ['m3m','m3']:
        A = [parmDict[pfx+'A0'],parmDict[pfx+'A0'],parmDict[pfx+'A0'],0,0,0]

    try:
        if SGData['SGLaue'] in ['-1',]:
            sigA = [sigDict[pfx+'A0'],sigDict[pfx+'A1'],sigDict[pfx+'A2'],
                sigDict[pfx+'A3'],sigDict[pfx+'A4'],sigDict[pfx+'A5']]
        elif SGData['SGLaue'] in ['2/m',]:
            if SGData['SGUniq'] == 'a':
                sigA = [sigDict[pfx+'A0'],sigDict[pfx+'A1'],sigDict[pfx+'A2'],
                    0,0,sigDict[pfx+'A5']]
            elif SGData['SGUniq'] == 'b':
                sigA = [sigDict[pfx+'A0'],sigDict[pfx+'A1'],sigDict[pfx+'A2'],
                    0,sigDict[pfx+'A4'],0]
            else:
                sigA = [sigDict[pfx+'A0'],sigDict[pfx+'A1'],sigDict[pfx+'A2'],
                    sigDict[pfx+'A3'],0,0]
        elif SGData['SGLaue'] in ['mmm',]:
            sigA = [sigDict[pfx+'A0'],sigDict[pfx+'A1'],sigDict[pfx+'A2'],0,0,0]
        elif SGData['SGLaue'] in ['4/m','4/mmm']:
            sigA = [sigDict[pfx+'A0'],0,sigDict[pfx+'A2'],0,0,0]
        elif SGData['SGLaue'] in ['6/m','6/mmm','3m1', '31m', '3']:
            sigA = [sigDict[pfx+'A0'],0,sigDict[pfx+'A2'],0,0,0]
        elif SGData['SGLaue'] in ['3R', '3mR']:
            sigA = [sigDict[pfx+'A0'],0,0,sigDict[pfx+'A3'],0,0]
        elif SGData['SGLaue'] in ['m3m','m3']:
            sigA = [sigDict[pfx+'A0'],0,0,0,0,0]
    except KeyError:
        sigA = [0,0,0,0,0,0]
    return A,sigA
        
def PrintRestraints(cell,SGData,AtPtrs,Atoms,AtLookup,textureData,phaseRest,pFile):
    'needs a doc string'
    if phaseRest:
        Amat = G2lat.cell2AB(cell)[0]
        cx,ct,cs = AtPtrs[:3]
        names = [['Bond','Bonds'],['Angle','Angles'],['Plane','Planes'],
            ['Chiral','Volumes'],['Torsion','Torsions'],['Rama','Ramas'],
            ['ChemComp','Sites'],['Texture','HKLs']]
        for name,rest in names:
            itemRest = phaseRest[name]
            if itemRest[rest] and itemRest['Use']:
                print >>pFile,'\n  %s %10.3f Use: %s'%(name+' restraint weight factor',itemRest['wtFactor'],str(itemRest['Use']))
                if name in ['Bond','Angle','Plane','Chiral']:
                    print >>pFile,'     calc       obs      sig   delt/sig  atoms(symOp): '
                    for indx,ops,obs,esd in itemRest[rest]:
                        try:
                            AtNames = G2mth.GetAtomItemsById(Atoms,AtLookup,indx,ct-1)
                            AtName = ''
                            for i,Aname in enumerate(AtNames):
                                AtName += Aname
                                if ops[i] == '1':
                                    AtName += '-'
                                else:
                                    AtName += '+('+ops[i]+')-'
                            XYZ = np.array(G2mth.GetAtomItemsById(Atoms,AtLookup,indx,cx,3))
                            XYZ = G2mth.getSyXYZ(XYZ,ops,SGData)
                            if name == 'Bond':
                                calc = G2mth.getRestDist(XYZ,Amat)
                            elif name == 'Angle':
                                calc = G2mth.getRestAngle(XYZ,Amat)
                            elif name == 'Plane':
                                calc = G2mth.getRestPlane(XYZ,Amat)
                            elif name == 'Chiral':
                                calc = G2mth.getRestChiral(XYZ,Amat)
                            print >>pFile,' %9.3f %9.3f %8.3f %8.3f   %s'%(calc,obs,esd,(obs-calc)/esd,AtName[:-1])
                        except KeyError:
                            del itemRest[rest]
                elif name in ['Torsion','Rama']:
                    print >>pFile,'  atoms(symOp)  calc  obs  sig  delt/sig  torsions: '
                    coeffDict = itemRest['Coeff']
                    for indx,ops,cofName,esd in itemRest[rest]:
                        AtNames = G2mth.GetAtomItemsById(Atoms,AtLookup,indx,ct-1)
                        AtName = ''
                        for i,Aname in enumerate(AtNames):
                            AtName += Aname+'+('+ops[i]+')-'
                        XYZ = np.array(G2mth.GetAtomItemsById(Atoms,AtLookup,indx,cx,3))
                        XYZ = G2mth.getSyXYZ(XYZ,ops,SGData)
                        if name == 'Torsion':
                            tor = G2mth.getRestTorsion(XYZ,Amat)
                            restr,calc = G2mth.calcTorsionEnergy(tor,coeffDict[cofName])
                            print >>pFile,' %8.3f %8.3f %.3f %8.3f %8.3f %s'%(calc,obs,esd,(obs-calc)/esd,tor,AtName[:-1])
                        else:
                            phi,psi = G2mth.getRestRama(XYZ,Amat)
                            restr,calc = G2mth.calcRamaEnergy(phi,psi,coeffDict[cofName])                               
                            print >>pFile,' %8.3f %8.3f %8.3f %8.3f %8.3f %8.3f %s'%(calc,obs,esd,(obs-calc)/esd,phi,psi,AtName[:-1])
                elif name == 'ChemComp':
                    print >>pFile,'     atoms   mul*frac  factor     prod'
                    for indx,factors,obs,esd in itemRest[rest]:
                        try:
                            atoms = G2mth.GetAtomItemsById(Atoms,AtLookup,indx,ct-1)
                            mul = np.array(G2mth.GetAtomItemsById(Atoms,AtLookup,indx,cs+1))
                            frac = np.array(G2mth.GetAtomItemsById(Atoms,AtLookup,indx,cs-1))
                            mulfrac = mul*frac
                            calcs = mul*frac*factors
                            for iatm,[atom,mf,fr,clc] in enumerate(zip(atoms,mulfrac,factors,calcs)):
                                print >>pFile,' %10s %8.3f %8.3f %8.3f'%(atom,mf,fr,clc)
                            print >>pFile,' Sum:                   calc: %8.3f obs: %8.3f esd: %8.3f'%(np.sum(calcs),obs,esd)
                        except KeyError:
                            del itemRest[rest]
                elif name == 'Texture' and textureData['Order']:
                    Start = False
                    SHCoef = textureData['SH Coeff'][1]
                    shModels = ['cylindrical','none','shear - 2/m','rolling - mmm']
                    SamSym = dict(zip(shModels,['0','-1','2/m','mmm']))
                    print '    HKL  grid  neg esd  sum neg  num neg use unit?  unit esd  '
                    for hkl,grid,esd1,ifesd2,esd2 in itemRest[rest]:
                        PH = np.array(hkl)
                        phi,beta = G2lat.CrsAng(np.array(hkl),cell,SGData)
                        ODFln = G2lat.Flnh(Start,SHCoef,phi,beta,SGData)
                        R,P,Z = G2mth.getRestPolefig(ODFln,SamSym[textureData['Model']],grid)
                        Z = ma.masked_greater(Z,0.0)
                        num = ma.count(Z)
                        sum = 0
                        if num:
                            sum = np.sum(Z)
                        print '   %d %d %d  %d %8.3f %8.3f %8d   %s    %8.3f'%(hkl[0],hkl[1],hkl[2],grid,esd1,sum,num,str(ifesd2),esd2)
        
def getCellEsd(pfx,SGData,A,covData):
    'needs a doc string'
    dpr = 180./np.pi
    rVsq = G2lat.calc_rVsq(A)
    G,g = G2lat.A2Gmat(A)       #get recip. & real metric tensors
    cell = np.array(G2lat.Gmat2cell(g))   #real cell
    cellst = np.array(G2lat.Gmat2cell(G)) #recip. cell
    scos = cosd(cellst[3:6])
    ssin = sind(cellst[3:6])
    scot = scos/ssin
    rcos = cosd(cell[3:6])
    rsin = sind(cell[3:6])
    rcot = rcos/rsin
    RMnames = [pfx+'A0',pfx+'A1',pfx+'A2',pfx+'A3',pfx+'A4',pfx+'A5']
    varyList = covData['varyList']
    covMatrix = covData['covMatrix']
    vcov = G2mth.getVCov(RMnames,varyList,covMatrix)
    Ax = np.array(A)
    Ax[3:] /= 2.
    drVdA = np.array([Ax[1]*Ax[2]-Ax[5]**2,Ax[0]*Ax[2]-Ax[4]**2,Ax[0]*Ax[1]-Ax[3]**2,
        Ax[4]*Ax[5]-Ax[2]*Ax[3],Ax[3]*Ax[5]-Ax[1]*Ax[4],Ax[3]*Ax[4]-Ax[0]*Ax[5]])
    srcvlsq = np.inner(drVdA,np.inner(vcov,drVdA.T))
    Vol = 1/np.sqrt(rVsq)
    sigVol = Vol**3*np.sqrt(srcvlsq)/2.
    R123 = Ax[0]*Ax[1]*Ax[2]
    dsasdg = np.zeros((3,6))
    dadg = np.zeros((6,6))
    for i0 in range(3):         #0  1   2
        i1 = (i0+1)%3           #1  2   0
        i2 = (i1+1)%3           #2  0   1
        i3 = 5-i2               #3  5   4
        i4 = 5-i1               #4  3   5
        i5 = 5-i0               #5  4   3
        dsasdg[i0][i1] = 0.5*scot[i0]*scos[i0]/Ax[i1]
        dsasdg[i0][i2] = 0.5*scot[i0]*scos[i0]/Ax[i2]
        dsasdg[i0][i5] = -scot[i0]/np.sqrt(Ax[i1]*Ax[i2])
        denmsq = Ax[i0]*(R123-Ax[i1]*Ax[i4]**2-Ax[i2]*Ax[i3]**2+(Ax[i4]*Ax[i3])**2)
        denom = np.sqrt(denmsq)
        dadg[i5][i0] = -Ax[i5]/denom-rcos[i0]/denmsq*(R123-0.5*Ax[i1]*Ax[i4]**2-0.5*Ax[i2]*Ax[i3]**2)
        dadg[i5][i1] = -0.5*rcos[i0]/denmsq*(Ax[i0]**2*Ax[i2]-Ax[i0]*Ax[i4]**2)
        dadg[i5][i2] = -0.5*rcos[i0]/denmsq*(Ax[i0]**2*Ax[i1]-Ax[i0]*Ax[i3]**2)
        dadg[i5][i3] = Ax[i4]/denom+rcos[i0]/denmsq*(Ax[i0]*Ax[i2]*Ax[i3]-Ax[i3]*Ax[i4]**2)
        dadg[i5][i4] = Ax[i3]/denom+rcos[i0]/denmsq*(Ax[i0]*Ax[i1]*Ax[i4]-Ax[i3]**2*Ax[i4])
        dadg[i5][i5] = -Ax[i0]/denom
    for i0 in range(3):
        i1 = (i0+1)%3
        i2 = (i1+1)%3
        i3 = 5-i2
        for ij in range(6):
            dadg[i0][ij] = cell[i0]*(rcot[i2]*dadg[i3][ij]/rsin[i2]-dsasdg[i1][ij]/ssin[i1])
            if ij == i0:
                dadg[i0][ij] = dadg[i0][ij]-0.5*cell[i0]/Ax[i0]
            dadg[i3][ij] = -dadg[i3][ij]*rsin[2-i0]*dpr
    sigMat = np.inner(dadg,np.inner(vcov,dadg.T))
    var = np.diag(sigMat)
    CS = np.where(var>0.,np.sqrt(var),0.)
    return [CS[0],CS[1],CS[2],CS[5],CS[4],CS[3],sigVol]
    
def SetPhaseData(parmDict,sigDict,Phases,RBIds,covData,RestraintDict=None,pFile=None):
    'needs a doc string'
    
    def PrintAtomsAndSig(General,Atoms,atomsSig):
        print >>pFile,'\n Atoms:'
        line = '   name      x         y         z      frac   Uiso     U11     U22     U33     U12     U13     U23'
        if General['Type'] == 'magnetic':
            line += '   Mx     My     Mz'
        elif General['Type'] == 'macromolecular':
            line = ' res no residue chain '+line
        cx,ct,cs,cia = General['AtomPtrs']
        print >>pFile,line
        print >>pFile,135*'-'
        fmt = {0:'%7s',ct:'%7s',cx:'%10.5f',cx+1:'%10.5f',cx+2:'%10.5f',cx+3:'%8.3f',cia+1:'%8.5f',
            cia+2:'%8.5f',cia+3:'%8.5f',cia+4:'%8.5f',cia+5:'%8.5f',cia+6:'%8.5f',cia+7:'%8.5f'}
        noFXsig = {cx:[10*' ','%10s'],cx+1:[10*' ','%10s'],cx+2:[10*' ','%10s'],cx+3:[8*' ','%8s']}
        for atyp in General['AtomTypes']:       #zero composition
            General['NoAtoms'][atyp] = 0.
        for i,at in enumerate(Atoms):
            General['NoAtoms'][at[ct]] += at[cx+3]*float(at[cx+5])     #new composition
            if General['Type'] == 'macromolecular':
                name = ' %s %s %s %s:'%(at[0],at[1],at[2],at[3])
                valstr = ' values:          '
                sigstr = ' sig   :          '
            else:
                name = fmt[0]%(at[ct-1])+fmt[1]%(at[ct])+':'
                valstr = ' values:'
                sigstr = ' sig   :'
            for ind in range(cx,cx+4):
                sigind = str(i)+':'+str(ind)
                valstr += fmt[ind]%(at[ind])                    
                if sigind in atomsSig:
                    sigstr += fmt[ind]%(atomsSig[sigind])
                else:
                    sigstr += noFXsig[ind][1]%(noFXsig[ind][0])
            if at[cia] == 'I':
                valstr += fmt[cia+1]%(at[cia+1])
                if '%d:%d'%(i,cia+1) in atomsSig:
                    sigstr += fmt[cia+1]%(atomsSig['%d:%d'%(i,cia+1)])
                else:
                    sigstr += 8*' '
            else:
                valstr += 8*' '
                sigstr += 8*' '
                for ind in range(cia+2,cia+8):
                    sigind = str(i)+':'+str(ind)
                    valstr += fmt[ind]%(at[ind])
                    if sigind in atomsSig:                        
                        sigstr += fmt[ind]%(atomsSig[sigind])
                    else:
                        sigstr += 8*' '
            print >>pFile,name
            print >>pFile,valstr
            print >>pFile,sigstr
            
    def PrintWavesAndSig(General,Atoms,wavesSig):
        cx,ct,cs,cia = General['AtomPtrs']
        print >>pFile,'\n Modulation waves'
        names = {'Sfrac':['Fsin','Fcos','Fzero','Fwid'],'Spos':['Xsin','Ysin','Zsin','Xcos','Ycos','Zcos','Tzero','Xslope','Yslope','Zslope'],
            'Sadp':['U11sin','U22sin','U33sin','U12sin','U13sin','U23sin','U11cos','U22cos',
            'U33cos','U12cos','U13cos','U23cos'],'Smag':['MXsin','MYsin','MZsin','MXcos','MYcos','MZcos']}
        print >>pFile,135*'-'
        for i,at in enumerate(Atoms):
            AtomSS = at[-1]['SS1']
            waveType = AtomSS['waveType']
            for Stype in ['Sfrac','Spos','Sadp','Smag']:
                Waves = AtomSS[Stype]
                if len(Waves):
                    print >>pFile,' atom: %s, site sym: %s, type: %s wave type: %s:'    \
                        %(at[ct-1],at[cs],Stype,waveType)
                    line = ''
                    for iw,wave in enumerate(Waves):
                        stiw = ':'+str(i)+':'+str(iw)
                        namstr = '  names :'
                        valstr = '  values:'
                        sigstr = '  esds  :'
                        if Stype == 'Spos':
                            nt = 6
                            ot = 0
                            if waveType in ['Sawtooth','ZigZag'] and not iw:
                                nt = 4
                                ot = 6
                            for j in range(nt):
                                name = names['Spos'][j+ot]
                                namstr += '%12s'%(name)
                                valstr += '%12.4f'%(wave[0][j])
                                if name+stiw in wavesSig:
                                    sigstr += '%12.4f'%(wavesSig[name+stiw])
                                else:
                                    sigstr += 12*' '
                        elif Stype == 'Sfrac':
                            ot = 0
                            if 'Crenel' in waveType and not iw:
                                ot = 2
                            for j in range(2):
                                name = names['Sfrac'][j+ot]
                                namstr += '%12s'%(names['Sfrac'][j+ot])
                                valstr += '%12.4f'%(wave[0][j])
                                if name+stiw in wavesSig:
                                    sigstr += '%12.4f'%(wavesSig[name+stiw])
                                else:
                                    sigstr += 12*' '
                        elif Stype == 'Sadp':
                            for j in range(12):
                                name = names['Sadp'][j]
                                namstr += '%10s'%(names['Sadp'][j])
                                valstr += '%10.6f'%(wave[0][j])
                                if name+stiw in wavesSig:
                                    sigstr += '%10.6f'%(wavesSig[name+stiw])
                                else:
                                    sigstr += 10*' '
                        elif Stype == 'Smag':
                            for j in range(6):
                                name = names['Smag'][j]
                                namstr += '%12s'%(names['Smag'][j])
                                valstr += '%12.4f'%(wave[0][j])
                                if name+stiw in wavesSig:
                                    sigstr += '%12.4f'%(wavesSig[name+stiw])
                                else:
                                    sigstr += 12*' '
                                
                    print >>pFile,namstr
                    print >>pFile,valstr
                    print >>pFile,sigstr
        
                
    def PrintRBObjPOAndSig(rbfx,rbsx):
        namstr = '  names :'
        valstr = '  values:'
        sigstr = '  esds  :'
        for i,px in enumerate(['Px:','Py:','Pz:']):
            name = pfx+rbfx+px+rbsx
            namstr += '%12s'%('Pos '+px[1])
            valstr += '%12.5f'%(parmDict[name])
            if name in sigDict:
                sigstr += '%12.5f'%(sigDict[name])
            else:
                sigstr += 12*' '
        for i,po in enumerate(['Oa:','Oi:','Oj:','Ok:']):
            name = pfx+rbfx+po+rbsx
            namstr += '%12s'%('Ori '+po[1])
            valstr += '%12.5f'%(parmDict[name])
            if name in sigDict:
                sigstr += '%12.5f'%(sigDict[name])
            else:
                sigstr += 12*' '
        print >>pFile,namstr
        print >>pFile,valstr
        print >>pFile,sigstr
        
    def PrintRBObjTLSAndSig(rbfx,rbsx,TLS):
        namstr = '  names :'
        valstr = '  values:'
        sigstr = '  esds  :'
        if 'N' not in TLS:
            print >>pFile,' Thermal motion:'
        if 'T' in TLS:
            for i,pt in enumerate(['T11:','T22:','T33:','T12:','T13:','T23:']):
                name = pfx+rbfx+pt+rbsx
                namstr += '%12s'%(pt[:3])
                valstr += '%12.5f'%(parmDict[name])
                if name in sigDict:
                    sigstr += '%12.5f'%(sigDict[name])
                else:
                    sigstr += 12*' '
            print >>pFile,namstr
            print >>pFile,valstr
            print >>pFile,sigstr
        if 'L' in TLS:
            namstr = '  names :'
            valstr = '  values:'
            sigstr = '  esds  :'
            for i,pt in enumerate(['L11:','L22:','L33:','L12:','L13:','L23:']):
                name = pfx+rbfx+pt+rbsx
                namstr += '%12s'%(pt[:3])
                valstr += '%12.3f'%(parmDict[name])
                if name in sigDict:
                    sigstr += '%12.3f'%(sigDict[name])
                else:
                    sigstr += 12*' '
            print >>pFile,namstr
            print >>pFile,valstr
            print >>pFile,sigstr
        if 'S' in TLS:
            namstr = '  names :'
            valstr = '  values:'
            sigstr = '  esds  :'
            for i,pt in enumerate(['S12:','S13:','S21:','S23:','S31:','S32:','SAA:','SBB:']):
                name = pfx+rbfx+pt+rbsx
                namstr += '%12s'%(pt[:3])
                valstr += '%12.4f'%(parmDict[name])
                if name in sigDict:
                    sigstr += '%12.4f'%(sigDict[name])
                else:
                    sigstr += 12*' '
            print >>pFile,namstr
            print >>pFile,valstr
            print >>pFile,sigstr
        if 'U' in TLS:
            name = pfx+rbfx+'U:'+rbsx
            namstr = '  names :'+'%12s'%('Uiso')
            valstr = '  values:'+'%12.5f'%(parmDict[name])
            if name in sigDict:
                sigstr = '  esds  :'+'%12.5f'%(sigDict[name])
            else:
                sigstr = '  esds  :'+12*' '
            print >>pFile,namstr
            print >>pFile,valstr
            print >>pFile,sigstr
        
    def PrintRBObjTorAndSig(rbsx):
        namstr = '  names :'
        valstr = '  values:'
        sigstr = '  esds  :'
        nTors = len(RBObj['Torsions'])
        if nTors:
            print >>pFile,' Torsions:'
            for it in range(nTors):
                name = pfx+'RBRTr;'+str(it)+':'+rbsx
                namstr += '%12s'%('Tor'+str(it))
                valstr += '%12.4f'%(parmDict[name])
                if name in sigDict:
                    sigstr += '%12.4f'%(sigDict[name])
            print >>pFile,namstr
            print >>pFile,valstr
            print >>pFile,sigstr
                
    def PrintSHtextureAndSig(textureData,SHtextureSig):
        print >>pFile,'\n Spherical harmonics texture: Order:' + str(textureData['Order'])
        names = ['omega','chi','phi']
        namstr = '  names :'
        ptstr =  '  values:'
        sigstr = '  esds  :'
        for name in names:
            namstr += '%12s'%(name)
            ptstr += '%12.3f'%(textureData['Sample '+name][1])
            if 'Sample '+name in SHtextureSig:
                sigstr += '%12.3f'%(SHtextureSig['Sample '+name])
            else:
                sigstr += 12*' '
        print >>pFile,namstr
        print >>pFile,ptstr
        print >>pFile,sigstr
        print >>pFile,'\n Texture coefficients:'
        SHcoeff = textureData['SH Coeff'][1]
        SHkeys = SHcoeff.keys()
        nCoeff = len(SHcoeff)
        nBlock = nCoeff/10+1
        iBeg = 0
        iFin = min(iBeg+10,nCoeff)
        for block in range(nBlock):
            namstr = '  names :'
            ptstr =  '  values:'
            sigstr = '  esds  :'
            for name in SHkeys[iBeg:iFin]:
                namstr += '%12s'%(name)
                ptstr += '%12.3f'%(SHcoeff[name])
                if name in SHtextureSig:
                    sigstr += '%12.3f'%(SHtextureSig[name])
                else:
                    sigstr += 12*' '
            print >>pFile,namstr
            print >>pFile,ptstr
            print >>pFile,sigstr
            iBeg += 10
            iFin = min(iBeg+10,nCoeff)
            
    print >>pFile,'\n Phases:'
    for phase in Phases:
        print >>pFile,' Result for phase: ',phase
        Phase = Phases[phase]
        General = Phase['General']
        SGData = General['SGData']
        Atoms = Phase['Atoms']
        if Atoms and not General.get('doPawley'):
            cx,ct,cs,cia = General['AtomPtrs']
            AtLookup = G2mth.FillAtomLookUp(Atoms,cia+8)
        cell = General['Cell']
        pId = Phase['pId']
        pfx = str(pId)+'::'
        if cell[0]:
            A,sigA = cellFill(pfx,SGData,parmDict,sigDict)
            cellSig = getCellEsd(pfx,SGData,A,covData)  #includes sigVol
            print >>pFile,' Reciprocal metric tensor: '
            ptfmt = "%15.9f"
            names = ['A11','A22','A33','A12','A13','A23']
            namstr = '  names :'
            ptstr =  '  values:'
            sigstr = '  esds  :'
            for name,a,siga in zip(names,A,sigA):
                namstr += '%15s'%(name)
                ptstr += ptfmt%(a)
                if siga:
                    sigstr += ptfmt%(siga)
                else:
                    sigstr += 15*' '
            print >>pFile,namstr
            print >>pFile,ptstr
            print >>pFile,sigstr
            cell[1:7] = G2lat.A2cell(A)
            cell[7] = G2lat.calc_V(A)
            print >>pFile,' New unit cell:'
            ptfmt = ["%12.6f","%12.6f","%12.6f","%12.4f","%12.4f","%12.4f","%12.3f"]
            names = ['a','b','c','alpha','beta','gamma','Volume']
            namstr = '  names :'
            ptstr =  '  values:'
            sigstr = '  esds  :'
            for name,fmt,a,siga in zip(names,ptfmt,cell[1:8],cellSig):
                namstr += '%12s'%(name)
                ptstr += fmt%(a)
                if siga:
                    sigstr += fmt%(siga)
                else:
                    sigstr += 12*' '
            print >>pFile,namstr
            print >>pFile,ptstr
            print >>pFile,sigstr
        ik = 6  #for Pawley stuff below
        if General['Type'] in ['modulated','magnetic']:
            ik = 7
            Vec,vRef,maxH = General['SuperVec']
            if vRef:
                print >>pFile,' New modulation vector:'
                namstr = '  names :'
                ptstr =  '  values:'
                sigstr = '  esds  :'
                for var in ['mV0','mV1','mV2']:
                    namstr += '%12s'%(pfx+var)
                    ptstr += '%12.6f'%(parmDict[pfx+var])
                    if pfx+var in sigDict:
                        sigstr += '%12.6f'%(sigDict[pfx+var])
                    else:
                        sigstr += 12*' '
                print >>pFile,namstr
                print >>pFile,ptstr
                print >>pFile,sigstr
            
        General['Mass'] = 0.
        if Phase['General'].get('doPawley'):
            pawleyRef = Phase['Pawley ref']
            for i,refl in enumerate(pawleyRef):
                key = pfx+'PWLref:'+str(i)
                refl[ik] = parmDict[key]
                if key in sigDict:
                    refl[ik+1] = sigDict[key]
                else:
                    refl[ik+1] = 0
        else:
            VRBIds = RBIds['Vector']
            RRBIds = RBIds['Residue']
            RBModels = Phase['RBModels']
            for irb,RBObj in enumerate(RBModels.get('Vector',[])):
                jrb = VRBIds.index(RBObj['RBId'])
                rbsx = str(irb)+':'+str(jrb)
                print >>pFile,' Vector rigid body parameters:'
                PrintRBObjPOAndSig('RBV',rbsx)
                PrintRBObjTLSAndSig('RBV',rbsx,RBObj['ThermalMotion'][0])
            for irb,RBObj in enumerate(RBModels.get('Residue',[])):
                jrb = RRBIds.index(RBObj['RBId'])
                rbsx = str(irb)+':'+str(jrb)
                print >>pFile,' Residue rigid body parameters:'
                PrintRBObjPOAndSig('RBR',rbsx)
                PrintRBObjTLSAndSig('RBR',rbsx,RBObj['ThermalMotion'][0])
                PrintRBObjTorAndSig(rbsx)
            atomsSig = {}
            wavesSig = {}
            cx,ct,cs,cia = General['AtomPtrs']
            for i,at in enumerate(Atoms):
                names = {cx:pfx+'Ax:'+str(i),cx+1:pfx+'Ay:'+str(i),cx+2:pfx+'Az:'+str(i),cx+3:pfx+'Afrac:'+str(i),
                    cia+1:pfx+'AUiso:'+str(i),cia+2:pfx+'AU11:'+str(i),cia+3:pfx+'AU22:'+str(i),cia+4:pfx+'AU33:'+str(i),
                    cia+5:pfx+'AU12:'+str(i),cia+6:pfx+'AU13:'+str(i),cia+7:pfx+'AU23:'+str(i)}
                for ind in range(cx,cx+4):
                    at[ind] = parmDict[names[ind]]
                    if ind in range(cx,cx+3):
                        name = names[ind].replace('A','dA')
                    else:
                        name = names[ind]
                    if name in sigDict:
                        atomsSig[str(i)+':'+str(ind)] = sigDict[name]
                if at[cia] == 'I':
                    at[cia+1] = parmDict[names[cia+1]]
                    if names[cia+1] in sigDict:
                        atomsSig['%d:%d'%(i,cia+1)] = sigDict[names[cia+1]]
                else:
                    for ind in range(cia+2,cia+8):
                        at[ind] = parmDict[names[ind]]
                        if names[ind] in sigDict:
                            atomsSig[str(i)+':'+str(ind)] = sigDict[names[ind]]
                ind = General['AtomTypes'].index(at[ct])
                General['Mass'] += General['AtomMass'][ind]*at[cx+3]*at[cx+5]
                if General['Type'] in ['modulated','magnetic']:
                    AtomSS = at[-1]['SS1']
                    waveType = AtomSS['waveType']
                    for Stype in ['Sfrac','Spos','Sadp','Smag']:
                        Waves = AtomSS[Stype]
                        for iw,wave in enumerate(Waves):
                            stiw = str(i)+':'+str(iw)
                            if Stype == 'Spos':
                                if waveType in ['ZigZag','Sawtooth'] and not iw:
                                    names = ['Tzero:'+stiw,'Xslope:'+stiw,'Yslope:'+stiw,'Zslope:'+stiw]
                                else:
                                    names = ['Xsin:'+stiw,'Ysin:'+stiw,'Zsin:'+stiw,
                                        'Xcos:'+stiw,'Ycos:'+stiw,'Zcos:'+stiw]
                            elif Stype == 'Sadp':
                                names = ['U11sin:'+stiw,'U22sin:'+stiw,'U33sin:'+stiw,
                                    'U12sin:'+stiw,'U13sin:'+stiw,'U23sin:'+stiw,
                                    'U11cos:'+stiw,'U22cos:'+stiw,'U33cos:'+stiw,
                                    'U12cos:'+stiw,'U13cos:'+stiw,'U23cos:'+stiw]
                            elif Stype == 'Sfrac':
                                if 'Crenel' in waveType and not iw:
                                    names = ['Fzero:'+stiw,'Fwid:'+stiw]
                                else:
                                    names = ['Fsin:'+stiw,'Fcos:'+stiw]
                            elif Stype == 'Smag':
                                names = ['MXsin:'+stiw,'MYsin:'+stiw,'MZsin:'+stiw,
                                    'MXcos:'+stiw,'MYcos:'+stiw,'MZcos:'+stiw]
                            for iname,name in enumerate(names):
                                AtomSS[Stype][iw][0][iname] = parmDict[pfx+name]
                                if pfx+name in sigDict:
                                    wavesSig[name] = sigDict[pfx+name]
                    
            PrintAtomsAndSig(General,Atoms,atomsSig)
            if General['Type'] in ['modulated','magnetic']:
                PrintWavesAndSig(General,Atoms,wavesSig)
            
        
        textureData = General['SH Texture']    
        if textureData['Order']:
            SHtextureSig = {}
            for name in ['omega','chi','phi']:
                aname = pfx+'SH '+name
                textureData['Sample '+name][1] = parmDict[aname]
                if aname in sigDict:
                    SHtextureSig['Sample '+name] = sigDict[aname]
            for name in textureData['SH Coeff'][1]:
                aname = pfx+name
                textureData['SH Coeff'][1][name] = parmDict[aname]
                if aname in sigDict:
                    SHtextureSig[name] = sigDict[aname]
            PrintSHtextureAndSig(textureData,SHtextureSig)
        if phase in RestraintDict and not Phase['General'].get('doPawley'):
            PrintRestraints(cell[1:7],SGData,General['AtomPtrs'],Atoms,AtLookup,
                textureData,RestraintDict[phase],pFile)
                    
################################################################################
##### Histogram & Phase data
################################################################################        
                    
def GetHistogramPhaseData(Phases,Histograms,Print=True,pFile=None,resetRefList=True):
    '''Loads the HAP histogram/phase information into dicts

    :param dict Phases: phase information
    :param dict Histograms: Histogram information
    :param bool Print: prints information as it is read
    :param file pFile: file object to print to (the default, None causes printing to the console)
    :param bool resetRefList: Should the contents of the Reflection List be initialized
      on loading. The default, True, initializes the Reflection List as it is loaded.

    :returns: (hapVary,hapDict,controlDict)
      * hapVary: list of refined variables
      * hapDict: dict with refined variables and their values
      * controlDict: dict with computation controls (?)
    '''
    
    def PrintSize(hapData):
        if hapData[0] in ['isotropic','uniaxial']:
            line = '\n Size model    : %9s'%(hapData[0])
            line += ' equatorial:'+'%12.5f'%(hapData[1][0])+' Refine? '+str(hapData[2][0])
            if hapData[0] == 'uniaxial':
                line += ' axial:'+'%12.5f'%(hapData[1][1])+' Refine? '+str(hapData[2][1])
            line += '\n\t LG mixing coeff.: %12.4f'%(hapData[1][2])+' Refine? '+str(hapData[2][2])
            print >>pFile,line
        else:
            print >>pFile,'\n Size model    : %s'%(hapData[0])+ \
                '\n\t LG mixing coeff.:%12.4f'%(hapData[1][2])+' Refine? '+str(hapData[2][2])
            Snames = ['S11','S22','S33','S12','S13','S23']
            ptlbls = ' names :'
            ptstr =  ' values:'
            varstr = ' refine:'
            for i,name in enumerate(Snames):
                ptlbls += '%12s' % (name)
                ptstr += '%12.6f' % (hapData[4][i])
                varstr += '%12s' % (str(hapData[5][i]))
            print >>pFile,ptlbls
            print >>pFile,ptstr
            print >>pFile,varstr
        
    def PrintMuStrain(hapData,SGData):
        if hapData[0] in ['isotropic','uniaxial']:
            line = '\n Mustrain model: %9s'%(hapData[0])
            line += ' equatorial:'+'%12.1f'%(hapData[1][0])+' Refine? '+str(hapData[2][0])
            if hapData[0] == 'uniaxial':
                line += ' axial:'+'%12.1f'%(hapData[1][1])+' Refine? '+str(hapData[2][1])
            line +='\n\t LG mixing coeff.:%12.4f'%(hapData[1][2])+' Refine? '+str(hapData[2][2])
            print >>pFile,line
        else:
            print >>pFile,'\n Mustrain model: %s'%(hapData[0])+ \
                '\n\t LG mixing coeff.:%12.4f'%(hapData[1][2])+' Refine? '+str(hapData[2][2])
            Snames = G2spc.MustrainNames(SGData)
            ptlbls = ' names :'
            ptstr =  ' values:'
            varstr = ' refine:'
            for i,name in enumerate(Snames):
                ptlbls += '%12s' % (name)
                ptstr += '%12.6f' % (hapData[4][i])
                varstr += '%12s' % (str(hapData[5][i]))
            print >>pFile,ptlbls
            print >>pFile,ptstr
            print >>pFile,varstr

    def PrintHStrain(hapData,SGData):
        print >>pFile,'\n Hydrostatic/elastic strain: '
        Hsnames = G2spc.HStrainNames(SGData)
        ptlbls = ' names :'
        ptstr =  ' values:'
        varstr = ' refine:'
        for i,name in enumerate(Hsnames):
            ptlbls += '%12s' % (name)
            ptstr += '%12.4g' % (hapData[0][i])
            varstr += '%12s' % (str(hapData[1][i]))
        print >>pFile,ptlbls
        print >>pFile,ptstr
        print >>pFile,varstr

    def PrintSHPO(hapData):
        print >>pFile,'\n Spherical harmonics preferred orientation: Order:' + \
            str(hapData[4])+' Refine? '+str(hapData[2])
        ptlbls = ' names :'
        ptstr =  ' values:'
        for item in hapData[5]:
            ptlbls += '%12s'%(item)
            ptstr += '%12.3f'%(hapData[5][item]) 
        print >>pFile,ptlbls
        print >>pFile,ptstr
    
    def PrintBabinet(hapData):
        print >>pFile,'\n Babinet form factor modification: '
        ptlbls = ' names :'
        ptstr =  ' values:'
        varstr = ' refine:'
        for name in ['BabA','BabU']:
            ptlbls += '%12s' % (name)
            ptstr += '%12.6f' % (hapData[name][0])
            varstr += '%12s' % (str(hapData[name][1]))
        print >>pFile,ptlbls
        print >>pFile,ptstr
        print >>pFile,varstr
        
    
    hapDict = {}
    hapVary = []
    controlDict = {}
    poType = {}
    poAxes = {}
    spAxes = {}
    spType = {}
    
    for phase in Phases:
        HistoPhase = Phases[phase]['Histograms']
        SGData = Phases[phase]['General']['SGData']
        cell = Phases[phase]['General']['Cell'][1:7]
        A = G2lat.cell2A(cell)
        if Phases[phase]['General']['Type'] in ['modulated','magnetic']:
            SSGData = Phases[phase]['General']['SSGData']
            Vec,x,maxH = Phases[phase]['General']['SuperVec']
        pId = Phases[phase]['pId']
        histoList = HistoPhase.keys()
        histoList.sort()
        for histogram in histoList:
            try:
                Histogram = Histograms[histogram]
            except KeyError:                        
                #skip if histogram not included e.g. in a sequential refinement
                continue
            hapData = HistoPhase[histogram]
            hId = Histogram['hId']
            if 'PWDR' in histogram:
                limits = Histogram['Limits'][1]
                inst = Histogram['Instrument Parameters'][0]
                Zero = inst['Zero'][0]
                if 'C' in inst['Type'][1]:
                    try:
                        wave = inst['Lam'][1]
                    except KeyError:
                        wave = inst['Lam1'][1]
                    dmin = wave/(2.0*sind(limits[1]/2.0))
                elif 'T' in inst['Type'][0]:
                    dmin = limits[0]/inst['difC'][1]
                pfx = str(pId)+':'+str(hId)+':'
                for item in ['Scale','Extinction']:
                    hapDict[pfx+item] = hapData[item][0]
                    if hapData[item][1]:
                        hapVary.append(pfx+item)
                names = G2spc.HStrainNames(SGData)
                HSvals = []
                for i,name in enumerate(names):
                    hapDict[pfx+name] = hapData['HStrain'][0][i]
                    HSvals.append(hapDict[pfx+name])
                    if hapData['HStrain'][1][i]:
                        hapVary.append(pfx+name)
                DIJS = G2spc.HStrainVals(HSvals,SGData)
                controlDict[pfx+'poType'] = hapData['Pref.Ori.'][0]
                if hapData['Pref.Ori.'][0] == 'MD':
                    hapDict[pfx+'MD'] = hapData['Pref.Ori.'][1]
                    controlDict[pfx+'MDAxis'] = hapData['Pref.Ori.'][3]
                    if hapData['Pref.Ori.'][2]:
                        hapVary.append(pfx+'MD')
                else:                           #'SH' spherical harmonics
                    controlDict[pfx+'SHord'] = hapData['Pref.Ori.'][4]
                    controlDict[pfx+'SHncof'] = len(hapData['Pref.Ori.'][5])
                    controlDict[pfx+'SHnames'] = G2lat.GenSHCoeff(SGData['SGLaue'],'0',controlDict[pfx+'SHord'],False)
                    controlDict[pfx+'SHhkl'] = []
                    try: #patch for old Pref.Ori. items
                        controlDict[pfx+'SHtoler'] = 0.1
                        if hapData['Pref.Ori.'][6][0] != '':
                            controlDict[pfx+'SHhkl'] = [eval(a.replace(' ',',')) for a in hapData['Pref.Ori.'][6]]
                        controlDict[pfx+'SHtoler'] = hapData['Pref.Ori.'][7]
                    except IndexError:
                        pass
                    for item in hapData['Pref.Ori.'][5]:
                        hapDict[pfx+item] = hapData['Pref.Ori.'][5][item]
                        if hapData['Pref.Ori.'][2]:
                            hapVary.append(pfx+item)
                for item in ['Mustrain','Size']:
                    controlDict[pfx+item+'Type'] = hapData[item][0]
                    hapDict[pfx+item+';mx'] = hapData[item][1][2]
                    if hapData[item][2][2]:
                        hapVary.append(pfx+item+';mx')
                    if hapData[item][0] in ['isotropic','uniaxial']:
                        hapDict[pfx+item+';i'] = hapData[item][1][0]
                        if hapData[item][2][0]:
                            hapVary.append(pfx+item+';i')
                        if hapData[item][0] == 'uniaxial':
                            controlDict[pfx+item+'Axis'] = hapData[item][3]
                            hapDict[pfx+item+';a'] = hapData[item][1][1]
                            if hapData[item][2][1]:
                                hapVary.append(pfx+item+';a')
                    else:       #generalized for mustrain or ellipsoidal for size
                        Nterms = len(hapData[item][4])
                        if item == 'Mustrain':
                            names = G2spc.MustrainNames(SGData)
                            pwrs = []
                            for name in names:
                                h,k,l = name[1:]
                                pwrs.append([int(h),int(k),int(l)])
                            controlDict[pfx+'MuPwrs'] = pwrs
                        for i in range(Nterms):
                            sfx = ':'+str(i)
                            hapDict[pfx+item+sfx] = hapData[item][4][i]
                            if hapData[item][5][i]:
                                hapVary.append(pfx+item+sfx)
                for bab in ['BabA','BabU']:
                    hapDict[pfx+bab] = hapData['Babinet'][bab][0]
                    if hapData['Babinet'][bab][1]:
                        hapVary.append(pfx+bab)
                                
                if Print: 
                    print >>pFile,'\n Phase: ',phase,' in histogram: ',histogram
                    print >>pFile,135*'-'
                    print >>pFile,' Phase fraction  : %10.4f'%(hapData['Scale'][0]),' Refine?',hapData['Scale'][1]
                    print >>pFile,' Extinction coeff: %10.4f'%(hapData['Extinction'][0]),' Refine?',hapData['Extinction'][1]
                    if hapData['Pref.Ori.'][0] == 'MD':
                        Ax = hapData['Pref.Ori.'][3]
                        print >>pFile,' March-Dollase PO: %10.4f'%(hapData['Pref.Ori.'][1]),' Refine?',hapData['Pref.Ori.'][2], \
                            ' Axis: %d %d %d'%(Ax[0],Ax[1],Ax[2])
                    else: #'SH' for spherical harmonics
                        PrintSHPO(hapData['Pref.Ori.'])
                        print >>pFile,' Penalty hkl list: '+str(controlDict[pfx+'SHhkl'])+' tolerance: %.2f'%(controlDict[pfx+'SHtoler'])
                    PrintSize(hapData['Size'])
                    PrintMuStrain(hapData['Mustrain'],SGData)
                    PrintHStrain(hapData['HStrain'],SGData)
                    if hapData['Babinet']['BabA'][0]:
                        PrintBabinet(hapData['Babinet'])                        
                if resetRefList:
                    refList = []
                    Uniq = []
                    Phi = []
                    if Phases[phase]['General']['Type'] in ['modulated','magnetic']:
                        ifSuper = True
                        HKLd = np.array(G2lat.GenSSHLaue(dmin,SGData,SSGData,Vec,maxH,A))
                        HKLd = G2mth.sortArray(HKLd,4,reverse=True)
                        for h,k,l,m,d in HKLd:
                            ext,mul,uniq,phi = G2spc.GenHKLf([h,k,l],SGData)    #is this right for SS refl.??
                            mul *= 2      # for powder overlap of Friedel pairs
                            if m or not ext:
                                if 'C' in inst['Type'][0]:
                                    pos = G2lat.Dsp2pos(inst,d)
                                    if limits[0] < pos < limits[1]:
                                        refList.append([h,k,l,m,mul,d, pos,0.0,0.0,0.0,0.0, 0.0,0.0,1.0,1.0,1.0])
                                        #... sig,gam,fotsq,fctsq, phase,icorr,prfo,abs,ext
                                        Uniq.append(uniq)
                                        Phi.append(phi)
                                elif 'T' in inst['Type'][0]:
                                    pos = G2lat.Dsp2pos(inst,d)
                                    if limits[0] < pos < limits[1]:
                                        wave = inst['difC'][1]*d/(252.816*inst['fltPath'][0])
                                        refList.append([h,k,l,m,mul,d, pos,0.0,0.0,0.0,0.0, 0.0,0.0,0.0,0.0,wave, 1.0,1.0,1.0])
                                        # ... sig,gam,fotsq,fctsq, phase,icorr,alp,bet,wave, prfo,abs,ext
                                        Uniq.append(uniq)
                                        Phi.append(phi)
                    else:
                        ifSuper = False
                        HKLd = np.array(G2lat.GenHLaue(dmin,SGData,A))
                        HKLd = G2mth.sortArray(HKLd,3,reverse=True)
                        for h,k,l,d in HKLd:
                            ext,mul,uniq,phi = G2spc.GenHKLf([h,k,l],SGData)
                            mul *= 2      # for powder overlap of Friedel pairs
                            if ext:
                                continue
                            if 'C' in inst['Type'][0]:
                                pos = G2lat.Dsp2pos(inst,d)
                                if limits[0] < pos < limits[1]:
                                    refList.append([h,k,l,mul,d, pos,0.0,0.0,0.0,0.0, 0.0,0.0,1.0,1.0,1.0])
                                    #... sig,gam,fotsq,fctsq, phase,icorr,prfo,abs,ext
                                    Uniq.append(uniq)
                                    Phi.append(phi)
                            elif 'T' in inst['Type'][0]:
                                pos = G2lat.Dsp2pos(inst,d)
                                if limits[0] < pos < limits[1]:
                                    wave = inst['difC'][1]*d/(252.816*inst['fltPath'][0])
                                    refList.append([h,k,l,mul,d, pos,0.0,0.0,0.0,0.0, 0.0,0.0,0.0,0.0,wave, 1.0,1.0,1.0])
                                    # ... sig,gam,fotsq,fctsq, phase,icorr,alp,bet,wave, prfo,abs,ext
                                    Uniq.append(uniq)
                                    Phi.append(phi)
                    Histogram['Reflection Lists'][phase] = {'RefList':np.array(refList),'FF':{},'Type':inst['Type'][0],'Super':ifSuper}
            elif 'HKLF' in histogram:
                inst = Histogram['Instrument Parameters'][0]
                hId = Histogram['hId']
                hfx = ':%d:'%(hId)
                for item in inst:
                    if type(inst) is not list and item != 'Type': continue # skip over non-refined items (such as InstName)
                    hapDict[hfx+item] = inst[item][1]
                pfx = str(pId)+':'+str(hId)+':'
                hapDict[pfx+'Scale'] = hapData['Scale'][0]
                if hapData['Scale'][1]:
                    hapVary.append(pfx+'Scale')
                                
                extApprox,extType,extParms = hapData['Extinction']
                controlDict[pfx+'EType'] = extType
                controlDict[pfx+'EApprox'] = extApprox
                if 'C' in inst['Type'][0]:
                    controlDict[pfx+'Tbar'] = extParms['Tbar']
                    controlDict[pfx+'Cos2TM'] = extParms['Cos2TM']
                if 'Primary' in extType:
                    Ekey = ['Ep',]
                elif 'I & II' in extType:
                    Ekey = ['Eg','Es']
                elif 'Secondary Type II' == extType:
                    Ekey = ['Es',]
                elif 'Secondary Type I' == extType:
                    Ekey = ['Eg',]
                else:   #'None'
                    Ekey = []
                for eKey in Ekey:
                    hapDict[pfx+eKey] = extParms[eKey][0]
                    if extParms[eKey][1]:
                        hapVary.append(pfx+eKey)
                for bab in ['BabA','BabU']:
                    hapDict[pfx+bab] = hapData['Babinet'][bab][0]
                    if hapData['Babinet'][bab][1]:
                        hapVary.append(pfx+bab)
                if Print: 
                    print >>pFile,'\n Phase: ',phase,' in histogram: ',histogram
                    print >>pFile,135*'-'
                    print >>pFile,' Scale factor     : %10.4f'%(hapData['Scale'][0]),' Refine?',hapData['Scale'][1]
                    if extType != 'None':
                        print >>pFile,' Extinction  Type: %15s'%(extType),' approx: %10s'%(extApprox)
                        text = ' Parameters       :'
                        for eKey in Ekey:
                            text += ' %4s : %10.3e Refine? '%(eKey,extParms[eKey][0])+str(extParms[eKey][1])
                        print >>pFile,text
                    if hapData['Babinet']['BabA'][0]:
                        PrintBabinet(hapData['Babinet'])
                Histogram['Reflection Lists'] = phase       
                
    return hapVary,hapDict,controlDict
    
def SetHistogramPhaseData(parmDict,sigDict,Phases,Histograms,FFtables,Print=True,pFile=None):
    'needs a doc string'
    
    def PrintSizeAndSig(hapData,sizeSig):
        line = '\n Size model:     %9s'%(hapData[0])
        refine = False
        if hapData[0] in ['isotropic','uniaxial']:
            line += ' equatorial:%12.5f'%(hapData[1][0])
            if sizeSig[0][0]:
                line += ', sig:%8.4f'%(sizeSig[0][0])
                refine = True
            if hapData[0] == 'uniaxial':
                line += ' axial:%12.4f'%(hapData[1][1])
                if sizeSig[0][1]:
                    refine = True
                    line += ', sig:%8.4f'%(sizeSig[0][1])
            line += ' LG mix coeff.:%12.4f'%(hapData[1][2])
            if sizeSig[0][2]:
                refine = True
                line += ', sig:%8.4f'%(sizeSig[0][2])
            if refine:
                print >>pFile,line
        else:
            line += ' LG mix coeff.:%12.4f'%(hapData[1][2])
            if sizeSig[0][2]:
                refine = True
                line += ', sig:%8.4f'%(sizeSig[0][2])
            Snames = ['S11','S22','S33','S12','S13','S23']
            ptlbls = ' name  :'
            ptstr =  ' value :'
            sigstr = ' sig   :'
            for i,name in enumerate(Snames):
                ptlbls += '%12s' % (name)
                ptstr += '%12.6f' % (hapData[4][i])
                if sizeSig[1][i]:
                    refine = True
                    sigstr += '%12.6f' % (sizeSig[1][i])
                else:
                    sigstr += 12*' '
            if refine:
                print >>pFile,line
                print >>pFile,ptlbls
                print >>pFile,ptstr
                print >>pFile,sigstr
        
    def PrintMuStrainAndSig(hapData,mustrainSig,SGData):
        line = '\n Mustrain model: %9s'%(hapData[0])
        refine = False
        if hapData[0] in ['isotropic','uniaxial']:
            line += ' equatorial:%12.1f'%(hapData[1][0])
            if mustrainSig[0][0]:
                line += ', sig:%8.1f'%(mustrainSig[0][0])
                refine = True
            if hapData[0] == 'uniaxial':
                line += ' axial:%12.1f'%(hapData[1][1])
                if mustrainSig[0][1]:
                     line += ', sig:%8.1f'%(mustrainSig[0][1])
            line += ' LG mix coeff.:%12.4f'%(hapData[1][2])
            if mustrainSig[0][2]:
                refine = True
                line += ', sig:%8.3f'%(mustrainSig[0][2])
            if refine:
                print >>pFile,line
        else:
            line += ' LG mix coeff.:%12.4f'%(hapData[1][2])
            if mustrainSig[0][2]:
                refine = True
                line += ', sig:%8.3f'%(mustrainSig[0][2])
            Snames = G2spc.MustrainNames(SGData)
            ptlbls = ' name  :'
            ptstr =  ' value :'
            sigstr = ' sig   :'
            for i,name in enumerate(Snames):
                ptlbls += '%12s' % (name)
                ptstr += '%12.6f' % (hapData[4][i])
                if mustrainSig[1][i]:
                    refine = True
                    sigstr += '%12.6f' % (mustrainSig[1][i])
                else:
                    sigstr += 12*' '
            if refine:
                print >>pFile,line
                print >>pFile,ptlbls
                print >>pFile,ptstr
                print >>pFile,sigstr
            
    def PrintHStrainAndSig(hapData,strainSig,SGData):
        Hsnames = G2spc.HStrainNames(SGData)
        ptlbls = ' name  :'
        ptstr =  ' value :'
        sigstr = ' sig   :'
        refine = False
        for i,name in enumerate(Hsnames):
            ptlbls += '%12s' % (name)
            ptstr += '%12.4g' % (hapData[0][i])
            if name in strainSig:
                refine = True
                sigstr += '%12.4g' % (strainSig[name])
            else:
                sigstr += 12*' '
        if refine:
            print >>pFile,'\n Hydrostatic/elastic strain: '
            print >>pFile,ptlbls
            print >>pFile,ptstr
            print >>pFile,sigstr
        
    def PrintSHPOAndSig(pfx,hapData,POsig):
        print >>pFile,'\n Spherical harmonics preferred orientation: Order:'+str(hapData[4])
        ptlbls = ' names :'
        ptstr =  ' values:'
        sigstr = ' sig   :'
        for item in hapData[5]:
            ptlbls += '%12s'%(item)
            ptstr += '%12.3f'%(hapData[5][item])
            if pfx+item in POsig:
                sigstr += '%12.3f'%(POsig[pfx+item])
            else:
                sigstr += 12*' ' 
        print >>pFile,ptlbls
        print >>pFile,ptstr
        print >>pFile,sigstr
        
    def PrintExtAndSig(pfx,hapData,ScalExtSig):
        print >>pFile,'\n Single crystal extinction: Type: ',hapData[0],' Approx: ',hapData[1]
        text = ''
        for item in hapData[2]:
            if pfx+item in ScalExtSig:
                text += '       %s: '%(item)
                text += '%12.2e'%(hapData[2][item][0])
                if pfx+item in ScalExtSig:
                    text += ' sig: %12.2e'%(ScalExtSig[pfx+item])
        print >>pFile,text        
        
    def PrintBabinetAndSig(pfx,hapData,BabSig):
        print >>pFile,'\n Babinet form factor modification: '
        ptlbls = ' names :'
        ptstr =  ' values:'
        sigstr = ' sig   :'
        for item in hapData:
            ptlbls += '%12s'%(item)
            ptstr += '%12.3f'%(hapData[item][0])
            if pfx+item in BabSig:
                sigstr += '%12.3f'%(BabSig[pfx+item])
            else:
                sigstr += 12*' ' 
        print >>pFile,ptlbls
        print >>pFile,ptstr
        print >>pFile,sigstr
    
    PhFrExtPOSig = {}
    SizeMuStrSig = {}
    ScalExtSig = {}
    BabSig = {}
    wtFrSum = {}
    for phase in Phases:
        HistoPhase = Phases[phase]['Histograms']
        General = Phases[phase]['General']
        SGData = General['SGData']
        pId = Phases[phase]['pId']
        histoList = HistoPhase.keys()
        histoList.sort()
        for histogram in histoList:
            try:
                Histogram = Histograms[histogram]
            except KeyError:                        
                #skip if histogram not included e.g. in a sequential refinement
                continue
            hapData = HistoPhase[histogram]
            hId = Histogram['hId']
            pfx = str(pId)+':'+str(hId)+':'
            if hId not in wtFrSum:
                wtFrSum[hId] = 0.
            if 'PWDR' in histogram:
                for item in ['Scale','Extinction']:
                    hapData[item][0] = parmDict[pfx+item]
                    if pfx+item in sigDict:
                        PhFrExtPOSig.update({pfx+item:sigDict[pfx+item],})
                wtFrSum[hId] += hapData['Scale'][0]*General['Mass']
                if hapData['Pref.Ori.'][0] == 'MD':
                    hapData['Pref.Ori.'][1] = parmDict[pfx+'MD']
                    if pfx+'MD' in sigDict:
                        PhFrExtPOSig.update({pfx+'MD':sigDict[pfx+'MD'],})
                else:                           #'SH' spherical harmonics
                    for item in hapData['Pref.Ori.'][5]:
                        hapData['Pref.Ori.'][5][item] = parmDict[pfx+item]
                        if pfx+item in sigDict:
                            PhFrExtPOSig.update({pfx+item:sigDict[pfx+item],})
                SizeMuStrSig.update({pfx+'Mustrain':[[0,0,0],[0 for i in range(len(hapData['Mustrain'][4]))]],
                    pfx+'Size':[[0,0,0],[0 for i in range(len(hapData['Size'][4]))]],
                    pfx+'HStrain':{}})                  
                for item in ['Mustrain','Size']:
                    hapData[item][1][2] = parmDict[pfx+item+';mx']
                    hapData[item][1][2] = min(1.,max(0.,hapData[item][1][2]))
                    if pfx+item+';mx' in sigDict:
                        SizeMuStrSig[pfx+item][0][2] = sigDict[pfx+item+';mx']
                    if hapData[item][0] in ['isotropic','uniaxial']:                    
                        hapData[item][1][0] = parmDict[pfx+item+';i']
                        if item == 'Size':
                            hapData[item][1][0] = min(10.,max(0.001,hapData[item][1][0]))
                        if pfx+item+';i' in sigDict: 
                            SizeMuStrSig[pfx+item][0][0] = sigDict[pfx+item+';i']
                        if hapData[item][0] == 'uniaxial':
                            hapData[item][1][1] = parmDict[pfx+item+';a']
                            if item == 'Size':
                                hapData[item][1][1] = min(10.,max(0.001,hapData[item][1][1]))                        
                            if pfx+item+';a' in sigDict:
                                SizeMuStrSig[pfx+item][0][1] = sigDict[pfx+item+';a']
                    else:       #generalized for mustrain or ellipsoidal for size
                        Nterms = len(hapData[item][4])
                        for i in range(Nterms):
                            sfx = ':'+str(i)
                            hapData[item][4][i] = parmDict[pfx+item+sfx]
                            if pfx+item+sfx in sigDict:
                                SizeMuStrSig[pfx+item][1][i] = sigDict[pfx+item+sfx]
                names = G2spc.HStrainNames(SGData)
                for i,name in enumerate(names):
                    hapData['HStrain'][0][i] = parmDict[pfx+name]
                    if pfx+name in sigDict:
                        SizeMuStrSig[pfx+'HStrain'][name] = sigDict[pfx+name]
                for name in ['BabA','BabU']:
                    hapData['Babinet'][name][0] = parmDict[pfx+name]
                    if pfx+name in sigDict:
                        BabSig[pfx+name] = sigDict[pfx+name]                
                
            elif 'HKLF' in histogram:
                for item in ['Scale',]:
                    if parmDict.get(pfx+item):
                        hapData[item][0] = parmDict[pfx+item]
                        if pfx+item in sigDict:
                            ScalExtSig[pfx+item] = sigDict[pfx+item]
                for item in ['Ep','Eg','Es']:
                    if parmDict.get(pfx+item):
                        hapData['Extinction'][2][item][0] = parmDict[pfx+item]
                        if pfx+item in sigDict:
                            ScalExtSig[pfx+item] = sigDict[pfx+item]
                for name in ['BabA','BabU']:
                    hapData['Babinet'][name][0] = parmDict[pfx+name]
                    if pfx+name in sigDict:
                        BabSig[pfx+name] = sigDict[pfx+name]                

    if Print:
        for phase in Phases:
            HistoPhase = Phases[phase]['Histograms']
            General = Phases[phase]['General']
            SGData = General['SGData']
            pId = Phases[phase]['pId']
            histoList = HistoPhase.keys()
            histoList.sort()
            for histogram in histoList:
                try:
                    Histogram = Histograms[histogram]
                except KeyError:                        
                    #skip if histogram not included e.g. in a sequential refinement
                    continue
                print >>pFile,'\n Phase: ',phase,' in histogram: ',histogram
                print >>pFile,130*'-'
                hapData = HistoPhase[histogram]
                hId = Histogram['hId']
                Histogram['Residuals'][str(pId)+'::Name'] = phase
                pfx = str(pId)+':'+str(hId)+':'
                hfx = ':%s:'%(hId)
                if 'PWDR' in histogram:
                    print >>pFile,' Final refinement RF, RF^2 = %.2f%%, %.2f%% on %d reflections'   \
                        %(Histogram['Residuals'][pfx+'Rf'],Histogram['Residuals'][pfx+'Rf^2'],Histogram['Residuals'][pfx+'Nref'])
                    print >>pFile,' Bragg intensity sum = %.3g'%(Histogram['Residuals'][pfx+'sumInt'])
                
                    if pfx+'Scale' in PhFrExtPOSig:
                        wtFr = hapData['Scale'][0]*General['Mass']/wtFrSum[hId]
                        sigwtFr = PhFrExtPOSig[pfx+'Scale']*wtFr/hapData['Scale'][0]
                        print >>pFile,' Phase fraction  : %10.5f, sig %10.5f Weight fraction  : %8.5f, sig %10.5f' \
                            %(hapData['Scale'][0],PhFrExtPOSig[pfx+'Scale'],wtFr,sigwtFr)
                    if pfx+'Extinction' in PhFrExtPOSig:
                        print >>pFile,' Extinction coeff: %10.4f, sig %10.4f'%(hapData['Extinction'][0],PhFrExtPOSig[pfx+'Extinction'])
                    if hapData['Pref.Ori.'][0] == 'MD':
                        if pfx+'MD' in PhFrExtPOSig:
                            print >>pFile,' March-Dollase PO: %10.4f, sig %10.4f'%(hapData['Pref.Ori.'][1],PhFrExtPOSig[pfx+'MD'])
                    else:
                        PrintSHPOAndSig(pfx,hapData['Pref.Ori.'],PhFrExtPOSig)
                    PrintSizeAndSig(hapData['Size'],SizeMuStrSig[pfx+'Size'])
                    PrintMuStrainAndSig(hapData['Mustrain'],SizeMuStrSig[pfx+'Mustrain'],SGData)
                    PrintHStrainAndSig(hapData['HStrain'],SizeMuStrSig[pfx+'HStrain'],SGData)
                    if len(BabSig):
                        PrintBabinetAndSig(pfx,hapData['Babinet'],BabSig)
                    
                elif 'HKLF' in histogram:
                    Inst = Histogram['Instrument Parameters'][0]
                    print >>pFile,' Final refinement RF, RF^2 = %.2f%%, %.2f%% on %d reflections (%d user rejected, %d sp.gp.extinct)'   \
                        %(Histogram['Residuals'][pfx+'Rf'],Histogram['Residuals'][pfx+'Rf^2'],Histogram['Residuals'][pfx+'Nref'],
                        Histogram['Residuals'][pfx+'Nrej'],Histogram['Residuals'][pfx+'Next'])
                    if FFtables != None and 'N' not in Inst['Type'][0]:
                        PrintFprime(FFtables,hfx,pFile)
                    print >>pFile,' HKLF histogram weight factor = ','%.3f'%(Histogram['wtFactor'])
                    if pfx+'Scale' in ScalExtSig:
                        print >>pFile,' Scale factor : %10.4f, sig %10.4f'%(hapData['Scale'][0],ScalExtSig[pfx+'Scale'])
                    if hapData['Extinction'][0] != 'None':
                        PrintExtAndSig(pfx,hapData['Extinction'],ScalExtSig)
                    if len(BabSig):
                        PrintBabinetAndSig(pfx,hapData['Babinet'],BabSig)

################################################################################
##### Histogram data
################################################################################        
                    
def GetHistogramData(Histograms,Print=True,pFile=None):
    'needs a doc string'
    
    def GetBackgroundParms(hId,Background):
        Back = Background[0]
        DebyePeaks = Background[1]
        bakType,bakFlag = Back[:2]
        backVals = Back[3:]
        backNames = [':'+str(hId)+':Back;'+str(i) for i in range(len(backVals))]
        backDict = dict(zip(backNames,backVals))
        backVary = []
        if bakFlag:
            backVary = backNames
        backDict[':'+str(hId)+':nDebye'] = DebyePeaks['nDebye']
        backDict[':'+str(hId)+':nPeaks'] = DebyePeaks['nPeaks']
        debyeDict = {}
        debyeList = []
        for i in range(DebyePeaks['nDebye']):
            debyeNames = [':'+str(hId)+':DebyeA;'+str(i),':'+str(hId)+':DebyeR;'+str(i),':'+str(hId)+':DebyeU;'+str(i)]
            debyeDict.update(dict(zip(debyeNames,DebyePeaks['debyeTerms'][i][::2])))
            debyeList += zip(debyeNames,DebyePeaks['debyeTerms'][i][1::2])
        debyeVary = []
        for item in debyeList:
            if item[1]:
                debyeVary.append(item[0])
        backDict.update(debyeDict)
        backVary += debyeVary
        peakDict = {}
        peakList = []
        for i in range(DebyePeaks['nPeaks']):
            peakNames = [':'+str(hId)+':BkPkpos;'+str(i),':'+str(hId)+ \
                ':BkPkint;'+str(i),':'+str(hId)+':BkPksig;'+str(i),':'+str(hId)+':BkPkgam;'+str(i)]
            peakDict.update(dict(zip(peakNames,DebyePeaks['peaksList'][i][::2])))
            peakList += zip(peakNames,DebyePeaks['peaksList'][i][1::2])
        peakVary = []
        for item in peakList:
            if item[1]:
                peakVary.append(item[0])
        backDict.update(peakDict)
        backVary += peakVary
        return bakType,backDict,backVary            
        
    def GetInstParms(hId,Inst):     
        dataType = Inst['Type'][0]
        instDict = {}
        insVary = []
        pfx = ':'+str(hId)+':'
        insKeys = Inst.keys()
        insKeys.sort()
        for item in insKeys:
            insName = pfx+item
            instDict[insName] = Inst[item][1]
            if len(Inst[item]) > 2 and Inst[item][2]:
                insVary.append(insName)
        if 'C' in dataType:
            instDict[pfx+'SH/L'] = max(instDict[pfx+'SH/L'],0.0005)
        return dataType,instDict,insVary
        
    def GetSampleParms(hId,Sample):
        sampVary = []
        hfx = ':'+str(hId)+':'        
        sampDict = {hfx+'Gonio. radius':Sample['Gonio. radius'],hfx+'Omega':Sample['Omega'],
            hfx+'Chi':Sample['Chi'],hfx+'Phi':Sample['Phi']}
        for key in ('Temperature','Pressure','FreePrm1','FreePrm2','FreePrm3'):
            if key in Sample:
                sampDict[hfx+key] = Sample[key]
        Type = Sample['Type']
        if 'Bragg' in Type:             #Bragg-Brentano
            for item in ['Scale','Shift','Transparency','SurfRoughA','SurfRoughB']:
                sampDict[hfx+item] = Sample[item][0]
                if Sample[item][1]:
                    sampVary.append(hfx+item)
        elif 'Debye' in Type:        #Debye-Scherrer
            for item in ['Scale','Absorption','DisplaceX','DisplaceY']:
                sampDict[hfx+item] = Sample[item][0]
                if Sample[item][1]:
                    sampVary.append(hfx+item)
        return Type,sampDict,sampVary
        
    def PrintBackground(Background):
        Back = Background[0]
        DebyePeaks = Background[1]
        print >>pFile,'\n Background function: ',Back[0],' Refine?',bool(Back[1])
        line = ' Coefficients: '
        for i,back in enumerate(Back[3:]):
            line += '%10.3f'%(back)
            if i and not i%10:
                line += '\n'+15*' '
        print >>pFile,line
        if DebyePeaks['nDebye']:
            print >>pFile,'\n Debye diffuse scattering coefficients'
            parms = ['DebyeA','DebyeR','DebyeU']
            line = ' names :  '
            for parm in parms:
                line += '%8s refine?'%(parm)
            print >>pFile,line
            for j,term in enumerate(DebyePeaks['debyeTerms']):
                line = ' term'+'%2d'%(j)+':'
                for i in range(3):
                    line += '%10.3f %5s'%(term[2*i],bool(term[2*i+1]))                    
                print >>pFile,line
        if DebyePeaks['nPeaks']:
            print >>pFile,'\n Single peak coefficients'
            parms =    ['BkPkpos','BkPkint','BkPksig','BkPkgam']
            line = ' names :  '
            for parm in parms:
                line += '%8s refine?'%(parm)
            print >>pFile,line
            for j,term in enumerate(DebyePeaks['peaksList']):
                line = ' peak'+'%2d'%(j)+':'
                for i in range(4):
                    line += '%12.3f %5s'%(term[2*i],bool(term[2*i+1]))                    
                print >>pFile,line
        
    def PrintInstParms(Inst):
        print >>pFile,'\n Instrument Parameters:'
        insKeys = Inst.keys()
        insKeys.sort()
        iBeg = 0
        Ok = True
        while Ok:
            ptlbls = ' name  :'
            ptstr =  ' value :'
            varstr = ' refine:'
            iFin = min(iBeg+9,len(insKeys))
            for item in insKeys[iBeg:iFin]:
                if item not in ['Type','Source']:
                    ptlbls += '%12s' % (item)
                    ptstr += '%12.6f' % (Inst[item][1])
                    if item in ['Lam1','Lam2','Azimuth','fltPath','2-theta',]:
                        varstr += 12*' '
                    else:
                        varstr += '%12s' % (str(bool(Inst[item][2])))
            print >>pFile,ptlbls
            print >>pFile,ptstr
            print >>pFile,varstr
            iBeg = iFin
            if iBeg == len(insKeys):
                Ok = False
            else:
                print >>pFile,'\n'
        
    def PrintSampleParms(Sample):
        print >>pFile,'\n Sample Parameters:'
        print >>pFile,' Goniometer omega = %.2f, chi = %.2f, phi = %.2f'% \
            (Sample['Omega'],Sample['Chi'],Sample['Phi'])
        ptlbls = ' name  :'
        ptstr =  ' value :'
        varstr = ' refine:'
        if 'Bragg' in Sample['Type']:
            for item in ['Scale','Shift','Transparency','SurfRoughA','SurfRoughB']:
                ptlbls += '%14s'%(item)
                ptstr += '%14.4f'%(Sample[item][0])
                varstr += '%14s'%(str(bool(Sample[item][1])))
            
        elif 'Debye' in Type:        #Debye-Scherrer
            for item in ['Scale','Absorption','DisplaceX','DisplaceY']:
                ptlbls += '%14s'%(item)
                ptstr += '%14.4f'%(Sample[item][0])
                varstr += '%14s'%(str(bool(Sample[item][1])))

        print >>pFile,ptlbls
        print >>pFile,ptstr
        print >>pFile,varstr
        
    histDict = {}
    histVary = []
    controlDict = {}
    histoList = Histograms.keys()
    histoList.sort()
    for histogram in histoList:
        if 'PWDR' in histogram:
            Histogram = Histograms[histogram]
            hId = Histogram['hId']
            pfx = ':'+str(hId)+':'
            controlDict[pfx+'wtFactor'] = Histogram['wtFactor']
            controlDict[pfx+'Limits'] = Histogram['Limits'][1]
            controlDict[pfx+'Exclude'] = Histogram['Limits'][2:]
            for excl in controlDict[pfx+'Exclude']:
                Histogram['Data'][0] = ma.masked_inside(Histogram['Data'][0],excl[0],excl[1])
            if controlDict[pfx+'Exclude']:
                ma.mask_rows(Histogram['Data'])
            Background = Histogram['Background']
            Type,bakDict,bakVary = GetBackgroundParms(hId,Background)
            controlDict[pfx+'bakType'] = Type
            histDict.update(bakDict)
            histVary += bakVary
            
            Inst = Histogram['Instrument Parameters'][0]
            Type,instDict,insVary = GetInstParms(hId,Inst)
            controlDict[pfx+'histType'] = Type
            if 'XC' in Type:
                if pfx+'Lam1' in instDict:
                    controlDict[pfx+'keV'] = 12.397639/instDict[pfx+'Lam1']
                else:
                    controlDict[pfx+'keV'] = 12.397639/instDict[pfx+'Lam']            
            histDict.update(instDict)
            histVary += insVary
            
            Sample = Histogram['Sample Parameters']
            Type,sampDict,sampVary = GetSampleParms(hId,Sample)
            controlDict[pfx+'instType'] = Type
            histDict.update(sampDict)
            histVary += sampVary
            
    
            if Print: 
                print >>pFile,'\n Histogram: ',histogram,' histogram Id: ',hId
                print >>pFile,135*'-'
                Units = {'C':' deg','T':' msec'}
                units = Units[controlDict[pfx+'histType'][2]]
                Limits = controlDict[pfx+'Limits']
                print >>pFile,' Instrument type: ',Sample['Type']
                print >>pFile,' Histogram limits: %8.2f%s to %8.2f%s'%(Limits[0],units,Limits[1],units)
                if len(controlDict[pfx+'Exclude']):
                    excls = controlDict[pfx+'Exclude']
                    for excl in excls:
                        print >>pFile,' Excluded region:  %8.2f%s to %8.2f%s'%(excl[0],units,excl[1],units)    
                PrintSampleParms(Sample)
                PrintInstParms(Inst)
                PrintBackground(Background)
        elif 'HKLF' in histogram:
            Histogram = Histograms[histogram]
            hId = Histogram['hId']
            pfx = ':'+str(hId)+':'
            controlDict[pfx+'wtFactor'] = Histogram['wtFactor']
            Inst = Histogram['Instrument Parameters'][0]
            controlDict[pfx+'histType'] = Inst['Type'][0]
            if 'X' in Inst['Type'][0]:
                histDict[pfx+'Lam'] = Inst['Lam'][1]
                controlDict[pfx+'keV'] = 12.397639/histDict[pfx+'Lam']                    
    return histVary,histDict,controlDict
    
def SetHistogramData(parmDict,sigDict,Histograms,FFtables,Print=True,pFile=None):
    'needs a doc string'
    
    def SetBackgroundParms(pfx,Background,parmDict,sigDict):
        Back = Background[0]
        DebyePeaks = Background[1]
        lenBack = len(Back[3:])
        backSig = [0 for i in range(lenBack+3*DebyePeaks['nDebye']+4*DebyePeaks['nPeaks'])]
        for i in range(lenBack):
            Back[3+i] = parmDict[pfx+'Back;'+str(i)]
            if pfx+'Back;'+str(i) in sigDict:
                backSig[i] = sigDict[pfx+'Back;'+str(i)]
        if DebyePeaks['nDebye']:
            for i in range(DebyePeaks['nDebye']):
                names = [pfx+'DebyeA;'+str(i),pfx+'DebyeR;'+str(i),pfx+'DebyeU;'+str(i)]
                for j,name in enumerate(names):
                    DebyePeaks['debyeTerms'][i][2*j] = parmDict[name]
                    if name in sigDict:
                        backSig[lenBack+3*i+j] = sigDict[name]            
        if DebyePeaks['nPeaks']:
            for i in range(DebyePeaks['nPeaks']):
                names = [pfx+'BkPkpos;'+str(i),pfx+'BkPkint;'+str(i),
                    pfx+'BkPksig;'+str(i),pfx+'BkPkgam;'+str(i)]
                for j,name in enumerate(names):
                    DebyePeaks['peaksList'][i][2*j] = parmDict[name]
                    if name in sigDict:
                        backSig[lenBack+3*DebyePeaks['nDebye']+4*i+j] = sigDict[name]
        return backSig
        
    def SetInstParms(pfx,Inst,parmDict,sigDict):
        instSig = {}
        insKeys = Inst.keys()
        insKeys.sort()
        for item in insKeys:
            insName = pfx+item
            Inst[item][1] = parmDict[insName]
            if insName in sigDict:
                instSig[item] = sigDict[insName]
            else:
                instSig[item] = 0
        return instSig
        
    def SetSampleParms(pfx,Sample,parmDict,sigDict):
        if 'Bragg' in Sample['Type']:             #Bragg-Brentano
            sampSig = [0 for i in range(5)]
            for i,item in enumerate(['Scale','Shift','Transparency','SurfRoughA','SurfRoughB']):
                Sample[item][0] = parmDict[pfx+item]
                if pfx+item in sigDict:
                    sampSig[i] = sigDict[pfx+item]
        elif 'Debye' in Sample['Type']:        #Debye-Scherrer
            sampSig = [0 for i in range(4)]
            for i,item in enumerate(['Scale','Absorption','DisplaceX','DisplaceY']):
                Sample[item][0] = parmDict[pfx+item]
                if pfx+item in sigDict:
                    sampSig[i] = sigDict[pfx+item]
        return sampSig
        
    def PrintBackgroundSig(Background,backSig):
        Back = Background[0]
        DebyePeaks = Background[1]
        lenBack = len(Back[3:])
        valstr = ' value : '
        sigstr = ' sig   : '
        refine = False
        for i,back in enumerate(Back[3:]):
            valstr += '%10.4g'%(back)
            if Back[1]:
                refine = True
                sigstr += '%10.4g'%(backSig[i])
            else:
                sigstr += 10*' '
        if refine:
            print >>pFile,'\n Background function: ',Back[0]
            print >>pFile,valstr
            print >>pFile,sigstr 
        if DebyePeaks['nDebye']:
            ifAny = False
            ptfmt = "%12.3f"
            names =  ' names :'
            ptstr =  ' values:'
            sigstr = ' esds  :'
            for item in sigDict:
                if 'Debye' in item:
                    ifAny = True
                    names += '%12s'%(item)
                    ptstr += ptfmt%(parmDict[item])
                    sigstr += ptfmt%(sigDict[item])
            if ifAny:
                print >>pFile,'\n Debye diffuse scattering coefficients'
                print >>pFile,names
                print >>pFile,ptstr
                print >>pFile,sigstr
        if DebyePeaks['nPeaks']:
            print >>pFile,'\n Single peak coefficients:'
            parms =    ['BkPkpos','BkPkint','BkPksig','BkPkgam']
            line = ' peak no. '
            for parm in parms:
                line += '%14s%12s'%(parm.center(14),'esd'.center(12))
            print >>pFile,line
            for ip in range(DebyePeaks['nPeaks']):
                ptstr = ' %4d '%(ip)
                for parm in parms:
                    fmt = '%14.3f'
                    efmt = '%12.3f'
                    if parm == 'BkPkpos':
                        fmt = '%14.4f'
                        efmt = '%12.4f'
                    name = pfx+parm+';%d'%(ip)
                    ptstr += fmt%(parmDict[name])
                    if name in sigDict:
                        ptstr += efmt%(sigDict[name])
                    else:
                        ptstr += 12*' '
                print >>pFile,ptstr
        sumBk = np.array(Histogram['sumBk'])
        print >>pFile,' Background sums: empirical %.3g, Debye %.3g, peaks %.3g, Total %.3g'    \
            %(sumBk[0],sumBk[1],sumBk[2],np.sum(sumBk))
        
    def PrintInstParmsSig(Inst,instSig):
        refine = False
        insKeys = instSig.keys()
        insKeys.sort()
        iBeg = 0
        Ok = True
        while Ok:
            ptlbls = ' names :'
            ptstr =  ' value :'
            sigstr = ' sig   :'
            iFin = min(iBeg+9,len(insKeys))
            for name in insKeys[iBeg:iFin]:
                if name not in  ['Type','Lam1','Lam2','Azimuth','Source','fltPath']:
                    ptlbls += '%12s' % (name)
                    ptstr += '%12.6f' % (Inst[name][1])
                    if instSig[name]:
                        refine = True
                        sigstr += '%12.6f' % (instSig[name])
                    else:
                        sigstr += 12*' '
            if refine:
                print >>pFile,'\n Instrument Parameters:'
                print >>pFile,ptlbls
                print >>pFile,ptstr
                print >>pFile,sigstr
            iBeg = iFin
            if iBeg == len(insKeys):
                Ok = False
        
    def PrintSampleParmsSig(Sample,sampleSig):
        ptlbls = ' names :'
        ptstr =  ' values:'
        sigstr = ' sig   :'
        refine = False
        if 'Bragg' in Sample['Type']:
            for i,item in enumerate(['Scale','Shift','Transparency','SurfRoughA','SurfRoughB']):
                ptlbls += '%14s'%(item)
                ptstr += '%14.4f'%(Sample[item][0])
                if sampleSig[i]:
                    refine = True
                    sigstr += '%14.4f'%(sampleSig[i])
                else:
                    sigstr += 14*' '
            
        elif 'Debye' in Sample['Type']:        #Debye-Scherrer
            for i,item in enumerate(['Scale','Absorption','DisplaceX','DisplaceY']):
                ptlbls += '%14s'%(item)
                ptstr += '%14.4f'%(Sample[item][0])
                if sampleSig[i]:
                    refine = True
                    sigstr += '%14.4f'%(sampleSig[i])
                else:
                    sigstr += 14*' '

        if refine:
            print >>pFile,'\n Sample Parameters:'
            print >>pFile,ptlbls
            print >>pFile,ptstr
            print >>pFile,sigstr
        
    histoList = Histograms.keys()
    histoList.sort()
    for histogram in histoList:
        if 'PWDR' in histogram:
            Histogram = Histograms[histogram]
            hId = Histogram['hId']
            pfx = ':'+str(hId)+':'
            Background = Histogram['Background']
            backSig = SetBackgroundParms(pfx,Background,parmDict,sigDict)
            
            Inst = Histogram['Instrument Parameters'][0]
            instSig = SetInstParms(pfx,Inst,parmDict,sigDict)
        
            Sample = Histogram['Sample Parameters']
            sampSig = SetSampleParms(pfx,Sample,parmDict,sigDict)

            print >>pFile,'\n Histogram: ',histogram,' histogram Id: ',hId
            print >>pFile,135*'-'
            print >>pFile,' PWDR histogram weight factor = '+'%.3f'%(Histogram['wtFactor'])
            print >>pFile,' Final refinement wR = %.2f%% on %d observations in this histogram'%(Histogram['Residuals']['wR'],Histogram['Residuals']['Nobs'])
            print >>pFile,' Other residuals: R = %.2f%%, Rb = %.2f%%, wRb = %.2f%% wRmin = %.2f%%'% \
                (Histogram['Residuals']['R'],Histogram['Residuals']['Rb'],Histogram['Residuals']['wRb'],Histogram['Residuals']['wRmin'])
            if Print:
                print >>pFile,' Instrument type: ',Sample['Type']
                if FFtables != None and 'N' not in Inst['Type'][0]:
                    PrintFprime(FFtables,pfx,pFile)
                PrintSampleParmsSig(Sample,sampSig)
                PrintInstParmsSig(Inst,instSig)
                PrintBackgroundSig(Background,backSig)
                
