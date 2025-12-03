"""
Contains function set_vx_params
"""

from textwrap import dedent

def set_vx_params(obtype,field_group,accum_hh):
    """Function for returning various verification parameters based on input args

    obtype      (str): Observation type to set up
    field_group (str): Field group to set up
    accum_hh    (int): Number of hours observation is accumulated over"""

    fieldname_in_obs_in = fieldname_in_fcst_in = fieldname_in_met_out = None
    fieldname_in_met_filedir_names = grid_or_point = None
    match obtype:
        case "CCPA":
            grid_or_point = "grid"
            if field_group == "APCP":
                fieldname_in_obs_in = field_group
                fieldname_in_fcst_in = field_group
                fieldname_in_met_out = field_group
                fieldname_in_met_filedir_names = f"{field_group}{accum_hh:02}"
        case "NOHRSC":
            grid_or_point = "grid"
            if field_group == "ASNOW":
                fieldname_in_obs_in = field_group
                fieldname_in_fcst_in = field_group
                fieldname_in_met_out = field_group
                fieldname_in_met_filedir_names = f"{field_group}{accum_hh:02}"
        case "MRMS":
            grid_or_point = "grid"

            if field_group == "REFC":
                fieldname_in_obs_in = "MergedReflectivityQCComposite"
            elif field_group == "RETOP":
                fieldname_in_obs_in = "EchoTop18"

            fieldname_in_fcst_in = field_group
            fieldname_in_met_out = field_group
            fieldname_in_met_filedir_names = field_group
        case "NDAS":
            grid_or_point = "point"
            if field_group in ["SFC", "UPA"]:
                fieldname_in_obs_in = ""
                fieldname_in_fcst_in = ""
                fieldname_in_met_out = f"ADP{field_group}"
                fieldname_in_met_filedir_names = f"ADP{field_group}"
        case "AERONET":
            grid_or_point = "point"
            if field_group == "AOD":
                fieldname_in_obs_in = field_group
                fieldname_in_fcst_in = "AOTK"
                fieldname_in_met_out = field_group
                fieldname_in_met_filedir_names = field_group
        case "AIRNOW":
            grid_or_point = "point"
            if field_group in ["PM25", "PM10"]:
                fieldname_in_obs_in = field_group
                fieldname_in_fcst_in = "MASSDEN"
                fieldname_in_met_out = field_group
                fieldname_in_met_filedir_names = field_group

    # Check if any necessary values are unset before returning
    if any(x is None for x in [fieldname_in_obs_in,fieldname_in_fcst_in,fieldname_in_met_out,
                               fieldname_in_met_filedir_names]):
        raise ValueError(dedent(
                                f"""A method for setting verification parameters has not been
                                specified for this observation type ({obtype}) and field group
                                ({field_group}) combination."""))

    return (grid_or_point, fieldname_in_obs_in, fieldname_in_fcst_in, fieldname_in_met_out,
            fieldname_in_met_filedir_names)
