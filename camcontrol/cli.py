from __future__ import annotations

import argparse
import os
import re
import sys
from typing import List, Optional

from .discovery import find_devices, pick_default_device
from .exceptions import CamcontrolError, ConnectionError, DiscoveryError, ProtocolError
from .interactive import run_interactive
from .serial_manager import SerialConfig, SerialManager


def _print_devices(devices) -> None:
    if not devices:
        print("No serial ports found.")
        return

    print("PORT   CH340  VID:PID   DESCRIPTION")
    for d in devices:
        vp = d.vid_pid or "-"
        ch = "yes" if d.is_ch340_like else "no"
        desc = d.description or d.product or "-"
        print(f"{d.device:<6} {ch:<5} {vp:<8} {desc}")


def _resolve_com_port(explicit: Optional[str]) -> str:
    if explicit:
        return explicit

    devices = find_devices()
    if not devices:
        raise DiscoveryError("No serial ports found.")

    chosen = pick_default_device(devices)
    if chosen is None:
        print("Multiple candidate devices found; specify one with --com.")
        _print_devices(devices)
        raise DiscoveryError("No default device could be selected.")

    return chosen.device


def _build_manager(args) -> SerialManager:
    port = _resolve_com_port(args.com)
    cfg = SerialConfig(
        port=port,
        read_timeout_s=args.read_timeout,
        write_timeout_s=args.write_timeout,
    )
    return SerialManager(cfg)


def cmd_list(_args) -> int:
    devices = find_devices()
    _print_devices(devices)
    return 0


def cmd_help(args) -> int:
    parser = build_parser(_program_name())
    if not args.topic:
        parser.print_help()
        return 0

    topic = args.topic[0]
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            sub = action.choices.get(topic)
            if sub is None:
                print(f"Unknown help topic: {topic}", file=sys.stderr)
                return 2
            print(sub.format_help())
            return 0

    parser.print_help()
    return 0


def cmd_connect(args) -> int:
    manager = _build_manager(args)
    with manager:
        print(f"Connected to {manager.port} @ {manager.baudrate} baud.")
    return 0


def _normalize_command(command: str, *, raw: bool) -> str:
    cmd = command.strip()
    if not raw:
        cmd = cmd.upper()
    return cmd


def cmd_send(args) -> int:
    manager = _build_manager(args)
    command = _normalize_command(" ".join(args.command), raw=args.raw)
    with manager:
        lines = manager.send_and_read_response(
            command,
            acs_port=args.port,
            total_timeout_s=args.total_timeout,
            idle_timeout_s=args.idle_timeout,
            clear_input=True,
        )

    if not lines:
        print("(no response)")
        return 0

    for line in lines:
        print(line)
    return 0


def cmd_temp(args) -> int:
    args.command = ["TEMP"]
    return cmd_send(args)


def cmd_interactive(args) -> int:
    manager = _build_manager(args)
    with manager:
        return run_interactive(manager, acs_port=args.port)


def _program_name() -> str:
    base = os.path.basename(sys.argv[0] or "camcontrol")
    name, _ext = os.path.splitext(base)
    return name or "camcontrol"


def build_parser(prog: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=prog,
        description="Camcontrol USB-serial CLI (fixed 115200 baud).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            f"  {prog} list\n"
            f"  {prog} --com COM15 connect\n"
            f"  {prog} --com COM15 send STATE\n"
            f"  {prog} --com COM15 send HOLD ON\n"
            f"  {prog} --com COM15 temp\n"
            f"  {prog} --com COM15 interactive\n"
            "\n"
            "Shortcuts:\n"
            f"  {prog} COM15 TEMP        (same as: --com COM15 send TEMP)\n"
            f"  {prog} COM15 HOLD ON     (same as: --com COM15 send HOLD ON)\n"
            "\n"
            "Notes:\n"
            "  - Commands are sent as complete lines terminated with \\n.\n"
            "  - Interactive mode sends only after ENTER (never per-character).\n"
        ),
    )
    p.add_argument(
        "--com",
        help="Serial port (e.g. COM3). If omitted, auto-selects a likely CH340 port.",
    )
    p.add_argument(
        "--read-timeout",
        type=float,
        default=0.2,
        help="Per-read timeout in seconds (default: 0.2).",
    )
    p.add_argument(
        "--write-timeout",
        type=float,
        default=1.0,
        help="Write timeout in seconds (default: 1.0).",
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("help", help="Show help for a command.")
    sp.add_argument("topic", nargs="*", help="Command to show help for (e.g. send).")
    sp.set_defaults(func=cmd_help)

    sp = sub.add_parser("list", help="List available serial ports.")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("connect", help="Open and close a serial connection (smoke test).")
    sp.set_defaults(func=cmd_connect)

    sp = sub.add_parser("send", help="Send a command and print the response.")
    sp.add_argument(
        "command",
        nargs="+",
        help="Command to send (e.g. STATE, UNLOCK, TEMP, HOLD ON).",
    )
    sp.add_argument(
        "--raw",
        action="store_true",
        help="Send exactly as provided (do not auto-uppercase).",
    )
    sp.add_argument(
        "--port",
        type=int,
        help="Reserved for multi-channel devices (e.g. ACS200).",
    )
    sp.add_argument(
        "--total-timeout",
        type=float,
        default=2.0,
        help="Max time to wait for the full response (default: 2.0).",
    )
    sp.add_argument(
        "--idle-timeout",
        type=float,
        default=0.35,
        help="Stop after this much response silence (default: 0.35).",
    )
    sp.set_defaults(func=cmd_send)

    sp = sub.add_parser("temp", help="Shortcut for: send TEMP.")
    sp.add_argument(
        "--raw",
        action="store_true",
        help="Send exactly as provided (do not auto-uppercase).",
    )
    sp.add_argument(
        "--port",
        type=int,
        help="Reserved for multi-channel devices (e.g. ACS200).",
    )
    sp.add_argument(
        "--total-timeout",
        type=float,
        default=2.0,
        help="Max time to wait for the full response (default: 2.0).",
    )
    sp.add_argument(
        "--idle-timeout",
        type=float,
        default=0.35,
        help="Stop after this much response silence (default: 0.35).",
    )
    sp.set_defaults(func=cmd_temp)

    sp = sub.add_parser("interactive", help="Interactive mode (line-based; sends only after ENTER).")
    sp.add_argument(
        "--port",
        type=int,
        help="Reserved for multi-channel devices (e.g. ACS200).",
    )
    sp.set_defaults(func=cmd_interactive)

    return p


_SUBCOMMANDS = {"help", "list", "connect", "send", "temp", "interactive"}


def _preprocess_argv(argv: List[str]) -> List[str]:
    if not argv:
        return argv

    out = list(argv)

    # Allow: camcontrol COM15 <...>
    if re.fullmatch(r"COM\d+", out[0], flags=re.IGNORECASE):
        out = ["--com", out[0], *out[1:]]

    # Allow: camcontrol [--com COM15] TEMP|STATE|HOLD ON  (default to send)
    # Find first positional token after known options and their values.
    options_with_values = {"--com", "--read-timeout", "--write-timeout"}
    i = 0
    insert_at: Optional[int] = None
    while i < len(out):
        t = out[i]
        if t in options_with_values:
            i += 2
            continue
        if t.startswith("-"):
            i += 1
            continue
        insert_at = i
        break

    if insert_at is not None:
        token = out[insert_at]
        is_subcommand = token.lower() in _SUBCOMMANDS and token == token.lower()
        if not is_subcommand:
            out = out[:insert_at] + ["send"] + out[insert_at:]

    # Allow: camcontrol help  (common muscle-memory)
    if out and out[0].lower() == "help":
        out = ["help", *out[1:]]

    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser(_program_name())
    args = parser.parse_args(
        _preprocess_argv(list(argv)) if argv is not None else _preprocess_argv(sys.argv[1:])
    )
    try:
        return int(args.func(args))
    except (DiscoveryError, ConnectionError, ProtocolError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except CamcontrolError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
