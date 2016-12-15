# Concurrency
Some tests are located in other directories where they must reside in order to be built and run.
To execute them in a local docker environment, run bash scripts that can be found here. For example:

To run a 1-minute test using addrecs chaincode (which adds 1K payload to ledger with each invoke)
where we repeatedly create 1000 go-threads to "simultaneously" send a transaction concurrently,
divided among the 4 peers, simply execute run_conc4p1min1000Thrd1TxPerLoop_LOCAL.sh.

Or, unleash 400 threads to concurrently send transactions for a minute (limited only by CPU resources
on your machine that is running the test), by executing run_conc4p1min400Thrd_LOCAL.sh.

For each of these, look for .log files to be created in the directory where the actual
go tests reside, in ../../fvt/consensus/tdk/ledgerstresstest/

