#!/usr/bin/env python3
#-*- coding: UTF-8 -*-

"""A simple masivefilenames editor that take advantage of the power of VIM"""

import argparse
import os
import re
import sys
import tempfile
import time

from subprocess import Popen, PIPE, check_output
from shutil import which

START_TIME = time.time()
VIMPATH = which("vim")

VERBOSE = 2

ORDER_OPTIONS = {
        "s": (" -S", "Size"),
        "S": (" -rS", "Reversed size"),
        "t": (" -t", "Created"),
        "T": (" -rt", "Reversed created"),
        "x": (" -X", "Extension"),
        "X": (" -rX", "Reversed extension"),
        "u": (" -u1", "Access time"),
        "U": (" -ru1", "Reversed access time"),
}


def parse_options():
    parser = argparse.ArgumentParser(
        description="""vimrenamer allows to edit tons of files a dirs names in """
            """the best text editor ever. If you master vim you can master """
            """file system xD .""")
    parser.add_argument("-v", '--verbose', action="append_const", dest="verbose",
        const=1, default=[2], help='Increase the verbosity of the output.')
    parser.add_argument("-q", '--quiet', action="append_const", dest="verbose",
        const=-1, help='Decrease the verbosity of the output.')
    parser.add_argument("-r", '--recursive', default=False, action="store_true",
        help="Go through all dirs present in the root dir.")
    parser.add_argument("-l", '--loop', default=False, action="store_true",
        help="Repeat until no changes are made.")
    parser.add_argument("-s", '--safe', default=False, action="store_true",
        help="Avoid moving a file over a existing one.")
    parser.add_argument("-o", "--order", dest="order", help="""Especify sorting
                        option, any of: %s""" % ", ".join( "'%s' %s" % (opt, value[1])
                            for opt, value in ORDER_OPTIONS.items()),
                        metavar="order", choices=ORDER_OPTIONS, default=None)

    options = vars(parser.parse_args())
    return options


def vprint(message, verbose=2):
    if VERBOSE >= verbose:
        try:
            print(message)
        except UnicodeEncodeError:
            print(message.encode("utf8"))

error = lambda m: vprint("E: %s" % m, 0)
warning = lambda m: vprint("W: %s" % m, 1)
info = lambda m: vprint(m, 2)
moreinfo = lambda m: vprint("+I: %s" % m, 3)
debug = lambda m: vprint("D: %s" % m, 4)


def debug(*args):
    """
    Write to stderr for debug
    """

    sys.stderr.writelines("".join(
        ["%7.2f" % (time.time() - START_TIME),
        " ",
        " ".join([str(e) for e in args]) + "\n",
        ]))


def dump(filename, lines):
    """
    Writes lines to the file (filename can be a fd int).
    """
    if type(filename) is int:
        fobj = os.fdopen(filename, "w")
    else:
        fobj = open(filename, "w")

    fobj.writelines([str(s) + "\n" for s in lines])
    fobj.close()


def load(filename):
    """
    Load a file and return their striped content.
    """
    return [s.rstrip("\n") for s in open(filename).readlines()]


def list2file(lines):
    tmp_fd, tmp_name = tempfile.mkstemp(".vimrenamer")
    dump(tmp_fd, lines)
    return tmp_name


def move(src, dst, safe=False):
    """
    If *dst* is "" or None:
        If *src* is a dir:
            Deletes dir *src* and all it's empty parents.
        Else:
            Deletes file *src*.

    Else:
        If *dst* has path.sep:
            Create *dst* dir and it's parents.

        If *dst* is dir:
            join *dst* filename(*source*)

        If *safe* and *dst* it's a file:
            Split *dst* into (basename, extension)
            If basename(*dst*) ends with "(number)":
                Increase number in *basename*
            Else:
                Append "(2)" to *basename*
            Recurse move(*src*, *basename*.*extension*)
        Else:
            Convert *dst* to *absdst*
            Exec command "mv *src* *dst*".
    """

    if dst in ("", None):
        if src.endswith("/"):
            debug("Removing directory: %s" % src)
            os.removedirs(src)
        else:
            debug("Removing file: %s" % src)
            os.remove(src)
        error = 0

    else:
        if os.path.sep in dst:
            dst_dir = os.path.dirname(dst)
            if not os.path.exists(dst_dir):
                debug("Creating dest dir %s" % dst_dir)
                os.makedirs(dst_dir)

        if os.path.isdir(dst):
            src_basename = os.path.basename(src)
            dst = os.path.join(dst, src_basename)

        if safe and os.path.isfile(dst):
            basename, extension = os.path.splitext(dst)
            match = re.match(r"(?P<basename>.+?) \((?P<number>\d+)\)", basename)
            if match:
                basename = match.group("basename")
                number = int(match.group("number"))
                dst = "%s (%d)%s" % (basename, number + 1, extension)
            else:
                dst = "%s (2)%s" % (basename, extension)
            return move(src, dst, safe)
        else:
            debug("Moving %s to %s" % (src, dst))
            error = mv(src, dst)

    return error


def mv(src, dst):
    """
    The best "move" implementation ever, just a unix mv wrapper.
    Maybe shutil.move will be a cross plataform option on its next version.
    """
    process = Popen(["", "--", src, dst], 0, "/bin/mv", stderr=PIPE,
        stdout=PIPE, env={"LANG":"C", "LC_ALL":"C"})

    error = process.wait()

    if error == 1:
        stderr = "\n".join(process.stderr.readlines())
        errors = {
            2: r""": cannot create regular file `.*': Permission denied$""",
            3: r""": cannot move .*: No such file or directory$""",
            4: r""": cannot move .*: Permission denied$""",
            5: r""": cannot stat `.*': No such file or directory\n""",
            }

        while error == 1 and len(errors) > 0:
            e, r = errors.popitem()

            if re.match(r, stderr):
                error = "    " + stderr

    return error


def parse_cmd(cmd, filename):
    """
    Returns `cmd` replacing "{}" with the escaped filename.
    If "{}" is not present appends `filename` to the end.
    """
    filename = '"%s"' % filename #FIXME: escape
    if "{}" in cmd:
        return cmd.replace("{}", filename)
    else:
        return cmd + " " + filename


def execute(cmd):
    """
    Executes `cmd`. Waits for the command to finish.
    """
    cmd = cmd[1:]
    debug("Executing '%s'" % cmd)
    process = Popen(cmd, shell=True)
    error = process.wait()


def listeditor(llines, rlines=None):
    """
    Simple wrapper to the vim editor. If rlines use vimdiff but return only
    llines.
    """

    lname = list2file(llines)

    if rlines:
        rname = list2file(rlines)
        assert Popen(["", "-d", lname, rname], 0, VIMPATH).wait() == 0
        os.remove(rname)
    else:
        assert Popen(["", lname], 0, VIMPATH).wait() == 0

    llines = load(lname)
    os.remove(lname)
    return llines 


def listdir(path="./", recursive=False, order=None):
    """
    Return a ordened list of dirs and files of the path.
    """

    if order:
        order_option, order_name = ORDER_OPTIONS[order]
    else:
        order_option, order_name = "", "Default order"

    if recursive:
        command = """ls -R1Q %s| awk -F '"' '/:$/{dir=$2} /"$/{print dir "/" $2}'"""
    else:
        command = "/bin/ls %s"

    command = command % order_option
    debug("Order:", order_name)
    debug("Command:", command)

    listdir = check_output(command, shell=True)
    listdir = listdir.splitlines()

    files = []
    dirs = []
    for name in listdir:
        name = name.decode()
        if recursive:
            toadd = name[2:]
        else:
            toadd = name
        toremove = os.path.join(*os.path.split(toadd)[:-1])

        if os.path.isdir(name) and not os.path.islink(name):
            dirs.append(toadd + "/")
            try:
                dirs.remove(toremove + "/")
            except:
                pass
        elif os.path.isfile(name):
            files.append(toadd)
            try:
                dirs.remove(toremove + "/")
            except:
                pass
            try:
                files.remove(toremove)
            except:
                pass
        elif os.path.islink(name):
            files.append(toadd)
            try:
                dirs.remove(toremove + "/")
            except:
                pass
            try:
                files.remove(toremove)
            except:
                pass
        else:
            debug("Filetype not supported %s" % name)

    if order:
        return dirs + files
    else:
        return sorted(dirs) + sorted(files)



def main():
    """
    The main function.
    """

    global VERBOSE
    options = parse_options()
    VERBOSE = sum(options["verbose"])

    recursive = options['recursive']
    loop = options['loop']
    safe = options['safe']
    order = options['order']

    keep = True
    while keep:
        startlist = listdir(recursive=recursive, order=order)
        finallist = listeditor(startlist)

        while len(startlist) != len(finallist):
            print("""No se debe modificar la cantidad de lineas, se """
                """abrirá un vimdiff con la lista original a la derecha """
                """para referencia.""")
            time.sleep(1)
            finallist = listeditor(finallist, startlist)

        changes = [(sline, fline)
                   for (sline, fline) in zip(startlist, finallist)
                   if sline != fline]

        if changes:
            for pos, change in enumerate(changes):
                src, dst = change
                if dst.startswith("!"):
                    dst = parse_cmd(dst, src)
                    change = (src, dst)
                    changes[pos] = change
            changes = listeditor(changes)

            for line in changes:
                src, dst = eval(line)
                if dst.startswith("!"):
                    error = execute(dst)
                else:
                    error = move(src, dst, safe)
                if error:
                    print(error)
        else:
            changes = False
            debug("No hay cambios que aplicar.")

        keep = changes and loop



if __name__ == "__main__":
    exit(main())
