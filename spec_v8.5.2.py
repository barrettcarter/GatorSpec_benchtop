print('Loading modules')
import seabreeze.spectrometers as sb
import datetime, json
import matplotlib.pyplot as plt
from gpiozero import PWMOutputDevice as PWM
from tkinter import (Tk, Frame, Button, Entry, Label)
import numpy as np
import pandas as pd
  
print('...done loading modules')


################################################# FUNCTIONS

# FUNCTION THAT READS PARAMETERS
def readPars(aFN):
    aFL=open(aFN,'r')                       # OPEN FILE, READ ONLY
    iPars=aFL.readlines()                   # READ ALL LINES IN THE FILE
    aFL.close()                             # CLOSE FILE
    print(len(iPars),'parameters found')
    parDict={} # 
    for p in iPars:                         # ...FOR EVERY LINE
        p=p.strip()                         # ...STRIP OUT SPACES
        #print(p,len(p))
        if p=='' or p[0]=='#' or len(p)==0: # IGNORE COMMENTS, OR BLANK LINES
            pass
        else:
            parDict[p.split('=')[0]]=p.split('=')[1]    # SPLIT THE PARAMETER BY THE '=' SIGN, STORES PARAMS IN DICTIONARY
    print(parDict)
    return(parDict)                         # RETURN DICTIONARY TO CALLING FUNCTION

def writeCSV(iWVL,iSPEC,oFN):
    oFL=open(oFN,'w')
    oFL.write('WVL,INT\n')
    aItems=len(iWVL)
    for i in range(aItems):
        oStr=','.join([str(x) for x in [iWVL[i],iSPEC[i]]])
        oFL.write(oStr+'\n')
    oFL.close()

ref_col = False

def analyze_ref():

    # Variables to be used in function and elsewhere
    global intTime
    global sINT_ref
    global sWVL
    global ref_col
    
    sample_name = 'ref'
    meas_ang = measurement_angle_entry.get()
    datetime_an = datetime.datetime.now().isoformat()
    
    # Collect spectrum
    intTime = int(integration_time_entry.get())*1000 # integration time from entry converted to microseconds
    lightSource = PWM(17,initial_value=0,frequency=100)  # Activate light source
    highIntensity = True
    # To make sure integration time is not too high
    while highIntensity == True:
        print('Intensity too high. Lowering integration time to')
        intTime=0.9*intTime
        spec.integration_time_micros(intTime)   # SET INTEGRATION TIME
        print(intTime)
        lightSource.value = 0.1 
        sINT=spec.intensities(correct_nonlinearity=True)        # CONDUCT NONLINEARITY AND DARK CORRECTIONS
        lightSource.value = 0
        if max(sINT)<16500:
            highIntensity = False

    intTimeStr=str(intTime)    
    sINT_ref = sINT
    
    sWVL=spec.wavelengths() # GET WAVELENGTHS FROM SPECTROMETER

    # Write spectrum to csv and json files
    oSpecFN=('spec_'+sample_name+"_"+meas_ang+'_'+
             intTimeStr+'_'+parDict['locCode']+'_'+datetime_an+'.json') # CREATE OUTPUT JSON FILE FOR SPECTRA
    oSpecFNcsv=oSpecFN.replace('.json','.csv')
    oSpecFL=open(specDir+oSpecFN,'w')
    print(oSpecFN)
    dSpec={'locCode':parDict['locCode'],'sWVL':sWVL.tolist(),'sINT':sINT.tolist()}  # GET SPECTRA FROM SPECTROMETER
    json.dump(dSpec,oSpecFL)                          # SAVE IN JSON FILE
    oSpecFL.close()                                         # WRITE JSON FILE
    writeCSV(sWVL,sINT,specDir+oSpecFNcsv)
        
    # Plot reference spectrum
    plt.figure()
    plt.plot(sWVL,sINT, label = 'reference')
    plt.xlabel('wavelength (nm)')
    plt.ylabel('intensity')
    plt.legend(loc='upper right')
    plt.ylim([0,16000])
    plt.show(block=False)
    print('Reference collected.')
    ref_col = True

def analyze_sample_abs():

    if ref_col == False:
        print('Need reference.')
        return
    
    sample_name = sample_name_entry.get()
    filtered = sample_filter_entry.get()
    meas_ang = measurement_angle_entry.get()
    date_col = collection_date_entry.get()
    datetime_an = datetime.datetime.now().isoformat()
    date_an = datetime_an.split('T')[0]
    time_an = datetime_an.split('T')[1]
    
    # Get spectrum
    lightSource = PWM(17,initial_value=0,frequency=100)  # Activate light source
    intTimeStr=str(intTime)
    spec.integration_time_micros(intTime)   # SET INTEGRATION TIME
    print(intTime)
    lightSource.value = 0.1 
    sINT=spec.intensities(correct_nonlinearity=True)        # CONDUCT NONLINEARITY AND DARK CORRECTIONS
    lightSource.value = 0

    # Compare to reference
    if max(sINT)/max(sINT_ref)<0.9 or max(sINT)/max(sINT_ref)>1.1:
        print('WARNING:Reference and sample may not be compatible!')

    # Write spectrum to csv and json
    
    oSpecFN=('spec_'+sample_name+"_"+filtered+'_'+date_col+'_'+meas_ang+'_'+
             intTimeStr+'_'+parDict['locCode']+'_'+datetime_an+'.json') # CREATE OUTPUT JSON FILE FOR SPECTRA
    oSpecFNcsv=oSpecFN.replace('.json','.csv')
    oSpecFL=open(specDir+oSpecFN,'w')
    print(oSpecFN)
    dSpec={'locCode':parDict['locCode'],'sWVL':sWVL.tolist(),'sINT':sINT.tolist()}  # GET SPECTRA FROM SPECTROMETER
    json.dump(dSpec,oSpecFL)                          # SAVE IN JSON FILE
    oSpecFL.close()                                         # WRITE JSON FILE
    writeCSV(sWVL,sINT,specDir+oSpecFNcsv)
        
    # Plot the sample and reference spectra
    plt.figure()
    plt.plot(sWVL,sINT, label = 'sample')
    plt.plot(sWVL,sINT_ref, label = 'reference')
    plt.xlabel('wavelength (nm)')
    plt.ylabel('intensity')
    plt.legend(loc='upper right')
    plt.ylim([0,16000])
    plt.show(block=False)
    print('Sample analyzed.')
    
    # Calculate absorbance
    # ref_spec = np.fromstring(sINT_ref)
    # sam_spec = np.fromstring(sINT)

    # absorbance = np.log10(ref_spec/sam_spec)
    
    absorbance = np.log10(sINT_ref/sINT)
    
    # Plot absorbance spectrum
    plt.figure()
    plt.plot(sWVL,absorbance,label = sample_name)
    plt.title('absorbance')
    plt.xlabel('wavelength (nm)')
    plt.ylabel('absorbance')
    plt.legend(loc='upper right')
    plt.show(block=False)
    print('Absorbance calculated')
    
    new_row = [sample_name,filtered,date_col,date_an,time_an,intTime,meas_ang]
    new_row.extend(absorbance)
    row_df = pd.DataFrame(data = [new_row])
    row_df.to_csv(absDir+'abs_df.csv',mode = 'a',header=False,index=False)
    print('Absorbance recorded')
    
    
################################################# DEFAULTS

parFile='/home/pi/WQspec/specPars_v2.txt'  # LOCATION OF PARAMETER FILE
specDir='/home/pi/WQspec/spectra/'      # LOCATION WHERE RAW SPECTRA ARE SAVED
absDir='/home/pi/WQspec/abs/'      # LOCATION WHERE ABSORBANCE SPECTRA ARE SAVED


############################### Read parameters

print('Reading parameters')
parDict=readPars(parFile)

################################################# PROCESS

print('checking if spectrometer is connected...')
devices=sb.list_devices()                                   # FIND SPECTROMETER
if len(devices)>0:
    spec=sb.Spectrometer(devices[0])
    print(len(devices),'devices found!',spec)

else:
        print('Spectrometer not found.')


##### Making the GUI

root = Tk()
root.geometry("400x450")
root.title('GatorSpec - Benchtop')
 
frame = Frame(root)
frame.pack()

sample_name_lab = Label(frame,text ='Sample Name')
sample_name_lab.pack(padx = 5, pady = 5)
 
sample_name_entry = Entry(frame, width = 20)
sample_name_entry.insert(0,'e.g., "sweetwater"')
sample_name_entry.pack(padx = 5, pady = 5)

collection_date_lab = Label(frame,text ='Collection Date (MM-dd-YYYY)')
collection_date_lab.pack(padx = 5, pady = 5)
 
collection_date_entry = Entry(frame, width = 20)
collection_date_entry.insert(0,'e.g., "11-04-1991"')
collection_date_entry.pack(padx = 5, pady = 5)

sample_filter_lab = Label(frame,text ='Filtered (True or False)')
sample_filter_lab.pack(padx = 5, pady = 5)

sample_filter_entry = Entry(frame, width = 20)
sample_filter_entry.insert(0,'e.g., "True"')
sample_filter_entry.pack(padx = 5, pady = 5)

measurement_angle_lab = Label(frame,text ='Measurement Angle')
measurement_angle_lab.pack(padx = 5, pady = 5)
 
measurement_angle_entry = Entry(frame, width = 20)
measurement_angle_entry.insert(0,'e.g., "0deg"')
measurement_angle_entry.pack(padx = 5, pady = 5)

integration_time_lab = Label(frame,text ='Integration Time (ms)')
integration_time_lab.pack(padx = 5, pady = 5)

integration_time_entry = Entry(frame, width = 20)
integration_time_entry.insert(0,'e.g., "25"')
integration_time_entry.pack(padx = 5, pady = 5)
 
ref_Button = Button(frame, text = "Collect Reference", command = analyze_ref)
ref_Button.pack(padx = 5, pady = 5)

sample_Button = Button(frame, text = "Analyze Sample", command = analyze_sample_abs)
sample_Button.pack(padx = 5, pady = 5)
 
root.mainloop()
