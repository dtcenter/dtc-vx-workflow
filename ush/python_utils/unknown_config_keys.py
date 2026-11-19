"""
Function for finding the keys in a configuration that a reference configuration doesn't define.

This module provides find_unknown_config_keys(), which compares a configuration (e.g. a user config)
with a reference configuration (e.g. the default settings) and returns the keys of the first
that are not in the second.  It is used to find misspelled or misplaced settings in a user
config, which would otherwise be silently ignored.

Both configurations are nested dictionaries, as returned by loading a YAML file.  A key is
identified by its "path", i.e. the names of the keys leading to it, separated by dots, e.g.
"verification.VX_FIELD_GROUPS".  A key is unknown if the reference has no key with the same
path.  For example, with the reference

    verification:
      VX_FIELD_GROUPS: [ "APCP" ]
    genensprod:
      execution:
        walltime: 02:00:00

the configuration

    verification:
      VX_FIELD_GROUP: [ "SFC" ]
    ensemble:
      execution:
        walltime: 08:00:00

has the unknown keys "verification.VX_FIELD_GROUP" (misspelled) and "ensemble" (a section the
reference doesn't have).  The keys under an unknown key (here, ensemble.execution and
ensemble.execution.walltime) are not reported separately, since the unknown key already
identifies the problem.

The comparison descends only into values that are dictionaries in both configurations.  The
items of lists are not compared, and neither are the contents of a value that is a dictionary in
only one of the two configurations.  The contents of some keys are not compared either:

- free_form_paths: keys at these paths are accepted, together with everything under them, even
  if the reference doesn't define them (e.g. a section whose contents are checked elsewhere).

- free_form_keys: keys with these names are accepted, together with everything under them,
  wherever the reference defines them (e.g. a section that holds settings passed through to
  another program, whose names the reference can't list).  Such a key is unknown where the
  reference doesn't define it, like any other key.

For example, with the reference

    genensprod:
      conf:
        LOG_GEN_ENS_PROD_VERBOSITY: 2
      execution:
        walltime: 02:00:00
    gridstat:
      execution:
        walltime: 01:00:00

the configuration

    rocoto:
      tasks:
        task_anything:
          walltime: 00:10:00
    genensprod:
      conf:
        GEN_ENS_PROD_EAS_PROB_SHAPE: CIRCLE
    gridstat:
      conf:
        GRID_STAT_NC_PAIRS_FLAG_LATLON: false

and free_form_paths=["rocoto"] and free_form_keys=["conf"], the only unknown key is
"gridstat.conf":

- rocoto is accepted, with everything under it, because it is in free_form_paths, although the
  reference doesn't define it.

- genensprod.conf is accepted, and its contents (GEN_ENS_PROD_EAS_PROB_SHAPE) are not compared,
  because conf is in free_form_keys and the reference defines genensprod.conf.

- gridstat.conf is unknown, although conf is in free_form_keys, because the reference doesn't
  define gridstat.conf.

Without free_form_paths and free_form_keys, the unknown keys would be "rocoto",
"genensprod.conf.GEN_ENS_PROD_EAS_PROB_SHAPE", and "gridstat.conf".
"""


def find_unknown_config_keys(config, ref_config, free_form_paths=(), free_form_keys=()) -> list:
    """Find the keys in config that are not in ref_config.

    See the module docstring for which keys are compared.

    Parameters
    ----------
    config : dict
        The configuration to check, e.g. a user config.
    ref_config : dict
        The configuration that defines the known keys, e.g. the default settings.
    free_form_paths : iterable of str
        Paths (e.g. "rocoto") of keys that are accepted, with everything under them, even if
        ref_config doesn't define them.
    free_form_keys : iterable of str
        Names (e.g. "fields") of keys whose contents are not compared, at any level at which
        ref_config defines them.  Where ref_config doesn't define such a key, it is flagged
        as unknown.

    Returns
    -------
    list of str
        The paths of the unknown keys, in the order in which they appear in config.  The list
        is empty if there are none.
    """
    free_form_paths = set(free_form_paths)
    free_form_keys = set(free_form_keys)
    unknown_keys = []

    def check(config, ref_config, path):
        """Append to unknown_keys the path of each key in config (the dict at the given path in
        the configuration being checked, "" for the top level) that is not in ref_config (the
        dict at the same path in the reference configuration), descending into only those values
        that are dicts in both."""
        for key, value in config.items():
            key_path = f"{path}.{key}" if path else str(key)
            if key_path in free_form_paths:
                continue  # accepted as is: not compared, not descended into
            if key not in ref_config:
                unknown_keys.append(key_path)
                continue  # recorded as unknown; its contents aren't checked
            if key in free_form_keys:
                continue  # known, but its contents aren't compared
            if isinstance(value, dict) and isinstance(ref_config[key], dict):
                check(value, ref_config[key], key_path)  # descend

    check(config, ref_config, "")
    return unknown_keys
