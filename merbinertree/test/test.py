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

import os
import random
import unittest

from merbinertree import SHA256MerbinerTree

def k(key):
    return key.ljust(32, b'\x00')

TestTree = SHA256MerbinerTree

class Test_MerbinerTree(unittest.TestCase):
    def test_empty(self):
        tree = TestTree()

        self.assertIsInstance(tree, TestTree.EmptyNodeClass)

        with self.assertRaises(KeyError):
            tree[k(b'\x00')]

    def test_hash(self):
        ta = TestTree()
        tb = TestTree()
        self.assertEqual(ta.hash, tb.hash)

        # add identical items, leading to identical trees
        ta = ta.put(k(b'\x00'), b'a')
        tb = tb.put(k(b'\x00'), b'a')
        self.assertFalse(ta is tb)
        self.assertEqual(ta.hash, tb.hash)

        # make b tree different
        tb = tb.put(k(b'\x00'), b'b')
        self.assertNotEqual(ta.hash, tb.hash)

        # add another item, still different
        ta2 = ta.put(k(b'\xff'), b'b')
        tb2 = tb.put(k(b'\xff'), b'b')
        self.assertNotEqual(ta2.hash, tb2.hash)

        # make b tree the same again
        tb2 = tb2.put(k(b'\x00'), b'a')
        self.assertEqual(ta2.hash, tb2.hash)

    def test_put_new_key(self):
        t0 = TestTree()

        # Empty -> Leaf
        t1 = t0.put(k(b'\x00'), b'a')
        self.assertEqual(t1[k(b'\x00')], b'a')
        self.assertIsInstance(t1, TestTree.FullLeafNodeClass)

        # Leaf -> Inner(Leaf, Leaf)
        t2 = t1.put(k(b'\xff'), b'b')
        self.assertEqual(t2[k(b'\x00')], b'a')
        self.assertEqual(t2[k(b'\xff')], b'b')
        self.assertIsInstance(t2, TestTree.InnerNodeClass)

        # As above, but with the keys reversed to ensure everything is ending
        # up on the correct sides.
        #
        # Empty -> Leaf
        t1 = t0.put(k(b'\xff'), b'a')
        self.assertEqual(t1[k(b'\xff')], b'a')
        self.assertIsInstance(t1, TestTree.FullLeafNodeClass)

        # Leaf -> Inner(Leaf, Leaf)
        t2 = t1.put(k(b'\x00'), b'b')
        self.assertEqual(t2[k(b'\xff')], b'a')
        self.assertEqual(t2[k(b'\x00')], b'b')
        self.assertIsInstance(t2, TestTree.InnerNodeClass)

        # As above, but both keys colliding on the first bit.
        t1 = t0.put(k(b'\xff'), b'a')
        t2 = t1.put(k(b'\x80'), b'b')
        self.assertIsInstance(t2.left, TestTree.InnerNodeClass)
        self.assertIsInstance(t2.right, TestTree.EmptyNodeClass)
        self.assertEqual(t2.left.left.key, k(b'\xff'))
        self.assertEqual(t2.left.right.key, k(b'\x80'))
        self.assertEqual(t2[k(b'\xff')], b'a')
        self.assertEqual(t2[k(b'\x80')], b'b')

        # 8 bit deep collision
        t1 = t0.put(k(b'\xff\x80'), b'a')
        t2 = t1.put(k(b'\xff\x00'), b'b')
        self.assertIsInstance(t2.left.left.left.left.left.left.left.right, TestTree.EmptyNodeClass)
        self.assertIsInstance(t2.left.left.left.left.left.left.left.left.left, TestTree.FullLeafNodeClass)
        self.assertIsInstance(t2.left.left.left.left.left.left.left.left.right, TestTree.FullLeafNodeClass)
        self.assertEqual(t2[k(b'\xff\x80')], b'a')
        self.assertEqual(t2[k(b'\xff\x00')], b'b')
        with self.assertRaises(KeyError):
            t2[k(b'\x00')]

    def test_put_existing_key(self):
        t0 = TestTree()

        # Empty -> Leaf
        t1 = t0.put(k(b'\x00'), b'a')
        self.assertEqual(t1[k(b'\x00')], b'a')
        self.assertIsInstance(t1, TestTree.FullLeafNodeClass)

        # Leaf 'a' -> Leaf 'b'
        t2 = t1.put(k(b'\x00'), b'b')
        self.assertEqual(t2[k(b'\x00')], b'b')
        self.assertIsInstance(t2, TestTree.FullLeafNodeClass)

        # Add second key
        t3 = t2.put(k(b'\xff'), b'c')
        self.assertEqual(t3[k(b'\x00')], b'b')
        self.assertEqual(t3[k(b'\xff')], b'c')

        # Change second key's value
        t4 = t3.put(k(b'\xff'), b'd')
        self.assertEqual(t4[k(b'\x00')], b'b')
        self.assertEqual(t4[k(b'\xff')], b'd')

        # Create an 8-bit deep collision and try changing a value
        t5 = t4.put(k(b'\xff\x80'), b'e')
        t6 = t5.put(k(b'\xff\x00'), b'd2')
        self.assertEqual(t6[k(b'\xff\x80')], b'e')
        self.assertEqual(t6[k(b'\xff\x00')], b'd2')

        t7 = t6.put(k(b'\xff\x80'), b'e2')
        self.assertEqual(t7[k(b'\xff\x80')], b'e2')

    def test___contains__(self):
        t0 = TestTree()

        self.assertNotIn(k(b'\x00'), t0)
        self.assertNotIn(k(b'\x01'), t0)

        t1 = t0.put(k(b'\x00'), b'a')
        self.assertIn(k(b'\x00'), t1)
        self.assertNotIn(k(b'\x01'), t1)

    def test___contains___with_invalid_keys(self):
        t0 = TestTree()

        with self.assertRaises(TypeError):
            1 in t0

        with self.assertRaises(ValueError):
            b'' in t0

    def test_remove(self):
        t0 = TestTree()

        # removing a non-existing key from an EmptyNode doesn't work
        with self.assertRaises(KeyError):
            t0.remove(k(b'\x00'))

        # remove a key from a LeafNode
        t1 = t0.put(k(b'\x00'), b'a')
        t2 = t1.remove(k(b'\x00'))
        self.assertNotIn(k(b'\x00'), t2)
        with self.assertRaises(KeyError):
            t2.remove(k(b'\x00'))

        # t2 is now identical to our starting tree
        self.assertEqual(t2.hash, t0.hash)

        # remove a key from an InnerNode(Leaf, Leaf)
        t1 = t0.put(k(b'\x00'), b'a')
        t2 = t1.put(k(b'\xff'), b'b')

        t3 = t2.remove(k(b'\x00'))
        self.assertNotIn(k(b'\x00'), t3)
        self.assertEqual(t3[k(b'\xff')], b'b')

        t4 = t3.remove(k(b'\xff'))
        self.assertNotIn(k(b'\x00'), t4)
        self.assertNotIn(k(b'\xff'), t4)

        self.assertEqual(t4.hash, t0.hash)

        # Remove a key from a deep leaf
        t1 = t0.put(k(b'\x00\x00'), b'a')
        t2 = t1.put(k(b'\x00\x01'), b'b')
        self.assertEqual(t2[k(b'\x00\x00')], b'a')
        self.assertEqual(t2[k(b'\x00\x01')], b'b')

        t3 = t2.remove(k(b'\x00\x00'))
        self.assertNotIn(k(b'\x00\x00'), t3)
        self.assertEqual(t3[k(b'\x00\x01')], b'b')

        t4 = t3.remove(k(b'\x00\x01'))
        self.assertNotIn(k(b'\x00\x00'), t4)
        self.assertNotIn(k(b'\x00\x01'), t4)

        self.assertEqual(t4.hash, t0.hash)

    def test_random_puts_removes(self):
        expected_contents = set()

        tree = TestTree()
        def grow(grow_prob, n):
            nonlocal tree
            for i in range(n):
                if random.random() < grow_prob:
                    new_item = (os.urandom(32), os.urandom(32))
                    expected_contents.add(new_item)
                    tree = tree.put(new_item[0], new_item[1])

                elif len(expected_contents) > 0:
                    del_item = expected_contents.pop()
                    tree = tree.remove(del_item[0])

        def modify(n):
            nonlocal tree
            for i in range(n):
                k, old_value = expected_contents.pop()
                new_value = os.urandom(32)
                expected_contents.add((k, new_value))
                tree = tree.put(k, new_value)

        def check():
            expected_tree = TestTree(expected_contents)
            self.assertEqual(tree.hash, expected_tree.hash)

            # test all keys for existence
            for k,v in expected_contents:
                self.assertIn(k, tree)

            # test .keys(), .values() and .items()
            expected_dict = dict(expected_contents)
            self.assertEqual(set(expected_dict.keys()), set(tree.keys()))
            self.assertEqual(set(expected_dict.values()), set(tree.values()))
            self.assertEqual(set(expected_dict.items()), set(tree.items()))

            # test some keys for non-existence
            for i in range(1000):
                non_key = os.urandom(32)
                self.assertNotIn(non_key, tree)

        n = 1000
        grow(1.0, n)
        check()

        grow(0.5, n)
        check()

        modify(n)
        check()

        # delete everything and check that we end up with an empty node
        for k,v in expected_contents:
            tree = tree.remove(k)

        self.assertIs(tree, TestTree())
