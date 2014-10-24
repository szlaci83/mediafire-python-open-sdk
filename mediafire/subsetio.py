"""SubsetIO"""

import os
import io


class SubsetIO(io.IOBase):
    """minimal file-like object exposing subset of parent file"""
    def __init__(self, fd, offset, length):
        """Create new ChunkedFileWrapper object

        fd -- parent file handle
        offset -- start byte of the view
        length -- length of the view
        """

        try:
            self.parent_fd = os.fdopen(os.dup(fd.fileno()), mode='rb')
        except io.UnsupportedOperation:
            self.parent_fd = fd

        self.offset = offset
        # name also makes requests.utils.super_len() work
        self.len = length

        # find the size of the original file
        self.parent_fd.seek(0, os.SEEK_END)
        file_size = self.parent_fd.tell()

        if self.offset + self.len > file_size:
            self.len = file_size - self.offset

        if self.offset < 0:
            self.offset = 0

        if self.len < 0:
            self.len = 0

        self.parent_fd.seek(self.offset)

    def read(self, limit=-1):
        """Read content. See file.read"""
        remaining = self.len - self.parent_fd.tell() + self.offset

        if limit > remaining or limit == -1:
            limit = remaining

        return self.parent_fd.read(limit)

    def seek(self, offset, whence=os.SEEK_SET):
        """Seek to position in stream, see file.seek"""

        pos = None
        if whence == os.SEEK_SET:
            pos = self.offset + offset
        elif whence == os.SEEK_CUR:
            pos = self.tell() + offset
        elif whence == os.SEEK_END:
            pos = self.offset + self.len + offset
        else:
            raise ValueError("invalid whence {}".format(whence))

        if pos > self.offset + self.len or pos < self.offset:
            raise ValueError("seek position beyond chunk area")

        self.parent_fd.seek(pos, os.SEEK_SET)

    def tell(self):
        """Get current position in file, see file.tell"""
        result = self.parent_fd.tell() - self.offset
        return result

    def close(self):
        """Close file, see file.close"""
        self.parent_fd.close()
