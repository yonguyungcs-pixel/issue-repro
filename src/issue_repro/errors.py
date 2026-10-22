class UserError(Exception):
    """The command cannot do what was asked. Local files are left unchanged."""


class FetchError(Exception):
    """The GitHub request failed. The caller still writes a blank template."""
