# Example Collins Modules

Here are a couple example modules I've used to test that my compiler and VM are working.

# Guesser

This is a simple number guessing game. It is implemented as a singleton in `Guesser.col`. This was the first thing I got running just to make sure the whole process was working from parsing through execution.

# Simulation

This is a program for testing out a lot of the fancier systems designed into the language. It begins by telling ten employees (defined in `Employee.col`) to each say hello to another employee. The employees (with IDs 0 through 9) don't have to be instaciated beforehand. They are just created in their default state as soon as you send a message to them.

Each employee is intialized with a random first and last name. They each also define their `greet_func`, which is an anonymous function stored in their state. When they get a message telling them to say hello to another employee, they send their `greet_func` as a message to that other employee. This demonstrates defining an anonymous function, storing it, and also that it can be sent as a message. When an employee receives a greet function, it runs it with its own name as the parameter.

The next thing the simulation does is define a relationship between each employee and a team they are on (defined in `Team.col`). When the relationship is defined, its members are notified with a message. In this simulation each team uses its own video conferencing system, so when a team learns of a new member, it sends that member a message telling them which system to use. The employee then prints a message to simulate setting up that system. This demonstrates defining relations and relation notifications.

When they are initialized, each employee sets a relation to its manager. The last thing the simulation does is ask one of the employees (who is a leader) to print the list of thier direct reports. When an employee receives that message, it requests its list of manager relations, extracts just the employee ids from it, converts them to strings, forms a string listing them all, and prints that string. This demonstrates directional relations from both ends, and also demonstrates using the pipe operator to flow data from one state into another.

You might notice that even though the operations are launched in one order, the results print out in a different one. That is because everything is running in parallel, so the quicker operations get done faster, while the others are still running.

# Advent of Code

The last example is an attempt to solve an actual problem with Collins. I took day two of 2024's [Advent of Code](https://adventofcode.com/2024/day/2) because it was a nice example of a problem that benefitted from parallel processing (and I had recently already solved it using another language). The problem requires you to read lines of digits from a file and determine if the numbers in the line have the right relation to each other. The final result is the count of lines that match that criteria.

The main module (`AocDay02.col`) reads the input file and then sends each line to an individual line processor (`AocDay02Line.col`). Since a module can be identified by an int or a string, I just used the line itself as the identifier. Each line is sent a message asking to check its result.

When a line is instanciated, it does the work of checking the line, and stores `:true` or `:false` as its state, to indicate if the the result. When it gets the `:check` message, it sends its state back to the main module. All this is triggered by simply sending each line the `:check` message, Since they don't already exist, it will create them, thier initialization will compute the result, and then they will process the `:check`.

Back in the main module, it will receive each line's `:true` or `:false` and add up the results it receives. It also keeps track of how many responses it has gotten and when that matches the number of lines that were in the file, it prints out the final result.
