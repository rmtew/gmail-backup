import sys, os
import cPickle

if __name__ == "__main__":
    sourceDumpTemplate = "source%05d.bin"
    # messageID = "108fc3cccbcbb9cf"
    messageID = "109dad159daaac1b"

    sourceDumpID = 1
    sourceDumpName = sourceDumpTemplate % sourceDumpID
    while os.path.exists(sourceDumpName):
        # Process what is in the given archive.
        d = cPickle.load(open(sourceDumpName, "rb"))
        if d.has_key(messageID):
            sys.stderr.write("Found message.\n")
            sys.stdout.write(d[messageID])
            sys.exit(1)
        # Set the ID and name up for the next candidate.
        sourceDumpID += 1
        sourceDumpName = sourceDumpTemplate % sourceDumpID

    sys.stderr.write("Did not find message.\n")
