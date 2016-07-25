# Release-Criteria Document

## The release criteria repository is organized as follows
1.  Each release is documented in its own branch.
2.  All the tests in each branch are executed on three platforms.

	a) locally on an machine running Windows on Intel.  
    
    b) On the Distributed Bluemix Service offering.  This is the free version.
    
    c) On the LinuxOne Secure Service Container Blumix Service offering.
3.  The configuration is a five node system.  Four peers and one member services node.    

## The folder structure for the branch
1.  Each branch will also have a README that breaks down all the tests have run successfully, failed, or are incomplete. 
2.  Each branch will have the commit level run for that release.
3.  The folder structure is designed to separate each area of verifiction and percolate the results back the the branch's README.md.
4.  The focused areas for verification are:  performance, system verification testing, functional verification testing, and automated behave runs.
5.  The source code is included and instructions to run the test are in every section.

## Future Work Will Include
1.  Using Jenkins as the CI Framework to drive all the tests.
	

