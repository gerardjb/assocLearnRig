#Control and reading of the primary Arduino
import serial
import time
import os.path
from threading import Thread
import threading
import sys

     
#
#Serial and initialization of object settings
serialStr = '/dev/ttyACM0' #
altSerialStr = '/dev/ttyACM1' #alternative Arduino port

options = {}
options['serial'] = {}
options['serial']['port'] = serialStr
options['serial']['baud'] = 115200 #57600

trial = {}
trial['isDTSC'] = 1 #1 = DTSC, 0  = DEC
trial['fStub'] = ''
trial['filePath'] = '/media/usb/'
trial['fileName'] = ''
trial['sessionNumber'] = 0
trial['sessionDur'] = 0 # (trialDur * numTrial)

trial['trialNumber'] = 0
trial['trialDur'] = 5000
trial['numTrial'] = 3

trial['ITIlow'] = 5000 #ms, lowest ITI from random draw
trial['ITIhigh'] = 20000 #ms, highest ITI
trial['preCSdur'] = 2000 #ms, imaged time prior to stim presentation
trial['CSdur'] = 350 #ms, duration of CS
trial['USdur'] = 50 #ms, duration of US
trial['CS_USinterval'] = 0 #ms (CSdur - USdur)
trial['percentUS'] = 0 #percent of trials with US only presentation
trial['percentCS'] = 10 #percent of trials with CS only presentation

trial['useMotor'] = 'motorOn' #{motorOn, motorLocked, motorFree}
trial['motorSpeed'] = 500 #steps/sec

trial['sessionDur'] = trial['numTrial'] * trial['trialDur']
trial['CS_USinterval'] = trial['CSdur'] - trial['USdur']

      
class arduinoRig():
    def __init__(self):
        self.animalID = 'noname'
        self.trial = trial
        self.fnameReady = False
                
        try:
            self.ser = serial.Serial(options['serial']['port'], options['serial']['baud'], timeout=0.25)
        except:
            options['serial']['port'] = altSerialStr
            try:
                self.ser = serial.Serial(options['serial']['port'], options['serial']['baud'], timeout = 0.25)
            
            except:
                self.ser = None
                print("======================================================")
                print("ERROR: DTSC did not find serial port '", options['serial']['port'], "'")
                print("======================================================")

                
        #serial is blocking. we need serial reads druing trials to run in a separate thread so we do not block user interface
        self.kill_flag = False
        self.flushing = False
        self.trialRunning = 0
        thread = Thread(target=self.background_thread, args=())
        thread.daemon  = True; #as a daemon the thread will stop when *this stops
        thread.start()
        self.exit_event = threading.Event()
            
        #save all serial data to file, set in setsavepath
        self.savepath = '/media/usb/'
        self.filePtr = None
        
        self.arduinoStateList = None #grab from arduino at start of trial, write into each epoch file
        
    def background_thread(self):
        '''Background thread to continuously read serial. Dumps to file during a trial'''
        while True:
            if self.trialRunning:
                string = self.ser.read(self.ser.in_waiting)
                if len(string)>0:
                    string = string.decode('utf-8')
                    print(string,end='')
                    sys.stdout.write('')
                    self.NewSerialData(string)
                if self.flushing:
                    self.trialRunning = False
                    self.flushing = False
                if self.exit_event.is_set():
                    break
            time.sleep(0.05)

    def NewSerialData(self, string):
        '''
        we have received new serial data. Write to the file
        special case is when we receive startSession or stopSession
        '''
        #we want 'millis,event,val', if serial data does not match this then do nothing
        #try:
        if len(string)>0:
            #save to file
            if self.filePtr:
                self.filePtr.write(string)
            
            if 'stopSession' in string:
                self.flushing = True
                print('arduinoRig.NewSerialData() detected session stopping')
                
            if not self.trialRunning and self.filePtr:
                self.filePtr.close()
                self.filePtr = None
                # self.stopSession()

    def startSession(self):
        if self.trialRunning:
            print('Warning: session is already running')
            return 0
            
        self.trial['sessionNumber'] += 1
        self.trial['trialNumber'] = 0
        
        self.newtrialfile(0)
        
        self.trialRunning = 1
        self.ser.write('<startSession>'.encode())#
        print('arduinoRig.startSession()')
        
        return 1
        
    def startTrial(self):
        if not self.trialRunning:
            print('Warning: startTrial() trial is not running')
            return 0
            
        self.trial['trialNumber'] += 1
                
        self.newtrialfile(self.trial['trialNumber'])
        
        return 1
        
    def stopSession(self):
        if self.filePtr:
            self.filePtr.close()
            self.filePtr = None
            
        self.trialRunning = 0

        self.ser.write('<stopSession>'.encode())
        print('arduinoRig.stopSession()')
        
        self.kill_flag = False
        self.fnameReady = False
        
    def newtrialfile(self, trialNumber):
        # open a file for this trial
        dateStr = time.strftime("%Y%m%d")
        timeStr = time.strftime("%H%M%S")
        datetimeStr = dateStr + '_' + timeStr

        sessionStr = ''
        sessionFolder = ''
        if self.animalID and not (self.animalID == 'default'):
            sessionStr = self.animalID + '_'
            sessionFolder = self.animalID + '_' + dateStr
        
        thisSavePath = self.savepath + dateStr + '/'
        if not os.path.exists(thisSavePath):
            os.makedirs(thisSavePath)
        thisSavePath += sessionFolder + '/'
        if not os.path.exists(thisSavePath):
            os.makedirs(thisSavePath)
        
        sessionFileStub = sessionStr + datetimeStr
        sessionFileName = sessionFileStub + 'rig.txt'
        sessionFilePath = thisSavePath + sessionFileName
        
        self.trial['fStub'] = thisSavePath + sessionFileStub
        self.trial['filePath'] = thisSavePath
        self.trial['fileName'] = sessionFileName
        
        #get arduino parameters and let gui know fStub is ready
        if trialNumber==0:
            self.arduinoStateList = self.GetArduinoState()
            self.fnameReady = True

        self.filePtr = open(sessionFilePath, 'w')

        self.filePtr.write('session='+str(self.trial['sessionNumber'])+';')
        self.filePtr.write('trial='+str(self.trial['trialNumber'])+';')
        self.filePtr.write('date='+dateStr+';')
        self.filePtr.write('time='+timeStr+';')
        
        for state in self.arduinoStateList:
            self.filePtr.write(str(state) + ';')
            
        self.filePtr.write('\n')
        
        #
        #header line 2 is column names
        self.filePtr.write('millis,event,value\n')

        #
        #each call to self.NewSerialData() will write serial data to this file
        
    def settrial(self, key, val):
        '''
        set values for arduino from param dict
        '''
        if self.trialRunning:
            print('Warning: trial is already running')
            return 0

        val = str(val)
        key = str(key)
        
        if key in self.trial:
            print("=== dtsc.settrial() key:'" + key + "' val:'" + val + "'")
            self.trial[key] = val
            serialCommand = '<settrial,' + key + ',' + val +'>'
            self.ser.write(serialCommand.encode())
            self.emptySerial()
        else:
            print('\tERROR: arduinoRig:settrial() did not find', key, 'in trial dict')
        
    def GetArduinoState(self):
        if self.trialRunning:
            print('Warning: trial is already running')
            return 0

        self.ser.write('<getState>'.encode())
        print("===Arduino Settings===")
        stateList = self.emptySerial()
        print("=========Done=========")
        
        return stateList
        
    def emptySerial(self):
        if self.trialRunning:
            print('Warning: trial is already running')
            return 0

        theRet = []
        line = self.ser.readline()
        lastLine = ''
        i = 0
        while line:
            line = line.rstrip().decode()
            if line != 'getState' and line != lastLine:
                print(line)
                theRet.append(line)
            lastLine = line
            line = self.ser.readline()
            i += 1
        return theRet
        
    def setserialport(self, newPort):
        if self.trialRunning:
            print('Warning: trial is already running')
            return 0

        if os.path.exists(newPort) :
            print('setserialport() port', newPort, 'exists')
            options['serial']['port'] = newPort
            return 1
        else:
            print('setserialport() port', newPort, 'does not exist')
            return 0
            
    def checkserialport(self):
        if self.trialRunning:
            print('Warning: trial is already running')
            return 0

        port = options['serial']['port']
        print('checking', port)
        if os.path.exists(port) :
            print('exists')
            return 1, port
        else:
            print('does not exist')
            return 0, port
            
    def checkarduinoversion(self):
        if self.trialRunning:
            print('Warning: trial is already running')
            return 0

        self.ser.write('<version>'.encode())
        self.emptySerial()
        
    def setsavepath(self, string):
        self.savepath = string
        
    def getFstub(self):
        return self.trial['fStub']
        
    def end(self):
        self.kill_flag = True
        self.stopSession()
        self.exit_event.set()
        if "self.fileptr" in locals():
            self.fileptr.close()
