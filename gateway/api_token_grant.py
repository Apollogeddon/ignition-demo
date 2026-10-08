"""Grant a security level gateway read and write access in an 8.3 core config.

Run by api-token.sh with the image's Jython and Gson (there is no Python
standard library on that path, so Java APIs only):

    api_token_grant.py <core collection dir> <level>

Adds <level> to security-properties' readPermissions and writePermissions,
and to security-levels if the core collection has its own copy (it then
shadows the external one). Anything already there is kept: only a missing
grant is added, so changes made in the gateway survive. Exits 0 when it
changed a file, 3 when there was nothing to do, 2 when security-properties
does not exist yet (the gateway has not commissioned).
"""
import sys

from java.io import File
from java.lang import String
from java.nio.file import Files

from com.google.gson import GsonBuilder, JsonArray, JsonObject, JsonParser

PERMISSIONS = ("readPermissions", "writePermissions")


def read(path):
    return JsonParser.parseString(String(Files.readAllBytes(File(path).toPath()), "UTF-8"))


def write(path, element):
    text = GsonBuilder().setPrettyPrinting().create().toJson(element) + "\n"
    Files.write(File(path).toPath(), String(text).getBytes("UTF-8"))


def level(name):
    entry = JsonObject()
    entry.addProperty("name", name)
    entry.add("children", JsonArray())
    return entry


def names(levels):
    return [levels.get(i).getAsJsonObject().get("name").getAsString() for i in range(levels.size())]


def main(core, name):
    props = "%s/ignition/security-properties/config.json" % core
    if not File(props).isFile():
        return 2
    changed = False
    config = read(props).getAsJsonObject()
    for key in PERMISSIONS:
        permission = config.getAsJsonObject(key)
        levels = permission.getAsJsonArray("securityLevels")
        if name not in names(levels):
            levels.add(level(name))
            changed = True
    if changed:
        write(props, config)
    defined = "%s/ignition/security-levels/config.json" % core
    if File(defined).isFile():
        tree = read(defined).getAsJsonObject()
        levels = tree.getAsJsonArray("securityLevels")
        if name not in names(levels):
            levels.add(level(name))
            write(defined, tree)
            changed = True
    return 0 if changed else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
