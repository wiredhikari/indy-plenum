#!/usr/bin/env python

import copy

from common.exceptions import PlenumTypeError, PlenumValueError

import rlp
from state.db.db import BaseDB
from state.util.fast_rlp import encode_optimized, decode_optimized
from state.util.utils import is_string, to_string, sha3, sha3rlp, encode_int, str_to_bytes, encode_hex
from storage.kv_in_memory import KeyValueStorageInMemory

rlp_encode = encode_optimized
rlp_decode = decode_optimized

bin_to_nibbles_cache = {}

hti = {c: i for i, c in enumerate('0123456789abcdef')}


def bin_to_nibbles(s):
    """convert string s to nibbles (half-bytes)

    >>> bin_to_nibbles("")
    []
    >>> bin_to_nibbles("h")
    [6, 8]
    >>> bin_to_nibbles("he")
    [6, 8, 6, 5]
    >>> bin_to_nibbles("hello")
    [6, 8, 6, 5, 6, 12, 6, 12, 6, 15]
    """
    return [hti[c] for c in encode_hex(s)]


def nibbles_to_bin(nibbles):
    if any(x > 15 or x < 0 for x in nibbles):
        raise Exception("nibbles can only be [0,..15]")

    if len(nibbles) % 2:
        raise Exception("nibbles must be of even numbers")

    res = b''
    for i in range(0, len(nibbles), 2):
        res += bytes([16 * nibbles[i] + nibbles[i + 1]])
    return res


NIBBLE_TERMINATOR = 16
RECORDING = 1
NONE = 0
VERIFYING = -1
ZERO_ENCODED = encode_int(0)

proving = False


class ProofConstructor:

    def __init__(self):
        self.mode = []
        self.nodes = []
        self.exempt = []

    def push(self, mode, nodes=None):
        global proving
        proving = True
        self.mode.append(mode)
        self.exempt.append(set())
        if mode == VERIFYING:
            nodes = nodes or []
            self.nodes.append(set([rlp_encode(x) for x in nodes]))
        else:
            self.nodes.append(set())

    def pop(self):
        global proving
        self.mode.pop()
        self.nodes.pop()
        self.exempt.pop()
        if not self.mode:
            proving = False

    def get_nodelist(self):
        return list(map(rlp.decode, list(self.nodes[-1])))

    def get_nodes(self):
        return self.nodes[-1]

    def add_node(self, node):
        node = rlp_encode(node)
        if node not in self.exempt[-1]:
            self.nodes[-1].add(node)

    def add_exempt(self, node):
        self.exempt[-1].add(rlp_encode(node))

    def get_mode(self):
        return self.mode[-1]


proof = ProofConstructor()


class InvalidSPVProof(Exception):
    pass


def with_terminator(nibbles):
    nibbles = nibbles[:]
    if not nibbles or nibbles[-1] != NIBBLE_TERMINATOR:
        nibbles.append(NIBBLE_TERMINATOR)
    return nibbles


def without_terminator(nibbles):
    nibbles = nibbles[:]
    if nibbles and nibbles[-1] == NIBBLE_TERMINATOR:
        del nibbles[-1]
    return nibbles


def adapt_terminator(nibbles, has_terminator):
    if has_terminator:
        return with_terminator(nibbles)
    else:
        return without_terminator(nibbles)


def without_terminator_and_flags(nibbles):
    nibbles = nibbles[:]
    if nibbles and nibbles[-1] == NIBBLE_TERMINATOR:
        del nibbles[-1]
    if len(nibbles) % 2:
        del nibbles[0]
    return nibbles


def pack_nibbles(nibbles):
    """pack nibbles to binary

    :param nibbles: a nibbles sequence. may have a terminator
    """

    if nibbles[-1] == NIBBLE_TERMINATOR:
        flags = 2
        nibbles = nibbles[:-1]
    else:
        flags = 0

    oddlen = len(nibbles) % 2
    flags |= oddlen   # set lowest bit if odd number of nibbles
    if oddlen:
        nibbles = [flags] + nibbles
    else:
        nibbles = [flags, 0] + nibbles
    o = b''
    for i in range(0, len(nibbles), 2):
        o += bytes([16 * nibbles[i] + nibbles[i + 1]])
    return o


def unpack_to_nibbles(bindata):
    """unpack packed binary data to nibbles

    :param bindata: binary packed from nibbles
    :return: nibbles sequence, may have a terminator
    """
    o = bin_to_nibbles(bindata)
    flags = o[0]
    if flags & 2:
        o.append(NIBBLE_TERMINATOR)
    if flags & 1 == 1:
        o = o[1:]
    else:
        o = o[2:]
    return o


def starts_with(full, part):
    ''' test whether the items in the part is
    the leading items of the full
    '''
    if len(full) < len(part):
        return False
    return full[:len(part)] == part


(
    NODE_TYPE_BLANK,
    NODE_TYPE_LEAF,
    NODE_TYPE_EXTENSION,
    NODE_TYPE_BRANCH
) = tuple(range(4))


def is_key_value_type(node_type):
    return node_type in [NODE_TYPE_LEAF,
                         NODE_TYPE_EXTENSION]


def key_nibbles_from_key_value_node(node):
    return without_terminator(unpack_to_nibbles(node[0]))


BLANK_NODE = b''
BLANK_ROOT = sha3rlp(BLANK_NODE)
DEATH_ROW_OFFSET = 2**62


def transient_trie_exception(*args):
    raise Exception("Transient trie")


class Trie:

    def __init__(self, db: BaseDB, root_hash=BLANK_ROOT, transient=False):
        '''it also present a dictionary like interface

        :param db key value database
        :root: blank or trie node in form of [key, value] or [v0,v1..v15,v]
        '''
        self._db = db  # Pass in a database object directly
        self.transient = transient
        if self.transient:
            self.update = self.get = self.delete = transient_trie_exception
        self.set_root_hash(root_hash)
        self.death_row_timeout = 5000
        self.nodes_for_death_row = []
        self.journal = []

    # For SPV proof production/verification purposes
    def spv_grabbing(self, node):
        global proving
        if not proving:
            pass
        elif proof.get_mode() == RECORDING:
            proof.add_node(copy.copy(node))
            # print('recording %s' % encode_hex(utils.sha3(rlp_encode(node))))
        elif proof.get_mode() == VERIFYING:
            # print('verifying %s' % encode_hex(utils.sha3(rlp_encode(node))))
            if rlp_encode(node) not in proof.get_nodes():
                raise InvalidSPVProof("Proof invalid!")

    def spv_storing(self, node):
        global proving
        if not proving:
            pass
        elif proof.get_mode() == RECORDING:
            proof.add_exempt(copy.copy(node))
        elif proof.get_mode() == VERIFYING:
            proof.add_node(copy.copy(node))

    @property
    def root_hash(self):
        '''always empty or a 32 bytes string
        '''
        return self.get_root_hash()

    def get_root_hash(self):
        if self.transient:
            return self.transient_root_hash
        if self.root_node == BLANK_NODE:
            return BLANK_ROOT
        assert isinstance(self.root_node, list)
        val = rlp_encode(self.root_node)
        key = sha3(val)
        self.spv_grabbing(self.root_node)
        return key

    def replace_root_hash(self, old_node, new_node):
        # sys.stderr.write('rrh %r %r\n' % (old_node, new_node))
        self._delete_node_storage(old_node, is_root=True)
        self._encode_node(new_node, is_root=True)
        self.root_node = new_node
        # sys.stderr.write('nrh: %s\n' % encode_hex(self.root_hash))

    @root_hash.setter
    def root_hash(self, value):
        self.set_root_hash(value)

    def set_root_hash(self, root_hash):
        if not is_string(root_hash):
            raise PlenumTypeError('root_hash', root_hash, bytes)
        if not (len(root_hash) in [0, 32]):
            raise PlenumValueError('root_hash', root_hash, 'length in range [0, 32]')
        if self.transient:
            self.transient_root_hash = root_hash
            return
        if root_hash == BLANK_ROOT:
            self.root_node = BLANK_NODE
            return
        # print(repr(root_hash))
        self.root_node = self._decode_to_node(root_hash)
        # dummy to increase reference count
        # self._encode_node(self.root_node)

    def all_nodes(self, node=None):
        proof.push(RECORDING)
        self.get_root_hash()
        self.to_dict()
        o = proof.get_nodelist()
        proof.pop()
        return list(o)
        # if node is None:
        #     node = self.root_node
        # node_type = self._get_node_type(node)
        # o = 1 if len(rlp_encode(node)) >= 32 else 0
        # if node_type == NODE_TYPE_BRANCH:
        #     for item in node[:16]:
        #         o += self.total_node_count(self._decode_to_node(item))
        # elif is_key_value_type(node_type):
        #     if node_type == NODE_TYPE_EXTENSION:
        #         o += self.total_node_count(self._decode_to_node(node[1]))
        # return o

    def clear(self):
        ''' clear all tree data
        '''
        self._delete_child_storage(self.root_node)
        self._delete_node_storage(self.root_node)
        self.root_node = BLANK_NODE

    def _delete_child_storage(self, node):
        node_type = self._get_node_type(node)
        if node_type == NODE_TYPE_BRANCH:
            for item in node[:16]:
                self._delete_child_storage(self._decode_to_node(item))
        elif is_key_value_type(node_type):
            node_type = self._get_node_type(node)
            if node_type == NODE_TYPE_EXTENSION:
                self._delete_child_storage(self._get_inner_node_from_extension(node))

    def _encode_node(self, node, is_root=False):
        if node == BLANK_NODE:
            return BLANK_NODE
        # assert isinstance(node, list)
        rlpnode = rlp_encode(node)
        if len(rlpnode) < 32 and not is_root:
            return node

        hashkey = sha3(rlpnode)
        self._db.inc_refcount(hashkey, rlpnode)
        return hashkey

    def _decode_to_node(self, encoded):
        if encoded == BLANK_NODE:
            return BLANK_NODE
        if isinstance(encoded, list):
            return encoded
        o = rlp.decode(self._db.get(encoded))
        self.spv_grabbing(o)
        return o

    def _get_inner_node_from_extension(self, node):
        return self._decode_to_node(node[1])

    @staticmethod
    def _get_node_type(node):
        ''' get node type and content

        :param node: node in form of list, or BLANK_NODE
        :return: node type
        '''
        if node == BLANK_NODE:
            return NODE_TYPE_BLANK

        if len(node) == 2:
            nibbles = unpack_to_nibbles(node[0])
            has_terminator = (nibbles and nibbles[-1] == NIBBLE_TERMINATOR)
            return NODE_TYPE_LEAF if has_terminator\
                else NODE_TYPE_EXTENSION
        if len(node) == 17:
            return NODE_TYPE_BRANCH

    def _get(self, node, key):
        """ get value inside a node

        :param node: node in form of list, or BLANK_NODE
        :param key: nibble list without terminator
        :return:
            BLANK_NODE if does not exist, otherwise value or hash
        """
        node_type = self._get_node_type(node)

        if node_type == NODE_TYPE_BLANK:
            return BLANK_NODE

        if node_type == NODE_TYPE_BRANCH:
            # already reach the expected node
            if not key:
                return node[-1]
            sub_node = self._decode_to_node(node[key[0]])
            return self._get(sub_node, key[1:])

        # key value node
        curr_key = key_nibbles_from_key_value_node(node)
        if node_type == NODE_TYPE_LEAF:
            return node[1] if key == curr_key else BLANK_NODE

        if node_type == NODE_TYPE_EXTENSION:
            # traverse child nodes
            if starts_with(key, curr_key):
                sub_node = self._get_inner_node_from_extension(node)
                return self._get(sub_node, key[len(curr_key):])
            else:
                return BLANK_NODE

    def _get_last_node_for_prfx(self, node, key_prfx, seen_prfx):
        """ get last node for the given prefix, also update `seen_prfx` to track the path already traversed

        :param node: node in form of list, or BLANK_NODE
        :param key_prfx: prefix to look for
        :param seen_prfx: prefix already seen, updates with each call
        :return:
            BLANK_NODE if does not exist, otherwise value or hash
        """
        node_type = self._get_node_type(node)

        if node_type == NODE_TYPE_BLANK:
            return BLANK_NODE

        if node_type == NODE_TYPE_BRANCH:
            # already reach the expected node
            if not key_prfx:
                return node
            sub_node = self._decode_to_node(node[key_prfx[0]])
            seen_prfx.append(key_prfx[0])
            return self._get_last_node_for_prfx(sub_node, key_prfx[1:], seen_prfx)

        # key value node
        curr_key = key_nibbles_from_key_value_node(node)

        if node_type == NODE_TYPE_LEAF:
            # Return this node only if the complete prefix is part of the current key
            if starts_with(curr_key, key_prfx):
                # Do not update `seen_prefix` as node has the prefix
                return node
            else:
                return BLANK_NODE

        if node_type == NODE_TYPE_EXTENSION:
            # traverse child nodes
            if len(key_prfx) > len(curr_key):
                if starts_with(key_prfx, curr_key):
                    sub_node = self._get_inner_node_from_extension(node)
                    seen_prfx.extend(curr_key)
                    return self._get_last_node_for_prfx(sub_node,
                                                        key_prfx[len(curr_key):],
                                                        seen_prfx)
                else:
                    return BLANK_NODE
            else:
                if starts_with(curr_key, key_prfx):
                    # Do not update `seen_prefix` as node has the prefix
                    return node
                else:
                    return BLANK_NODE

    def _update(self, node, key, value):
        # sys.stderr.write('u\n')
        """ update item inside a node

        :param node: node in form of list, or BLANK_NODE
        :param key: nibble list without terminator
            .. note:: key may be []
        :param value: value string
        :return: new node

        if this node is changed to a new node, it's parent will take the
        responsibility to *store* the new node storage, and delete the old
        node storage
        """
        node_type = self._get_node_type(node)

        if node_type == NODE_TYPE_BLANK:
            o = [pack_nibbles(with_terminator(key)), value]
            self._encode_node(o)
            return o

        elif node_type == NODE_TYPE_BRANCH:
            if not key:
                node[-1] = value
            else:
                new_node = self._update_and_delete_storage(
                    self._decode_to_node(node[key[0]]),
                    key[1:], value)
                node[key[0]] = self._encode_node(new_node)
                self._delete_node_storage(new_node)
            self._encode_node(node)
            return node

        elif is_key_value_type(node_type):
            return self._update_kv_node(node, key, value)

    def _update_and_delete_storage(self, node, key, value):
        # sys.stderr.write('uds_start %r\n' % node)
        old_node = copy.deepcopy(node)
        new_node = self._update(node, key, value)
        # sys.stderr.write('uds_mid %r\n' % old_node)
        self._delete_node_storage(old_node)
        # sys.stderr.write('uds_end %r\n' % old_node)
        return new_node

    def _update_kv_node(self, node, key, value):
        node_type = self._get_node_type(node)
        curr_key = key_nibbles_from_key_value_node(node)
        is_inner = node_type == NODE_TYPE_EXTENSION
        # sys.stderr.write('ukv %r %r\n' % (key, value))

        # find longest common prefix
        prefix_length = 0
        for i in range(min(len(curr_key), len(key))):
            if key[i] != curr_key[i]:
                break
            prefix_length = i + 1

        # sys.stderr.write('pl: %d\n' % prefix_length)

        remain_key = key[prefix_length:]
        remain_curr_key = curr_key[prefix_length:]
        new_node_encoded = False

        if remain_key == [] == remain_curr_key:
            # Updating the value of an existing key
            if not is_inner:
                o = [node[0], value]
                self._encode_node(o)
                return o
            new_node = self._update_and_delete_storage(
                self._decode_to_node(node[1]), remain_key, value)
            new_node_encoded = True

        elif remain_curr_key == []:
            if is_inner:
                # sys.stderr.write('22221\n')
                new_node = self._update_and_delete_storage(
                    self._decode_to_node(node[1]), remain_key, value)
                new_node_encoded = True
                # sys.stderr.write('22221e\n')
            else:
                # sys.stderr.write('22222\n')
                new_node = [BLANK_NODE] * 17
                new_node[-1] = node[1]
                new_node[remain_key[0]] = self._encode_node([
                    pack_nibbles(with_terminator(remain_key[1:])),
                    value
                ])
        else:
            # sys.stderr.write('3333\n')
            new_node = [BLANK_NODE] * 17
            if len(remain_curr_key) == 1 and is_inner:
                new_node[remain_curr_key[0]] = node[1]
            else:
                new_node[remain_curr_key[0]] = self._encode_node([
                    pack_nibbles(
                        adapt_terminator(remain_curr_key[1:], not is_inner)
                    ),
                    node[1]
                ])

            if remain_key == []:
                new_node[-1] = value
            else:
                new_node[remain_key[0]] = self._encode_node([
                    pack_nibbles(with_terminator(remain_key[1:])), value
                ])

        if prefix_length:
            # sys.stderr.write('444441: %d\n' % prefix_length)
            # create node for key prefix
            o = [pack_nibbles(curr_key[:prefix_length]),
                 self._encode_node(new_node)]
            if new_node_encoded:
                self._delete_node_storage(new_node)
            self._encode_node(o)
            return o
        else:
            # sys.stderr.write('444442: %d\n' % prefix_length)
            if not new_node_encoded:
                self._encode_node(new_node)
            return new_node

    def _getany(self, node, reverse=False, path=[]):
        node_type = self._get_node_type(node)
        if node_type == NODE_TYPE_BLANK:
            return None
        if node_type == NODE_TYPE_BRANCH:
            if node[16]:
                return [16]
            scan_range = list(range(16))
            if reverse:
                scan_range.reverse()
            for i in scan_range:
                o = self._getany(self._decode_to_node(
                    node[i]), path=path + [i])
                if o:
                    return [i] + o
            return None
        curr_key = key_nibbles_from_key_value_node(node)

        if node_type == NODE_TYPE_LEAF:
            return curr_key

        if node_type == NODE_TYPE_EXTENSION:
            sub_node = self._get_inner_node_from_extension(node)
            return self._getany(sub_node, path=path + curr_key)

    def _iter(self, node, key, reverse=False, path=[]):
        node_type = self._get_node_type(node)

        if node_type == NODE_TYPE_BLANK:
            return None

        elif node_type == NODE_TYPE_BRANCH:
            if len(key):
                sub_node = self._decode_to_node(node[key[0]])
                o = self._iter(sub_node, key[1:], reverse, path + [key[0]])
                if o:
                    return [key[0]] + o
            if reverse:
                scan_range = list(range(key[0] if len(key) else 0))
            else:
                scan_range = list(range(key[0] + 1 if len(key) else 0, 16))
            for i in scan_range:
                sub_node = self._decode_to_node(node[i])
                o = self._getany(sub_node, reverse, path + [i])
                if o:
                    return [i] + o
            if reverse and node[16]:
                return [16]
            return None

        descend_key = key_nibbles_from_key_value_node(node)
        if node_type == NODE_TYPE_LEAF:
            if reverse:
                return descend_key if descend_key < key else None
            else:
                return descend_key if descend_key > key else None

        if node_type == NODE_TYPE_EXTENSION:
            # traverse child nodes
            sub_node = self._get_inner_node_from_extension(node)
            sub_key = key[len(descend_key):]
            if starts_with(key, descend_key):
                o = self._iter(sub_node, sub_key, reverse, path + descend_key)
            elif descend_key > key[:len(descend_key)] and not reverse:
                o = self._getany(sub_node, sub_key, False, path + descend_key)
            elif descend_key < key[:len(descend_key)] and reverse:
                o = self._getany(sub_node, sub_key, True, path + descend_key)
            else:
                o = None
            return descend_key + o if o else None

    def next(self, key):
        key = bin_to_nibbles(key)
        o = self._iter(self.root_node, key)
        return nibbles_to_bin(o) if o else None

    def prev(self, key):
        key = bin_to_nibbles(key)
        o = self._iter(self.root_node, key, reverse=True)
        return nibbles_to_bin(o) if o else None

    def _delete_node_storage(self, node, is_root=False):
        '''delete storage
        :param node: node in form of list, or BLANK_NODE
        '''
        if node == BLANK_NODE:
            return
        # assert isinstance(node, list)
        encoded = rlp_encode(node)
        if len(encoded) < 32 and not is_root:
            return
        """
        ===== FIXME ====
        in the current trie implementation two nodes can share identical
        subtrees thus we can not safely delete nodes for now
        """
        hashkey = sha3(encoded)
        self._db.dec_refcount(hashkey)

    def _delete(self, node, key):
        """ update item inside a node

        :param node: node in form of list, or BLANK_NODE
        :param key: nibble list without terminator
            .. note:: key may be []
        :return: new node

        if this node is changed to a new node, it's parent will take the
        responsibility to *store* the new node storage, and delete the old
        node storage
        """
        # sys.stderr.write('del\n')
        node_type = self._get_node_type(node)
        if node_type == NODE_TYPE_BLANK:
            return BLANK_NODE

        if node_type == NODE_TYPE_BRANCH:
            return self._delete_branch_node(node, key)

        if is_key_value_type(node_type):
            return self._delete_kv_node(node, key)

    def _normalize_branch_node(self, node):
        # sys.stderr.write('nbn\n')
        '''node should have only one item changed
        '''
        not_blank_items_count = sum(1 for x in range(17) if node[x])
        assert not_blank_items_count >= 1

        if not_blank_items_count > 1:
            self._encode_node(node)
            return node

        # now only one item is not blank
        not_blank_index = [i for i, item in enumerate(node) if item][0]

        # the value item is not blank
        if not_blank_index == 16:
            o = [pack_nibbles(with_terminator([])), node[16]]
            self._encode_node(o)
            return o

        # normal item is not blank
        sub_node = self._decode_to_node(node[not_blank_index])
        sub_node_type = self._get_node_type(sub_node)

        if is_key_value_type(sub_node_type):
            # collape subnode to this node, not this node will have same
            # terminator with the new sub node, and value does not change
            self._delete_node_storage(sub_node)
            new_key = [not_blank_index] + \
                unpack_to_nibbles(sub_node[0])
            o = [pack_nibbles(new_key), sub_node[1]]
            self._encode_node(o)
            return o
        if sub_node_type == NODE_TYPE_BRANCH:
            o = [pack_nibbles([not_blank_index]),
                 node[not_blank_index]]
            self._encode_node(o)
            return o
        assert False

    def _delete_and_delete_storage(self, node, key):
        # sys.stderr.write('dds_start %r\n' % node)
        old_node = copy.deepcopy(node)
        new_node = self._delete(node, key)
        # sys.stderr.write('dds_mid %r\n' % old_node)
        self._delete_node_storage(old_node)
        # sys.stderr.write('dds_end %r %r\n' % (old_node, new_node))
        return new_node

    def _delete_branch_node(self, node, key):
        # sys.stderr.write('dbn\n')
        # already reach the expected node
        if not key:
            node[-1] = BLANK_NODE
            return self._normalize_branch_node(node)

        o = self._delete_and_delete_storage(
            self._decode_to_node(node[key[0]]), key[1:])

        encoded_new_sub_node = self._encode_node(o)
        self._delete_node_storage(o)
        # sys.stderr.write('dbn2\n')

        # if encoded_new_sub_nod == node[key[0]]:
        #     return node

        node[key[0]] = encoded_new_sub_node
        if encoded_new_sub_node == BLANK_NODE:
            return self._normalize_branch_node(node)
        self._encode_node(node)

        return node

    def _delete_kv_node(self, node, key):
        # sys.stderr.write('dkv\n')
        node_type = self._get_node_type(node)
        assert is_key_value_type(node_type)
        curr_key = key_nibbles_from_key_value_node(node)

        if not starts_with(key, curr_key):
            # key not found
            self._encode_node(node)
            return node

        if node_type == NODE_TYPE_LEAF:
            if key == curr_key:
                return BLANK_NODE
            else:
                self._encode_node(node)
                return node

        # for inner key value type
        new_sub_node = self._delete_and_delete_storage(
            self._get_inner_node_from_extension(node), key[len(curr_key):])
        # sys.stderr.write('nsn: %r %r\n' % (node, new_sub_node))

        # if self._encode_node(new_sub_node) == node[1]:
        #     return node

        # new sub node is BLANK_NODE
        if new_sub_node == BLANK_NODE:
            return BLANK_NODE

        assert isinstance(new_sub_node, list)

        # new sub node not blank, not value and has changed
        new_sub_node_type = self._get_node_type(new_sub_node)

        if is_key_value_type(new_sub_node_type):
            # sys.stderr.write('nsn1\n')
            # collapse subnode to this node, not this node will have same
            # terminator with the new sub node, and value does not change
            new_key = curr_key + unpack_to_nibbles(new_sub_node[0])
            o = [pack_nibbles(new_key), new_sub_node[1]]
            self._delete_node_storage(new_sub_node)
            self._encode_node(o)
            return o

        if new_sub_node_type == NODE_TYPE_BRANCH:
            # sys.stderr.write('nsn2\n')
            o = [pack_nibbles(curr_key), self._encode_node(new_sub_node)]
            self._delete_node_storage(new_sub_node)
            self._encode_node(o)
            return o

        # should be no more cases
        assert False

    def delete(self, key):
        '''
        :param key: a string with length of [0, 32]
        '''
        if not is_string(key):
            raise Exception("Key must be string")

        # if len(key) > 32:
        #     raise Exception("Max key length is 32")

        old_root = copy.deepcopy(self.root_node)
        self.root_node = self._delete_and_delete_storage(
            self.root_node,
            bin_to_nibbles(to_string(key)))
        self.replace_root_hash(old_root, self.root_node)

    def clear_all(self, node=None):
        if node is None:
            node = self.root_node
            self._delete_node_storage(node)
        if node == BLANK_NODE:
            return

        node_type = self._get_node_type(node)

        self._delete_node_storage(node)

        if is_key_value_type(node_type):
            value_is_node = node_type == NODE_TYPE_EXTENSION
            if value_is_node:
                self.clear_all(self._decode_to_node(node[1]))

        elif node_type == NODE_TYPE_BRANCH:
            for i in range(16):
                self.clear_all(self._decode_to_node(node[i]))

    def _get_size(self, node):
        '''Get counts of (key, value) stored in this and the descendant nodes

        :param node: node in form of list, or BLANK_NODE
        '''
        if node == BLANK_NODE:
            return 0

        node_type = self._get_node_type(node)

        if is_key_value_type(node_type):
            value_is_node = node_type == NODE_TYPE_EXTENSION
            if value_is_node:
                return self._get_size(self._get_inner_node_from_extension(node))
            else:
                return 1
        elif node_type == NODE_TYPE_BRANCH:
            sizes = [self._get_size(self._decode_to_node(node[x]))
                     for x in range(16)]
            sizes = sizes + [1 if node[-1] else 0]
            return sum(sizes)

    def _to_dict(self, node):
        '''convert (key, value) stored in this and the descendant nodes
        to dict items.

        :param node: node in form of list, or BLANK_NODE

        .. note::

            Here key is in full form, rather than key of the individual node
        '''
        if node == BLANK_NODE:
            return {}

        node_type = self._get_node_type(node)

        if is_key_value_type(node_type):
            nibbles = key_nibbles_from_key_value_node(node)
            key = b'+'.join([to_string(x) for x in nibbles])
            if node_type == NODE_TYPE_EXTENSION:
                sub_dict = self._to_dict(self._get_inner_node_from_extension(node))
            else:
                sub_dict = {to_string(NIBBLE_TERMINATOR): node[1]}

            # prepend key of this node to the keys of children
            res = {}
            for sub_key, sub_value in sub_dict.items():
                full_key = (key + b'+' + sub_key).strip(b'+')
                res[full_key] = sub_value
            return res

        elif node_type == NODE_TYPE_BRANCH:
            res = {}
            for i in range(16):
                sub_dict = self._to_dict(self._decode_to_node(node[i]))

                for sub_key, sub_value in sub_dict.items():
                    full_key = (str_to_bytes(str(i)) +
                                b'+' + sub_key).strip(b'+')
                    res[full_key] = sub_value

            if node[16]:
                res[to_string(NIBBLE_TERMINATOR)] = node[-1]
            return res

    def to_dict(self, node=None):
        node = node or self.root_node
        d = self._to_dict(node)
        res = {}
        for key_str, value in d.items():
            key = self.nibble_key_str_to_bin(key_str)
            res[key] = value
        return res

    def iter_branch(self):
        for key_str, value in self._iter_branch(self.root_node):
            key = self.nibble_key_str_to_bin(key_str)
            yield key, value

    def _iter_branch(self, node):
        """yield (key, value) stored in this and the descendant nodes
        :param node: node in form of list, or BLANK_NODE

        .. note::
            Here key is in full form, rather than key of the individual node
        """
        if node == BLANK_NODE:
            raise StopIteration

        node_type = self._get_node_type(node)

        if is_key_value_type(node_type):
            nibbles = key_nibbles_from_key_value_node(node)
            key = b'+'.join([to_string(x) for x in nibbles])
            if node_type == NODE_TYPE_EXTENSION:
                sub_tree = self._iter_branch(self._get_inner_node_from_extension(node))
            else:
                sub_tree = [(to_string(NIBBLE_TERMINATOR), node[1])]

            # prepend key of this node to the keys of children
            for sub_key, sub_value in sub_tree:
                full_key = (key + b'+' + sub_key).strip(b'+')
                yield (full_key, sub_value)

        elif node_type == NODE_TYPE_BRANCH:
            for i in range(16):
                sub_tree = self._iter_branch(self._decode_to_node(node[i]))
                for sub_key, sub_value in sub_tree:
                    full_key = (str_to_bytes(str(i)) +
                                b'+' + sub_key).strip(b'+')
                    yield (full_key, sub_value)
            if node[16]:
                yield (to_string(NIBBLE_TERMINATOR), node[-1])

    def get(self, key):
        return self._get(self.root_node, bin_to_nibbles(to_string(key)))

    def __len__(self):
        return self._get_size(self.root_node)

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        return self.update(key, value)

    def __delitem__(self, key):
        return self.delete(key)

    def __iter__(self):
        return iter(self.to_dict())

    def __contains__(self, key):
        return self.get(key) != BLANK_NODE

    def update(self, key, value):
        '''
        :param key: a string
        :value: a string
        '''
        if not is_string(key):
            raise Exception("Key must be string")

        # if len(key) > 32:
        #     raise Exception("Max key length is 32")

        if not is_string(value):
            raise Exception("Value must be string")

        # if value == '':
        #     return self.delete(key)
        old_root = copy.deepcopy(self.root_node)
        self.root_node = self._update_and_delete_storage(
            self.root_node,
            bin_to_nibbles(to_string(key)),
            to_string(value))
        self.replace_root_hash(old_root, self.root_node)

    def root_hash_valid(self):
        if self.root_hash == BLANK_ROOT:
            return True
        return self.root_hash in self._db

    def get_at(self, root_node, key):
        """
        Get value of a key when the root node was `root_node`
        :param root_node:
        :param key:
        :return:
        """
        return self._get(root_node, bin_to_nibbles(to_string(key)))

    def produce_spv_proof(self, key, root=None, get_value=False):
        root = root if root is not None else self.root_node
        proof.push(RECORDING)
        rv = self.get_at(root, key)
        o = proof.get_nodelist()
        proof.pop()
        value = rv if rv != BLANK_NODE else None
        return (o, value) if get_value else o

    def produce_spv_proof_for_keys_with_prefix(self, key_prfx, root=None, get_value=False):
        # Return a proof for keys in the trie with the given prefix.
        root = root if root is not None else self.root_node
        proof.push(RECORDING)
        seen_prfx = []
        prefix_node = self._get_last_node_for_prfx(root,
                                                   bin_to_nibbles(to_string(key_prfx)),
                                                   seen_prfx=seen_prfx)
        # The next line traverses the prefix node and the children of the
        # prefix node. Needed for generating the proof and the values
        rv = self._to_dict(prefix_node)
        # If values are needed then convert the keys appropriately
        if get_value:
            new_rv = {}
            for k, v in rv.items():
                # Add the seen prefix to each key
                k_ = seen_prfx + [int(x) for x in k.split(b'+')]
                new_rv[nibbles_to_bin(without_terminator_and_flags(k_))] = v
            rv = new_rv
        o = proof.get_nodelist()
        proof.pop()
        return (o, rv) if get_value else o

    def generate_state_proof(self, key, root=None, serialize=False, get_value=False):
        # NOTE: The method `produce_spv_proof` is not deliberately modified
        return self._generate_state_proof(key, self.produce_spv_proof,
                                          root=root, serialize=serialize,
                                          get_value=get_value)

    def generate_state_proof_for_keys_with_prefix(self, key_prfx, root=None,
                                                  serialize=False, get_value=False):
        return self._generate_state_proof(key_prfx, self.produce_spv_proof_for_keys_with_prefix,
                                          root=root, serialize=serialize,
                                          get_value=get_value)

    def _generate_state_proof(self, path, func, root=None, serialize=False, **kwargs):
        root = root if root is not None else self.root_node
        rv = func(path, root, **kwargs)
        has_val = isinstance(rv, tuple) and len(rv) == 2
        pf = rv[0] if has_val else rv
        pf.append(copy.deepcopy(root))
        if serialize:
            if has_val:
                rv = (self.serialize_proof(pf), rv[1])
            else:
                rv = self.serialize_proof(pf)
        return rv

    @staticmethod
    def verify_spv_proof(root, key, value, proof_nodes, serialized=False):
        # NOTE: `root` is a derivative of the last element of `proof_nodes`
        # but it's important to keep `root` as a separate as signed root
        # hashes will be published.
        if serialized:
            proof_nodes = Trie.deserialize_proof(proof_nodes)
        proof.push(VERIFYING, proof_nodes)

        new_trie = Trie.get_new_trie_with_proof_nodes(proof_nodes)

        try:
            new_trie.root_hash = root
            v = new_trie.get(key)
            proof.pop()
            return v == value
        except Exception as e:
            print(e)
            proof.pop()
            return False

    @staticmethod
    def verify_spv_proof_multi(root, key_values, proof_nodes,
                               serialized=False):
        # Takes a list of proof nodes for several key values
        if serialized:
            proof_nodes = Trie.deserialize_proof(proof_nodes)

        proof.push(VERIFYING, proof_nodes)

        new_trie = Trie.get_new_trie_with_proof_nodes(proof_nodes)

        try:
            new_trie.root_hash = root
        except Exception as e:
            print(e)
            proof.pop()
            return False

        for k, v in key_values.items():
            try:
                _v = new_trie.get(k)
            except Exception as e:
                print(e)
                proof.pop()
                return False
            if v != _v:
                proof.pop()
                return False

        proof.pop()
        return True

    @staticmethod
    def get_new_trie_with_proof_nodes(proof_nodes):
        new_trie = Trie(KeyValueStorageInMemory())

        for node in proof_nodes:
            R = rlp_encode(node)
            H = sha3(R)
            new_trie._db.put(H, R)

        return new_trie

    @staticmethod
    def serialize_proof(proof_nodes):
        return rlp_encode(proof_nodes)

    @staticmethod
    def deserialize_proof(ser_proof):
        return rlp_decode(ser_proof)

    @staticmethod
    def nibble_key_str_to_bin(key_str):
        if key_str:
            nibbles = [int(x) for x in key_str.split(b'+')]
        else:
            nibbles = []
        return nibbles_to_bin(without_terminator_and_flags(nibbles))
