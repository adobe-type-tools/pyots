# Copyright (c) 2020 The OTS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Python interface for pyots.
import _pyots

version = _pyots.version


class OTSResult():
    def __init__(self, raw_tuple):
        self.sanitized = bool(raw_tuple[0])
        self.modified = bool(raw_tuple[1])
        self.messages = tuple(raw_tuple[2].strip().split("\n"))


def sanitize(input, output=None, quiet=False, font_index=-1) -> OTSResult:
    """
    Sanitize a file. Options:
        output      path for output file. If not specified, no output will be
                    written (and input file will not be modified)
        quiet       ots "quiet" mode (no output). Default False.
        font_index  font_index for TTC/OTC. Specify a TTC index to sanitize.
                    Ignored for non-Collections; if left at default, will
                    sanitize all fonts in Collection.

    Returns an OTSResult with the following attributes:
        sanitized (bool)    File was successfully sanitized
        modified (bool)     Modifications were necessary to sanitize the input
                            file (SEE README.md!)
        messages (string)   Messages generated during sanitzation (empty if
                            'quiet' was specified as True).
    """
    (san, mod, rmsg) = _pyots._sanitize(input, output or '', quiet, font_index)

    if rmsg is not None:
        if isinstance(rmsg, bytes):
            msg = rmsg.decode('ascii', errors='backslashreplace')
        else:
            msg = rmsg
    else:
        msg = ''

    return OTSResult((san, mod, msg))
