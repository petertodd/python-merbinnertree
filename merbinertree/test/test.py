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
        tree = SHA256MerbinerTree()

        self.assertIsInstance(tree, TestTree.EmptyNodeClass)

        with self.assertRaises(KeyError):
            tree[k(b'\x00')]

    def test_put_new_key(self):
        t0 = SHA256MerbinerTree()

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
        t0 = SHA256MerbinerTree()

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
        t0 = SHA256MerbinerTree()

        self.assertNotIn(k(b'\x00'), t0)
        self.assertNotIn(k(b'\x01'), t0)

        t1 = t0.put(k(b'\x00'), b'a')
        self.assertIn(k(b'\x00'), t1)
        self.assertNotIn(k(b'\x01'), t1)

    def test___contains___with_invalid_keys(self):
        t0 = SHA256MerbinerTree()

        with self.assertRaises(TypeError):
            1 in t0

        with self.assertRaises(ValueError):
            b'' in t0

    def test_remove(self):
        t0 = SHA256MerbinerTree()

        # removing a non-existing key from an EmptyNode doesn't work
        with self.assertRaises(KeyError):
            t0.remove(k(b'\x00'))

        # remove a key from a LeafNode
        t1 = t0.put(k(b'\x00'), b'a')
        t2 = t1.remove(k(b'\x00'))
        self.assertNotIn(k(b'\x00'), t2)
        with self.assertRaises(KeyError):
            t2.remove(k(b'\x00'))

        # FIXME: test that t2 == t0

        # remove a key from an InnerNode(Leaf, Leaf)
        t1 = t0.put(k(b'\x00'), b'a')
        t2 = t1.put(k(b'\xff'), b'b')

        t3 = t2.remove(k(b'\x00'))
        self.assertNotIn(k(b'\x00'), t3)
        self.assertEqual(t3[k(b'\xff')], b'b')

        # FIXME

        t4 = t3.remove(k(b'\xff'))
        self.assertNotIn(k(b'\x00'), t4)
        self.assertNotIn(k(b'\xff'), t4)

        # FIXME: test equality

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

        # FIXME
