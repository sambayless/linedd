linedd
==============

linedd is a [delta-debugger](http://en.wikipedia.org/wiki/Delta_Debugging) for line-oriented text formats, for minimizing error-causing inputs to programs while preserving errors.
In contrast to most delta-debuggers, linedd isn't specialized to deal with any particular syntax or format, beyond expecting line endings.
This means that it can be used without modification to delta-debug any line-oriented text file.  

Given a system command of the form 'command argument1 argument2 file', (with file as the last argument),
linedd will execute that command on the file and record the exit code. It will then repeatedly attempt to remove one or more individual lines
from the file, each time executing the original command on the new, smaller file. If the exit code of the command changes after removing
a line, linedd will backtrack, replacing the line and removing a new one. 

In this way it continues removing lines until it reaches a fixed point.

Usage is as simple as

    linedd <file_to_minimize> <output_file> "command arg1 arg2 arg3"

Where the 'file_to_minimize' is the file you start with, and 'output_file' is where linedd should write its minimzed version. 'command' is any arbitrary command, and may include spaces and arguments. 
linedd will then repeatedly execute 'command output_file' while removing lines from 'output_file'. linedd assumes that the command expects the file as its last argument. 

For example, if you have a config file 'cofiguration.txt':

   windowed=True
   maximized=false
   startup=False

with an error on line 3 ('false' should be capitalized), and

   myProgram --configuration=configuration.txt 

crashes with exit code 1 trying to read in that configuration file, then executing 

   linedd configuration.txt reduced_config.txt "myProgram --configuration="
   
will produce a reduced_config.txt containing just the error-inducing line,

   maximized=false

linedd is styled after the delta-debugging tools developed at the [Institute for Formal Models and Verification](http://fmv.jku.at/fuzzddtools/).
