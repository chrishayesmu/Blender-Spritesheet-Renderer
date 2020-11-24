import os
import sys

class TerminalWriter:
    """
        Simple class that handles writing to a terminal in one continuous operation, avoiding flickering
        which is caused by backspacing or other techniques for updating the stream in-place. Largely
        intended for use with stdout, and only with a terminal connected.
    """

    def __init__(self, stream):
        self.indent = 0
        self._maxQueueSize = 300
        self._outStream = stream
        self._outQueue = []

    def clearTerminal(self):
        if not self._outStream.isatty():
            return

        self._outStream.write("\x1b[2J\x1b[H")
        self._outStream.flush()

    def write(self, msg, unpersistedPortion = None, persistMsg = True, ignoreIndent = False):
        if not self._outStream.isatty():
            return

        # Remove any leading newlines to add back later, so they don't mess with the indent.
        # Only remove newlines if the whole message isn't newlines, otherwise the tabs will
        # end up on the wrong line.
        numNewlines = 0
        if not ignoreIndent and msg.replace("\n", ""):
            while msg.startswith("\n"):
                numNewlines += 1
                msg = msg.replace("\n", "", 1)

        indent = 0 if ignoreIndent else self.indent
        msg = (numNewlines * "\n") + (indent * "\t") + msg
        msg = msg.expandtabs(4)

        existingOut = "".join(self._outQueue)

        if persistMsg:
            if len(self._outQueue) >= self._maxQueueSize:
                self._outQueue.pop()

            self._outQueue.append(msg)

        if unpersistedPortion:
            msg += unpersistedPortion

        # Don't use self.clearTerminal() to avoid flushing/writing to the stream multiple times
        self._outStream.write("\x1b[2J\x1b[H" + existingOut + msg)
        self._outStream.flush()


