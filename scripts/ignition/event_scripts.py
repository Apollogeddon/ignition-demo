"""Build a project's Ignition 8.1 gateway events (event-scripts/data.bin) from
its 8.3 event script files, so both versions run the same scripts.

Runs under Jython inside an Ignition 8.1 image, using Ignition's own
serializer (see scripts/generate-event-scripts.sh):

    event_scripts.py <project src dir>

Reads  ignition/startup/onStartup.py, ignition/update/onUpdate.py,
       ignition/shutdown/onShutdown.py, the timer events,
       ignition/timer/<name>/handleTimerEvent.py, and the gateway message
       handlers, ignition/message/<name>/handleMessage.py (whichever exist;
       8.3's format: the script body inside its "def ...(...):" line, as 8.1
       stores an event or a timer, with a timer's resource.json delay,
       fixedDelay, sharedThread and enabled; for a message handler the whole
       "def handleMessage(payload):" function, as 8.1 also stores it, and its
       resource.json's enabled and threadType)
Writes ignition/event-scripts/data.bin and resource.json (8.1's format)
"""
import sys

# the image's Jython has no standard library on its path: Java APIs only
from java.io import ByteArrayInputStream, ByteArrayOutputStream, File
from java.lang import String
from java.nio import ByteBuffer
from java.nio.file import Files
from java.util import LinkedHashMap
from java.util.regex import Pattern
from java.util.zip import GZIPInputStream, GZIPOutputStream

from com.inductiveautomation.ignition.common.script import ScriptConfig, TimerKey
from com.inductiveautomation.ignition.common.script.message import MessageHandlerKey
from com.inductiveautomation.ignition.common.xmlserialization.serialization import XMLSerializer

EVENTS = (
    ("startup", "onStartup.py", "setStartupScript"),
    ("update", "onUpdate.py", "setUpdateScript"),
    ("shutdown", "onShutdown.py", "setShutdownScript"),
)

# canonical form (scripts/sanitise.py): sorted keys, two-space indent
RESOURCE = """{
  "attributes": {
    "lastModification": {
      "actor": "system",
      "timestamp": "2025-01-01T00:00:00Z"
    },
    "lastModificationSignature": "0000000000000000000000000000000000000000000000000000000000000000"
  },
  "files": [
    "data.bin"
  ],
  "overridable": true,
  "restricted": false,
  "scope": "G",
  "version": 1
}
"""


def body(path):
    """Return the script inside the file's def line, one indent level out."""
    lines = open(path).read().replace("\r\n", "\n").split("\n")
    if not lines or not lines[0].startswith("def "):
        raise ValueError("%s: expected the 8.3 'def on...(...):' line first" % path)
    out = []
    for line in lines[1:]:
        if line.startswith("\t"):
            line = line[1:]
        elif line.startswith("    "):
            line = line[4:]
        out.append(line)
    return "\n".join(out).rstrip("\n") + "\n"


# a message handler's attributes in its 8.3 resource.json (the image's
# Jython has no json module): "enabled": <bool> and "threadType": "<type>"
ENABLED = Pattern.compile('"enabled"\\s*:\\s*(true|false)')
THREAD_TYPE = Pattern.compile('"threadType"\\s*:\\s*"([A-Za-z]+)"')
# a timer's: "delay": <ms>, "fixedDelay": <bool> and "sharedThread": <bool>
DELAY = Pattern.compile('"delay"\\s*:\\s*([0-9]+)')
FIXED_DELAY = Pattern.compile('"fixedDelay"\\s*:\\s*(true|false)')
SHARED_THREAD = Pattern.compile('"sharedThread"\\s*:\\s*(true|false)')


def attribute(pattern, text, default):
    match = pattern.matcher(text)
    return match.group(1) if match.find() else default


def message_handlers(src):
    """Return 8.1's message handler map (key -> script) and the names found."""
    handlers = LinkedHashMap()
    names = []
    folder = File("%s/ignition/message" % src)
    for entry in sorted(folder.listFiles() or [], key=lambda f: f.getName()):
        script = File(entry, "handleMessage.py")
        if not script.isFile():
            continue
        resource = File(entry, "resource.json")
        text = open(resource.getPath()).read() if resource.isFile() else ""
        key = MessageHandlerKey()
        key.setName(entry.getName())
        key.setEnabled(attribute(ENABLED, text, "true") == "true")
        key.setThreadType(attribute(THREAD_TYPE, text, MessageHandlerKey.THREAD_SHARED))
        # unlike the events, 8.1 keeps a handler's whole function: it compiles
        # the script and then calls the handleMessage it defines
        handlers.put(key, open(script.getPath()).read().replace("\r\n", "\n"))
        names.append(entry.getName())
    return handlers, names


def timer_scripts(src):
    """Return 8.1's timer script map (key -> script body) and the names found."""
    timers = LinkedHashMap()
    names = []
    folder = File("%s/ignition/timer" % src)
    for entry in sorted(folder.listFiles() or [], key=lambda f: f.getName()):
        script = File(entry, "handleTimerEvent.py")
        if not script.isFile():
            continue
        resource = File(entry, "resource.json")
        text = open(resource.getPath()).read() if resource.isFile() else ""
        key = TimerKey()
        key.setName(entry.getName())
        key.setEnabled(attribute(ENABLED, text, "true") == "true")
        key.setDelay(int(attribute(DELAY, text, "10000")))
        key.setFixedDelay(attribute(FIXED_DELAY, text, "true") == "true")
        key.setSharedThread(attribute(SHARED_THREAD, text, "true") == "true")
        timers.put(key, body(script.getPath()))
        names.append(entry.getName())
    return timers, names


# the binary format stores its write time (epoch ms) at this offset of the
# uncompressed payload; pinned so the same scripts always give the same file
WRITE_TIME_OFFSET = 20
WRITE_TIME_MS = 1735689600000  # 2025-01-01T00:00:00Z


def pin_write_time(gzipped):
    """Return the gzipped payload with its write time set to WRITE_TIME_MS."""
    raw = ByteArrayOutputStream()
    stream = GZIPInputStream(ByteArrayInputStream(gzipped))
    buf = ByteBuffer.allocate(8192).array()
    n = stream.read(buf)
    while n > 0:
        raw.write(buf, 0, n)
        n = stream.read(buf)
    data = ByteBuffer.wrap(raw.toByteArray())
    data.putLong(WRITE_TIME_OFFSET, WRITE_TIME_MS)
    out = ByteArrayOutputStream()
    gz = GZIPOutputStream(out)
    gz.write(data.array())
    gz.close()
    return out.toByteArray()


def main(src):
    config = ScriptConfig()
    found = []
    for folder, name, setter in EVENTS:
        path = "%s/ignition/%s/%s" % (src, folder, name)
        if File(path).isFile():
            getattr(config, setter)(body(path))
            found.append(folder)
    timers, names = timer_scripts(src)
    if names:
        config.setTimerScripts(timers)
        found.append("timers (%s)" % ", ".join(names))
    handlers, names = message_handlers(src)
    if names:
        config.setMessageHandlerScripts(handlers)
        found.append("message handlers (%s)" % ", ".join(names))
    if not found:
        raise SystemExit("no event scripts under %s/ignition" % src)
    serializer = XMLSerializer()
    serializer.initDefaults()
    # a fixed timestamp keeps the output reproducible (and diffs meaningful)
    serializer.addRootAttribute("timestamp", "Wed Jan 01 00:00:00 UTC 2025")
    data = pin_write_time(serializer.serializeBinary(config, True))
    out = File("%s/ignition/event-scripts" % src)
    out.mkdirs()
    Files.write(File(out, "data.bin").toPath(), data)
    Files.write(File(out, "resource.json").toPath(), String(RESOURCE).getBytes("UTF-8"))
    print("event-scripts/data.bin: %s" % ", ".join(found))


if __name__ == "__main__":
    main(sys.argv[1])
