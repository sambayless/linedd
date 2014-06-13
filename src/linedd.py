#!/usr/bin/env python
from __future__ import division, print_function
import argparse
import os
import shutil
import sys
import tempfile

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

parser = argparse.ArgumentParser(description="A line-oriented delta debugger.\nUsage: " + os.path.basename(sys.argv[0]) + " [options] <input_file> <output_file> command", formatter_class=argparse.RawTextHelpFormatter, usage=argparse.SUPPRESS) 

#optional arguments
parser.add_argument("--expect", type=int, help="Expected exit code. If supplied, linedd will skip the initial execution of the command (default: None)", default=None)

parser.add_argument('--signal', dest='signal', action='store_true', help="Preserve the full unix termination-signal, instead of just the exit code (default: --no-signal)")
parser.add_argument('--no-signal', dest='signal', action='store_false', help=argparse.SUPPRESS)
parser.set_defaults(signal=False)

parser.add_argument('-q', '--quiet', dest='quiet', action='store_true', help="Suppress progress information (default: --no-quiet)")
parser.add_argument('--no-quiet', dest='quiet', action='store_false', help=argparse.SUPPRESS)
parser.set_defaults(quiet=False)

parser.add_argument('--reverse', dest='reverse', action='store_true', help="Remove lines starting from the end of the file, rather than the beginning (default: --no-reverse)")
parser.add_argument('--no-reverse', dest='reverse', action='store_false', help=argparse.SUPPRESS)
parser.set_defaults(reverse=False)

parser.add_argument('--linear', dest='linear', action='store_true', help="Only remove lines one-by-one, instead of applying a binary search (default: --no-linear)")
parser.add_argument('--no-linear', dest='linear', action='store_false', help=argparse.SUPPRESS)
parser.set_defaults(linear=False)

parser.add_argument("--first", type=int, help="Don't remove lines before this one  (default: 0)", default=0)
parser.add_argument("--last", type=int, help="Don't remove lines after this one (-1 for infinity)  (default: -1)", default= -1)

#positional arguments
parser.add_argument("infile", type=str, help="Path to input file (this file will not be altered); this file will be appended to the command before it is executed")
parser.add_argument("outfile", type=str, help="Path to store reduced input file in")
parser.add_argument("command", type=str, help="Command to execute (with the input file will be appended to the end). May include arguments to be passed to the command", nargs=argparse.REMAINDER, action="store")

args = parser.parse_args()

first = args.first
last = args.last
expect = args.expect
backward = args.reverse
linear = args.linear
use_signal = args.signal
quiet = args.quiet

abortOnExistingFile = False
allowOverwritingBackups = True

if quiet:
    def print_out(*args, **kwargs):
        pass
else:
    def print_out(*args, **kwargs):
        print(*args, **kwargs)
        sys.stdout.flush()

def error_quit(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
    sys.exit(1)
         
infile = args.infile
if (not infile):
    error_quit("Input file " + infile + " doesn't exist, aborting!"); 

with open(infile) as f:
    original_lines = f.readlines()

outfile = args.outfile;

if (os.path.exists(outfile)):
    if(abortOnExistingFile):
        error_quit("Output file " + outfile + " already exists, aborting")
    
    mfile = outfile + ".backup"
    if (os.path.exists(mfile)):
        mnum = 1
        while(mnum < 10 and os.path.exists(mfile + str(mnum))):
            mnum += 1
        mfile = mfile + str(mnum)
    if(os.path.exists(mfile) and not allowOverwritingBackups):        
        print_out("Output file " + outfile + " already exists, too many backups already made, over-writing the last one!"); 
        
    else:
        if os.path.exists(mfile):
            print_out("Output file " + outfile + " already exists, too many backups already made, over-writing " + outfile + "!");      
        
        print_out("Output file " + outfile + " already exists, moving to " + mfile);
        shutil.move(outfile, mfile) 
            
command = " ".join(args.command)

def run(filename):
    
    retval = os.system(command + " " + filename + " >/dev/null 2>&1");
    if not use_signal:
        retval = retval >> 8
    return retval

  
print_out("Executing command: \"" + command + " " + infile + "\"")

skip_sanity = expect is not None #If the user supplied an expected exit code, assume that they are doing so because the run is slow, so skip the sanity check too

if expect is None:
    expect = run(infile)
    

if(use_signal):
    print_out("Expected exit code is " + str(expect) + " (value=" + str(expect >> 8) + ", signal=" + str(expect & 0xff) + ")")
else:
    print_out("Expected exit code is " + str(expect))


num_enabled = len(original_lines)
enabled = [True ] * num_enabled

def writeTo(filename):
    fout = open(filename, 'w')
    for l in range(0, len(original_lines)):
        if(enabled[l]):
            fout.write(original_lines[l])
    fout.close()

#sanity check: 
testingFile = tempfile.NamedTemporaryFile(delete=False);
testingFileName = testingFile.name;
testingFile.close();

writeTo(testingFileName)
if not skip_sanity:
    ret = run(testingFileName)
    if(ret != expect):
        error_quit("Return value (" + str(ret) + ") of " + command + " " + testingFileName + " doesn't match expected value (" + str(expect) + "), even though no changes were made. Aborting!\n")
     

if last < 0:
    last = len(original_lines)

changed = True
round = 0
nremoved = 0
num_left = last - first


#This executes a simple binary search, first removing half the lines at a time, then a quarter of the lines at a time, and so on until eventually individual lines are removed one-by-one.
while(changed):
    changed = False
    ntried = 0
    round += 1
    cur_removed = 0
    nsize = last - first - nremoved
    print_out("Round " + str(round) + ": Tried " + str(ntried) + ", Removed " + str(cur_removed) + "/" + str(nsize), end='')
    
    stride = num_left if not linear else 1
    while(stride >= 1):       
        nfound = 0      
        disabledSet = set()
        for i in  range(first, last) if not backward else  range(first, last)[::-1]:       
            if(enabled[i]):
                nfound += 1
                
  
                disabledSet.add(i)
                enabled[i] = False
                if(nfound == stride):
                    nfound = 0
                    ntried += 1
                    writeTo(testingFileName)
                    ret = run(testingFileName)
                    if(ret == expect):
                        changed = True
                        writeTo(outfile)
                        num_enabled -= len(disabledSet)
                        num_left -= len(disabledSet)
                        nremoved += len(disabledSet)
                        cur_removed += len(disabledSet)    
                        disabledSet = set()           
                    else:           
                        for p in disabledSet:
                            enabled[p] = True
                        disabledSet = set()                        
                    print_out("\rRound " + str(round) + ": Tried " + str(ntried) + ", Removed " + str(cur_removed) + "/" + str(nsize), end='')
        
        #If there are any remaining elements in the disabled set, then test them here.
        if(len(disabledSet) > 0):                   
            nfound = 0
            ntried += 1
            writeTo(testingFileName)
            ret = run(testingFileName)
            if(ret == expect):
                changed = True
                writeTo(outfile)
                num_enabled -= len(disabledSet)
                num_left -= len(disabledSet)
                nremoved += len(disabledSet)   
                cur_removed += len(disabledSet)   
                disabledSet = set()           
            else:
                for p in disabledSet:
                    enabled[p] = True
                disabledSet = set()
                
            print_out("\rRound " + str(round) + ": Tried " + str(ntried) + ", Removed " + str(cur_removed) + "/" + str(nsize), end='')
            
        assert(len(disabledSet) == 0);
        if(stride == 1):
            break
        
        stride = stride // 2
        assert(stride > 0)
            
    print_out("\rRound " + str(round) + ": Tried " + str(ntried) + ", Removed " + str(cur_removed) + "/" + str(nsize), end='\n')       
             
#just in case this file got over-written at some point.   
writeTo(outfile)    
os.remove(testingFileName)
print("Done. Kept " + str(num_enabled) + " lines, removed " + str(nremoved) + "/" + str(len(enabled) - first) + " lines. Minimized file written to " + outfile + ".")
