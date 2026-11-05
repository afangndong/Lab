#!/usr/bin/env python3
"""Schreibt eine Notiz oder setzt den Status eines Tickets."""
import argparse
import sys

from tickets import client_from_env


def main(argv=None, client=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    note = sub.add_parser("note")
    note.add_argument("number")
    note.add_argument("text")
    state = sub.add_parser("state")
    state.add_argument("number")
    state.add_argument("state")
    args = parser.parse_args(argv)

    client = client or client_from_env()
    if args.command == "note":
        client.add_note(args.number, args.text)  # client.add_note(...) mit number und text
    else:
        client.set_state(args.number, args.state)  # client.set_state(...) mit number und state
    return 0


if __name__ == "__main__":
    sys.exit(main())