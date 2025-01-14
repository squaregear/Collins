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
