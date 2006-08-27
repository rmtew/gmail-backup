import sys, os
import cPickle

messageFileNameTemplate = "messages%05d.bin"

def GetMessageFileNames():
    fileNumber = 1
    fileName = messageFileNameTemplate % fileNumber

    while os.path.exists(fileName):
        yield fileName

        # Set the ID and name for the next candidate.
        fileNumber += 1
        fileName = messageFileNameTemplate % fileNumber


if __name__ == "__main__":
    # Load in the original messages:
    # - Find any missing or bad entries.
    # - Cache which we have.

    messagesByID = {}
    addedMessagesByID = {}
    for fileName in GetMessageFileNames():
        messagesByID.update(cPickle.load(open(fileName, "rb")))

    try:
        pass
    finally:
        messageFileNames = list(GetMessageFileNames())

        # We need to delete the split files and save one bulk one.
        if len(messageFileNames) > 1 or messageChanges:
            for fileName in messageFileNames:
                os.remove(fileName)

            print "Saving", len(messagesByID), "messages...",
            cPickle.dump(messagesByID, open(messageFileNameTemplate % 1, "wb"))
            print "done"
