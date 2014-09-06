# Copyright (C) 2014 Peter Todd <pete@petertodd.org>
#
# This file is part of python-merbinnertree.
#
# It is subject to the license terms in the LICENSE file found in the top-level
# directory of this distribution.
#
# No part of python-merbinnertree, including this file, may be copied,
# modified, propagated, or distributed except according to the terms contained
# in the LICENSE file.

import hashlib

def make_MerbinnerTree_baseclass(basecls=object):
    class MerbinnerTree(basecls):
        """Immutable merklized binary radix tree"""
        __slots__ = ['_mt_cached_hash']

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
                leaf_nodes = [cls.FullLeafNodeClass(k, v) for k,v in items]
                return cls.InnerNodeClass._mt_from_leaf_nodes(leaf_nodes, 0)

        @property
        def hash(self):
            try:
                return self._mt_cached_hash
            except AttributeError:
                object.__setattr__(self, '_mt_cached_hash', self.calc_hash_data())
                return self._mt_cached_hash

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
        def key_side(cls, key, depth):
            return key[depth // 8] >> (7 - depth % 8) & 0b1

        def calc_hash_data(self):
            """Calculate the data that is hashed to produce the node hash"""
            raise NotImplementedError

        def _mt_get_keys(self, result, keys, depth, prove):
            """Internal: get keys from a branch in the tree

            For each matching InnerNode result[key] is set to that node, which
            may or may not be pruned. Missing keys do *not* raise an error.

            Returns pruned_tree if prove=True, where pruned_tree is a pruned
            version of self that can satisfy the request.
            """
            raise NotImplementedError

        def prove_existence(self, keys):
            """Prove the existence or non-existence of one or more keys in the tree"""

        def __getitem__(self, key):
            """Return value associated with key"""
            self.check_key(key)
            result = {}
            self._mt_get_keys(result, (key,), 0, False)

            # Note how if the key is not found, this will return the KeyError
            # for us.
            found_node = result[key]

            try:
                return found_node.value
            except AttributeError:
                # Node was pruned, so we don't have the value available to us
                # even though we could confirm that the key is present in the
                # tree.
                assert isinstance(found_node, self.PrunedLeafNodeClass)
                raise PrunedError

        def __contains__(self, key):
            self.check_key(key)
            result = {}
            self._mt_get_keys(result, (key,), 0, False)

            try:
                found_node = result[key]
            except KeyError:
                # FIXME: do we really need to do this?
                return False
            else:
                return True

        def _mt_put_keys(self, changed_keys, items, depth, prove):
            """Internal: change key(s) to specified node(s)

            Changing a key to an EmptyNodeClass instance has the effect of
            removing it.

            Returns (new_tree, pruned_tree)
            """
            raise NotImplementedError

        def put(self, key, value):
            """Set key to value

            Returns a new tree with that key set.
            """
            self.check_key(key)
            self.check_value(value)

            leaf_node = self.FullLeafNodeClass(key, value)

            changed_keys = set()
            (new_tree, ignored) = self._mt_put_keys(changed_keys, [(key, leaf_node)], 0, False)
            assert len(changed_keys) <= 1

            # Check that the put was successful
            if key not in changed_keys:
                raise KeyError(key)

            return new_tree

        def put_value_hash(self, key, value_hash):
            """Set key to a value hash

            Returns a new tree with that key set. This tree will be a pruned
            tree.
            """
            raise NotImplementedError

        def remove(self, key):
            """Remove key from tree"""
            self.check_key(key)

            changed_keys = set()
            (new_tree, ignored) = self._mt_put_keys(changed_keys, [(key, self.EmptyNodeClass())], 0, False)

            # Check that the remove was succesful
            if key not in changed_keys:
                raise KeyError(key)

            return new_tree

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

        def _mt_iter_nodes(self):
            """Iterate through all nodes in the tree

            Ordering is depth-first: left-node, right-node, then self
            """
            yield self

        # FIXME: do we care that what the following return isn't "set-like"?
        def keys(self):
            for node in self._mt_iter_nodes():
                try:
                    yield node.key
                except AttributeError:
                    continue

        def values(self):
            for node in self._mt_iter_nodes():
                try:
                    yield node.value
                except AttributeError:
                    continue

        def items(self):
            for node in self._mt_iter_nodes():
                try:
                    yield (node.key, node.value)
                except AttributeError:
                    continue

    return MerbinnerTree

def make_MerbinnerTree_class(treecls):
    treecls._mt_baseclass = treecls
    class MerbinnerTreeEmptyNodeClass(treecls):
        __slots__ = []

        __instance = None
        def __new__(cls):
            if cls.__instance is None:
                cls.__instance = object.__new__(cls)

            return cls.__instance

        def _mt_get_keys(self, result, keys, depth, prove):
            # Regardless of what keys are being requested, if any, return self
            # as we can prove the existence or non-existence of that set of
            # keys.
            return self

        def _mt_put_keys(self, changed_keys, items, depth, prove):
            # There's no keys in this part of the tree, so any non-empty items
            # can be simply passed to _mt_from_leaf_nodes() to create a new
            # tree populated with them. Empty items meanwhile indicate that the
            # callee was attempting to remove a key from the tree, which
            # obviously failed.

            leaf_nodes = []
            # Remember that the EmptyNodeClass is a singleton.
            for key, node in items:
                if node is not self:
                    changed_keys.add(key)
                    leaf_nodes.append(node)

            # _mt_from_leaf_nodes() handles the empty and len(leaf_nodes) == 1
            # cases for us. new_tree is replacing us, so the correct depth is
            # our depth, not depth+1
            new_tree = self.InnerNodeClass._mt_from_leaf_nodes(leaf_nodes, depth)

            # In all circumstances the pruned tree required to
            # perform this operation is ourselves - you can always add keys to
            # an empty node.
            return (new_tree, self)


        def _mt_update(self, tree, depth):
            return tree

        def _mt_merge(self, tree, depth):
            return tree

        def calc_hash_data(self):
            """Calculate the data that is hashed to produce the node hash"""
            return b'\x00'
    treecls.EmptyNodeClass = MerbinnerTreeEmptyNodeClass

    class MerbinnerTreeInnerNodeClass(treecls):
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

        def calc_hash_data(self):
            """Calculate the data that is hashed to produce the node hash"""
            return self.left.hash + self.right.hash + b'\x01'

        @classmethod
        def _mt_from_leaf_nodes(cls, leaf_nodes, depth):
            if len(leaf_nodes) > 1:
                left_leaves = []
                right_leaves = []

                for leaf_node in leaf_nodes:
                    if cls.key_side(leaf_node.key, depth):
                        left_leaves.append(leaf_node)
                    else:
                        right_leaves.append(leaf_node)

                left = cls._mt_from_leaf_nodes(left_leaves, depth+1)
                right = cls._mt_from_leaf_nodes(right_leaves, depth+1)
                return cls.InnerNodeClass(left, right)

            elif len(leaf_nodes) == 1:
                return leaf_nodes[0]

            else:
                return cls.EmptyNodeClass()

        def _mt_get_keys(self, result, keys, depth, prove):
            if len(keys):
                left_keys = []
                right_keys = []

                for key in keys:
                    if self.key_side(key, depth):
                        left_keys.append(key)
                    else:
                        right_keys.append(key)

                pruned_left_node = self.left._mt_get_keys(result, left_keys, depth+1, prove)
                pruned_right_node = self.right._mt_get_keys(result, right_keys, depth+1, prove)

                if prove:
                    return self.InnerNodeClass(pruned_left_node, pruned_right_node)

            elif prove:
                return self.PrunedInnerNodeClass.from_inner_node(self)

        def _mt_put_keys(self, changed_keys, items, depth, prove):
            if len(items):
                # Split items up into left and right
                left_items = []
                right_items = []
                for item in items:
                    if self.key_side(item[0], depth):
                        left_items.append(item)
                    else:
                        right_items.append(item)

                # Our left and right sides can now recursively handle left and
                # right items
                new_left_node, pruned_left_node = self.left._mt_put_keys(changed_keys, left_items, depth+1, prove)
                new_right_node, pruned_right_node = self.right._mt_put_keys(changed_keys, right_items, depth+1, prove)

                # It's possible nothing has changed if the callee was trying to
                # remove items that aren't present in the tree. Check for that
                # case - cheap! - and don't unnecessarily create new objects.
                new_node = self
                if new_left_node is not self.left or new_right_node is not self.right:
                    new_node = self.InnerNodeClass(new_left_node, new_right_node)

                pruned_node = None
                if prove:
                    # The pruned_node necessary to prove this put may also be
                    # unchanged.
                    if pruned_left_node is not self.left or pruned_right_node is not self.right:
                        pruned_node = self.InnerNodeClass(pruned_left_node, pruned_right_node)

                return (new_node, pruned_node)

            else:
                pruned_node = None
                if prove:
                    # No items were changed, which means the minimum
                    # information to prove that is the pruned version of
                    # ourselves.
                    pruned_node = self.PrunedInnerNodeClass.from_inner_node(self)

                return (self, pruned_node)

        def _mt_update(self, tree, depth):
            raise NotImplementedError

        def _mt_merge(self, tree, depth):
            raise NotImplementedError

        def _mt_iter_nodes(self):
            yield from self.left._mt_iter_nodes()
            yield from self.right._mt_iter_nodes()
            yield self



    treecls.InnerNodeClass = MerbinnerTreeInnerNodeClass

    class MerbinnerTreePrunedInnerNodeClass(treecls):
        __slots__ = ['pruned_hash']
        def __new__(cls, pruned_hash):
            self = object.__new__(cls)
            object.__setattr__(self, 'pruned_hash', pruned_hash)
            return self

        def _mt_get_keys(self, key, depth):
            raise self.PrunedError('get', key, depth)

        def _mt_get_keys(self, result, keys, depth, ignore_missing=False, prove=False):
            if len(keys):
                raise self.PrunedError('get', key, depth)
            else:
                return self

        def _mt_put_keys(self, changed_keys, items, depth, prove):
            if len(items):
                # We're pruned, so we don't have the information necessary to
                # change anything in this part of the tree.
                raise self.PrunedError('set', key, depth)

            else:
                # However we do have the information necessary to do nothing.
                return (self, self)

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
            if not isinstance(tree, MerbinnerTreePrunedInnerNodeClass):
                # Other tree is something other than a pruned inner node, so it
                # must have more information than we do.
                return tree

            else:
                # Otherwise return ourself so that self.merge(tree) is self
                return self
    treecls.PrunedInnerNodeClass = MerbinnerTreePrunedInnerNodeClass

    class MerbinnerTreeLeafNodeClass(treecls):
        __slots__ = ['key']

        def _mt_get_keys_common(self, result, keys, depth, ignore_missing=False, prove=False):
            found_match = False
            for key in keys:
                if self.key == key:
                    found_match = True
                    result[key] = self
                    break

            return found_match

        def _mt_put_keys(self, changed_keys, items, depth, prove):
            # Similar to the EmptyNode implementation, we can let
            # _mt_from_leaf_nodes() do all the real work.

            # All empty items where the callee was trying to remove a key from
            # the tree can be filtered out of items as those keys obviously
            # don't exist.
            add_ourself = True
            leaf_nodes = []
            for key, new_node in items:
                # If our key is present in items we're being modified, so we
                # don't want to add ourselves to the list of leaf_nodes
                if add_ourself and self.key == key:
                    # This does however mean that our key is now changed.
                    changed_keys.add(key)
                    add_ourself = False

                if not isinstance(new_node, self.EmptyNodeClass):
                    changed_keys.add(key)
                    leaf_nodes.append(new_node)

            if add_ourself:
                leaf_nodes = [self] + leaf_nodes

            # _mt_from_leaf_nodes() handles the empty and len(leaf_nodes) == 1
            # cases for us. new_tree is replacing us, so the correct depth is
            # our depth, not depth+1
            new_tree = self.InnerNodeClass._mt_from_leaf_nodes(leaf_nodes, depth)

            pruned_tree = None
            if prove:
                # The pruned version of this node is the information necessary
                # to perform this put operation.
                if isinstance(pruned_tree, self.FullLeafNodeClass):
                    pruned_tree = self.PrunedLeafNodeClass.from_FullLeafNode(self)
                else:
                    pruned_tree = self

            return (new_tree, pruned_tree)

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

    treecls.LeafNodeClass = MerbinnerTreeLeafNodeClass

    class MerbinnerTreeFullLeafNodeClass(MerbinnerTreeLeafNodeClass):
        __slots__ = ['value']
        def __new__(cls, key, value):
            self = object.__new__(cls)
            object.__setattr__(self, 'key', key)
            object.__setattr__(self, 'value', value)
            return self

        def _mt_get_keys(self, result, keys, depth, ignore_missing=False, prove=False):
            found_match = self._mt_get_keys_common(result, keys, depth, ignore_missing, prove)
            if found_match:
                return self

            elif prove:
                return self.PrunedLeafNodeClass.from_FullLeafNode(self)

        def _mt_merge(self, tree, depth):
            # merge() checked that self and tree are the same, so tree must be
            # a leaf node.
            assert isinstance(tree, self.LeafNodeClass)

            # Since we're a full leaf, tree can't have more information than we
            # do, so return self to avoid unnecessarily creating extra objects.
            return self

        def calc_hash_data(self):
            return self.calc_value_hash(self.value) + self.key + b'\x02'

    treecls.FullLeafNodeClass = MerbinnerTreeFullLeafNodeClass

    class MerbinnerTreePrunedLeafNodeClass(MerbinnerTreeLeafNodeClass):
        __slots__ = ['value_hash']
        def __new__(cls, key, value_hash):
            self = object.__new__(cls)
            object.__setattr__(self, 'key', key)
            object.__setattr__(self, 'value_hash', value_hash)
            return self

        @classmethod
        def from_FullLeafNode(cls, full_leaf_node):
            return cls(full_leaf_node.key, cls.calc_value_hash(full_leaf_node.value))

        def _mt_get_keys(self, result, keys, depth, ignore_missing=False, prove=False):
            self._mt_get_keys_common(result, keys, depth, ignore_missing, prove)

            # Whether or not a match is found is irrelevant; the best we can do
            # is return ourselves as we're pruned.
            return self

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

        def calc_hash_data(self):
            return self.value_hash + self.key + b'\x02'


    treecls.PrunedLeafNodeClass = MerbinnerTreePrunedLeafNodeClass

    return treecls


@make_MerbinnerTree_class
class SHA256MerbinnerTree(make_MerbinnerTree_baseclass()):
    __slots__ = []
    KEYSIZE = 32

    @classmethod
    def check_value(cls, value):
        if not isinstance(value, bytes):
            raise TypeError('value must be bytes instance; got %r instead' % value.__class__)

    @staticmethod
    def hash_func(data):
        return hashlib.sha256(data).digest()

    @staticmethod
    def calc_value_hash(value):
        return hashlib.sha256(value).digest()
