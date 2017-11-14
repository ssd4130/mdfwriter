def formatstring(s, limit):
    """This method truncates strings to specified length and makes
    sure they are delimited with correct MDF spec delimiter (NULL)."""
    if len(s) > 0 & len(s) <= limit-1:
        s += chr(0)*(limit-len(s))
    elif len(s) == 0:
        s = chr(0)*limit
    elif len(s) >= limit:
        s = s[0:limit-1] + chr(0)
    return s
