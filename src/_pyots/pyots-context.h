// Copyright (c) 2020 The OTS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef SRC__PYOTS_PYOTS_CONTEXT_H_
#define SRC__PYOTS_PYOTS_CONTEXT_H_

#include <cstdarg>
#include <fstream>
#include <sstream>

#include "opentype-sanitiser.h"

namespace ots {

class PyOTSContext: public OTSContext {
 public:
  explicit PyOTSContext(int level): level_(level) { }
  std::stringstream msgs;
  bool modified = false;

  void Message(int level, const char *format, ...) {
    va_list va;

    if (level) {
      // This is almost certainly not the right way to determine this, but...
      modified = true;
    }

    if (level > level_)
      return;

    if (level == 0) {
      msgs << "ERROR: ";
    } else {
      msgs << "WARNING: ";
    }

    char *tmp;
    va_start(va, format);
    vasprintf(&tmp, format, va);
    msgs << tmp << std::endl;
    free(tmp);
    va_end(va);
  }

  TableAction GetTableAction(uint32_t tag) {
    switch (tag) {
      case OTS_TAG('C', 'B', 'D', 'T'):
      case OTS_TAG('C', 'B', 'L', 'C'):
      case OTS_TAG('s', 'b', 'i', 'x'):

        return TABLE_ACTION_PASSTHRU;

      default:
        return TABLE_ACTION_DEFAULT;
    }
  }

 private:
  int level_;
};

}  // namespace ots

#endif  // SRC__PYOTS_PYOTS_CONTEXT_H_
