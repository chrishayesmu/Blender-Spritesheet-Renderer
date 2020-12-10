from typing import Optional

class TerminalWriter:
    """
        Simple class that handles writing to a terminal in one continuous operation, avoiding flickering
        which is caused by backspacing or other techniques for updating the stream in-place. Largely
        intended for use with stdout, and only with a terminal connected.
    """

    def __init__(self, stream, suppress_output: bool):
        self.indent = 0
        self._max_queue_size = 300
        self._out_stream = stream
        self._out_queue = []
        self._suppress_output = suppress_output

    def clear(self):
        if self._suppress_output or not self._out_stream.isatty():
            return

        self._out_stream.write("\x1b[2J\x1b[H")
        self._out_stream.flush()

    def write(self, msg: str, unpersisted_portion: Optional[str] = None, persist_msg: bool = True, ignore_indent: bool = False):
        if self._suppress_output or not self._out_stream.isatty():
            return

        # Remove any leading newlines to add back later, so they don't mess with the indent.
        # Only remove newlines if the whole message isn't newlines, otherwise the tabs will
        # end up on the wrong line.
        num_newlines = 0
        if not ignore_indent and msg.replace("\n", ""):
            while msg.startswith("\n"):
                num_newlines += 1
                msg = msg.replace("\n", "", 1)

        indent = 0 if ignore_indent else self.indent
        msg = (num_newlines * "\n") + (indent * "\t") + msg
        msg = msg.expandtabs(4)

        existing_out = "".join(self._out_queue)

        if persist_msg:
            if len(self._out_queue) >= self._max_queue_size:
                self._out_queue.pop()

            self._out_queue.append(msg)

        if unpersisted_portion:
            msg += unpersisted_portion

        # Don't use self.clearTerminal() to avoid flushing/writing to the stream multiple times
        self._out_stream.write("\x1b[2J\x1b[H" + existing_out + msg)
        self._out_stream.flush()
