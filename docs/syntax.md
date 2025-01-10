# Collins Syntax

A Collins file defines a module and consists of function definitions and message handlers. Instances of the module can be addressed by an identifier and sent messages. Identifiers can be strings or integers.

An instance has some internal state that you define. When an instance receives a message it can take actions and optionally update its state.

## Function Definition

Each function can have multiple definitions. Each one should accept a different pattern of inputs. The order they are defined matters. When a function is called, each pattern is tested in the order they were defined. The first one that matches will be the function definition that gets executed. The different definitions for a function are typically located one after the other in your code, but they don't have to be.

A function definition begins with a head that consists of the function name and the pattern of parameters it takes. It can optionally include a guard stating other logic that should be tested against the parameters. After the head is a block of instructions to be executed. The last expression of the function determines its return value.

    MyAdd(int=>a, int=>b) where a>5
        a+b

In this example the function name is `MyAdd`. The pattern being accepted here consists of two integers, the first one will be called `a` and the second one `b`. There is a guard saying that this definition should only be executed if `a` is greater than 5. The block to be executed here consists of only a return value, the sum of the two values.

### Patterns

A pattern can consist of a simple literal, like an integer, a string, or an atom (see the [Atoms](#atoms) section for a full discussion of what atoms are). These expect to match both value specified and its type.

    Function(42, "hello", :my_atom)

A pattern can consist of just a variable name to assign the value to. In its simplest form, this matches anything and makes the input available in the code block under that name. To use a name with another pattern, see below.

    Function(a, foo)

Sometimes you need a parameter in one version of a function, but not in another. If you use a variable name and it begins with a `_`, then the parameter is ignored and not available in the code for this definition. 

    Function(a, _foo)

As a functional language, functions are first-class objects in Collins and you can pass them in as parameters. To match a function, use `&/x` where x is the arity (number of paramters) of the expected function.

    Function(&/2)

You can specify a type to match without specifying a value. For simple types just indicate `int`, `float`, or `string`. To match against any list use `[]`. To match against any map use `{}`. 

You can match against the contents of a list by specifying patterns in square brackets. Any kind of pattern can be nested within a list. Any list at least as long as the pattern list and matching its members will match. So if you specify a list with three patterns in it, a list with five members where the first three match will be considered a match (i.e. the list `[1,2,3,4,5]` would match the pattern `[int, int, int]`)

    Function([:my_atom, int, &/2])

You can match against the contents of a map by specifying key:value patterns in curly braces. The key parts of each pattern has to be an int or string literal. The value part can be any kind of pattern. Any list that has those keys and corresponding values that match the specified patterns matches the map pattern.

    Function({"name": username, "age": int, "items": []})

Function, type, list, and map patterns can also be mapped to a variable name with the use of the `=>` operator. This is how you can capture a whole list, for example, while also capturing its specific members.

    Function(&/4=>my_func)
    Function(int=>i, []=>my_list)
    Function([int=>i, {"name": username}=>user]=>my_list)

### Guards

Guards add some extra logic on top of pattern mathing. Only simple logic is allowed at this point. You can compare variables and simple literals with `<`, `>`, and `=`. You can do simple logic with `and` and `or`.

    Function(int=>a, int=>b) where a<b and b<10

### Code Block

Code blocks consist of three different types of statements: assignments, message sends, and return values. A block may consist of any number of assignments and message sends, but it can have only one return value and it must be the last statement in the block. In fact the parser uses a return value to know when it's reached the end of a function definition.

Assignments take an expression and assign it to a variable. Unlike most langauges, this is done in a left-to-right manner using `=>`.

    a + 5 => b

Messages can be sent to instances of other modules using the `:>` operator, with an espression to its left and a target to its right. The target consists of a module name and the ID of an instance of that module, separated by a `:`. That instance of that module will be sent the expression as a message.

    [:set_first_name, "Alice"] :> Employee:12345

A return value is simply an expression. It must be the last statement of a code block and is the only time you build an expression that isn't either assigned to a variable or sent as a message.

Comments are preceeded with a `#`. They can be included mid-line. There are no multiline comments, just preceed each line with `#`.

#### Expressions

Expressions are mostly pretty similar to expressions in other languages, with addition, subtraction, and parenthesis like normal. You can access members of a list or a map with square brackets.

Comparison, like `<` and `>` return [atoms](#atoms) `:true` or `:false`. Logical operators, like `and` and `or` treat the atom `:true` as true and anything else as false.

When you call a function, you have to specify the module and function name, separated with a dot like this: `module.function()`. If you are referring to a function defined in the current module, you can leave the module name off, but you still have to include the dot like this: `.function()`. It's a little weird and takes some getting used to, but this is how the compiler distinguishes between when you're calling a regular function, or an anonymous function that is the result of an expression.

When you want to pass the result of one function (or any kind of expression) into another function, you can use the pipe operator `|>`. The pipe operator must be followed by a function call, either a normal funciton, or an anonymous one. The pipe operator will take the result of the expression on its left and pass it as the first parameter to the function on its right. You specify any further parameters as you would normally. So

    2+5 |> foo(a, b)

is exactly equivalent to

    foo(2+5, a, b)

The pipe operator is best used to form a flow of data through a series of functions.

    my_list
    |> sort()
    |> Enum.Map(&(x) {x*x})
    |> Enum.Reduce(&(a,b) {a+b})
    => sum_result

Anonymous functions are defined with the `&` operator, followed by its list of paramters (with an optional guard), and then a code block enclosed in curly braces.

    &(int=>i, {"multiplier":m}) {i*m)

You can define multiple variations of an anonymous function with different parameters just like you can with regular functions. Just include multiple anonymous function definitions right after each other. They must all take the same number of paramters (the same arity).

    &(x) where x<0 {-x} &(x) {x}

Anonymous functions can be assined to a variable and then used later by that name.

    &(x) {x+5} => add_five
    add_five(3)

They can be passed directly as parameters to other functions, or returned as the return value of a function.

### The Initial Function

Modules should generally include a definition for a function called Initial, which takes one parameter. This is used when a new instance of the module is first crated. Initial will be called with the instance's identifier. The return value will be kept as that instance's initial state.

If Initial is not defined in your module a default implementaion will be added that simply sets the instance's state to 0.

## Atoms

Atoms are like enums in other languages. They let you use descriptive names for things in your code, while using a simple integer ID behind the scenes. Unlike enums, you don't have to declare them beforehand, or define them in groups. Atoms look like a variable name preceeded by a `:`. Atoms can be stored in variables or returned from a function like any other value.

    :startup => state
    [:update_state, state] :> MyModule:123
    :ok

## Message Handlers

Message handlers determine what an instance of your module does when it receives a message. They begin with the keyword `msg`, followed by a single pattern to match messages against (including an optional guard), and a block to be executed when the instance receives a matching message. You can have multiple message handlers to catch different types of messages. Patterns will be tried in the order they appear in the file, just like functions.

The code blocks of your message handlers consist of assignments, message sends, and return values just like a function. In the code block, you can use a variable called `state` to access the state of this instance. The value returned by your message handler will be the new state of this instance. If you don't want the state to change, you can just return `state` as is.

There are a few other variables available to your messages handlers. `ident` is the identifier of this instance. `from_module` and `from_ident` identify which instance of which module sent the message.

The `msg` message handler syntax is actually just a shorthand for function. Each message handler is compiled as a function called Receive like this:

    Receive(state, my_pattern, ident, from_module, from_ident)

You can define `Receive` yourself if you want to implement fancier pattern matching. It can be used interchangeably with other `msg` handlers.
