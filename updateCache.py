#
# Name: updateCache.py.
# Author: Richard Tew <richard.m.tew@gmail.com>
#
# This project is released under the terms of the MIT license,
# which you should find included in the LICENSE file.
#
# The purpose of this script is to keep a local backup of the
# complete contents of your gmail account. These are the
# elements it backs up:
#
#  - All original messages (attachments included I assume).
#  - Message / thread relationships.
#  - Thread / label relationships.
#  - List of labels.
#
# This script will create a 'data' directory, in the current
# directory, which is where it also expects to save the
# backed up data, and to be run from.
#
# ** What format is the data backed up in:
#
#  - As pickled files, using the Python pickling format.
#
#    To make use of this data, you will need to write your
#    own scripts to unpickle it and process it as needed.
#    But the key point is that it is there, backed up, and
#    accessible.
#
# ** What this script does not handle:
#
#  - Removal of labels.  You will need to write code to
#    handle this case yourself.
#
#  - Renaming of labels.  Labels do not appear to have IDs
#    and as such there is no easy way to relate an old
#    label name to a new one.  If you want the mails in
#    the backed up data under the renamed label, you will
#    have to move it there yourself.
#
# ** Notes about gmail and the development of this script:
#
#  - Where this script receives an unexpected result back from
#    gmail, it exits immediately saving any data it has
#    collected that is worth saving.
#
#    DO NOT RE-RUN IT UNTIL YOU HAVE USED YOUR EMAIL ACCOUNT
#    IN A BROWSER AND ENSURED THAT YOU ARE NOT LOCKED OUT OF
#    YOUR ACCOUNT BECAUSE OF "unusual usage detected".
#
#    I am convinced that the potential case of being locked
#    out of your account for up to 24 hours is more likely
#    the more you use something like this script when gmail
#    has already locked you out, or just after the let you
#    back into your account.
#
#  - Being locked out of your account seems pretty harmless.
#    I was locked out of mine about five times during the
#    development of this script.  Filling in the form they
#    provide to get your account unlocked is.. well, all
#    it seemed to get me was a confused sounding email
#    telling me to reply providing the same information I
#    entered into the form if I thought I shouldn't have
#    been locked out.  The same thing filling out the form
#    was supposed to accomplish.  No fricking idea what is
#    going on there.
#
#  - In order to avoid being locked out of your account it
#    is worthwhile, when modifying this script, to enable
#    the option "backupSearchResults" and to understand how
#    it can help you hammer the gmail servers less.
#
#  - Are the delays enough?  Throughout this script, wherever
#    the gmail servers are hit with requests, this is followed
#    with a 2 second delay to avoid hammering them.  I just
#    did it as a token effort.
#

import sys, os, time
import cPickle
from getpass import getpass
from libgmail import libgmail

defaultUsername = "no default" # "username@gmail.com"

# If you are planning to run this over and over tweaking the script
# you will want to take advantage of this in or
backupSearchResults = False

messageDumpFileNameTemplate = "data/messages%05d.bin"
messageIndexFileNameTemplate = "data/messages%05d.idx"
threadMessagesFileName = "data/threadMessages.bin"
threadLabelsFileName = "data/threadLabels.bin"
labelsFileName = "data/labels.bin"

def GetNextMessageDumpFileName():
    fileNumber = 1

    l = list(GetMessageFileNames())
    if len(l):
        fileNumber = l[-1][0] + 1

    fileName = messageDumpFileNameTemplate % fileNumber
    if os.path.exists(fileName):
        raise RuntimeError("Found unexpected file")
    return fileName

def GetMessageFileNames():
    fileNumber = 1
    dumpFileName = messageDumpFileNameTemplate % fileNumber
    indexFileName = messageIndexFileNameTemplate % fileNumber

    while os.path.exists(dumpFileName):
        yield fileNumber, indexFileName, dumpFileName

        fileNumber += 1
        dumpFileName = messageDumpFileNameTemplate % fileNumber
        indexFileName = messageIndexFileNameTemplate % fileNumber


def ValidMessage(s):
    if not (s is None or s.startswith("<script>")):
        return True
    return False

tempSearchLimitedFileName = "data/tmp.SEARCH-1.bin"
tempSearchCompleteFileName = "data/tmp.SEARCH-2.bin"

def FetchSearchResult(ga, allPages=False):
    if allPages:
        tempSearchFileName = tempSearchCompleteFileName
    else:
        tempSearchFileName = tempSearchLimitedFileName

    if backupSearchResults and os.path.exists(tempSearchFileName):
        print " Loading the cached search result."
        searchResult = cPickle.load(open(tempSearchFileName, "rb"))
        searchResult._account = ga
    else:
        print " Fetching the latest search result from the server...",
        searchResult = ga.getMessagesByFolder("all", allPages=allPages)
        if backupSearchResults:
            cPickle.dump(searchResult, open(tempSearchFileName, "wb"))
        print "done."

    return searchResult

def PurgeCachedSearchResults():
    if os.path.exists(tempSearchLimitedFileName):
        os.remove(tempSearchLimitedFileName)

    if os.path.exists(tempSearchCompleteFileName):
        os.remove(tempSearchCompleteFileName)

class Data:
    threadID = None
    threadTally = 0

def ProcessSearchResult(result, data):
    cnt = 1
    for thread in result:
        print " %05d" % cnt,
        data.threadTally += 1

        if data.wantedThreadMessages.has_key(thread.id):
            print "Skipping previously processed thread", thread.id
            continue

        usedCache = True
        if len(thread._messages) == 0:
            print "Fetching messages for thread", thread.id, "from server...",
            usedCache = False
        else:
            print "Using cached messages for thread", thread.id

        messages = thread[:]

        if not usedCache:
            print "done."

        if not len(messages):
            print
            print "FATAL ERROR: No messages returned for thread", thread.id
            sys.exit(1)

        lastMessageID = messages[-1].id

        messageDataByID = data.messageIDsByThreadID.get(thread.id, None)
        if messageDataByID is not None:
            if messageDataByID.has_key(lastMessageID):
                # Identified a preprocessed point (hopefully).
                data.threadID = thread.id
                return True

            expectAbsence = False
            for msg in thread:
                if messageDataByID.has_key(msg.id):
                    if expectAbsence:
                        print " WARNING: Found an unexpected message", msg.id, "in thread", thread.id
                else:
                    expectAbsence = True

                    if not data.wantedThreadMessages.has_key(thread.id):
                        data.wantedThreadMessages[thread.id] = {}
                    data.wantedThreadMessages[thread.id][msg.id] = None
                    if not data.cachedMessages.has_key(msg.id):
                        data.wantedMessages[msg.id] = None
        else:
            d = data.wantedThreadMessages[thread.id] = {}
            for msg in thread:
                # Index it by thread.
                d[msg.id] = None
                # Note to get the full message if it is not cached already.
                if not data.cachedMessages.has_key(msg.id):
                    data.wantedMessages[msg.id] = None

        # Store the labels for the thread.
        for label in thread.getLabels():
            if not data.threadsByLabel.has_key(label):
                data.threadsByLabel[label] = {}
            data.threadsByLabel[label][thread.id] = None

        # Token attempt not to hammer the gmail server.
        if not usedCache:
            time.sleep(2.0)

        cnt += 1

    # Did not identify that we had reached a preprocessed point.
    return False

def UpdateCachedLabels(ga, data):
    data.labels = []
    if os.path.exists(labelsFileName):
        data.labels = cPickle.load(open(labelsFileName, "rb"))

    currentLabels = ga.getLabelNames()

    # Check that no labels have gone missing.
    labelsMissing = False
    for label in data.labels:
        if label not in currentLabels:
            print "ERROR: Label '%s' no longer exists." % label
            labelsMissing = True
    if labelsMissing:
        print "You've removed one or more labels, this is your problem to sort out!"
        sys.exit(1)

    # Check for labels that need to be added.
    labelsAdded = False
    for label in currentLabels:
        if label not in data.labels:
            print "New label '%s' detected." % label
            data.labels.append(label)
            labelsAdded = True

    if labelsAdded:
        cPickle.dump(data.labels, open(labelsFileName, "wb"))
    else:
        print "Loaded %d labels." % len(data.labels)

if __name__ == "__main__":
    if not os.path.exists("data"):
        os.mkdir("data")

    data = Data()

    # Process the cached messages we already have.
    messagesByID = {}
    data.cachedMessages = {}
    data.wantedMessages = {}
    for fileNumber, indexFileName, dumpFileName in GetMessageFileNames():
        if os.path.exists(indexFileName):
            wanted, cached = cPickle.load(open(indexFileName, "rb"))
        else:
            wanted = {}
            cached = {}
            for k, v in cPickle.load(open(dumpFileName, "rb")).iteritems():
                if not ValidMessage(v):
                    wanted[k] = None
                else:
                    cached[k] = len(v)
            cPickle.dump((wanted, cached), open(indexFileName, "wb"))

        data.wantedMessages.update(wanted)
        data.cachedMessages.update(cached)

        # May have one big dump, which would otherwise be kept around.
        wanted = cached = None

    # Delete wanted messages that were in later caches.
    for messageID in data.wantedMessages.keys():
        if data.cachedMessages.has_key(messageID):
            del data.wantedMessages[messageID]

    invalidCount = len(data.wantedMessages)
    print "Loaded", len(data.cachedMessages), "cached messages (%d were invalid)." % invalidCount

    # Load in the thread / message index.
    data.messageIDsByThreadID = {}
    if os.path.exists(threadMessagesFileName):
        data.messageIDsByThreadID = cPickle.load(open(threadMessagesFileName, "rb"))

    # Process it, correcting the entry format, and noting missing
    # messages from the cache of "original message" data.
    for threadID, messageDataByID in data.messageIDsByThreadID.iteritems():
        for messageID in messageDataByID.keys():
            messageDataByID[messageID] = None

            if not data.cachedMessages.has_key(messageID):
                data.wantedMessages[messageID] = None

    s = ""
    delta = len(data.wantedMessages) - invalidCount
    if delta > 0:
        s = " (%d messages are not cached)" % delta
    print "Loaded", len(data.messageIDsByThreadID), "thread message mappings"+ s +"."

    data.threadsByLabel = {}
    if os.path.exists(threadLabelsFileName):
        data.threadsByLabel = cPickle.load(open(threadLabelsFileName, "rb"))

    # TODO: Check we have the same threads as in the thread messages dictionary.

    print "Loaded", len(data.threadsByLabel), "thread label mappings."
    print

    # Log into gmail.

    username = raw_input("Username [%s]: " % defaultUsername).strip()
    if not len(username):
        username = defaultUsername
    elif username == "no default":
        print "No username given = unable to login to gmail."
        sys.exit(1)

    password = getpass("Password: ")

    ga = libgmail.GmailAccount(username, password)

    print
    print "Please wait, attempting login...",
    try:
        ga.login()
        print "succeeded."
        print
    except libgmail.GmailLoginFailure:
        print "FAILED (Wrong username/password?)."
        sys.exit(1)

    UpdateCachedLabels(ga, data)

    print
    print "Pass 1: Checking the first page."
    print

    limitedSearchResult = FetchSearchResult(ga, allPages=False)
    completeSearchResult = None

    try:
        data.wantedThreadMessages = {}
        if not ProcessSearchResult(limitedSearchResult, data):
            print
            print "Pass 2: Falling back to checking all pages."
            print

            completeSearchResult = FetchSearchResult(ga, allPages=True)
            ProcessSearchResult(completeSearchResult, data)
        else:
            print " Skipping pass 2 as the last indexed thread was located."

        # Fix up mistake with thread label indexing.
        if False:
            print "Temporary pass: Indexing the threads by label."

            for thread in limitedSearchResult:
                for label in thread.getLabels():
                    if not data.threadsByLabel.has_key(label):
                        data.threadsByLabel[label] = {}
                    if data.threadsByLabel[label].has_key(thread.id):
                        print "HAD THREAD LABEL ENTRY"
                    else:
                        print "Did not have thread label entry"
                    data.threadsByLabel[label][thread.id] = None

            if completeSearchResult is None:
                completeSearchResult = FetchSearchResult(ga, allPages=True)

            for thread in completeSearchResult:
                for label in thread.getLabels():
                    if not data.threadsByLabel.has_key(label):
                        data.threadsByLabel[label] = {}
                    if not data.threadsByLabel[label].has_key(thread.id):
                        print "HAD THREAD LABEL ENTRY"
                    else:
                        print "Did not have thread label entry"
                    data.threadsByLabel[label][thread.id] = None

        print
        print "Pass 3: Processing collected data."
        print

        # First update the "original message" store.
        cnt = len(data.wantedMessages)
        for messageID in data.wantedMessages.iterkeys():
            print " %05d" % cnt,
            oldSize = -1
            if data.cachedMessages.has_key(messageID):
                oldSize = data.cachedMessages[messageID]

            print " Fetching message", messageID, "...",
            v = ga.getRawMessage(messageID)
            if ValidMessage(v):
                messagesByID[messageID] = v

                if oldSize != -1:
                    if len(v) != oldSize:
                        print "BAD MESSAGE.", messageID, (oldSize, len(v))
                    else:
                        print "WAS A DUPLICATE."
                else:
                    print "done."
            else:
                print "error."
                print v

                # Always exit when gmail fails us.  This tends to be
                # when your account is locked for "unusual usage".
                sys.exit(1)

            time.sleep(2.0)
            cnt -= 1

        if len(data.wantedMessages):
            print

        # Then record the thread messages changes.
        data.messageIDsByThreadID.update(data.wantedThreadMessages)

        print " Processed", len(data.wantedMessages), "messages that need to be fetched."
        print " Processed", len(data.wantedThreadMessages), "threads that need to be indexed."
        print
    finally:
        if backupSearchResults:
            if limitedSearchResult is not None:
                cPickle.dump(limitedSearchResult, open(tempSearchLimitedFileName, "wb"))

            if completeSearchResult is not None:
                cPickle.dump(completeSearchResult, open(tempSearchCompleteFileName, "wb"))

        if len(messagesByID):
            print "Saving", len(messagesByID), "added messages...",
            dumpFileName = GetNextMessageDumpFileName()
            cPickle.dump(messagesByID, open(dumpFileName, "wb"))
            print "done"

        print "Saving", len(data.messageIDsByThreadID), "thread message mappings...",
        cPickle.dump(data.messageIDsByThreadID, open(threadMessagesFileName, "wb"))
        print "done"

        print "Saving", len(data.threadsByLabel), "thread label mappings...",
        cPickle.dump(data.threadsByLabel, open(threadLabelsFileName, "wb"))
        print "done"

if backupSearchResults:
    # This should only be done in event of no error.

    print
    print "Clean up:"
    print

    confirm = raw_input(" Enter 'y' if you wish to purge the cached search results: ")
    if confirm.strip() == "y":
        PurgeCachedSearchResults()

