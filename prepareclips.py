#!/usr/bin/env python3

import sys
import argparse
import time
from pathlib import Path
import os
from os import path
import subprocess
import tempfile
from shutil import copyfile

def _parse_arguments():
    parser = argparse.ArgumentParser(description="Prepare raw timelapse video clips from captured image sequences.")
    parser.add_argument("source", type=str, action="store", help="source directory for image sequences")
    parser.add_argument("--destination", dest="destination", metavar='D', type=str, action="store", default="clips", help="destination directory for raw clips")
    parser.add_argument("-f", "--framerate", metavar='F', dest="framerate", action="store", default=20, type=int, help="the framerate to use for the video clips") # TODO: Determine best default
    parser.add_argument("-d", "--debug", action="store_true", dest="debug", help="print debugging information")
    parser.add_argument("-s", "--skippadclip", action="store_true", dest="skip_pad_clip", help="skip creation of a padding clip based  on the final frame")
    args = parser.parse_args()
    return args


def _verify_destination(destination, source):
    p = Path(destination)
    if not p.is_absolute():
        p = Path(source).joinpath(p)
    if not p.exists():
        p.mkdir()
    else:
        if p.is_file():
            raise NotADirectoryError()


def _verify_source(destination):
    p = Path(destination)
    if not p.exists():
        raise FileNotFoundError()
    else:
        if p.is_file():
            raise NotADirectoryError()


def _prepare_clips(args):
    source = Path(args.source)
    dest = Path(args.destination)
    if not dest.is_absolute():
        dest = source.joinpath(dest)

    last_sequence_directory = None
    for child in sorted(source.glob('*')):
        if child.is_dir():
            if not child.samefile(dest):
                last_sequence_directory = child
                _prepare_clip(child, dest, args.framerate)

    if last_sequence_directory and not args.skip_pad_clip:
        # Prepare a padding clip
        _prepare_padding_clip(last_sequence_directory, dest)


def _prepare_clip(seq_directory, dest, framerate):
    target = dest.joinpath("{0}.mp4".format(seq_directory.name))
    if target.exists():
        target.unlink()
    print("Preparing clip for {0} - destination {1}".format(seq_directory, target))
    # The capture_output argument did not work here... Output is just being printed, and stderr will probably be empty in the event of an error??
    status = subprocess.run(
        ["ffmpeg", "-framerate", "{0:d}".format(framerate), "-pattern_type", "glob", "-i", "{0}/*.png".format(seq_directory), "-c:v", "libx264", "-profile:v", "high", "-crf", "20", "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", target]
    )
    if status.returncode != 0:
        print (status.stderr)


def _prepare_padding_clip(seq_directory, dest):
    target = dest.joinpath("{0}_pad.mp4".format(seq_directory.name))
    if target.exists():
        target.unlink()
    # Get the last frame of the sequence
    last_frame = sorted(seq_directory.glob('*.png'))[-1]

    with tempfile.TemporaryDirectory() as temp_dir:
        for i in range(60):
            copyfile(str(last_frame), str(Path(temp_dir).joinpath("{0:02d}.png".format(i))))

        print("Preparing pad clip from {0} - destination: {1}".format(seq_directory, target))
        # The capture_output argument did not work here... Output is just being printed, and stderr will probably be empty in the event of an error??
        status = subprocess.run(
            [
                "ffmpeg",
                "-framerate",
                "1",
                "-pattern_type", "glob", "-i", "{0}/*.png".format(temp_dir),
                "-c:v",
                "libx264",
                "-profile:v",
                "high",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                "-vf",
                "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                target
            ]
        )
        if status.returncode != 0:
            print (status.stderr)


def _main():
    args = _parse_arguments()
    try:
        try:
            _verify_source(args.source)
        except FileNotFoundError:
            print ("The specified source does not exist.")
            sys.exit(1)
        except NotADirectoryError:
            print ("The specified source is not a directory.")
            sys.exit(1)

        try:
            _verify_destination(args.destination, args.source)
        except NotADirectoryError:
            print ("The specified destination is not a directory.")
            sys.exit(1)
        except FileNotFoundError:
            print ("The specified destination directory could not be created because of missing parents.")
            sys.exit(1)
        except PermissionError:
            print ("The destination directory could not be created due to inadequate permissions.")
            sys.exit(1)

        try:
            _prepare_clips(args)
        except IOError:
            print ("An IO error occurred while saving a screenshot to a file.")
            sys.exit(1)
        except PermissionError:
            print ("A screenshot could not be saved due to inadequate permissions")
            sys.exit(1)
    except KeyboardInterrupt:
        # TODO: Maybe track some statistics and print them on exit.
        print()
        sys.exit(0)


if __name__ == "__main__":
    _main()
