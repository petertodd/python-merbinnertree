python-merbinertree
===================

This Python3 library implements a form of Merklized Binary Radix Tree called a
"Merbiner Tree". Like a standard merkle tree a Merbiner Tree is a cryptographic
data structure that securely and efficiently commits a set of items such that
the existence of a given item in the set can be efficiently proven. Unlike a
merkle tree these items are key:value pairs, forming a map/dictionary, allowing
one to also efficently prove that a given key does *not* exist.

Items in a merbiner tree can be efficiently updated and removed, creating a new
tree. Merbiner trees can also be pruned, resulting in a tree that can prove a
subset of the operations the unpruned tree can prove.


Design Goals
============

* Reasonable performance in space and time for both large and small number of
  items.

* Simple implementation.

* Deterministic: any key modification ordering should result in same tree.

* Assume key and value are hashes - long key collisions essentially impossible.

* Must be cryptographically secure and without collisions even in the face of
  an adversary.


Why not pure merkle binary radix tree? Makes things simplier, but requires
about an order of magnitude more hashes. (e.g. 20bit ~= 1million items vs
256bit)


Supported Operations
====================

get
===


put
===

set key:value


remove
======

remove key from tree


closest
=======

Return the key:value pair whose key is closest (rounding?) to a given key.


merge
=====

Merge two pruned trees together, resulting in a tree that can prove the
superset of operations the two pruned trees supported.


update
======

Update one tree with another.



Postfix Key Compression
=======================

Compromise between a standard radix tree and a pure merkle binary radix tree.
When keys are hashes it's infeasible to find long collisions, limiting maximum
proof size, good engineering. Also radix key compression becomes useless.


Types of Nodes
==============

Empty Node
==========

Contains: Nothing

Hashed: <0x00>

Signifies that this part of the tree has nothing in it.

Leaf Node
=========

Contains: key and H(value)

Hashed: <key> <H(value)> <0x01>


Inner Node
==========

Contains: left and right child nodes

Hashed: {H(sums)} <left> <right> <0x02>



Pruned Inner Node
=================

Contains: hash

Signifies that this part of the tree contains an inner node, however the
contents have been pruned. We can't modify these contents, nor do we know
what's in them.




Full Leaf Node
==============

Contains: key and value





Unit Tests
==========

python3 -m unittest discover -s merbinertree
