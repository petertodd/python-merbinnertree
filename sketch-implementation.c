struct item {
    uint256 key;
    uint256 value;
};

uint256 hash_subtree(struct item *start, struct item *end, depth){
    if (start - end == 0) {
        /* return hash of the empty node */
    }
    else if (start - end == 1) {
        /* just one item, hash it as an inner node */
    }
    else {
        /* more than one item */
        uint256 left_start = start;
        uint256 left_end = start;

        /* increment left_end until it's at an item that should go on the next
         * side; this is the calculation where depth is used */

        uint256 right_start = left_end + 1;
        uint256 right_end = end;

        /* call recursively */
        left_hash = hash_subtree(left_start, left_end, depth+1);
        right_hash = hash_subtree(right_start, right_end, depth+1);

        return hash_inner_node(left_hash, right_hash);
    }
}

uint256 hash_tree(struct item *items, size_t num_nodes){
    /* sort items in place */

    return hash_subtree(items[0], items[num_nodes-1], 0);
}
