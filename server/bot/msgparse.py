"""
msgparse.py - Parse bot messages

February 2020, Lewis Gaul
"""

__all__ = ("parse_msg",)

import argparse
import logging
import sys
from typing import Any, Callable, Iterable, List, Optional, Tuple, Union

from minegauler.shared import highscores as hs

from . import formatter
from .utils import USER_NAMES


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Message parsing
# ------------------------------------------------------------------------------


class InvalidArgsError(Exception):
    pass


class PositionalArg:
    def __init__(
        self,
        name: str,
        *,
        parse_name: bool = False,
        nargs: Union[int, str] = 1,
        default: Any = None,
        choices: Optional[Iterable[Any]] = None,
        type: Optional[Callable] = None,
        validate: Optional[Callable] = None,
    ):
        if (isinstance(nargs, int) and nargs < 1) and nargs not in ["?", "*", "+"]:
            raise ValueError(f"Bad nargs value {nargs!r}")
        self.name = name
        self.parse_name = parse_name
        self.nargs = nargs
        if default is None and nargs not in [1, "?"]:
            self.default = []
        else:
            self.default = default
        self._choices = choices
        self._type = type
        self._validate = validate

    def convert(self, value):
        if self._type is not None:
            return self._type(value)
        return value

    def validate(self, value):
        if self._choices is not None and value not in self._choices:
            return False
        if self._validate:
            return self._validate(value)
        return True


class ArgParser(argparse.ArgumentParser):
    """
    A specialised arg parser.

    The list of args to be parsed can contain the following, with no overlap:
     - Ordered positional args at the start
     - Regular argparse args with no order

    Positional args are added with 'add_positional_arg()'. The order of calls to
    this method determines the order the args must appear in. The following
    options are accepted:
     - parse_name: Whether the arg name should be parsed.
     - nargs: The number of args to accept. Accepted values are positive
        integers, "?" for 0 or 1, "*" for 0 or more, "+" for 1 or more.
     - choices: As for 'add_argument()'.
     - type: As for 'add_argument()'.

    Positional args are greedily consumed, but if an arg does not satisfy
    choices or if the 'type' callable raises an exception then no more values
    will be accepted for that arg.

    Examples:
     - If a positional arg has no type/choices restrictions and unbounded
        'nargs' (i.e. set to "*" or "+") then all positional options will be
        consumed by this arg.
     - If a positional arg has unbounded 'nargs' but has a 'type' that raises an
        exception for invalid args, subsequent args will take over the matching.
        Note that if insufficient options are matched (e.g. nargs="+" and no
        options are matched) then parsing ends with a standard error.

    Positional argument parsing ends as soon as an option starting with a dash
    is encountered, or when the positional args are exhausted. The remaining
    options are passed to a standard argparse parser to match args added with
    'add_argument()'.
    """

    def __init__(self):
        super().__init__(add_help=False)
        self._name_parse_args = []
        self._positional_args = []

    def parse_known_args(self, args: Iterable[str], namespace=None):
        """
        Override the default behaviour.
        """
        if namespace is None:
            namespace = argparse.Namespace()

        # Start with positional args.
        args = self._parse_positional_args(args, namespace)

        # Replace optional args so that they don't require the dashes.
        for i, arg in enumerate(args):
            if arg in self._name_parse_args:
                args[i] = f"--{arg}"

        # Regular parsing of remaining args
        return super().parse_known_args(args, namespace)

    def add_argument(self, name, *args, **kwargs):
        """
        Override the default behaviour.
        """
        if not name.startswith("--"):
            self._name_parse_args.append(name)
            name = "--" + name.lstrip("-")
        super().add_argument(name, *args, **kwargs)

    def error(self, message):
        raise InvalidArgsError(message)

    def add_positional_arg(self, name: str, **kwargs) -> None:
        """
        Add a positional argument for parsing.

        :param name:
            The name of the argument - must be unique.
        :param kwargs:
            Arguments to pass to the 'PositionalArg' class.
        """
        self._positional_args.append(PositionalArg(name, **kwargs))

    def _parse_positional_args(self, kws: Iterable[str], namespace) -> Iterable[str]:
        """
        Parse the positional args.

        :param kws:
            The provided keywords.
        :param namespace:
            The namespace to set argument values in.
        :return:
            The remaining unmatched keywords.
        """
        for arg in self._positional_args:
            result, kws = self._parse_single_positional_arg(arg, kws)
            setattr(namespace, arg.name, result)
        return kws

    def _parse_single_positional_arg(
        self, arg: PositionalArg, kws: Iterable[str]
    ) -> Tuple[Any, Iterable[str]]:
        """
        Parse a single positional arg. Raise InvalidArgsError if not enough
        matching args are found.
        """
        required = arg.nargs not in ["?", "*"]
        if isinstance(arg.nargs, int):
            max_matches = arg.nargs
            exp_args_string = str(arg.nargs)
        elif arg.nargs == "?":
            max_matches = 1
            exp_args_string = "optionally one"
        elif arg.nargs == "*":
            max_matches = None
            exp_args_string = "any number of"
        elif arg.nargs == "+":
            max_matches = None
            exp_args_string = "at least one"
        else:
            assert False

        # First parse the arg name if required.
        if kws and arg.parse_name:
            if kws[0] == arg.name:  # Found arg
                kws.pop(0)
            elif not required:  # No match
                return arg.default, kws
            else:
                raise InvalidArgsError(f"Expected to find {arg.name!r}")

        # Now parse argument values.
        matches = []
        while kws and (max_matches is None or len(matches) < max_matches):
            try:
                kw_value = arg.convert(kws[0])
                assert arg.validate(kw_value)
            except Exception as e:
                logger.debug(e)
                if arg.parse_name and not matches:
                    # We parsed the name of the arg, so we expected to find
                    # at least one value...
                    raise InvalidArgsError(
                        f"Got name of positional arg {arg.name!r} but no values"
                    )
                else:
                    break
            else:
                matches.append(kw_value)
                kws.pop(0)

        if required and not matches:
            raise InvalidArgsError(f"Expected {exp_args_string} {arg.name!r} arg")
        elif isinstance(arg.nargs, int) and len(matches) != arg.nargs:
            assert len(matches) < arg.nargs
            raise InvalidArgsError(f"Expected {exp_args_string} {arg.name!r} arg")

        arg_value = arg.default
        if matches:
            if arg.nargs in [1, "?"]:
                assert len(matches) == 1
                arg_value = matches[0]
            else:
                arg_value = matches

        return arg_value, kws


class BotMsgParser(ArgParser):
    def add_username_arg(self, *, nargs: Union[int, str] = 1):
        self.add_positional_arg("username", nargs=nargs, choices=USER_NAMES.keys())

    def add_difficulty_arg(self):
        self.add_positional_arg(
            "difficulty", nargs="?", type=self._convert_difficulty_arg
        )

    def add_rank_type_arg(self):
        def convert(arg):
            try:
                return self._convert_difficulty_arg(arg)
            except InvalidArgsError:
                raise  # TODO
                # if arg == "combined":
                #     return "combined"
                # elif arg == "official":
                #     return "official"
                # else:
                #     raise InvalidArgsError(f"Invalid rank type {arg!r}")

        self.add_positional_arg(
            "rank_type", nargs="?", type=convert, default="beginner"
        )

    def add_per_cell_arg(self):
        self.add_argument("per-cell", type=int, choices=[1, 2, 3])

    def add_drag_select_arg(self):
        def _arg_type(arg):
            if arg == "on":
                return True
            elif arg == "off":
                return False
            else:
                raise InvalidArgsError("Drag select should be one of {'on', 'off'}")

        self.add_argument("drag-select", type=_arg_type)

    @staticmethod
    def _convert_difficulty_arg(arg):
        if arg in ["b", "beginner"]:
            return "beginner"
        elif arg in ["i", "intermediate"]:
            return "intermediate"
        elif arg in ["e", "expert"]:
            return "expert"
        elif arg in ["m", "master"]:
            return "master"
        else:
            raise InvalidArgsError(f"Invalid difficulty {arg!r}")


# ------------------------------------------------------------------------------
# Message handling
# ------------------------------------------------------------------------------


GENERAL_HELP = "General help :)"

GENERAL_INFO = "General info!"


def helpstring(text):
    def decorator(func):
        func.__helpstring__ = text
        return func

    return decorator


def schema(text):
    def decorator(func):
        func.__schema__ = text
        return func

    return decorator


@helpstring("Get help for a command")
@schema("help [<command>]")
def help_(
    args_or_func: Union[List[str], Callable, None],
    *,
    only_schema: bool = False,
    allow_markdown: bool = False,
) -> str:
    if hasattr(args_or_func, "__schema__") or args_or_func is None:
        func = args_or_func
    else:
        func = _map_to_cmd(" ".join(args_or_func))[0]

    if func is None:
        return GENERAL_HELP

    lines = []
    if not only_schema:
        try:
            lines.append(func.__helpstring__)
        except AttributeError:
            logger.warning(
                "No helpstring found on message handling function %r", func.__name__
            )
    try:
        schema = func.__schema__
    except AttributeError:
        logger.warning("No schema found on message handling function %r", func.__name__)
    else:
        if allow_markdown:
            lines.append(f"\n`{schema}`")
        else:
            lines.append(schema)

    if not lines:
        return "Unexpect error: unable to get help message\n\n" + GENERAL_HELP

    return "\n".join(lines)


@helpstring("Get information about the game")
@schema("info")
def info(args, *, allow_markdown: bool = False):
    # Check no args given.
    BotMsgParser().parse_args(args)
    return GENERAL_INFO


@helpstring("Get player info")
@schema(
    "player <name> [b[eginner] | i[ntermediate] | e[xpert] | m[aster]] "
    "[drag-select {on | off}] [per-cell {1 | 2 | 3}]"
)
def player(args, *, allow_markdown: bool = False):

    parser = BotMsgParser()
    parser.add_difficulty_arg()
    parser.add_per_cell_arg()
    parser.add_drag_select_arg()
    args = parser.parse_args(args)
    return str(args)


@helpstring("Get rankings")
@schema(
    "ranks [b[eginner] | i[ntermediate] | e[xpert] | m[aster]] "
    "[drag-select {on | off}] [per-cell {1 | 2 | 3}]"
)
def ranks(args, *, allow_markdown: bool = False) -> str:
    parser = BotMsgParser()
    parser.add_rank_type_arg()
    parser.add_per_cell_arg()
    parser.add_drag_select_arg()
    args = parser.parse_args(args)

    kwargs = {
        k: getattr(args, k)
        for k in ["per_cell", "drag_select"]
        if getattr(args, k) is not None
    }
    if args.rank_type[0] in ["b", "i", "e", "m"]:
        kwargs["difficulty"] = args.rank_type[0]
        highscores = hs.filter_and_sort(
            hs.get_highscores(hs.HighscoresDatabases.REMOTE, **kwargs)
        )
        highscores = [h for h in highscores if h.name in USER_NAMES.values()]
    else:
        assert False
        # assert args.rank_type == "all"

    kwargs["difficulty"] = args.rank_type
    lines = ["Rankings for {}".format(formatter.format_kwargs(kwargs))]
    ranks = formatter.format_highscores(highscores)
    if allow_markdown:
        ranks = f"```\n{ranks}\n```"
    lines.append(ranks)

    return "\n".join(lines)


@helpstring("Get stats")
@schema(
    "stats [b[eginner] | i[ntermediate] | e[xpert] | m[aster]] "
    "[drag-select {on | off}] [per-cell {1 | 2 | 3}]"
)
def stats(args, *, allow_markdown: bool = False):
    parser = BotMsgParser()
    parser.add_difficulty_arg()
    parser.add_per_cell_arg()
    parser.add_drag_select_arg()
    args = parser.parse_args(args)
    return "Stats"


@helpstring("Get player stats")
@schema(
    "stats players {all | <name> [<name> ...]} "
    "[b[eginner] | i[ntermediate] | e[xpert] | m[aster]] "
    "[drag-select {on | off}] [per-cell {1 | 2 | 3}]"
)
def stats_players(args, *, allow_markdown: bool = False):
    parser = BotMsgParser()
    parser.add_username_arg(nargs="+")
    parser.add_difficulty_arg()
    parser.add_per_cell_arg()
    parser.add_drag_select_arg()
    args = parser.parse_args(args)
    return "Player stats {}".format(", ".join(args.username))


@helpstring("Get matchups for given players")
@schema(
    "matchups <name> [<name> ...] "
    "[b[eginner] | i[ntermediate] | e[xpert] | m[aster]] "
    "[drag-select {on | off}] [per-cell {1 | 2 | 3}]"
)
def matchups(args, *, allow_markdown: bool = False):
    parser = BotMsgParser()
    parser.add_username_arg(nargs="+")
    parser.add_difficulty_arg()
    parser.add_per_cell_arg()
    parser.add_drag_select_arg()
    args = parser.parse_args(args)
    return "Matchups {}".format(", ".join(args.username))


@helpstring("Get the best matchups")
@schema(
    "best-matchups [<name> ...] "
    "[b[eginner] | i[ntermediate] | e[xpert] | m[aster]] "
    "[drag-select {on | off}] [per-cell {1 | 2 | 3}]"
)
def best_matchups(args, *, allow_markdown: bool = False):
    parser = BotMsgParser()
    parser.add_username_arg(nargs="*")
    parser.add_difficulty_arg()
    parser.add_per_cell_arg()
    parser.add_drag_select_arg()
    args = parser.parse_args(args)
    return "Best matchups {}".format(", ".join(args.username))


@helpstring("Challenge other players to a game")
@schema(
    "challenge <name> [<name> ...] "
    "[b[eginner] | i[ntermediate] | e[xpert] | m[aster]] "
    "[drag-select {on | off}] [per-cell {1 | 2 | 3}]"
)
def challenge(args, *, allow_markdown: bool = False):
    parser = BotMsgParser()
    parser.add_username_arg(nargs="+")
    parser.add_difficulty_arg()
    parser.add_per_cell_arg()
    parser.add_drag_select_arg()
    args = parser.parse_args(args)
    return "Challenge {}".format(", ".join(args.username))


@helpstring("Set your nickname")
@schema("set nickname <name>")
def set_nickname(args, *, allow_markdown: bool = False):
    nickname = " ".join(args)
    return f"Nickname set to {nickname}"


# fmt: off
COMMANDS = {
    "help": help_,
    "info": info,
    "player": player,
    "ranks": ranks,
    "stats": {
        None: stats,
        "players": stats_players
    },
    "matchups": matchups,
    "best-matchups": best_matchups,
    "challenge": challenge,
    "set": {
        "nickname": set_nickname,
    },
}
# fmt: on


def _map_to_cmd(msg: str) -> Tuple[Callable, List[str]]:
    cmds = COMMANDS
    func = None
    words = msg.split()

    while words:
        next_word = words[0]
        if next_word in cmds:
            words.pop(0)
            if callable(cmds[next_word]):
                func = cmds[next_word]
                break
            else:
                cmds = cmds[next_word]
        else:
            break
        if None in cmds:
            func = cmds[None]

    return func, words


def parse_msg(msg: str, allow_markdown: bool = False) -> str:
    msg = msg.strip()
    if msg.endswith("?"):
        msg = "help " + msg[:-1]

    func = None
    try:
        func, args = _map_to_cmd(msg)
        if func is None:
            raise InvalidArgsError("Base command not found")
        return func(args, allow_markdown=allow_markdown)
    except InvalidArgsError:
        logger.debug("Invalid message: %r", msg)
        return "\n".join(
            [
                "Unrecognised command",
                help_(func, only_schema=True, allow_markdown=allow_markdown),
            ]
        )


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------


def main(argv):
    print(parse_msg(" ".join(argv)))


if __name__ == "__main__":
    main(sys.argv[1:])
