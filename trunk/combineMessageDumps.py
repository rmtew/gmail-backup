import sys, os
import cPickle

messageDumpFileNameTemplate = "data/messages%05d.bin"
messageIndexFileNameTemplate = "data/messages%05d.idx"

def GetMessageFileNames():
    fileNumber = 1
    dumpFileName = messageDumpFileNameTemplate % fileNumber
    indexFileName = messageIndexFileNameTemplate % fileNumber

    while os.path.exists(dumpFileName):
        yield dumpFileName, indexFileName

        # Set the ID and name for the next candidate.
        fileNumber += 1
        dumpFileName = messageDumpFileNameTemplate % fileNumber
        indexFileName = messageIndexFileNameTemplate % fileNumber

def ValidMessage(s):
    if not (s is None or s.startswith("<script>")):
        return True
    return False


if __name__ == "__main__":
    # We need to delete the split files and save one bulk one.

    messageFileNames = list(GetMessageFileNames())

    if len(messageFileNames) > 1:
        # Read in and combine all the messages.  Deleting the files.
        messagesByID = {}
        for dumpFileName, indexFileName in messageFileNames:
            messagesByID.update(cPickle.load(open(dumpFileName, "rb")))

            if os.path.exists(dumpFileName):
                os.remove(dumpFileName)
            if os.path.exists(indexFileName):
                os.remove(indexFileName)

        # Save out the combined dump.
        print "Saving", len(messagesByID), "messages...",
        cPickle.dump(messagesByID, open(messageDumpFileNameTemplate % 1, "wb"))
        print "done"

        # Build an index of the new dump.
        wanted = {}
        cached = {}
        indexFileName = messageIndexFileNameTemplate % 1
        for k, v in messagesByID.iteritems():
            if not ValidMessage(v):
                wanted[k] = None
            else:
                cached[k] = len(v)
        cPickle.dump((wanted, cached), open(indexFileName, "wb"))
