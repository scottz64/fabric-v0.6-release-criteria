# HYPERLEDGER FABRIC v1.0

They Hyperledger Fabric is a platform that enables the delivery of a secure, robust, permissioned blockchain for the enterprise that incorporates a byzantine fault tolerant consensus.  We have learned much as we progressed throuh the v0.6-preview release.  In particular, that in order to provide for the scalability and confidentiality needs of many use cases, a refactoring of the architecture was needed.  The v0.6-preview release will be the final (barring any bug fixes) release based upon the original architecture.

The Hyperledger Fabric v1.0 architecture has been designed to address two vital enterprise-grade requirements – **security** and **scalability**.  Businesses can leverage this new architecture to execute confidential transactions on networks with shared or common assets – e.g. supply chain, FOREX market, healthcare, etc.  The progression to V1 will be incremental, with myriad windows for community members to contribute code and start curating the fabric to fit specific business needs.

## WHERE WE ARE:

The current implementation involves every validating peer shouldering the responsibility for the full gauntlet of network functionality.  They execute transactions, perform consensus, and maintain the shared ledger.  Not only does this configuration lay a huge computational burden on each peer, hindering scalability, but it also constricts important facets of privacy and confidentiality.  Namely, there is no mechanism to “channel” or “silo” confidential transactions.  Every peer can see the logic for every transaction.

## WHERE WE'RE GOING

The new architecture introduces a clear functional separation of peer roles, and allows a transaction to pass through the network in a structured and modularized fashion.  The peers are diverged into two distinct roles – Endorser & Committer.  As an endorser, the peer will simulate the transaction and ensure that the outcome is deterministic or stable.  As a committer, the peer will validate the integrity of a transaction and then append to the ledger.  Now confidential transactions can be sent to specific endorsers and their correlating committers, without the network being made cognizant of the transaction.  Additionally, policies can be set to determine what levels of “endorsement” and “validation” are acceptable for a specific class of transactions.  A failure to meet these thresholds would simply result in a transaction being thrown out, rather than imploding or stagnating the entire network.  This new model also introduces the possibility for more elaborate networks, such as a foreign exchange market.  Entities may need to only participate as endorsers for their transactions, while leaving consensus and commitment (i.e. settlement) to a trusted third party such as a clearing house.

The consensus process (i.e. algorithmic computation) is entirely abstracted from the peer.  This modularity not only provides a powerful security layer – the consenting nodes are agnostic to the transaction logic – but it also generates a framework where consensus can become pluggable and scalability can truly occur.  There is no longer a parallel relationship between the number of peers in a network and the number of consenters.  Now networks can grow dynamically (i.e. add endorsers and committers) without having to add corresponding consenters, and exist in a modular infrastructure designed to support high transaction throughput.  Moreover, networks now have the capability to completely liberate themselves from the computational and legal burden of consensus by tapping into a pre-existing consensus cloud.

As V1 manifests, we will see the foundation for interoperable blockchain networks that have the ability to scale and transact in a manner adherent with regulatory and industry standards.  The following is a high-level overview of the upcoming additions to the fabric codebase that will spawn the capabilities in V1:

## HOW TO CONTRIBUTE

1. Familiarize yourself with the [guidelines for code contributions](CONTRIBUTING.md) to this project.  **Note**: In order to participate in the development of the Hyperledger Fabric project, you will need an [LF account](Gerrit/lf-account.md). This will give you single
sign-on to JIRA and Gerritt.
1. Explore the design document for the new [architecture](https://github.com/hyperledger-archives/fabric/wiki/Next-Consensus-Architecture-Proposal)
1. Explore [JIRA](https://jira.hyperledger.org/projects/FAB/issues/) for open Hyperledger Fabric issues.
1. Explore the [JIRA](https://jira.hyperledger.org/projects/FAB/issues/) backlog for upcoming Hyperledger Fabric issues.
1. Explore [JIRA](https://jira.hyperledger.org/issues/?filter=10147) for Hyperledger Fabric issues tagged with "help wanted."
1. Explore the [source code](https://github.com/hyperledger/fabric)
1. Explore the [documentation](http://hyperledger-fabric.readthedocs.io/en/latest/)
