Guy Ben Israel - 308459973
Nadav Ostrowsky – 302186549

Used AMI: 'ami-bb6801ad' 
The application should be run as follows : python LocalApp.py inputFile outputFile n 
or, if you want to terminate the manager: python LocalApp.py inputFile outputFile n terminate
**outputFile should end with .html

Did you think for more than 2 minutes about security?
-We’ve created environment variables on the first running using AWS Command Line UI and created an image from which we created all the machines we use.

Threads in your application, when is it a good idea? When is it bad? Invest time to think about threads in your application.
-In this project threads could be used in the manager class since the manager has to receive messages from two different queues and perform differently for each sort of message. However we decided not to use threads for several reasons:
The processing of the data done by the workers takes longer than the parsing that has to be done by the manager and therefore the use of threads could be wasteful.
We are using CPython and it is installed on all of our machines, and it doesn’t support threading well which makes using threads less significant for us.
The processing of the data is the most time and resource consuming part of the project and it is being handled by the different workers that work on different machines and therefore require no use of thread.

Did you think about scalability? Will your program work properly when 1 million clients connected at the same time? How about 2 million? 1 billion? Scalability is very important aspect of the system, be sure it is scalable!
-Our program will be able to work properly no matter what the amount of clients will be. However, since there is only one manager the will be a load on it and it won’t run as fast as it would with fewer clients.

What about persistence? What if a node dies? Have you taken care of all possible outcomes in the system? Think of more possible issues that might arise from failures. What did you do to solve it? What about broken communications? Be sure to handle all fail-cases!
-The tasks for the workers are all found in a queue and are not deleted from that queue until the task is done and the manager gets the result, we achieved that by changing the visibility of the message for enough time for the worker to complete his task. That guarantees us that if a node dies the task would not be lost. 

Do you understand how the system works? Do a full run using pen and paper, draw the different parts and the communication that happens between them.
A n_g.pdf is added.

Did you manage the termination process? Be sure all is closed once requested
-We perform the termination process as follows:
* A  local application that received “terminate” as an argument sends a “terminate” message.
* The manager receives the “terminate” message and send a “terminate” message for each of the workers to receive after all the previously sent jobs are done.
* Each worker gets the “terminate” message, stops listening to the queue for any more messages and letting the manager know that it stopped working with a “worker-terminated” message.
* When the manager receives the “worker-terminated” message from all workers he then terminates all the instances of the workers and sends a “manager terminated” message to the local application.
* The local application receives the “manager terminated” message and terminates the instance of the manager and all the queues.




Did you take in mind the system limitations that we are using? Be sure to use it to its fullest!
*We can only create up to 5 instances of ec2 so we made sure that the maximum amount of workers we create is 4 and one more for the manager.
*All the data is always kept in the s3 in case one of the ec2 instances crashs. this way we have all our files backed up.


Are all your workers working hard? Or some are slacking? Why?
-in our program there are two scenarios where a worker might be “slacking”:
* When we initialize new workers some of them might take longer than others to  start operating and therefore other workers will work harder.
* There’s an unlikely scenario where every time a worker tries to get a new message a different worker will take it before him. The more messages there are the more unlikely it is to happen.

Lastly, are you sure you understand what distributed means? Is there anything in your system awaiting another?
-Distributed in our case means using several computer systems that are located on the network that communicate through messages and have distribute the actions between them to perform our program.
In our system there are several occasions where there will be an element awaiting another:
* The local application waits for the manager and the workers to process the data and send back the appropriate response.
* The manager waits for either the workers to send a message when they’re done processing the pdf, or for a local application to send a new job.
* The workers  wait for the manager to send them a new message with a pdf to process
We have elements in our system that awaits another:
* the local application waits for the manager to finish analyzing his request.
* the manager waits for the workers to finish working on all the requests, and also for the termination message to shut down the whole system.
* the workers are waiting for results from NASA`S website, and also for new tasks to analyze from the manager.
