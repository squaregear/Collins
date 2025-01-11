# Collins

This began when I read an article encouraging programmers to design their own programming language. Doing so lets you tackle all sorts of crunchy problems like writing a parser and building a virtual machine. But it also makes you think deeply about big picture things like what have you liked and disliked about the languages you've used? What would your ideal prgramming language be? Collins is my attempt to answer those quetions.

* [Collins language syntax](docs/syntax.md)

## Philosophy

As a programmer, when I start a new project I want to be thinking about the problem to be solved. But too often I have to first spend time working out infrastructure plans. How much will this need to scale? How many servers will I need? How will they connect and share information? How will my data be stored? I don't want to have to do that. I want a language and evironment where I can start from the beginning with the real logic and the deploy it in a system where it can scale from five users to five million without me having to think about it. I haven't actually build such a scalable system, but I hope the language I'm building here makes that possible.

The actor model seems like a good base to build such a system on. Independent entities that share nothing and communicate only with message passing allow parallelization and locality-independence. I really like the model [Orleans](https://learn.microsoft.com/en-us/dotnet/orleans/overview) adopted. It treats object instances as actors instead of focusing on processes as actors. But their attempts to keep things object oriented and c#ish mean that it is easy to deadlock your objects. I'd like a system like that, but more strict and functional. If your objects never block, then they can never deadlock.

I have also really enjoyed using [Elixir](https://elixir-lang.org/), so I took a lot of ideas and elements of syntax from there. I especially like pattern matching and function piping. Pattern matching is a way of having many specialized versions of a function. Each one defines a pattern of inputs it expects and only gets executed when that pattern comes up. It allows you to write very small, focused functions, which are very easy to reason about and test. Function piping lets you easily send the result of one function into another one. It encourages you to think about your process as a flow of data through a series of operations. I took it even further, with everything following a similar left-to-right flow, including variable assignment.

## How Collins Works

You write modules that define the behavior of a type of object. Objects can represent real world things, like employees or products, or more abstract things, like organizations and plans. Anything that has state, recieves, or sends messages can be an object. There can be multiple instances of any module type. They are differentiated with an identifier, which can be an integer or a string. Some modules act as singletons, where only one instance is needed. Typically, those are just addressed with id 0.

You don't need to explicitly create objects before addressing them. You just send a message to the identifier of the object you want, and it will be created for you. If it exists, it will be pulled into memory and made ready to receive your message. If it doen't already exist, it will be created and initialized using its Initial() function.

(Actually, with my toy implementation of everything, objects only exist in memory and aren't persisted in any way beyond that. So when your program exits, everything diappears. A real implementation, though, would persist your instances and be clever about when they need to be saved to disk.)

### Startup

When you run the VM, you specify a main module. The VM will instaciate identity 0 of that module and send it a message consisting of the command line parameters that it was started with. 
