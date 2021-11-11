import PySimpleGUI as sg
from picamera import PiCamera
import RPi.GPIO as GPIO
import pivideostream as pvid
import cv2
import numpy as np
import time
import sys
import signal
from arduinoRig import arduinoRig

    
####Build the GUI####
sg.theme("DarkAmber")#BluePurple also has a nice asthetic

###Define the window layout
camera_layout = [
    ##Camera control and display panels
    [sg.Image(filename="", key="-IMAGE-",size=(300,240))],
    [sg.Button("Stream",size=(9,1)),sg.Button("End Stream",size=(9,1)),
    sg.Button("Save Stream",size=(9,1)),sg.Button("End Recording",size=(9,1))],
    #[sg.Button("End Program", size=(10, 1))]
]

trial_layout = [
    ##Arduino, file name, and session controls
    [sg.Button("Start Session",size=(14,1),button_color=('white','springgreen4')),
     sg.Button("Stop Session",size=(14,1),button_color=('white','firebrick3'))],
    [
        sg.Text("Animal ID"),
        sg.Input(size=(25,1),key="Animal"),
        sg.Button('Set',bind_return_key=True)
    ],
    [
        sg.Text("Session type"),
        sg.Radio('DTSC',"RADIO",default=True,key="DTSC"),
        sg.Radio('DEC',"RADIO",key="DEC")
    ],
    [sg.HSeparator()],
    [sg.Column([
        [sg.T("Number trials"),sg.Input(size=(10,1),key="numTrial",default_text="100")],
        [sg.T("ITI low (ms)"),sg.Input(size=(10,1),key="ITIlow",default_text="5000")],
        [sg.T("Percent CS"),sg.Input(size=(10,1),key="percentCS",default_text="10")],
        [sg.T("CS duration (ms)"),sg.Input(size=(10,1),key="CSdur",default_text="250")],
        [sg.T("Pre-CS duration (ms)"),sg.Input(size=(10,1),key="preCSdur",default_text="100")]
    ]),
    sg.Column([
        [sg.T("Trial duration (ms)"),sg.Input(size=(10,1),key="trialDur",default_text="1000")],
        [sg.T("ITI high (ms)"),sg.Input(size=(10,1),key="ITIhigh",default_text="20000")],
        [sg.T("Percent US"),sg.Input(size=(10,1),key="percentUS",default_text="0")],
        [sg.T("US duration (ms)"),sg.Input(size=(10,1),key="USdur",default_text="50")]
    ],vertical_alignment='top')
    ],
    [sg.Button("Upload to Arduino"),sg.Button("Current Arduino settings")]
]

exit_layout = [
    [sg.Button("End Program",size=(30,2))]
]

##full GUI layout
layout = [
    
    [
        [sg.Frame("Camera controls",camera_layout,title_location='n',element_justification='c'),
        sg.Frame("Arduino session controls",trial_layout,title_location='n',element_justification='l')],
        exit_layout
    ]
]

####Create the window, arduinoRig, and piStream####
window = sg.Window("Associative Learning control GUI", layout)
rig = arduinoRig()
vs = None


####Handling the GUI, rig, and piCamera####
#Loop booleans and variables
streaming = False#state of camera output
frame = None#current frame for output to GUI video
dispNow = True#to display current fame on GUI video
lastpicTime = 0#timing when next frame should be output to GUI video

#What to do if keyboard interrupt called
def signal_handler(sig, frame):
    if vs is not None:
        vs.end()
        print("vs.end()")
    rig.end()
    print("\nProgram ended")
    sys.exit(0)
signal.signal(signal.SIGINT,signal_handler)

####GUI read loop
while True:

    #Get whatever input the user applied to GUI
    event, values = window.read(timeout=0)
    
    #If the camera is on, check if we need to update GUI frame
    if streaming:
        now = time.perf_counter()
        dispTime = now - lastpicTime
        #Only update frame once every ~20 ms
        if dispTime>0.05:
            frame = vs.read()
            lastpicTime = time.perf_counter()
    
    ##Button options, left panel
    if event == "End Program" or event == sg.WIN_CLOSED:
        break
    elif event == "Stream":
        #Only call camera first time stream activated
        if not streaming:
            if vs is None:
                vs = pvid.piCamHandler()
            else:
                vs.reset_cam()
            streaming = True
            print("Start stream")
        else:
            print("Camera already streaming!")
    elif event == "End Stream":
        if vs is not None:
            vs.endStream()
        streaming = False
        frame = None
        print("End Stream")
    elif event == "Save Stream":
        if streaming:
            if not vs.saving.value:
                vs.guiStartRecording()
                print("Save Stream")
            elif vs.saving.value:
                print("Stream is already recording")
        else:
            print("No stream open")
    elif event == "End Recording":
        if streaming and vs.saving.value:
            vs.guiStopRecording()
            print("End Recording")
        else:
            print("Not recording")
    
    ##Button options right panel
    elif event == "Start Session":
        rig.startSession()
        while not rig.fnameReady:
            pass
        fStub = rig.getFstub()
        if vs is not None:
            vs.passFstub(fStub)
    elif event == "Stop Session":
        rig.stopSession()
    elif event == "Set":
        rig.animalID = values['Animal']
        print("Set animalID: ",values['Animal'])
    elif event == "Upload to Arduino":
        if values['DTSC']:
            rig.settrial('isDTSC',1)
        else:
            rig.settrial('isDTSC',0)
        for item in values.items():
            if item[0] not in ['Animal','DTSC','DEC']:
                rig.settrial(item[0],item[1])
                time.sleep(0.001)
    elif event == "Current Arduino settings":
        rig.GetArduinoState()
    
    ##Process and display the current frame capture in GUI if streaming
    if streaming and frame is not None:
        if len(frame)>0:
            #imgbytes = frame
            data = cv2.resize(cv2.imdecode(np.frombuffer(frame, dtype=np.uint8), cv2.IMREAD_GRAYSCALE),(300,240))
            imgbytes = cv2.imencode('.png',data)[1].tobytes()
            window["-IMAGE-"].update(data=imgbytes)
        frame = None
    
    
    
##Do this when the program is ended
window.close()
if vs is not None:
    vs.end()
    print("vs.end()")
rig.end()
print("rig.end()")
print('Program ended')
