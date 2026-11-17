"""
Function for finding duplicate keys in a YAML file.

This module provides find_duplicate_keys(), which finds the keys that appear more than once in
the same mapping of a YAML file.  Loading such a file silently keeps only the last occurrence of
each such key, so the settings under the earlier occurrences are lost.  The sections below
explain what a mapping and a duplicate key are (section 1), why duplicate keys can't be found
after the file is loaded and what is read instead (section 2), and how the duplicates are found
(section 3).

1. Mappings and duplicate keys
==============================

A mapping in a YAML file is a set of "key: value" pairs directly under the same parent key, or
at the top level of the file.  It is called a mapping because it maps each key to one value, as
a mapping (or function) does in mathematics, so the keys of a mapping must be unique.  (A Python
dict is the same kind of structure.)  A value may itself be a mapping, which is how sections are
nested.  For example, a YAML file containing

    workflow:
      PREEXISTING_DIR_METHOD: rename
      FCST_LEN_HRS: 6
      PREEXISTING_DIR_METHOD: delete
    platform:
      ACCOUNT: an_account
      PREEXISTING_DIR_METHOD: quit
    workflow:
      FCST_LEN_HRS: 12
      EXPT_SUBDIR: my_expt

consists of four mappings:

1) The top-level mapping, whose "key: value" pairs are

     workflow:
       ...
     platform:
       ...
     workflow:
       ...

2) The mapping directly under the first "workflow:", whose "key: value" pairs are

     PREEXISTING_DIR_METHOD: rename
     FCST_LEN_HRS: 6
     PREEXISTING_DIR_METHOD: delete

   For brevity, we will call this mapping value_of_workflow_1.

3) The mapping directly under "platform:", whose "key: value" pairs are

     ACCOUNT: an_account
     PREEXISTING_DIR_METHOD: quit

   For brevity, we will call this mapping value_of_platform.

4) The mapping directly under the second "workflow:", whose "key: value" pairs are

     FCST_LEN_HRS: 12
     EXPT_SUBDIR: my_expt

   For brevity, we will call this mapping value_of_workflow_2.

With the definitions of value_of_workflow_1, value_of_platform, and value_of_workflow_2 given
above, we can rewrite the top-level mapping as follows:

     workflow: value_of_workflow_1
     platform: value_of_platform
     workflow: value_of_workflow_2

The example YAML file above contains the following two duplicate keys:

1) "workflow" appears twice in the top-level mapping (lines 1 and 8).
2) "PREEXISTING_DIR_METHOD" appears twice in value_of_workflow_1 (lines 2 and 4).

The PREEXISTING_DIR_METHOD on line 7 is not a duplicate because although it is at the same
level as the other two (one below the top level), it is in a different mapping
(value_of_platform) than the other two (which are in the value_of_workflow_1 mapping).

When a key appears more than once in the same mapping, PyYAML's loaders (including the one used
by uwtools) silently keep only the last occurrence, so the value of each earlier occurrence
(including everything under it) is lost.  For example, loading the file above returns the dict

    {"workflow": {"FCST_LEN_HRS": 12, "EXPT_SUBDIR": "my_expt"},
     "platform": {"ACCOUNT": "an_account", "PREEXISTING_DIR_METHOD": "quit"}}

so all the settings under the first "workflow:" are lost.

Instead of the block form above, a mapping can be written on a single line, with its pairs in
braces.  For example, the block under "platform:", i.e.

    ACCOUNT: an_account
    PREEXISTING_DIR_METHOD: quit

(aka value_of_platform) can be rewritten on one line as

    {ACCOUNT: an_account, PREEXISTING_DIR_METHOD: quit}

so that the key-value pair involving platform: becomes

    platform: {ACCOUNT: an_account, PREEXISTING_DIR_METHOD: quit}

Here, {ACCOUNT: an_account, PREEXISTING_DIR_METHOD: quit} is the value_of_platform mapping
written in single-line form.

2. The node tree
================

Loading a YAML file normally turns each mapping into a Python dict (as in the result of loading
the example file in section 1).  Since a dict can hold each key only once, duplicate keys can't
be detected afterwards.  The function yaml.compose() stops one step earlier than loading and
returns the file as a tree of "nodes" instead of a dict.  (Since in this module no Python
objects are constructed from the nodes, tags such as !int and !list are not evaluated.)  Each
node represents one part of the file and is one of the three kinds MappingNode, SequenceNode,
and ScalarNode, where:

1) A MappingNode represents a mapping.  It holds the mapping's pairs as a list of node pairs,
   where the first node of each pair corresponds to the key and the second to the value (which
   may be a scalar, a list, or another mapping).  We will refer to these as (key node, value
   node) pairs.  The pairs are in the order in which they appear in the file, so the list
   contains every occurrence of a key, including duplicates.

2) A SequenceNode represents a sequence (a list) and holds the nodes of its items.

3) A ScalarNode represents a single value, such as a key, or a value like 6 or rename.

The kind of node each part of a YAML file becomes depends on what that part represents:

- A key is always a ScalarNode (at least in any file that the dtc-vx-workflow will load; see
  below).  The node's .value attribute is the key's text as written, e.g. "platform" for the
  key platform:, and "6" (not the integer 6) for the key 6:.  So keys are compared as strings.
  Two keys that are written differently but load as the same non-string value (e.g. on: and
  true:, which both load as the boolean True, or 6: and 0x6:, which both load as the integer 6)
  are therefore not detected.  We do not worry about this case because no key in the
  dtc-vx-workflow's config files is written as a boolean, a number, null, or a date.

- Any other node (a value in a mapping, an item in a sequence, or the root node, described
  below) is one of the following:

  - a ScalarNode if it corresponds to a single value, e.g. 6 or rename,
  - a SequenceNode if it corresponds to a list, e.g. [a, b], or
  - a MappingNode if it corresponds to a mapping, e.g. the value of workflow:.

YAML also allows a key to be a list or a mapping, but a file containing such a key can't be
loaded.  Loading turns each mapping into a Python dict, so each key becomes a dict key, and the
keys of a dict must be values that can't be changed after they are created ("hashable"), such as
strings and numbers.  A key written as a list or a mapping would become a Python list or dict,
which can be changed, so loading fails with the error "while constructing a mapping ... found
unhashable key".  In practice, every key in the dtc-vx-workflow's own config files is a plain
name, i.e. a string, and user config files should use plain names as keys as well.

The most likely way to create such a key by accident is to leave a Jinja template unquoted.  YAML
knows nothing about Jinja and reads each "{" as the start of a mapping written on a single line
(see section 1), so in

    key: {{ name }}

{ name } is a mapping whose only key is name, with no value (i.e. null), and the outer braces
make a second mapping whose only key is that first mapping, again with no value.  The value of
key is therefore a mapping whose key is a mapping, and the file can't be loaded.  In the node
tree, it is

    MappingNode                                  (the root node)
    +-- (ScalarNode key, MappingNode)            (value: the outer braces)
        +-- (MappingNode, ScalarNode null)       (key: the inner { name })
            +-- (ScalarNode name, ScalarNode null)   (the pair of the key, not of the value)

Quoting the template, as in key: '{{ name }}', makes it a plain string, which is left for Jinja
to fill in later.  This is why every Jinja template in the dtc-vx-workflow's config files is
quoted.

All three kinds of node have the following attributes:

- .value: For a ScalarNode, the text of the value as written.  For a MappingNode, the list of
  its (key node, value node) pairs.  For a SequenceNode, the list of the nodes of its items.

- .tag: The node's type, e.g. str or int (inferred by PyYAML), or a tag written in the file,
  such as !int.

- .start_mark and .end_mark: Where the node starts and ends in the file.  Each is a Mark object
  with the following attributes:

  - .line and .column: the line and column, both counting from 0,
  - .index: the number of characters before it in the file,
  - .name: the path of the file being read, and
  - .buffer and .pointer: used by PyYAML to print error messages.

In addition, a ScalarNode has .style, which says how the value was written (None if unquoted,
' or " if quoted, and | or > for a block scalar).  A MappingNode or SequenceNode instead has
.flow_style, which is True if it is written on one line (in braces or brackets) and False
otherwise.

Of all these attributes, this module uses only .value and .start_mark.line.

A MappingNode or SequenceNode contains further nodes, which is what makes the nodes a tree.  The
node at the top of the tree is the root node.  yaml.compose() returns the root node, or None if
the file is empty.  For the example file in section 1, the root node is the MappingNode of the
top-level mapping, and the tree is

    MappingNode                                   (the root node, i.e. the top-level mapping)
    +-- (ScalarNode workflow (1), MappingNode)    (value_of_workflow_1)
    |   +-- (ScalarNode PREEXISTING_DIR_METHOD (2), ScalarNode rename)
    |   +-- (ScalarNode FCST_LEN_HRS (3),           ScalarNode 6)
    |   +-- (ScalarNode PREEXISTING_DIR_METHOD (4), ScalarNode delete)
    +-- (ScalarNode platform (5), MappingNode)    (value_of_platform)
    |   +-- (ScalarNode ACCOUNT (6),                ScalarNode an_account)
    |   +-- (ScalarNode PREEXISTING_DIR_METHOD (7), ScalarNode quit)
    +-- (ScalarNode workflow (8), MappingNode)    (value_of_workflow_2)
        +-- (ScalarNode FCST_LEN_HRS (9),           ScalarNode 12)
        +-- (ScalarNode EXPT_SUBDIR (10),           ScalarNode my_expt)

Each line in parentheses that starts with "(ScalarNode" is a (key node, value node) pair, and
the number after each key is the line on which the key appears (counting from 1, i.e.
.start_mark.line + 1).  The pairs indented under a pair are those of its value node.  The two
workflow keys are in the root node's list of pairs, so workflow is a duplicate.  The two
PREEXISTING_DIR_METHOD keys on lines 2 and 4 are in the list of pairs of value_of_workflow_1, so
PREEXISTING_DIR_METHOD is also a duplicate there.  The PREEXISTING_DIR_METHOD on line 7 is in
the list of pairs of value_of_platform, a different MappingNode, so it is not a duplicate.

Nodes have no names.  A node also doesn't record its parent or its position in the tree.  For
example, the MappingNode value_of_platform is the value of platform only because the two are
paired in the root node's list of pairs.  The labels value_of_workflow_1, value_of_platform, and
value_of_workflow_2 are only the names used in section 1.

An alias in a YAML file (written *name) is not a copy of its anchored node (the node marked
with &name) but the same node object, reached from another place in the tree.  (The anchor name
itself is not stored in the node.)  For example, in

    key1: &some_name
      sub_key: 1
      sub_key: 2
    key2: *some_name

the values of key1 and key2 are the same MappingNode.  (The key sub_key appears twice in it so
that it contains a duplicate key; section 3 uses this example.)  An alias can also refer to a
node that contains it, as in

    a: &x [1, *x]

where the SequenceNode of the list contains itself as its second item.  Section 3 describes how
the search handles both cases.

3. How the search works
=======================

find_duplicate_keys() calls _find_duplicate_keys_in_node() on the root node.  That function
checks the node it is given and calls itself on each value of a mapping and each item of a
sequence, so every node in the tree is checked.  A ScalarNode contains no keys, so there is
nothing to check in it.

Since nodes have no names, the location of each node is built up during the recursion as its
"path": the names of the keys leading to it, separated by dots, with [i] for item i of a
sequence.  The path starts as "" (i.e. an empty string) for the root node, and examples are
"workflow.FCST_LEN_HRS" and "fields[0].level".  It is not the path to a file.

In each mapping, the lines on which each key appears are collected.  For each key that appears
more than once, a (first_line, path, lines) tuple is appended to the list duplicates, where
path is the key's path, lines lists the lines on which it appears (counting from 1), and
first_line is the first of these lines.  For the example file in section 1, the tuples are

    (1, "workflow", [1, 8])
    (2, "workflow.PREEXISTING_DIR_METHOD", [2, 4])

A mapping's values are checked (by the recursive calls) before the duplicates among the
mapping's own keys are appended, so the second of these tuples is appended first.
find_duplicate_keys() therefore sorts the tuples by first_line, so that the keys are reported
in the order in which they first appear in the file.  It then turns each tuple into a string
such as "workflow (lines 1, 8)".

If a duplicate key is in a mapping written in single-line form (see section 1), e.g.

    a: {x: 1, x: 2, x: 7}

its line number is repeated.  In this example, the tuple in duplicates is (1, "a.x", [1, 1, 1]),
and the string returned for it is "a.x (lines 1, 1, 1)".

Each node is checked only once.  The ids (from id()) of the nodes already checked are kept in
the set visited_node_ids, and a node whose id is in it is skipped.  This is needed because of
aliases (section 2).  In the key1/key2 example, without it the duplicate sub_key would be
reported twice in the duplicates list, as key1.sub_key and key2.sub_key.  (Note that if there
were only one sub_key under key1, neither key1.sub_key nor key2.sub_key would be in duplicates,
with or without visited_node_ids.)  In the a: &x [1, *x] example, the recursion would never
end.  The id of a node is stored rather than the node itself to make clear that the test is
whether it is the same object.  (Two mappings written separately with the same contents are
different nodes, and both must be checked.)  A set is used for visited_node_ids (instead of,
say, a list) because checking whether it contains an id takes the same time regardless of how
many ids it holds.  The same set is passed to every recursive call and added to in place, so a
node checked in one branch of the tree is skipped in all the others.

The key "<<" is not reported even if it appears more than once in a mapping.  It is the YAML
merge key (e.g. <<: *defaults copies the pairs of the mapping anchored as &defaults into the
current mapping), and PyYAML applies every occurrence of it, so repeating it loses nothing.

The keys that << copies in are not in the current mapping's list of pairs, so a key written in
the mapping to override one of them is not reported either, which is the behavior we want.  For
example, in

    defaults: &defaults
      cycledefs: forecast
      maxtries: 1
    attrs:
      <<: *defaults
      maxtries: 3

the list of pairs of the value of attrs contains only << and maxtries, so maxtries appears in it
only once.  When the file is loaded, << copies cycledefs and maxtries into attrs, and the
maxtries written in attrs replaces the copied one, so the value of attrs becomes

    {"cycledefs": "forecast", "maxtries": 3}

The task files in parm/wflow use << in this way throughout.
"""

import yaml


def find_duplicate_keys(yaml_path) -> list:
    """Find the keys that appear more than once in the same mapping of a YAML file.

    See the module docstring for what a mapping and a duplicate key are and for how the
    duplicates are found.  The file is read without being loaded, so tags such as !int and !list
    are not evaluated.

    Parameters
    ----------
    yaml_path : str or Path
        Path to the YAML file.

    Returns
    -------
    list of str
        One entry for each duplicate key, in the order in which the keys first appear in the
        file, giving the key's path and the lines on which it appears.  For the example file in
        the module docstring, the list is

            ["workflow (lines 1, 8)", "workflow.PREEXISTING_DIR_METHOD (lines 2, 4)"]

        The list is empty if there are no duplicate keys.
    """
    #
    # Read the file as a tree of nodes rather than as dicts, so that every
    # occurrence of each key is kept (see section 2 of the module docstring).
    # root_node is the top of the tree, or None if the file is empty.
    #
    with open(yaml_path, encoding="utf-8") as yaml_file:
        root_node = yaml.compose(yaml_file, Loader=yaml.SafeLoader)
    #
    # Find the duplicate keys (see section 3 of the module docstring).  Each
    # one is recorded in duplicates as a (first_line, path, lines) tuple.
    #
    duplicates = []
    #
    # The last argument of the call to _find_duplicate_keys_in_node() below is
    # visited_node_ids, the set of the ids of the nodes that have already
    # been checked.  Since no node has been checked yet, it is set to an
    # empty set, created with set().  It is created here, as is duplicates,
    # so that each call of this function starts with its own empty set and
    # list.  A default argument such as visited_node_ids=set() would be
    # created only once, when the function is defined, and then shared by
    # all calls.
    #
    _find_duplicate_keys_in_node(root_node, "", duplicates, set())
    #
    # Sort the tuples by first_line, the line on which each key first appears
    # (see section 3 of the module docstring for why this is needed):
    #
    # - sort() reorders the list itself (in place) and returns None.
    #
    # - key= gives a function that sort() calls once on each item.  The items
    #   are ordered by the values it returns rather than by the items
    #   themselves.
    #
    # - lambda dup: dup[0] is that function, written inline.  It takes a tuple
    #   dup (a duplicate) and returns its first element, first_line.
    #
    duplicates.sort(key=lambda dup: dup[0])
    #
    # Turn each tuple into an entry (a string) in the returned list giving
    # the key's path and all the lines on which it appears, e.g.
    #
    #     "workflow.PREEXISTING_DIR_METHOD (lines 2, 4)"
    #
    # first_line is not needed in this entry because it is already present
    # as the first element in the list of lines.
    #
    entries = []
    for _first_line, path, lines in duplicates:
        line_numbers = ", ".join(str(line) for line in lines)
        entries.append(f"{path} (lines {line_numbers})")
    return entries


def _find_duplicate_keys_in_node(node, path, duplicates, visited_node_ids):
    """Append to duplicates a (first_line, path, lines) tuple for each duplicate key in node and
    in the nodes below it (see section 3 of the module docstring).  path is the location of node
    in the file, written as described in section 3 (e.g. "workflow" or "fields[0]", and "" for
    the root node)."""
    #
    # Skip a node that has already been checked, which can happen because of
    # aliases (see sections 2 and 3 of the module docstring).
    #
    if node is None or id(node) in visited_node_ids:
        return
    #
    # Mark the current node as visited by adding its id to visited_node_ids.
    #
    visited_node_ids.add(id(node))
    #
    # In a mapping, node.value is the list of its (key_node, value_node)
    # pairs.  key_node is a ScalarNode whose .value is the key's name and
    # whose .start_mark.line is its line number (counting from 0).
    # value_node may itself be a mapping or a sequence, so it is checked by
    # calling this function again.
    #
    # A ScalarNode matches neither this branch nor the SequenceNode branch
    # below, so nothing more is done with it (it contains no keys).
    #
    if isinstance(node, yaml.MappingNode):
        # For each key in this mapping, collect the lines on which it appears.
        key_lines = {}
        for key_node, value_node in node.value:
            # In any file the workflow can load, key_node is a ScalarNode
            # whose .value is the key's name as a str, so str() in the
            # following line has no effect.  str() is needed only for a key
            # that is itself a list or a mapping, e.g. from an unquoted Jinja
            # template such as {{ name }} (see section 2 of the module
            # docstring).  Such a file can't be loaded, but it can still reach
            # this function, since setup.py checks for duplicate keys (via
            # this function) before loading the file.  key_node is then a
            # SequenceNode or MappingNode whose .value is a list, which can't
            # be used as a key of key_lines.
            key = str(key_node.value)
            #
            # Note that the statement
            #
            #   some_dict.setdefault(some_key, default_val)
            #
            # first checks whether some_key is a key in the dictionary
            # some_dict.  If so, it returns the value corresponding to
            # some_key.  If not, it creates some_key in some_dict, sets its
            # value to default_val, and returns default_val.  In both cases,
            # the object returned is the one stored in some_dict, not a copy.
            #
            # Here, the first time a key is seen, an empty list is stored
            # under it in key_lines.  Each time the key is seen (including
            # the first), its line number (counting from 1) is appended to
            # that list, i.e. to the list in key_lines.  (The + 1 is needed
            # because key_node.start_mark.line counts from 0, i.e. it takes
            # the first line of the file to be line 0.)
            #
            key_lines.setdefault(key, []).append(key_node.start_mark.line + 1)
            _find_duplicate_keys_in_node(
                value_node, f"{path}.{key}" if path else key, duplicates, visited_node_ids
            )
        for key, lines in key_lines.items():
            # "<<", the YAML merge key, may appear more than once (see
            # section 3 of the module docstring).
            if len(lines) > 1 and key != "<<":
                duplicates.append((lines[0], f"{path}.{key}" if path else key, lines))
    #
    # In a sequence (list), node.value is the list of the nodes of its items.
    # An item may be a mapping, so check each one.
    #
    # The path of item i is the path of the sequence followed by [i].
    # f"{path}[{i}]" is an f-string: each {...} is replaced by the value of
    # the expression inside it, and everything else, including the square
    # brackets, is copied as written.  For example, for
    #
    #   workflow:
    #     taskgroups: [get_obs.yaml, verify_det.yaml]
    #
    # the path of the sequence is workflow.taskgroups, so its items get the
    # paths workflow.taskgroups[0] and workflow.taskgroups[1].  If an item is
    # a mapping, its keys continue the path with dots, e.g. fields[0].level.
    #
    # Unlike in the mapping case above, no dot is put before the [ because
    # an index attaches directly to the name of the list, as in Python.  So
    # no "if path" test is needed: if the whole file is a list, its items get
    # the paths [0], [1], ..., which read correctly.  (In the mapping case,
    # the test avoids a leading dot, as in .workflow.)
    #
    elif isinstance(node, yaml.SequenceNode):
        for i, item in enumerate(node.value):
            _find_duplicate_keys_in_node(item, f"{path}[{i}]", duplicates, visited_node_ids)
