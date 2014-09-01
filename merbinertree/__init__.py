# Copyright (C) 2014 Peter Todd <pete@petertodd.org>
#
# This file is part of python-merbinertree.
#
# It is subject to the license terms in the LICENSE file found in the top-level
# directory of this distribution.
#
# No part of python-merbinertree, including this file, may be copied, modified,
# propagated, or distributed except according to the terms contained in the
# LICENSE file.

import hashlib

def make_MerbinerTree_baseclass(basecls=object):
    class MerbinerTree(basecls):
        """Immutable merklized binary radix tree"""
        __slots__ = []

        _mt_baseclass = None

        def __setattr__(self, name, value):
            raise AttributeError('Object is immutable')

        def __delattr__(self, name):
            raise AttributeError('Object is immutable')

        class PrunedError(Exception):
            def __init__(msg, key, depth):
                super(PrunedError, self).__init__(msg)
                self.key = key
                self.depth = depth

        def __new__(cls, items=None):
            if items is None:
                return cls.EmptyNodeClass()

            else:
                return cls.from_items(items)

        @classmethod
        def check_key(cls, key):
            if not isinstance(key, bytes):
                raise TypeError('key must be bytes instance; got %r instead' % key.__class__)
            if len(key) != cls.KEYSIZE:
                raise ValueError('key must be exactly %d bytes long; got %d bytes instead' % (cls.KEYSIZE, len(key)))

        @classmethod
        def check_value(cls, value):
            raise NotImplementedError

        @classmethod
        def from_items(cls, items):
            raise NotImplementedError

        @classmethod
        def key_side(cls, key, depth):
            return key[depth // 8] >> (7 - depth % 8) & 0b1

        def _mt_get(self, keys, depth):
            """Internal implementation of get()"""
            raise NotImplementedError

        def __getitem__(self, key):
            """Return value associated with key"""
            self.check_key(key)
            return self._mt_get(key, 0)

        def __contains__(self, key):
            # FIXME: working?
            try:
                self[key]
            except KeyError:
                return False
            else:
                return True

        def _mt_put(self, leaf_node, depth):
            """Internal implementation of put() and put_value_hash()"""
            raise NotImplementedError

        def put(self, key, value):
            """Set key to value

            Returns a new tree with that key set.
            """
            self.check_key(key)
            self.check_value(value)
            leaf_node = self.FullLeafNodeClass(key, value)
            return self._mt_put(leaf_node, 0)

        def put_value_hash(self, key, value_hash):
            """Set key to a value hash

            Returns a new tree with that key set. This tree will be a pruned
            tree.
            """
            self.check_key(key)
            self.check_value_hash(value_hash)
            leaf_node = self.PrunedLeafNodeClass(key, value_hash)
            return self._mt_put(key, leaf_node, 0)


        def _mt_remove(self, key, depth):
            """Internal implementation of remove()"""
            raise NotImplementedError

        def remove(self, key):
            """Remove key from tree"""
            self.check_key(key)
            return self._mt_remove(key, 0)


        def _mt_update(self, tree, depth):
            """Internal implementation of update()"""
            raise NotImplementedError

        def update(self, tree):
            """Update """
            if not ininstance(tree, self.__class__.__base__):
                raise TypeError('trees are of different classes')
            return self._mt_update(tree, 0)

        def _mt_merge(self, tree, depth):
            """Internal implementation of merge()"""
            raise NotImplementedError

        def merge(self, tree):
            """Merge two pruned trees together"""
            if not ininstance(tree, self.__class__.__base__):
                raise TypeError("Can't merge: trees are of different classes")
            if self.hash != tree.hash:
                raise ValueError("Can't merge: trees have different hashes")
            return self._mt_merge(tree, 0)

    return MerbinerTree

def make_MerbinerTree_class(treecls):
    treecls._mt_baseclass = treecls
    class MerbinerTreeEmptyNodeClass(treecls):
        __slots__ = []

        __instance = None
        def __new__(cls):
            if cls.__instance is None:
                cls.__instance = object.__new__(cls)

            return cls.__instance

        def _mt_get(self, key, depth):
            raise KeyError(key)

        def _mt_put(self, leaf_node, depth):
            return leaf_node

        def _mt_remove(self, key, depth):
            raise KeyError(key)

        def _mt_update(self, tree, depth):
            return tree

        def _mt_merge(self, tree, depth):
            return tree
    treecls.EmptyNodeClass = MerbinerTreeEmptyNodeClass

    class MerbinerTreeInnerNodeClass(treecls):
        __slots__ = ['left', 'right']
        def __new__(cls, left, right):
            # Ensure attempts to create deeper than necessary inner nodes fail
            # and instead return the depth-optimized version instead.
            if isinstance(left, cls.EmptyNodeClass) and isinstance(right, (cls.EmptyNodeClass, cls.LeafNodeClass)):
                return right

            elif isinstance(right, cls.EmptyNodeClass) and isinstance(left, (cls.EmptyNodeClass, cls.LeafNodeClass)):
                return left

            # Ensure that if left and right are leaf nodes they are on the correct sides
            assert (not (isinstance(left, cls.LeafNodeClass) and isinstance(right, cls.LeafNodeClass))
                    or left.key > right.key)

            self = object.__new__(cls)
            object.__setattr__(self, 'left', left)
            object.__setattr__(self, 'right', right)
            return self

        @classmethod
        def from_leaf_nodes(cls, leaf_nodes, depth):
            if len(leaf_nodes) > 1:
                left_leaves = []
                right_leaves = []

                for leaf_node in leaf_nodes:
                    if cls.key_side(leaf_node.key, depth):
                        left_leaves.append(leaf_node)
                    else:
                        right_leaves.append(leaf_node)

                left = cls.from_leaf_nodes(left_leaves, depth+1)
                right = cls.from_leaf_nodes(right_leaves, depth+1)
                return cls.InnerNodeClass(left, right)

            elif len(leaf_nodes) == 1:
                return leaf_nodes[0]

            else:
                return cls.EmptyNodeClass()

        def _mt_get(self, key, depth):
            if self.key_side(key, depth):
                return self.left._mt_get(key, depth+1)
            else:
                return self.right._mt_get(key, depth+1)

        def _mt_put(self, leaf_node, depth):
            new_left = self.left
            new_right = self.right

            if self.key_side(leaf_node.key, depth):
                new_left = self.left._mt_put(leaf_node, depth+1)
            else:
                new_right = self.right._mt_put(leaf_node, depth+1)

            if (new_left is not self.left) or (new_right is not self.right):
                return self.InnerNodeClass(new_left, new_right)
            else:
                return self

        def _mt_remove(self, key, depth):
            new_left = self.left
            new_right = self.right

            if self.key_side(key, depth):
                new_left = self.left._mt_remove(key, depth+1)
            else:
                new_right = self.right._mt_remove(key, depth+1)

            assert new_left is not self.left or new_right is not self.right
            return self.InnerNodeClass(new_left, new_right)

        def _mt_update(self, tree, depth):
            raise NotImplementedError

        def _mt_merge(self, tree, depth):
            raise NotImplementedError

    treecls.InnerNodeClass = MerbinerTreeInnerNodeClass

    class MerbinerTreePrunedInnerNodeClass(treecls):
        __slots__ = ['pruned_hash']
        def __new__(cls, pruned_hash):
            self = object.__new__(cls)
            object.__setattr__(self, 'pruned_hash', pruned_hash)
            return self

        def _mt_get(self, key, depth):
            raise self.PrunedError('get', key, depth)

        def _mt_put(self, leaf_node, depth):
            raise self.PrunedError('set', key, depth)

        def _mt_remove(self, key, depth):
            raise self.PrunedError('remove', key, depth)

        def _mt_update(self, tree, depth):
            if self.hash == tree.hash:
                # Updating with a tree that is equivalent to us. Return self so
                # that we don't unnecessarily increase the infromation stored
                # in the tree by updating. (the other tree may be less pruned
                # than we are)
                return self

            else:
                # FIXME: what should key be here?
                raise self.PrunedError('update', key, depth)

        def _mt_merge(self, tree, depth):
            if not isinstance(tree, MerbinerTreePrunedInnerNodeClass):
                # Other tree is something other than a pruned inner node, so it
                # must have more information than we do.
                return tree

            else:
                # Otherwise return ourself so that self.merge(tree) is self
                return self
    treecls.PrunedInnerNodeClass = MerbinerTreePrunedInnerNodeClass

    class MerbinerTreeLeafNodeClass(treecls):
        __slots__ = ['key']
        def _mt_put(self, leaf_node, depth):
            # FIXME: return self if both are exactly equal
            if self.key == leaf_node.key:
                return leaf_node

            else:
                # Note how the depth is *not* increased by one, as the inner
                # node is replacing the node at this level.
                return self.InnerNodeClass.from_leaf_nodes((self, leaf_node), depth)

        def _mt_remove(self, key, depth):
            if self.key == key:
                return self.EmptyNodeClass()
            else:
                raise KeyError(key)

        def _mt_update(self, tree, depth):
            if self.hash == tree.hash:
                # Updating with a tree that is equivalent to us. Return self so
                # that we don't unnecessarily increase the infromation stored
                # in the tree by updating. (the other tree may be less pruned
                # than we are)
                return self

            else:
                # FIXME: what should key be here?
                raise self.PrunedError('update', key, depth)

    treecls.LeafNodeClass = MerbinerTreeLeafNodeClass

    class MerbinerTreeFullLeafNodeClass(MerbinerTreeLeafNodeClass):
        __slots__ = ['value']
        def __new__(cls, key, value):
            self = object.__new__(cls)
            object.__setattr__(self, 'key', key)
            object.__setattr__(self, 'value', value)
            return self

        def _mt_get(self, key, depth):
            if self.key == key:
                return self.value
            else:
                raise KeyError(key)

        def _mt_remove(self, key, depth):
            if self.key == key:
                return self.EmptyNodeClass()
            else:
                raise KeyError(key)

        def _mt_merge(self, tree, depth):
            # merge() checked that self and tree are the same, so tree must be
            # a leaf node.
            assert isinstance(tree, self.LeafNodeClass)

            # Since we're a full leaf, tree can't have more information than we
            # do, so return self to avoid unnecessarily creating extra objects.
            return self


    treecls.FullLeafNodeClass = MerbinerTreeFullLeafNodeClass

    class MerbinerTreePrunedLeafNodeClass(MerbinerTreeLeafNodeClass):
        __slots__ = ['value_hash']
        def __new__(cls, key, value):
            self = object.__new__(cls)
            object.__setattr__(self, 'key', key)
            object.__setattr__(self, 'value', value)
            return self

        def _mt_get(self, key, depth):
            if self.key == key:
                return self.value
            else:
                raise KeyError(key)

        def _mt_remove(self, key, depth):
            if self.key == key:
                return self.EmptyNodeClass()
            else:
                raise KeyError(key)

        def _mt_merge(self, tree, depth):
            # merge() checked that self and tree are the same, so tree must be
            # a leaf node.
            assert isinstance(tree, self.LeafNodeClass)

            # We're a pruned leaf, so if tree is a full leaf, return it for
            # more info.
            if isinstance(tree, self.FullLeafNodeClass):
                return tree

            else:
                # Otherwise return self to avoid creating new objects
                # unnecessarily.
                return self

    treecls.PrunedLeafNodeClass = MerbinerTreePrunedLeafNodeClass


    return treecls


@make_MerbinerTree_class
class SHA256MerbinerTree(make_MerbinerTree_baseclass()):
    __slots__ = []
    KEYSIZE = 32

    @classmethod
    def check_value(cls, value):
        if not isinstance(value, bytes):
            raise TypeError('value must be bytes instance; got %r instead' % value.__class__)

    @staticmethod
    def hash_func(data):
        return hashlib.sha256(data).digest()
