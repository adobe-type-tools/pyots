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
  int buffsize = 2048;
  char *buff = (char *)malloc(buffsize * sizeof(char));
  int offset = 0;
  bool modified = false;

  void Message(int level, const char *format, ...) {
    va_list va;

    if (level >= 0) {
      // assume any Warning or Error means a modification was needed.
      modified = true;
    }

    if (level > level_)
      return;

    if (offset > buffsize - 256) {
      buffsize *= 1.5;
      char *tmp_buff = (char *)realloc(buff, buffsize * sizeof(char));
      if (tmp_buff == NULL) {
        printf("Memory error; aborting.\n");
        free(buff);
        exit(-2);
      } else {
        buff = tmp_buff;
      }
    }

    if (level == 0) {
      offset += snprintf(buff + offset, buffsize - offset, "ERROR: ");
    } else {
      offset += snprintf(buff + offset, buffsize - offset, "WARNING: ");
    }

    va_start(va, format);
    offset += vsnprintf(buff + offset, buffsize - offset, format, va);
    va_end(va);
    offset += snprintf(buff + offset, buffsize - offset, "\n");
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

  ~PyOTSContext() {
    if (buff)
      free(buff);
  }

 private:
  int level_;
};

}  // namespace ots

#endif  // SRC__PYOTS_PYOTS_CONTEXT_H_
