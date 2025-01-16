# Python Implementation

This is a python implementation of a compiler and VM for the Collins language. I wrote it in python because it's a really easy langauge to work with, and I could piggyback some of my semantics on top of python's. It's a pretty simplistic and toyish implementation of everything, but all I was shooting for was enough to demonstrate that the concepts in the language can actually work.

It is a very happy-path implementation. If anything doesn't work just as expected, it pretty much just crashes out immediatly, without very helpful error messages.

I am a very inexperienced parser programmer, so bad input files will fail with often cryptic messages. Sorry about that. I really love how some languages these days can give descriptive error messages with suggestions of how you might correct them, but that's way beyond me at this point.

## Compiling and Running

    python collinscompile.py sourcefile.col outputfile.cc

This will read in the source Collins file, compile it to bytecode, and save the result in the Compiled Collins output file. While compiling, it will build a list of other modules that it uses and keep track of what it needs to execute.

    python collinsloader.py mainfile.cc other input parameters

This will load up the main compiled Collins file, make an instance of it with identity 0, and send it a message consisting of the command line starting with the Compile Collins file itself. It will also load any other modules that the main one needs.

It will execute until there is nothing queued up to run and then exit. So that initial message should trigger other actions you want to happen by sending messages to other module instances. In a real system, it could idle and respond to other inputs, but this simple implementation expects to just run and exit.
