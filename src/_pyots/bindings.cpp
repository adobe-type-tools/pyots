// Copyright (c) 2020 The OTS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <algorithm>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <memory>

#include "Python.h"

#include "config.h"
#include "ots-memory-stream.h"
#include "pyots-context.h"


static PyObject* method_sanitize(PyObject* self, PyObject* args) {
  PyObject* pyInFilenameObj;
  PyObject* pyOutFilenameObj;
  int quiet = 0;
  int kwFontIndex = -1;

  /* parse the Python args */
  if (!PyArg_ParseTuple(args, "O&O&ii",
                        PyUnicode_FSConverter, &pyInFilenameObj,
                        PyUnicode_FSConverter, &pyOutFilenameObj,
                        &quiet,
                        &kwFontIndex)) {
    return NULL;
  }

  /* Parse the Python input filename obj into a C string */
  Py_ssize_t lenIn;
  char *infilename;
  if (PyBytes_AsStringAndSize(pyInFilenameObj, &infilename, &lenIn)) {
    Py_XDECREF(pyInFilenameObj);
    return NULL;
  }

  /* Open the input filestream */
  std::ifstream ifs(infilename, std::ifstream::binary);
  if (!ifs.good()) {
    return PyErr_SetFromErrnoWithFilenameObject(PyExc_OSError, pyInFilenameObj);
  }
  /* Read the input file */
  std::vector<uint8_t> in((std::istreambuf_iterator<char>(ifs)),
                          (std::istreambuf_iterator<char>()));
  ifs.close();

  /* Define our OTS context */
  ots::PyOTSContext context(quiet ? -1: 4);

  /* set up output stream */
  ots::ExpandingMemoryStream output(in.size() * 2, in.size() * 8);

  /* process (sanitize) */
  bool sanitized;
  sanitized = context.Process(&output, in.data(), in.size(), kwFontIndex);

  /* check for file modifications */
  // TODO(josh-hadley): figure out the right way to do this...ots seems to
  // modify *everything*. Currently using very naive approach: basically if
  // any WARNINGs were generated, but file was successfully sanitized, we
  // count it as a modification. Probably need to analyze ots and look for
  // specific messages that indicate modification and trap for those.
  bool modified = sanitized && context.modified;

  /* write output, if specified */
  if (PyObject_IsTrue(pyOutFilenameObj)) {
    char *outfilename;
    Py_ssize_t ofl;
    if (PyBytes_AsStringAndSize(pyOutFilenameObj, &outfilename, &ofl)) {
      Py_XDECREF(pyOutFilenameObj);
      return NULL;
    }

    std::ofstream outs(outfilename, std::ofstream::out | std::ofstream::binary);
    if (!outs.good()) {
      return PyErr_SetFromErrnoWithFilenameObject(
        PyExc_OSError, pyOutFilenameObj);
    }
    outs.write(reinterpret_cast<const char*>(output.get()), output.Tell());
    outs.close();
  }

  // Set up returns
  PyObject* pymsgstr;
  PyObject* pysanitized = PyBool_FromLong(sanitized);
  PyObject* pymodified = PyBool_FromLong(modified & sanitized);
  if (quiet) {
    pymsgstr = Py_BuildValue("y", NULL);
  } else {
    pymsgstr = PyBytes_FromStringAndSize(context.buff, context.offset);
  }
  PyObject* retTuple = Py_BuildValue("OOO",
                                     pysanitized,
                                     pymodified,
                                     pymsgstr);

  // decref PyObjects
  Py_XDECREF(pyInFilenameObj);
  Py_XDECREF(pyOutFilenameObj);
  Py_XDECREF(pymsgstr);
  Py_XDECREF(pysanitized);
  Py_XDECREF(pymodified);

  return retTuple;
}


/* Module method list */
static PyMethodDef py_ot_sanitizer_methods[] = {
    {"_sanitize", method_sanitize, METH_VARARGS,
     "Back-end sanitize function. Generally, you won't call this directly. "
     "Use pyots.sanitize() instead."},
    {NULL, NULL, 0, NULL}, /* sentinel to indicate no more methods */
};


/* Module definition */
static struct PyModuleDef py_ot_sanitizer_module = {
    PyModuleDef_HEAD_INIT,
    "_pyots",
    "pyots backend module",
    -1,
    py_ot_sanitizer_methods,
};


/* Module initialization */
PyMODINIT_FUNC PyInit__pyots(void) {
  PyObject *_pyots = PyModule_Create(&py_ot_sanitizer_module);

  PyModule_AddStringConstant(_pyots, "version", PACKAGE " " VERSION);

  return _pyots;
}
