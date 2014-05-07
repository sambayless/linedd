#!/usr/bin/env python3
'''
Created on 2014-04-13

@author: sam
'''


import math
import os
import shutil
import sys
import tempfile

def usage():
    print("Usage: " + sys.argv[0] + " <input file> <output file> command\n")
    sys.exit(0)

command=""
first=0
last=-1
expect=None
backward=False
linear=False
use_signal=False
abortOnExistingFile=False
allowOverwritingBackups=True

while(len(sys.argv)>4):
    if(sys.argv[1]=='--help'):
        usage()
    elif(sys.argv[1]=='-h'):
        usage()       
    elif(sys.argv[1]=='--backward'):
        backward=True
        sys.argv.pop(1)
    elif(sys.argv[1]=='--expect'):
        expect=int(sys.argv[2])
        sys.argv.pop(1)
        sys.argv.pop(1)
    elif(sys.argv[1]=='--signal'):
        use_signal=True
        sys.argv.pop(1)
        
    elif(sys.argv[1]=='--linear'):
        linear=True
        sys.argv.pop(1)               
    
    elif(sys.argv[1]=='-f'):
        first=int(sys.argv[2])
        sys.argv.pop(1)
        sys.argv.pop(1)
        print("Starting at line " + str(first))
    
    elif(sys.argv[1]=='-l'):
        last=int(sys.argv[2])
        sys.argv.pop(1)
        sys.argv.pop(1)
        print("Ending at line " + str(last))
    else:
        print("Unknown argument " + sys.argv[1])        
        sys.exit(1)  
if(len(sys.argv)!=4):
    usage();

         
infile = sys.argv[1]
if (not infile):
    print("Input file " + infile + " doesn't exist, aborting!"); 
    sys.exit(0)

with open(infile) as f:
    original_lines = f.readlines()

outfile = sys.argv[2];

if ( os.path.exists(outfile)):
    if(abortOnExistingFile):
        print("Output file " + outfile + " already exists, aborting")
    
    mfile=outfile+".backup"
    if ( os.path.exists(mfile)):
        mnum=1
        while(mnum<10 and os.path.exists(mfile+str(mnum))):
            mnum+=1
        mfile = mfile+str(mnum)
    if(os.path.exists(mfile) and not allowOverwritingBackups):        
        print("Output file " + outfile + " already exists, too many backups already made, over-writing the last one!"); 
        
    else:
        if os.path.exists(mfile):
            print("Output file " + outfile + " already exists, too many backups already made, over-writing " + outfile + "!");      
        
        print("Output file " + outfile + " already exists, moving to " + mfile);
        shutil.move(outfile,mfile) 
        
    
    
    
command = sys.argv[3]

def run(filename):
    
    retval= os.system(command + " " + filename + " >/dev/null 2>&1");
    if not use_signal:
        retval=retval>>8
    return retval


    
print("Running command: "+ command + " " + infile)

skip_sanity=expect is not None #If the user supplied an expected exit code, assume that they are doing so because the run is slow, so skip the sanity check too

if expect is None:
    expect = run(infile)
if(use_signal):
    print("Expected exit code is " + str(expect) + " (value="+ str(expect >> 8) + ", signal=" + str(expect & 0xff) + ")")
else:
    print("Expected exit code is " + str(expect))



num_enabled= len(original_lines)
enabled=[True ]* num_enabled


def writeTo(filename):
    fout = open(filename,'w')
    for l in range(0,len(original_lines)):
        if(enabled[l]):
            fout.write(original_lines[l])
    fout.close()

#sanity check:
 
testingFile =  tempfile.NamedTemporaryFile(delete=False);
testingFileName = testingFile.name;
testingFile.close();


writeTo(testingFileName)
if not skip_sanity:
    ret = run(testingFileName)
    if(ret!=expect):
        print("Return value (" + str(ret) + ") of " + command + " " + testingFileName + " doesn't match expected value (" + str(expect)+ "), even though no changes were made. Aborting!\n")
        sys.exit(1)

if last<0:
    last=len(original_lines)



changed=True
round = 0
nremoved=0
num_left = last-first
#Todo: improve on this with a binary search...
while(changed):
    changed=False
    ntried=0
    round+=1
    print("Round " + str(round) + ":Tried " + str(ntried) +", Removed " + str(nremoved) + "/"+str(len(enabled)-first), end='\r' )
    nsize = last-first
    
    stride =  num_left if not linear else 1
    while(stride>=1):
        
        
        nfound=0
        i=0
        disabledSet=set()
        for i in  range(first,last) if not backward else  range(first,last)[::-1]:       
            if(enabled[i]):
                nfound+=1
                ntried+=1
                disabledSet.add(i)
                enabled[i]=False
                if(nfound==stride):
                    nfound=0
                    writeTo(testingFileName)
                    ret = run(testingFileName)
                    if(ret==expect):
                        changed=True
                        writeTo(outfile)
                        num_enabled-=len(disabledSet)
                        num_left-=len(disabledSet)
                        nremoved+=len(disabledSet)     
                        disabledSet=set()           
                    else:
                        #enabled[i]=True
                        for p in disabledSet:
                            enabled[p]=True
                        disabledSet=set()
                        
                    print("Round " + str(round)  + ":Tried " + str(ntried) +", Removed " + str(nremoved) + "/"+str(nsize), end='\r' )
        
        #If there are any remaining elements in the disabled set, then test them here.
        if(len(disabledSet)>0):                   
            nfound=0
            writeTo(testingFileName)
            ret = run(testingFileName)
            if(ret==expect):
                changed=True
                writeTo(outfile)
                num_enabled-=len(disabledSet)
                num_left-=len(disabledSet)
                nremoved+=len(disabledSet)     
                disabledSet=set()           
            else:
                #enabled[i]=True
                for p in disabledSet:
                    enabled[p]=True
                disabledSet=set()
                
            print("Round " + str(round)  + ":Tried " + str(ntried) +", Removed " + str(nremoved) + "/"+str(nsize), end='\r' )
            
        assert(len(disabledSet)==0);
        if(stride==1):
            break
        stride = int(math.floor( stride/2.0))
        
            
    print("Round " + str(round) + ":Tried " + str(ntried) +", Removed " + str(nremoved) + "/"+str(nsize), end='\n' )       
             
#just in case this file got over-written at some point.   
writeTo(outfile)    
os.remove(testingFileName)
print("Done. Kept " + str(num_enabled) + " lines, removed " + str(nremoved) + "/"+str(len(enabled)-first) + " lines.         ")
   