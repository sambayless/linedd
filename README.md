linedd
==============

linedd is a [delta-debugger](http://en.wikipedia.org/wiki/Delta_Debugging) for line-oriented text files. You can use it to minimize error-causing inputs to programs while preserving those errors (making it easier to debug your code).

In contrast to most delta-debuggers, linedd isn't specialized to deal with any particular syntax or format, beyond expecting line endings.
This means that it can be used without modification to delta-debug any line-oriented text file.  

Using linedd is as simple as:

    linedd <file_to_minimize> <output_file> command_to_execute

Where the ```file_to_minimize``` is the file you start with, and ```output_file``` is where linedd should write its minimzed version. ```command``` is any arbitrary command, and may include spaces and arguments. 
linedd will then repeatedly execute ```command output_file``` while removing lines from ```output_file```. linedd assumes that the command expects the file as its last argument. 

For example, if you have a configuration file "config.txt":

    windowed=True
    maximized=false
    startup=False

with an error on line 2 ('false' should be capitalized), and

    myProgram --myFlag --configuration=config.txt 

crashes with exit code 1 trying to read config.txt, then executing 

    linedd config.txt reduced_config.txt "myProgram --myFlag --configuration="
    
will create reduced_config.txt, containing just the error-inducing line

    maximized=false
    
Technical Stuff
---------------

linedd will copy ```file_to_minimize``` to ```output_file```, and then execute ```command output_file``` and record the exit code. It will then repeatedly attempt to remove one or more individual lines
from ```output_file```, each time executing ```command output_file```. If the exit code is preserved on this smaller file, linedd will keep the change and continue trying to remove other lines; if the exit code changes, linedd will backtrack, replacing the line and removing a new one. 

In this way it continues removing lines until it reaches a fixed point.

linedd is styled after the delta-debugging tools developed at the [Institute for Formal Models and Verification](http://fmv.jku.at/fuzzddtools/). 
