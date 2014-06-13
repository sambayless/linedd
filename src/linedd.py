#!/usr/bin/env python
from __future__ import division
from __future__ import print_function

'''
Copyright (c) 2014, Sam Bayless

 Permission is hereby granted, free of charge, to any person obtaining
 a copy of this software and associated documentation files (the
 "Software"), to deal in the Software without restriction, including
 without limitation the rights to use, copy, modify, merge, publish,
 distribute, sublicense, and/or sell copies of the Software, and to
 permit persons to whom the Software is furnished to do so, subject to
 the following conditions:
 
 The above copyright notice and this permission notice shall be included
 in all copies or substantial portions of the Software.
 
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
 CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

"""
linedd is a delta-debugger for line-oriented text formats, used for minimizing inputs to programs while preserving errors.
In contrast to most delta-debuggers, linedd isn't specialized to deal with any particular syntax or format, beyond line endings.
It can be directly employed, without modification, to delta-debug any line-oriented text file. 
 
Given a system command of the form "command argument1 argument2 file", (with file as the last argument),
linedd will execute that command on the file and record the exit code. It will then repeatedly attempt to remove one or more individual lines
from the file, each time executing the original command on the new, smaller file. If the exit code of the command changes after removing
a line, linedd will backtrack, replacing the line and removing a new one. 

In this way it continues removing lines until it reaches a fixed point.

Usage is as simple as

$linedd <file_to_minimize> <output_file> "command arg1 arg2 arg3"

Where the file_to_minimize is the file you start with, and output_file is where linedd should write its minimzed version. Command is any arbitrary command, optionally with arguments.
Command will then be executed repeatedly as "command arg1 arg2 arg3 output_file". linedd assumes that the command expects the file as its last argument. 
"""

import os
import shutil
import sys
import tempfile

def usage():
    print("Usage: " + sys.argv[0] + " <input file> <output file> command")
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
quiet=False
while(len(sys.argv)>4):
    if(sys.argv[1]=='--help'):
        usage()
    elif(sys.argv[1]=='-h'):
        usage()       
    elif(sys.argv[1]=='--reverse'):
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
    elif(sys.argv[1]=='-q' or sys.argv[1]=='--quiet' ):
        quiet=True
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

if quiet:
    def print_out(*args, **kwargs):
        pass
else:
    def print_out(*args, **kwargs):
        print(*args, **kwargs)

def error_quit(*args, **kwargs):
    print(*args,file=sys.stderr, **kwargs)
    sys.exit(1)
         
infile = sys.argv[1]
if (not infile):
    error_quit("Input file " + infile + " doesn't exist, aborting!"); 


with open(infile) as f:
    original_lines = f.readlines()

outfile = sys.argv[2];

if ( os.path.exists(outfile)):
    if(abortOnExistingFile):
        error_quit("Output file " + outfile + " already exists, aborting")
    
    mfile=outfile+".backup"
    if ( os.path.exists(mfile)):
        mnum=1
        while(mnum<10 and os.path.exists(mfile+str(mnum))):
            mnum+=1
        mfile = mfile+str(mnum)
    if(os.path.exists(mfile) and not allowOverwritingBackups):        
        print_out("Output file " + outfile + " already exists, too many backups already made, over-writing the last one!"); 
        
    else:
        if os.path.exists(mfile):
            print_out("Output file " + outfile + " already exists, too many backups already made, over-writing " + outfile + "!");      
        
        print_out("Output file " + outfile + " already exists, moving to " + mfile);
        shutil.move(outfile,mfile) 
            
command = sys.argv[3]

def run(filename):
    
    retval= os.system(command + " " + filename + " >/dev/null 2>&1");
    if not use_signal:
        retval=retval>>8
    return retval

  
print_out("Running command: "+ command + " " + infile)

skip_sanity=expect is not None #If the user supplied an expected exit code, assume that they are doing so because the run is slow, so skip the sanity check too

if expect is None:
    expect = run(infile)
    

if(use_signal):
    print_out("Expected exit code is " + str(expect) + " (value="+ str(expect >> 8) + ", signal=" + str(expect & 0xff) + ")")
else:
    print_out("Expected exit code is " + str(expect))


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
        error_quit("Return value (" + str(ret) + ") of " + command + " " + testingFileName + " doesn't match expected value (" + str(expect)+ "), even though no changes were made. Aborting!\n")
     

if last<0:
    last=len(original_lines)

changed=True
round = 0
nremoved=0
num_left = last-first


#This executes a simple binary search, first removing half the lines at a time, then a quarter of the lines at a time, and so on until eventually individual lines are removed one-by-one.
while(changed):
    changed=False
    ntried=0
    round+=1
    cur_removed = 0
    print_out("Round " + str(round) + ":Tried " + str(ntried) +", Removed " + str(nremoved) + "/"+str(len(enabled)-first), end='\r' )
    nsize = last-first
    
    stride =  num_left if not linear else 1
    while(stride>=1):       
        nfound=0      
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
                        cur_removed+= len(disabledSet)    
                        disabledSet=set()           
                    else:           
                        for p in disabledSet:
                            enabled[p]=True
                        disabledSet=set()                        
                    print_out("Round " + str(round)  + ":Tried " + str(ntried) +", Removed " + str(cur_removed) + "/"+str(nsize), end='\r' )
        
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
                for p in disabledSet:
                    enabled[p]=True
                disabledSet=set()
                
            print_out("Round " + str(round)  + ":Tried " + str(ntried) +", Removed " + str(nremoved) + "/"+str(nsize), end='\r' )
            
        assert(len(disabledSet)==0);
        if(stride==1):
            break
        
        stride =stride//2
        assert(stride>0)
            
    print_out("Round " + str(round) + ":Tried " + str(ntried) +", Removed " + str(nremoved) + "/"+str(nsize), end='\n' )       
             
#just in case this file got over-written at some point.   
writeTo(outfile)    
os.remove(testingFileName)
print("Done. Kept " + str(num_enabled) + " lines, removed " + str(nremoved) + "/"+str(len(enabled)-first) + " lines. Minimized file written to " + outfile +".")
