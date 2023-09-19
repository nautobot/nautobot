"""Constants for use in Nautobot core models."""

# For our purposes, COMPOSITE_KEY_SEPARATOR needs to be:
# 1. Safe in a URL path component (so that we can do URLS like "/dcim/devices/<composite_key>/delete/")
#    Per RFC3986 section 2.3 the general "unreserved" characters are ALPHA and DIGIT and the characters -._~
#    Per RFC3986 section 3.3 path components also permit characters :@ and the "sub-delims" characters !$&'()*+,;=
# 2. Not readily confused with characters commonly seen in un-escaped natural key component fields
#    "." is already ruled out as an unreserved character but also would appear in IPv4 IPAddress and Prefix objects
#    ":" similarly would appear in IPv6 IPAddress/Prefix objects
#    "/" would appear in Prefix objects as well as various numbered device component names
# 3. Safe in a URL query string component (so that we can do URLs like "/dcim/devices/?location=<composite_key>"
#    This rules out "&" and "="
COMPOSITE_KEY_SEPARATOR = ";"

# For the natural slug separator, it's much simpler and we can just go with "_".
NATURAL_SLUG_SEPARATOR = "_"
