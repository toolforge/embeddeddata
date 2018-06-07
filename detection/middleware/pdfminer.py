#! /usr/bin/env python
# -*- coding: UTF-8 -*-
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General License for more details.
#
# You should have received a copy of the GNU General License
# along with self program.  If not, see <http://www.gnu.org/licenses/>
#

from __future__ import absolute_import

import tempfile
import traceback

from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdftypes import PDFStream
from pdfminer.psparser import LIT

from detection.by_magic import detect as magic_detect
from detection.middleware import register_detector
from detection.utils import filetype

LITERAL_FILESPEC = LIT('Filespec')
LITERAL_EMBEDDEDFILE = LIT('EmbeddedFile')


# This is modified from
# https://github.com/euske/pdfminer/blob/44977b6726640933d86028d16ca06fab5ea26d1a/tools/dumppdf.py#L160
@register_detector('Pdfminer_EmbeddedFile',
                   lambda major, minor: minor == 'pdf')
def pdfminer_EmbeddedFile(f):
    ret = []

    with open(f, 'rb') as fp:
        parser = PDFParser(fp)
        doc = PDFDocument(
            parser,
            password='',  # if PDF is protected by password, we know it is evil
            caching=False  # we can run OOM if we cache all the files
        )
        ids = set()
        for xref in doc.xrefs:
            ids.update(xref.get_objids())
        for obj_id in ids:
            try:
                obj = doc.getobj(obj_id)
            except Exception:
                traceback.print_exc()
                continue
            if (
                isinstance(obj, PDFStream) and (
                    obj.get('Type') is LITERAL_EMBEDDEDFILE or
                    'Params' in obj
                )
            ):
                try:
                    data = obj.get_data()
                except Exception:
                    traceback.print_exc()
                    continue

                if len(data):
                    with tempfile.NamedTemporaryFile() as tmp:
                        tmp.write(data)
                        tmp.flush()
                        del obj, data  # save some memory, hopefully
                        ret.append({
                            'pos': 0,
                            'mime': (filetype(tmp.name),
                                     filetype(tmp.name, False))
                        })

                        for item in magic_detect(f) or []:
                            if item['pos']:
                                ret.append(item)
    return ret
