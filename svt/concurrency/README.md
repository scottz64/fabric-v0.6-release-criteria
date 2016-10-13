# Concurrency
Some tests are located in other directories where they must reside in order to be built and run.
To execute them, run bash scripts that can be found here. For example,
to run a 1-minute test using addrecs chaincode (which adds 1K payload to ledger with each invoke)
where 4 peers simultaneously send bursts of transactions for 1 minute, simply execute run_concurrency4peers1min.sh

