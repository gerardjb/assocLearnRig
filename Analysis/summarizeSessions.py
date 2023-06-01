# -*- coding: utf-8 -*-
"""
analyzeSession

This utility queries the user to pick a directory containing as many data
directories as they would like analyzed. For each session, the user will
be asked to make an ROI around the subjects eye. Wheel and eye data
will then be processed.

Data will be output to a summary subdirectory in both the data directory
as well as a master summary in the head directory. In the data subdirectory
plots of the data will be generated.

@author: gerardjb
"""

#%% import libraries
from tkinter import Tk, filedialog
import numpy as np
import pickle
import cv2
import matplotlib.pyplot as pl
from matplotlib import cm
import pandas as pd
import os
import csv
import re

#%% Select directory with animal data
root = Tk()
root.withdraw()
root.attributes('-topmost', True)
pathMaster = filedialog.askdirectory()

#%% Mask out the ROI to analyze, plot
# select eye ROI
def pickROI(imArray):
    pl.imshow(imArray.mean(axis=0), cmap=pl.cm.Greys_r)
    pts = pl.ginput(timeout=-1, n=-1)
    pl.close()
    
    # convert points to mask
    pts = np.asarray(pts, dtype=np.int32)
    roi = np.zeros(imArray[0].shape, dtype=np.int32)
    roi = cv2.fillConvexPoly(roi, pts, (1,1,1), lineType=cv2.LINE_AA)
    roi = roi.astype(np.float)
    return roi   

#%% initializing the image stack and parsing the image stack
#unpickling the bytes stream from mjpg and converting to np array shape [nIm,wid,height]
def mjpg2array(filename):   
    #Open and unpickle the bytes file
    filehand = open(filename,'rb')
    stream = []
    while 1:
        try:
            stream.append(pickle.load(filehand))
        except EOFError:
            break
    filehand.close()
    #Removing the extra list packaging, getting nImages points
    stream = [x for l in stream for x in l]
    lists = [list(t) for t in zip(*stream)]
    ts = np.array(lists[0])*1000#convert to millis
    stream = lists[1]
    nIm = len(stream)
    
    #Reading through the binary file to parse image data
    idx = 0 #for buidling the np image array
    for img in stream:
        #grab frame start and end on hex stream
        a = img.find(b'\xff\xd8')
        b = img.find(b'\xff\xd9')
        if a != -1 and b != -1:
            jpg = img[a:b+2]
            #stream = stream[b+2:]
            data = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            
            if idx==0:
                #For plot of line scan
                sizeWH = data.shape
                #Full output array
                mov = np.empty([int(sizeWH[0]),int(sizeWH[1]),nIm],dtype=np.uint8)
                mov[:,:,0] = data
            else:
                mov[:,:,idx] = data
            idx += 1
            #cv2.imshow('i', data)
            #if cv2.waitKey(1)==27:
                #exit(0)
        elif a==-1 or b==-1:
            pass
    
    # permute the data to put time element first
    imArray = np.transpose(mov,(2,0,1))
    return imArray,ts

#%Takes arduino data frame and trial idx as inputs	
def parseRotary(df,idx):
	#Wheel information for converting pulse/time to cm/s
	circ = 15.24*np.pi#Dimensions of Aeromat roller
	counts = 2000*4
	count2cm = circ/counts
	
	#Get timing of trials and rate arduino polls rotary encoder
	startIdxs = np.append(np.where(df.event=='startTrial')[0],df.index[-1])
	subDf = df[(df.index>startIdxs[idx]) & (df.index<startIdxs[idx+1]) & (df.event=='rotary')]
	time = (subDf.millis.astype('int') - int(df.millis[startIdxs[idx]]))#in ms
	pollrate = np.mean(np.diff(time))
	
	#Convert counts to cm/s
	wheelVel = subDf.value*count2cm/(pollrate/1000)
	wheelVel[wheelVel>1000] = np.nan
	
	return wheelVel,time


#%% Choose a directory
#All camera and timestamp files
subDirs = next(os.walk(pathMaster))[1]
print('Available datasets:')
for idx,n in enumerate(subDirs):
    print('\t{}\t{}'.format(idx,n))

#%%
#grabbing the files and metadata from the chosen directory for analysis
subDirIdx = range(len(subDirs))#

#Loop over all directories in pathMaster directory
for thisSubDir in subDirIdx:
    path = os.path.join(pathMaster,subDirs[thisSubDir])
    files = [(d,f) for d,_,fs in os.walk(path) for f in fs if f.endswith('.data')]
	#pass if no data files
    if not files:
        continue
    #for sorting
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    im_files = sorted([os.path.join(*i) for i in files],key=alphanum_key)
    
    #Set local and summary save directories
    localDir = os.path.join(path,'Summary')
    if not os.path.exists(localDir):
            os.makedirs(localDir)
    headDir = os.path.join(pathMaster,'Summary')
    if not os.path.exists(headDir):
        os.makedirs(headDir)
    
    #Trial structure and metadata
    txt_files = sorted([(d,f) for d,_,fs in os.walk(path) for f in fs if f.endswith('.txt')])
    txt_files = [os.path.join(*i) for i in txt_files]
    with open(txt_files[0]) as txtfilehand:
        headers = next(csv.reader(txtfilehand))
        headers = dict(x.split('=') for x in headers[0].split(';') if '=' in x)
        dataR = pd.read_csv(txtfilehand,header=0) #column heads as millis, events, value
    txtfilehand.close()
    #Trial types
    trialTypes = ('CS','US','CS_US')
    trialTypes = dataR['event'][dataR['event'].isin(trialTypes)].values
    #ISI inter-start intervals
    ISI = np.diff(dataR['millis'][dataR['event']=='startTrial'].apply(pd.to_numeric))
    ISI = np.insert(ISI,0,0) #ISI for first trial is 0       
    
    #Extracting subject, date, session from directory header
    sessionInfo = subDirs[thisSubDir].split('_')
    animalID = sessionInfo[0]
    date = sessionInfo[1]
    
    #%% pick roi
    imPickArray,time = mjpg2array(im_files[0])
    #If ROI already selected, use saved version
    if os.path.exists(os.path.join(localDir,'_'.join(sessionInfo)+'roi.npy')):
        roi = np.load(os.path.join(localDir,'_'.join(sessionInfo)+'roi.npy'))
    else:
        pl.close('all')
        roi = pickROI(imPickArray)
        
    #%% getting data for each analyzed trial
    data = pd.DataFrame()
    for idx in range(len(files)):
        #Initialize data frame to hold this trial's data
        newData = pd.DataFrame()
        
        #Read image data, process
        imArray,time = mjpg2array(im_files[idx])
        tr = imArray.reshape([len(imArray), -1]) @ roi.reshape(np.product(roi.shape))
        
       
        #add eyetrace to the new dataframe and append to full dataframe
        newData['time'] = time
        newData['eyetrace'] = tr
        newData['trial'] = idx
        #add session and trial info to the dataframe
        newData.insert(0,'date',date)
        newData.insert(0,'animalID',animalID)
        newData['trialType'] = trialTypes[idx]
        #Concatenate
        frames = [data,newData]
        data = pd.concat(frames)
        print('_'.join(sessionInfo)+' '+str(idx))
    
    
    #%% pull pi Master-specific metadata
    csTime = float(headers['preCSdur'])#number of millis at which cs starts
    csusInt = float(headers['CS_USinterval'])#length of cs alone
    camFreq = 100#frames per second for picamera #TIMES 2 FOR MR. NYQUIST!!!!!
    pad = [csTime,500]#ms pad before and after cs
    timeBins = np.arange(-pad[0]+csTime,pad[1]+csTime+csusInt,1)
    #Need parser for CS v. US trials
    
    #%% making some summary plots
    #Initializing directory to save figures
    localDir = os.path.join(path,'Summary')
    if not os.path.exists(localDir):
            os.makedirs(localDir)
            
    #this is a single trial with its time series data
    uniTrials = data.trial.unique()
    colors = cm.jet(np.linspace(0,1,len(uniTrials)))
    
    #for holding clips of the eyetrace and rotary data
    slices = np.zeros((len(uniTrials),len(timeBins)))
    slicesR = np.zeros((len(uniTrials),len(timeBins)))
	
    #loop and plot individual trials
    pl.figure(1)
    pl.figure(2)
    for idx in range(len(uniTrials)):
        thisT = np.array(data['time'][data['trial']==uniTrials[idx]],dtype=float)
        thisEye = np.array(data['eyetrace'][data['trial']==uniTrials[idx]],dtype=float)
        thisRot, thisT_rot = parseRotary(dataR,idx)
    	
        if any(thisT>0):
            interpEye = np.interp(timeBins,thisT[thisT>0],thisEye[thisT>0])
            interpR = np.interp(timeBins,thisT_rot[thisT_rot>0],thisRot[thisT_rot>0])
        else:
            interpEye = np.empty((len(timeBins)))
            interpEye[:] = np.nan
            interpR = np.interp(timeBins,thisT_rot[thisT_rot>0],thisRot[thisT_rot>0])
            print(idx)
        pl.figure(1)
        pl.plot(timeBins-csTime,interpEye,linewidth=0.3,color=colors[idx])
        slices[idx] = interpEye
		
        pl.figure(2)
        pl.plot(timeBins-csTime,interpR,linewidth=0.3,color=colors[idx])
        slicesR[idx] = interpR

    pl.figure(1)
    n,x = pl.ylim()
    pl.vlines(csusInt, n, x, linestyle='--', color='black')
    pl.vlines(0, n, x, linestyle='--', color='black')
    pl.xlabel('time from CS onset (ms)')
    pl.ylabel('Eyelid (a.u.)')
    pl.title('_'.join(sessionInfo))
    pl.tight_layout()
    pl.savefig(os.path.join(localDir,'_'.join(sessionInfo)+'traces.jpg'))
	
    pl.figure(2)
    n,x = pl.ylim()
    pl.vlines(csusInt, n, x, linestyle='--', color='black')
    pl.vlines(0, n, x, linestyle='--', color='black')
    pl.xlabel('time from CS onset (ms)')
    pl.ylabel('Wheel speed (cm/s)')
    pl.title('_'.join(sessionInfo))
    pl.tight_layout()
    pl.savefig(os.path.join(localDir,'_'.join(sessionInfo)+'rotarytraces.jpg'))
    
    pl.close('all')
	
    #Show an average of the trial type of choice with std bars
    trialKinds = np.array(['CS_US','CS','US'])
    colors = np.array(['blue','red','green'])
    pl.figure(1)
    pl.figure(2)
    idx = 0
    legStr = []
    legHand = []
    legStrR = []
    legHandR = []
    for kind in trialKinds:
        if not sum(trialTypes==kind)==0:
            subSlices = slices[trialTypes[uniTrials]==kind]
            mean = np.nanmean(subSlices,axis=0)
            err = np.nanstd(subSlices,axis=0)
            subSlicesR = slicesR[trialTypes[uniTrials]==kind]
            meanR = np.nanmean(subSlicesR,axis=0)
            errR = np.nanstd(subSlicesR,axis=0)
            pl.figure(1)
            h, = pl.plot(timeBins-csTime,mean,color=colors[trialKinds==kind][0])
            legHand.append(h)
            pl.fill_between(timeBins-csTime, mean-err, mean+err, alpha=.1, color=colors[trialKinds==kind][0], lw=0)
            legStr.append(kind)
            pl.figure(2)
            h, = pl.plot(timeBins-csTime,meanR,color=colors[trialKinds==kind][0])
            legHandR.append(h)
            pl.fill_between(timeBins-csTime, meanR-errR, meanR+errR, alpha=.1, color=colors[trialKinds==kind][0], lw=0)
            legStrR.append(kind)
            idx+=1
    pl.figure(1)
    n,x = pl.ylim()
    pl.vlines(csusInt, n, x, linestyle='--', color='black')
    pl.vlines(0, n, x, linestyle='--', color='black')
    pl.xlabel('time from CS onset (ms)')
    pl.ylabel('Average eyelid position (a.u.)')
    pl.title('_'.join(sessionInfo))
    pl.legend(legHand,legStr)
    pl.tight_layout()
    pl.savefig(os.path.join(localDir,'_'.join(sessionInfo)+'avgTraces.pdf'))
	
    pl.figure(2)
    n,x = pl.ylim()
    pl.vlines(csusInt, n, x, linestyle='--', color='black')
    pl.vlines(0, n, x, linestyle='--', color='black')
    pl.xlabel('time from CS onset (ms)')
    pl.ylabel('Average speed (cm/s)')
    pl.title('_'.join(sessionInfo))
    pl.legend(legHandR,legStrR)
    pl.tight_layout()
    pl.savefig(os.path.join(localDir,'_'.join(sessionInfo)+'avgTracesRotary.pdf'))
    
    #Make a heatmap of the time slices
    xAxis = [timeBins[0]-csTime,timeBins[-1]-csTime]
    pl.figure()
    imgHand = pl.imshow(slices,\
                        cmap='Greys_r',extent=[xAxis[0],xAxis[1],len(uniTrials-1),0],aspect = 'auto')
    pl.colorbar()
    n,x = pl.ylim()
    pl.vlines(csusInt, n, x, linestyle='--', color='red')
    pl.vlines(0, n, x, linestyle='--', color='red')
    pl.xlabel('time from CS onset (ms)')
    pl.ylabel('trial number')
    pl.title('_'.join(sessionInfo))
    pl.tight_layout()
    pl.savefig(os.path.join(localDir,'_'.join(sessionInfo)+'tracesImg.jpg'))
    
    #If analyzing multiple files, close these figures
    #if len(subDirIdx)>1:
        #pl.close('all')
        
    #%% Save dataframes in this directory and in the head directory
    #Saving to local directory
    data.to_hdf(os.path.join(localDir,'_'.join(sessionInfo)+'data.h5'),key = 'df') #camera dataframe
    dataR.to_hdf(os.path.join(localDir,'_'.join(sessionInfo)+'dataR.h5'),key = 'df') #metadata dataframe
    np.save(os.path.join(localDir,'_'.join(sessionInfo)+'roi'),roi)
    with open(os.path.join(localDir,'_'.join(sessionInfo)+'trialTypes.csv'),'w') as f:
        write = csv.writer(f)
        write.writerow(zip(trialTypes))
    f.close()
    
    #Saving to summary directory
    data.to_hdf(os.path.join(headDir,'_'.join(sessionInfo)+'data.h5'),key = 'df') #camera dataframe
    dataR.to_hdf(os.path.join(headDir,'_'.join(sessionInfo)+'dataR.h5'),key = 'df') #metadata dataframe
    np.save(os.path.join(headDir,'_'.join(sessionInfo)+'traces.npy'),slices)
