def str_to_var_name(verbose_name):
    """Convert a string to a variable compatible name.
    Examples:
        IP Addresses > ip_addresses
    """
    return verbose_name.lower().replace(" ", "_").replace("-", "_")
