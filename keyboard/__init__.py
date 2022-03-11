# -*- coding: utf-8 -*-
from __future__ import print_function as _print_function

version = "0.13.5"

import re as _re
import itertools as _itertools
import collections as _collections
import threading as _threading
import time as _time
import contextlib as _contextlib

# Python2... Buggy on time changes and leap seconds, but no other good option (https://stackoverflow.com/questions/1205722/how-do-i-get-monotonic-time-durations-in-python).
_time.monotonic = getattr(_time, "monotonic", None) or _time.time

try:
    # Python2
    long, basestring
    _is_str = lambda x: isinstance(x, basestring)
    _is_number = lambda x: isinstance(x, (int, long))
    import Queue as _queue

    # threading.Event is a function in Python2 wrapping _Event (?!).
    from threading import _Event as _UninterruptibleEvent
except NameError:
    # Python3
    _is_str = lambda x: isinstance(x, str)
    _is_number = lambda x: isinstance(x, int)
    import queue as _queue
    from threading import Event as _UninterruptibleEvent
_is_list = lambda x: isinstance(x, (list, tuple))

# The "Event" class from `threading` ignores signals when waiting and is
# impossible to interrupt with Ctrl+C. So we rewrite `wait` to wait in small,
# interruptible intervals.
class _Event(_UninterruptibleEvent):
    def wait(self):
        while True:
            if _UninterruptibleEvent.wait(self, 0.5):
                break


import platform as _platform

if _platform.system() == "Windows":
    from . import _winkeyboard as _os_keyboard
elif _platform.system() == "Linux":
    from . import _nixkeyboard as _os_keyboard
elif _platform.system() == "Darwin":
    from . import _darwinkeyboard as _os_keyboard
else:
    raise OSError("Unsupported platform '{}'".format(_platform.system()))

from ._keyboard_event import KEY_DOWN, KEY_UP, KeyboardEvent
from ._canonical_names import all_modifiers, sided_modifiers, normalize_name

_modifier_scan_codes = set()


def is_modifier(key):
    """
    Returns True if `key` is a scan code or name of a modifier key.
    """
    if _is_str(key):
        return key in all_modifiers
    else:
        return key in _modifier_scan_codes


class _Enum(object):
    def __init__(self, n, name):
        self.n = n
        self.name = name

    def __lt__(self, other):
        return self.n < other.n

    def __repr__(self):
        return self.name


# Allow the event, if no other hooks SUSPEND'ed or SUPPRESS'ed the event.
ALLOW = _Enum(0, "ALLOW")
# Temporarily suspend the event if no other hooks SUPPRESS'ed it, to be either
# allowed or suppressed in the future.
SUSPEND = _Enum(1, "SUSPEND")
# Suppress the event completely, regardless of other hooks decisions.
SUPPRESS = _Enum(2, "SUPPRESS")


class _KeyboardListener(object):
    """
    Class for managing hooks and processing keyboard events. Keeps track of which
    keys are pressed (physically and logically), which keys are suspended, etc.
    """

    STOP_PROCESSING = object()

    def __init__(self):
        # Lock for changing states.
        self.lock = _threading.Lock()

        # Set of scan codes that we've receive KEY_DOWN events but no KEY_UP yet.
        self.physically_pressed_keys = set()
        # Set of scans codes that we've sent or allowed KEY_DOWN events but no KEY_UP yet.
        self.logically_pressed_keys = set()
        # Set of modifiers of currently pressed modifier keys.
        self.active_modifiers = set()
        # Pairs of (event, modifiers).
        self.suspended_event_pairs = []
        # Set when replaying a suspended event, that should not be processed
        # again.
        self.is_replaying = False

        # Maps pressed scan codes to the newest KEY_DOWN event.
        self.pressed_events = {}

        self.suppressing_hooks = []
        self.nonsuppressing_hooks = []
        self.hook_disable_by_id = _collections.defaultdict(set)
        self.async_events_queue = _queue.Queue()

        self.os_listener = None

    def register(self, hook_obj, ids, suppress):
        """
        Registers a hook to process events. Hooks added with suppress=True are
        run in the main blocking thread, and are able to suppress and temporarily
        suspend events.

        The list of ids allows the hook to be removed by id later, such as callback
        or hotkey string.
        """
        hooks_list = self.suppressing_hooks if suppress else self.nonsuppressing_hooks

        # The hook object will be exposed to the user, and it's useful to have
        # `hook_obj.enable()` and `hook_obj.disable()` methods.
        # This could also be done by adding `listener`, `suppress`, and `ids`
        # attributes to the hook, but that's more complicated than just using
        # closures.

        def enable():
            if hook_obj.is_enabled:
                return
            for hook_id in ids:
                self.hook_disable_by_id[hook_id].add(disable)
            hooks_list.append(hook_obj)
            hook_obj.is_enabled = True

        hook_obj.enable = enable

        def disable():
            if not hook_obj.is_enabled:
                return
            for hook_id in ids:
                self.hook_disable_by_id[hook_id].discard(disable)
            if hook_obj in hooks_list:
                hooks_list.remove(hook_obj)
            hook_obj.is_enabled = False

        hook_obj.disable = disable

        enable()

        return hook_obj

    def disable_hook_by_id(self, hook_id):
        """
        Removes all the hooks that were added with this id.
        """
        if hasattr(hook_id, "disable"):
            hook_obj = hook_id
            hook_obj.disable()
        else:
            for hook_disable in list(self.hook_disable_by_id[hook_id]):
                hook_disable()

    @property
    def is_running(self):
        return self.os_listener is not None

    def start(self):
        """
        If not yet started, starts the background threads that intercept OS
        events and handles hooks.
        """
        if self.os_listener:
            return

        self.os_listener = _os_keyboard.Listener()
        listening_thread = _threading.Thread(
            target=lambda: self.os_listener.listen(self.process_sync_event)
        )
        listening_thread.daemon = True
        listening_thread.start()

        # While this thread reads events from the queue and runs hooks
        # asynchronously.
        processing_thread = _threading.Thread(target=self.process_async_queue)
        processing_thread.daemon = True
        processing_thread.start()

    def stop(self):
        """
        If currently running, signals the background threads and OS event
        interception to stop. Further events will not be processed, but the
        threads may live a little longer while they wind down.
        """
        if not self.os_listener:
            return

        with self.async_events_queue.mutex:
            self.async_events_queue.queue.clear()
        self.async_events_queue.put(self.STOP_PROCESSING)

        self.os_listener.stop()
        self.os_listener = None

        # A new flag_running object must be created, otherwise a fast stop/start
        # pair may cause the async thread to never see the flag being cleared.
        # Note that the async thread receives a reference to the flag, so it
        # won't see the new flag_running object.
        self.flag_running = _Event()

    def run_sync_hooks(self, event):
        """
        Passes the given event through all sync hooks registered, deciding to
        allow or suppress the event.
        """
        run_hook = lambda hook: hook.process_event(
            event,
            set(self.pressed_events.keys()),
            self.logically_pressed_keys,
            self.active_modifiers,
        )
        hooks_decisions = [run_hook(hook) for hook in self.suppressing_hooks] or [{}]
        temporary_modifiers_state = set(self.active_modifiers)
        _listener.is_replaying = True

        # Check for previously suspended events. Note that decisions for unrelated
        # keys are ignored.
        for suspended_event, suspended_modifiers in list(self.suspended_event_pairs):
            # Use `max` to merge decisions because ALLOW < SUSPEND < SUPPRESS.
            decision = max(
                decisions.get(suspended_event, ALLOW) for decisions in hooks_decisions
            )
            if decision is SUSPEND:
                # Suspended event continues suspended. Do nothing.
                pass
            elif decision is SUPPRESS:
                # Suspended event is now suppressed, forget about it.
                self.suspended_event_pairs.remove(
                    (suspended_event, suspended_modifiers)
                )
            else:
                assert decision is ALLOW
                # Suspended event is now allowed, replay it.
                if suspended_event.scan_code not in _modifier_scan_codes:
                    # The suspended event may have had a different set of modifiers
                    # than what is currently active. We temporarily send fake key
                    # presses and releases the match the suspended modifiers,
                    # replay the suspended event, then restore the state of the
                    # modifiers.
                    for modifier in temporary_modifiers_state - suspended_modifiers:
                        _os_keyboard.release(modifier)
                        temporary_modifiers_state.remove(modifier)

                if suspended_event.event_type == KEY_DOWN:
                    _os_keyboard.press(suspended_event.scan_code)
                else:
                    _os_keyboard.release(suspended_event.scan_code)
                self.suspended_event_pairs.remove(
                    (suspended_event, suspended_modifiers)
                )

        # Restore state of modifiers.
        for modifier in self.active_modifiers - temporary_modifiers_state:
            _os_keyboard.press(modifier)
        _listener.is_replaying = False

        decision = max((decisions.get(event, ALLOW) for decisions in hooks_decisions))
        if decision is SUSPEND:
            self.suspended_event_pairs.append((event, set(self.active_modifiers)))
            return SUPPRESS
        elif decision is SUPPRESS:
            return SUPPRESS
        else:
            return ALLOW

    def process_sync_event(self, event):
        """
        Processes one event, synchronously (blocking the OS from passing the event
        forward). Passes the event through all hooks that could suppress the event,
        and merge their decisions, returning True (the event is allowed) or False
        (the event should be suppressed).

        May replay previously suppressed events that hooks have suspended before
        but marked as allowed now.
        """
        if self.is_replaying:
            decision = ALLOW
        else:
            # Update list of active modifiers and pressed keys.
            if event.event_type == KEY_DOWN:
                self.pressed_events[event.scan_code] = event
            else:
                self.pressed_events.pop(event.scan_code, None)

            if event.scan_code in _modifier_scan_codes:
                if event.event_type == KEY_DOWN:
                    self.active_modifiers.add(event.scan_code)
                else:
                    self.active_modifiers.discard(event.scan_code)

            # Send event to be processed by non-blocking hooks.
            self.async_events_queue.put(event)
            decision = self.run_sync_hooks(event)

        if decision is ALLOW:
            if event.event_type == KEY_DOWN:
                self.logically_pressed_keys.add(event.scan_code)
            else:
                self.logically_pressed_keys.discard(event.scan_code)
            return True
        else:
            return False

    def process_async_queue(self):
        """
        Reads events from the queue set up by `process_sync_event`, running the hooks
        that are not capable of suppressing events, asynchronously without blocking
        the OS from passing the event forward.
        """
        while True:
            event = self.async_events_queue.get()

            if event is self.STOP_PROCESSING:
                return

            for hook_obj in self.nonsuppressing_hooks:
                # Ignore decisions of non-suppressing hooks.
                _ = hook_obj.process_event(
                    event,
                    set(self.pressed_events.keys()),
                    self.logically_pressed_keys,
                    self.active_modifiers,
                )

            # Enable tests and others to call `self.async_events_queue.join()`
            # to check when all async events are processed.
            self.async_events_queue.task_done()


def start():
    """
    Starts the global keyboard listener, including background threads, to process
    OS events.
    """
    _os_keyboard.init()
    _modifier_scan_codes.clear()
    _modifier_scan_codes.update(
        *(key_to_scan_codes(name, ()) for name in all_modifiers)
    )
    _listener.start()


def stop():
    """
    Stops the global keyboard listener, and signals the background threads to exit.
    """
    _listener.stop()


def reload():
    """
    Restarts the global keyboard listener, including background threads, and reloads
    the mapping of scan codes to key names.
    """
    stop()
    start()


class _SimpleHook(object):
    """
    A hook that will invoke a user-defined function on every keyboard event,
    passing both a reference to the event and a set of all currently pressed
    scan codes.
    """

    def __init__(self, callback):
        self.is_enabled = False
        self.callback = callback

    def enable(self):
        # To be overwritten when added to a listener.
        pass

    def disable(self):
        # To be overwritten when added to a listener.
        pass

    def process_event(
        self, event, physically_pressed_keys, logically_pressed_keys, active_modifiers
    ):
        result = self.callback(event)
        return {event: result if result in (ALLOW, SUPPRESS) else SUPPRESS}

    def __enter__(self):
        self.enable()
        return self

    def __exit__(self, type, value, traceback):
        self.disable()


def hook(callback, suppress=False, extra_ids=()):
    """
    Installs a global listener on all available keyboards, invoking `callback`
    each time a key is pressed or released.

    If `suppress` is True, then the callback is invoked before the event is
    received by other programs, and the event is suppressed unless the callback
    returns `keyboard.ALLOW`.

    The event passed to the callback is of type `keyboard.KeyboardEvent`,
    with the following attributes:

    - `name`: an Unicode representation of the character (e.g. "&") or
    description (e.g.  "space"). The name is always lower-case.
    - `scan_code`: number representing the physical key, e.g. 55.
    - `time`: timestamp of the time the event occurred, with as much precision
    as given by the OS.

    Returns a Hook object with `.enable()` and `.disable()` methods.

    Example:

    ```py
    hook(lambda event: print('Got event:', event))
    ```
    """
    hook_obj = _SimpleHook(callback)
    return _listener.register(hook_obj, [callback] + list(extra_ids), suppress)


add_hook = hook


class _KeyHook(_SimpleHook):
    def __init__(self, scan_codes, callback):
        super(_KeyHook, self).__init__(callback)
        self.scan_codes = scan_codes

    def process_event(
        self, event, physically_pressed_keys, logically_pressed_keys, active_modifiers
    ):
        if event.scan_code in self.scan_codes:
            result = self.callback(event)
            return {event: result if result in (ALLOW, SUPPRESS) else SUPPRESS}
        else:
            return {event: ALLOW}


def hook_key(key, callback, suppress=False):
    """
    Hooks key up and key down events for a single key. Returns the event handler
    created.

    If `suppress` is True, then the callback is invoked before the event is
    received by other programs, and the event is suppressed unless the callback
    returns `keyboard.ALLOW`.

    Returns a Hook object with `.enable()` and `.disable()` methods.
    """
    hook_obj = _KeyHook(key_to_scan_codes(key), callback)
    return _listener.register(hook_obj, [key, callback], suppress)


class _HotkeyHook(_SimpleHook):
    """
    Hook subclass to detect and trigger callbacks when a hotkey is detected.
    """

    def __init__(self, hotkey, timeout, trigger_on_release, callback):
        super(_HotkeyHook, self).__init__(callback)
        self.hotkey = hotkey
        self.timeout = timeout
        self.trigger_on_release = trigger_on_release
        # A set of Finite State Machine transitions based on the current state
        # and input events.
        self.transitions = self.build_hotkey_transition_table(hotkey)

        # Map of {event: one_of(SUPPRESS, ALLOW, SUSPEND)}. Suspended and suppressed
        # key presses are kept around until the corresponding key release comes.
        self.decisions = {}
        # The current state of the hotkey's Finite State Machine. Every state
        # corresponding to a step in the hotkey, with one extra state after to
        # represent a hotkey that was completed but the callback not yet invoked.
        self.state = 0

    def build_hotkey_transition_table(self, hotkey):
        """
        Builds a transition table mapping current hotkey step and received scan code
        to the new step. Technically a Moore-type Finite State Machine.

        transitions[current_state, (1, 2, 3)] -> new_state
        """
        transitions = _collections.defaultdict(lambda: 0)
        # Runs a sequence of input through the current transitions.
        get_final_state = (
            lambda sequence, state=0: state
            if not sequence
            else get_final_state(sequence[1:], state=transitions[state, sequence[0]])
        )

        history = []
        for i, step in enumerate(hotkey.steps):
            for previous_inputs in set(history):
                # If a wrong input is given, but which could be the start (or middle)
                # of a correct sequence, what's the most advanced state it would reach?
                overlapping_state = max(
                    get_final_state(history[j:] + [previous_inputs])
                    for j in range(1, len(history) + 1)
                )
                transitions[i, previous_inputs] = overlapping_state

            # Since each key in the hotkey combination can have multiple scan codes,
            # the cartesian product is taken between all scan codes in each step.
            for input_scan_codes in _itertools.product(
                *[key.scan_codes for key in step.keys]
            ):
                transitions[i, tuple(sorted(input_scan_codes))] = i + 1

            history.append(input_scan_codes)

        return transitions

    def process_event(
        self, event, physically_pressed_keys, logically_pressed_keys, active_modifiers
    ):
        """
        Processes receiving events, updating its current state and calling
        `self.callback` whenever the hotkey is completed.

        Most of this code is to keep track of what events have been suspended
        or suppressed, to return the correct decision to the listener. It tries
        to follow standard hotkey behavior as closely as I could deduce it from
        the OS and other programs.

        It might look like a rat's nest of if-else conditionals and stateful
        mutations, and it is. But trust me, it used to be even worse, and this is
        the fourth clean-slate attempt, plus several full days of effort to
        simplify this attempt down...

        If you have a suggestion on how to simplify it and still pass the tests,
        I'll be thankful.
        """
        step = self.hotkey.steps[min(self.state, len(self.hotkey.steps) - 1)]

        if event.scan_code in _modifier_scan_codes and step.is_standard:
            return self.decisions

        if event.event_type == KEY_UP:
            # If we have a previous decision on the corresponding key press for
            # this key release, repeat the same decision.
            previous_presses = [
                e
                for e in self.decisions
                if e.event_type == KEY_DOWN and e.scan_code == event.scan_code
            ]
            if previous_presses:
                self.decisions[event] = self.decisions[previous_presses[-1]]
                if self.decisions[event] is SUSPEND:
                    is_used_in_this_step = any(
                        event.scan_code in key.scan_codes for key in step.keys
                    )
                    is_used_in_previous_step = self.state > 0 and any(
                        event.scan_code in key.scan_codes
                        for key in self.hotkey.steps[self.state - 1].keys
                    )
                    if (
                        not step.is_standard
                        and is_used_in_this_step
                        and not is_used_in_previous_step
                    ):
                        # We just released a key that we needed for the current step,
                        # and we didn't need it for the previous step, which cancels
                        # the hotkey. Roll back the state.
                        # TODO: don't go back to state 0, but instead check what's
                        # the other possible state we could be in.
                        self.state = 0
                        self.decisions = {
                            e: d for e, d in self.decisions.items() if d == SUPPRESS
                        }
                else:
                    # ALLOW and SUPPRESS decisions for key presses are kept around
                    # for the benefit of the corresponding release. Since it just
                    # happened, delete it.
                    for previous_press in previous_presses:
                        del self.decisions[previous_press]
        elif self.state < len(self.hotkey.steps):
            # If a main key is pressed and the hotkey is not completed yet,
            # it's time to update the state.

            if (
                self.decisions
                and event.time - max([e.time for e in self.decisions]) >= self.timeout
            ):
                # In case of timeout reset the state and the suspended events.
                self.state = 0
                self.decisions = {
                    e: d for e, d in self.decisions.items() if d == SUPPRESS
                }

            self.decisions[event] = SUSPEND

            old_state = self.state
            # Normalize input keys as sorted tuple.
            input_scan_codes = tuple(
                sorted(
                    {event.scan_code} | active_modifiers
                    if step.is_standard
                    else physically_pressed_keys
                )
            )
            self.state = self.transitions[self.state, input_scan_codes]
            if self.state <= old_state and (
                step.is_standard or len(physically_pressed_keys) >= len(step.keys)
            ):
                # The pressed key was unexpected, and the state did not go forward.
                # We must check if any of the suspended events can be allowed now.

                # How many key presses it took to get to this state.
                n_useful_presses_left = sum(
                    1 if step.is_standard else len(step.keys)
                    for step in self.hotkey.steps[: self.state]
                )
                for suspended_event in sorted(
                    self.decisions, key=lambda e: e.time, reverse=True
                ):
                    # Every key press beyond this point is not useful for this hotkey, and should be allowed.
                    if n_useful_presses_left <= 0:
                        del self.decisions[suspended_event]
                    n_useful_presses_left -= suspended_event.event_type == KEY_DOWN

        is_expected_event_type = event.event_type == (
            KEY_UP if self.trigger_on_release else KEY_DOWN
        )
        is_expected_key = any(event.scan_code in key.scan_codes for key in step.keys)
        if (
            is_expected_event_type
            and is_expected_key
            and self.state == len(self.hotkey.steps)
        ):
            # The hotkey is completed, and the callback is finally invoked.
            callback_decision = ALLOW if self.callback() is ALLOW else SUPPRESS
            for e, event_decision in self.decisions.items():
                if event_decision is SUSPEND:
                    self.decisions[e] = callback_decision
            self.state = 0

        # To prevent stuck keys, key releases are not suppressed if a key press
        # was allowed through in the past ("logically pressed").
        for e, event_decision in self.decisions.items():
            if (
                e.event_type == KEY_UP
                and event_decision is SUPPRESS
                and e.scan_code in logically_pressed_keys
            ):
                self.decisions[e] = ALLOW

        return self.decisions


def add_hotkey(
    hotkey, callback, args=(), suppress=True, timeout=1, trigger_on_release=False
):
    """
    Invokes a callback every time a hotkey is pressed. The hotkey must
    be in the format `ctrl+shift+a, s`. This would trigger when the user holds
    ctrl, shift and "a" at once, releases, and then presses "s". To represent
    literal commas, pluses, and spaces, use their names ('comma', 'plus',
    'space').

    - `args` is an optional list of arguments to passed to the callback during
    each invocation.
    - `suppress` defines if successful triggers should block the keys from being
    sent to other programs.
    - `timeout` is the amount of seconds allowed to pass between key presses.
    - `trigger_on_release` if true, the callback is invoked on key release instead
    of key press.

    Returns a Hook object with `.enable()` and `.disable()` methods.

    Note: hotkeys are activated when the last key is *pressed*, not released.
    Note: the callback is executed in a separate thread, asynchronously. For an
    example of how to use a callback synchronously, see `wait`.

    Examples:

        # Different but equivalent ways to listen for a spacebar key press.
        add_hotkey(' ', print, args=['space was pressed'])
        add_hotkey('space', print, args=['space was pressed'])
        add_hotkey('Space', print, args=['space was pressed'])
        # Here 57 represents the keyboard code for spacebar; so you will be
        # pressing 'spacebar', not '57' to activate the print function.
        add_hotkey(57, print, args=['space was pressed'])

        add_hotkey('ctrl+q', quit)
        add_hotkey('ctrl+alt+enter, space', some_callback)
    """
    if args:
        callback = lambda f=callback: f(*args)

    parsed_hotkey = parse_hotkey(hotkey)
    hook_obj = _HotkeyHook(
        hotkey=parsed_hotkey,
        callback=callback,
        timeout=timeout,
        trigger_on_release=trigger_on_release,
    )
    return _listener.register(hook_obj, suppress=suppress, ids=[callback, hotkey])


def key_to_scan_codes(key, default=None):
    """
    Returns a list of scan codes associated with this key (name or scan code).
    """
    if _is_number(key):
        return (key,)
    elif _is_list(key):
        return sum((key_to_scan_codes(i) for i in key), ())
    elif not _is_str(key):
        raise ValueError(
            "Unexpected key type " + str(type(key)) + ", value (" + repr(key) + ")"
        )

    normalized = normalize_name(key)
    if normalized in sided_modifiers:
        left_scan_codes = key_to_scan_codes("left " + normalized, ())
        right_scan_codes = key_to_scan_codes("right " + normalized, ())
        return left_scan_codes + tuple(
            c for c in right_scan_codes if c not in left_scan_codes
        )

    try:
        # Put items in ordered dict to remove duplicates.
        return tuple(
            _collections.OrderedDict(
                (scan_code, True)
                for scan_code, modifier in _os_keyboard.map_name(normalized)
            )
        )
    except (KeyError, ValueError) as exception:
        if default is None:
            raise ValueError(
                "Key {} is not mapped to any known key.".format(repr(key)), exception
            )
        else:
            return default


class Hotkey(object):
    def __init__(self, steps):
        self.steps = tuple(steps)

    def __eq__(self, other):
        return str(self) == str(other)

    def __repr__(self):
        return ", ".join(map(str, self.steps))


class Step(object):
    def __init__(self, keys):
        self.keys = tuple(keys)
        self.modifiers = [key for key in self.keys if is_modifier(key.scan_codes[0])]
        non_modifiers = [key for key in self.keys if key not in self.modifiers]
        if len(non_modifiers) == 1:
            self.is_standard = True
            self.main_key = non_modifiers[0]
        else:
            self.is_standard = False
            self.main_key = None

    def __eq__(self, other):
        return str(self) == str(other)

    def __repr__(self):
        return "+".join(map(str, self.keys))


class Key(object):
    def __init__(self, label, scan_codes):
        self.label = label
        self.scan_codes = tuple(scan_codes)
        assert self.scan_codes and all(
            _is_number(scan_code) for scan_code in self.scan_codes
        )

    def __eq__(self, other):
        return str(self) == str(other)

    def __repr__(self):
        if self.label:
            return str(self.label)
        elif len(self.scan_codes) == 1:
            return str(self.scan_codes[0])
        else:
            return "({})".format(",".join(map(str, self.scan_codes)))


def parse_hotkey(hotkey):
    """
    Parses a user-provided hotkey into nested tuples representing the
    parsed structure, with the bottom values being lists of scan codes.
    Also accepts raw scan codes, which are then wrapped in the required
    number of nestings.

    Example:

        parse_hotkey("alt+shift+a, alt+b, c")
        #    Keys:    ^~^ ^~~~^ ^  ^~^ ^  ^
        #    Steps:   ^~~~~~~~~~^  ^~~~^  ^

        # ((alt_codes, shift_codes, a_codes), (alt_codes, b_codes), (c_codes,))
    """
    if isinstance(hotkey, Hotkey):
        return hotkey
    elif _is_number(hotkey) or hasattr(hotkey, "__len__") and len(hotkey) == 1:
        key = Key(hotkey, key_to_scan_codes(hotkey))
        step = Step([key])
        return Hotkey([step])
    elif _is_list(hotkey):
        if not any(map(_is_list, hotkey)):
            keys = [Key(k, key_to_scan_codes(k)) for k in hotkey]
            step = Step(keys)
            return Hotkey([step])
        else:
            steps = [Step(Key(None, k) for k in step) for step in hotkey]
            return Hotkey(steps)
    elif isinstance(hotkey, str):
        steps = []
        for step in _re.split(r",\s?", hotkey):
            key_names = _re.split(r"\s?\+\s?", step)
            steps.append(
                Step([Key(name, key_to_scan_codes(name)) for name in key_names])
            )
        return Hotkey(steps)
    else:
        raise TypeError(
            "Hotkey type must be keyboard.Hotkey, int, list of ints, or str. Found {} ({})".format(
                repr(hotkey), type(hotkey)
            )
        )


def send(hotkey, do_press=True, do_release=True, process_events=False):
    """
    Sends OS events that perform the given *hotkey* hotkey.

    - `hotkey` can be either a scan code (e.g. 57 for space), single key
    (e.g. 'space') or multi-key, multi-step hotkey (e.g. 'alt+F4, enter').
    - `do_press` if true then press events are sent. Defaults to True.
    - `do_release` if true then release events are sent. Defaults to True.

        send(57)
        send('ctrl+alt+del')
        send('alt+F4, enter')
        send('shift+s')

    Note: keys are released in the opposite order they were pressed.
    """
    if not process_events:
        _listener.is_replaying = True

    parsed = parse_hotkey(hotkey)
    for step in parsed.steps:
        if do_press:
            for key in step.keys:
                _os_keyboard.press(key.scan_codes[0])

        if do_release:
            for key in reversed(step.keys):
                _os_keyboard.release(key.scan_codes[0])

    if not process_events:
        _listener.is_replaying = False


# Alias.
press_and_release = send


def press(hotkey, process_events=False):
    """Presses and holds down a hotkey (see `send`)."""
    send(hotkey, True, False, process_events=process_events)


def release(hotkey, process_events=False):
    """Releases a hotkey (see `send`)."""
    send(hotkey, False, True, process_events=process_events)


def is_pressed(hotkey):
    """
    Returns True if the key is pressed.

        is_pressed(57) #-> True
        is_pressed('space') #-> True
        is_pressed('ctrl+space') #-> True
    """
    if _is_number(hotkey):
        # Shortcut.
        with _listener.lock:
            return hotkey in _listener.pressed_events

    steps = parse_hotkey(hotkey).steps
    if len(steps) > 1:
        raise ValueError(
            "Impossible to check if multi-step hotkeys are pressed (`a+b` is ok, `a, b` isn't)."
        )

    with _listener.lock:
        pressed_scan_codes = set(_listener.pressed_events)
    for key in steps[0].keys:
        if not any(scan_code in pressed_scan_codes for scan_code in key.scan_codes):
            return False
    return True


def call_later(fn, args=(), delay=0.001):
    """
    Calls the provided function in a new thread after waiting some time.
    Useful for giving the system some time to process an event, without suppressing
    the current execution flow.
    """
    thread = _threading.Thread(target=lambda: (_time.sleep(delay), fn(*args)))
    thread.start()


def on_press(callback, suppress=False):
    """
    Invokes `callback` for every KEY_DOWN event. For details see `hook`.
    """
    return hook(lambda e: e.event_type == KEY_UP or callback(e), suppress=suppress)


def on_release(callback, suppress=False):
    """
    Invokes `callback` for every KEY_UP event. For details see `hook`.
    """
    return hook(lambda e: e.event_type == KEY_DOWN or callback(e), suppress=suppress)


def on_press_key(key, callback, suppress=False):
    """
    Invokes `callback` for KEY_DOWN event related to the given key. For details see `hook`.
    """
    return hook_key(
        key, lambda e: e.event_type == KEY_UP or callback(e), suppress=suppress
    )


def on_release_key(key, callback, suppress=False):
    """
    Invokes `callback` for KEY_UP event related to the given key. For details see `hook`.
    """
    return hook_key(
        key, lambda e: e.event_type == KEY_DOWN or callback(e), suppress=suppress
    )


def block_key(key):
    """
    Suppresses all key events of the given key, regardless of modifiers.
    """
    return hook_key(key, lambda e: None, suppress=True)


def unhook(callback_or_hook_or_hotkey):
    """
    Removes a previously added hook, either by callback or by the return value
    of `hook`.
    """
    _listener.disable_hook_by_id(callback_or_hook_or_hotkey)


unhook_key = (
    unremap_key
) = (
    unremap_hotkey
) = (
    unblock_key
) = (
    unregister_hotkey
) = clear_hotkey = remove_hotkey = remove_abbreviation = remove_word_listener = unhook


def unhook_all():
    """
    Removes all keyboard hooks in use, including hotkeys, abbreviations, word
    listeners, blocked keys, `record`ers and `wait`s.
    """
    del _listener.suppressing_hooks[:]
    del _listener.nonsuppressing_hooks[:]


unregister_all_hotkeys = (
    remove_all_hotkeys
) = clear_all_hotkeys = unhook_all_hotkeys = unhook_all


def remap_key(src, dst):
    """
    Whenever the key `src` is pressed or released, regardless of modifiers,
    press or release the hotkey `dst` instead.
    """

    def handler(event):
        if event.event_type == KEY_DOWN:
            press(dst)
        else:
            release(dst)

    return hook_key(src, handler, suppress=True)


def remap_hotkey(src, dst, suppress=True, trigger_on_release=False):
    """
    Whenever the hotkey `src` is pressed, suppress it and send
    `dst` instead.

    Example:

        remap('alt+w', 'ctrl+up')
    """

    def handler():
        with ensure_state():
            send(dst)

    return add_hotkey(
        src, handler, suppress=suppress, trigger_on_release=trigger_on_release
    )


@_contextlib.contextmanager
def ensure_state(*keys):
    """
    Context manager to ensure that ensures only the given keys are pressed. E.g.:

    ```py
    with keyboard.ensure_state("ctrl"):
        mouse.scroll(-5)
    ```

    Will release any currently active modifiers, press `ctrl`, scroll the mouse,
    release `ctrl`, and press again the previously active modifiers.
    """
    active_modifiers = _listener.active_modifiers
    for modifier in active_modifiers:
        release(modifier)

    for key in keys:
        press(key)

    yield None

    for key in reversed(keys):
        release(key)

    for modifier in active_modifiers:
        press(modifier)


def stash_state():
    """
    Builds a list of all currently pressed scan codes, releases them and returns
    the list. Pairs well with `restore_state` and `restore_modifiers`.
    """
    # TODO: stash caps lock / numlock /scrollock state.
    with _listener.lock:
        state = sorted(_listener.pressed_events)
    for scan_code in state:
        _os_keyboard.release(scan_code)
    return state


def release_all_keys():
    """
    Sends a release event for each key that is seen as pressed by other programs.
    """
    for key in list(_listener.logically_pressed_keys):
        _os_keyboard.release(key)


def restore_state(scan_codes):
    """
    Given a list of scan_codes ensures these keys, and only these keys, are
    pressed. Pairs well with `stash_state`, alternative to `restore_modifiers`.
    """
    _listener.is_replaying = True

    with _listener.lock:
        current = set(_listener.pressed_events)
    target = set(scan_codes)
    for scan_code in sorted(current - target):
        _os_keyboard.release(scan_code)
    for scan_code in sorted(target - current):
        _os_keyboard.press(scan_code)

    _listener.is_replaying = False


def restore_modifiers(scan_codes):
    """
    Like `restore_state`, but only restores modifier keys.
    """
    restore_state((scan_code for scan_code in scan_codes if is_modifier(scan_code)))


def write(text, delay=0, restore_state_after=True, exact=None):
    """
    Sends artificial keyboard events to the OS, simulating the typing of a given
    text. Characters not available on the keyboard are typed as explicit unicode
    characters using OS-specific functionality, such as alt+codepoint.

    To ensure text integrity, all currently pressed keys are released before
    the text is typed, and modifiers are restored afterwards.

    - `delay` is the number of seconds to wait between keypresses, defaults to
    no delay.
    - `restore_state_after` can be used to restore the state of pressed keys
    after the text is typed, i.e. presses the keys that were released at the
    beginning. Defaults to True.
    - `exact` forces typing all characters as explicit unicode (e.g.
    alt+codepoint or special events). If None, uses platform-specific suggested
    value.
    """
    if exact is None:
        exact = _platform.system() == "Windows"

    state = stash_state()

    # Window's typing of unicode characters is quite efficient and should be preferred.
    if exact:
        for letter in text:
            if letter in "\n\b":
                send(letter)
            else:
                _os_keyboard.type_unicode(letter)
            if delay:
                _time.sleep(delay)
    else:
        for letter in text:
            try:
                entries = _os_keyboard.map_name(normalize_name(letter))
                scan_code, modifiers = next(iter(entries))
            except (KeyError, ValueError, StopIteration):
                _os_keyboard.type_unicode(letter)
                continue

            for modifier in modifiers:
                press(modifier)

            _os_keyboard.press(scan_code)
            _os_keyboard.release(scan_code)

            for modifier in modifiers:
                release(modifier)

            if delay:
                _time.sleep(delay)

    if restore_state_after:
        restore_modifiers(state)


def wait(hotkey=None, suppress=False, trigger_on_release=False):
    """
    Blocks the program execution until the given hotkey is pressed or,
    if given no parameters, blocks forever.
    """
    if hotkey:
        lock = _Event()
        with add_hotkey(
            hotkey,
            lock.set,
            suppress=suppress,
            trigger_on_release=trigger_on_release,
        ):
            lock.wait()
    else:
        while True:
            _time.sleep(1e6)


def get_hotkey_name(names=None):
    """
    Returns a string representation of hotkey from the given key names, or
    the currently pressed keys if not given.  This function:

    - normalizes names;
    - removes "left" and "right" prefixes;
    - replaces the "+" key name with "plus" to avoid ambiguity;
    - puts modifier keys first, in a standardized order;
    - sort remaining keys;
    - finally, joins everything with "+".

    Example:

        get_hotkey_name(['+', 'left ctrl', 'shift'])
        # "ctrl+shift+plus"
    """
    if names is None:
        with _listener.lock:
            names = [
                e.name or str(e.scan_code) for e in _listener.pressed_events.values()
            ]
    else:
        names = [normalize_name(name) for name in names]
    clean_names = set(
        e.replace("left ", "").replace("right ", "").replace("+", "plus") for e in names
    )
    # https://developer.apple.com/macos/human-interface-guidelines/input-and-output/keyboard/
    # > List modifier keys in the correct order. If you use more than one modifier key in a
    # > hotkey, always list them in this order: Control, Option, Shift, Command.
    modifiers = ["ctrl", "alt", "shift", "windows"]
    sorting_key = lambda k: (modifiers.index(k) if k in modifiers else 5, str(k))
    return "+".join(sorted(clean_names, key=sorting_key))


def read_event(suppress=False, timeout=None):
    """
    Blocks until a keyboard event happens, then returns that event.

    If `timeout` is not None, waits at most `timeout` seconds else raise a
    queue.Empty exception.
    """
    queue = _queue.Queue(maxsize=1)
    with hook(queue.put, suppress=suppress):
        return queue.get(timeout=timeout)


def read_key(suppress=False, timeout=None):
    """
    Blocks until a keyboard event happens, then returns that event's name or,
    if missing, its scan code.

    If `timeout` is not None, waits at most `timeout` seconds else raise a
    queue.Empty exception.
    """
    queue = _queue.Queue(maxsize=1)
    with hook(queue.put, suppress=suppress):
        while True:
            event = queue.get(timeout=timeout)
            if event.event_type == KEY_DOWN:
                return event.name or event.scan_code


def read_hotkey(suppress=True, timeout=None):
    """
    Similar to `read_key()`, but blocks until the user presses and releases a
    hotkey (or single key), then returns a string representing the hotkey
    pressed.

    If `timeout` is not None, waits at most `timeout` seconds else raise a
    queue.Empty exception.

    Example:

        read_hotkey()
        # "ctrl+shift+p"
    """
    names = []
    queue = _queue.Queue()
    with hook(queue.put, suppress=suppress):
        while True:
            event = queue.get(timeout=timeout)
            if event.event_type == KEY_DOWN:
                names.append(event.name or event.scan_code)
            elif names:
                break
    return get_hotkey_name(names)


def get_typed_strings(events, allow_backspace=True):
    """
    Given a sequence of events, tries to deduce what strings were typed.
    Strings are separated when a non-textual key is pressed (such as tab or
    enter). Characters are converted to uppercase according to shift and
    capslock status. If `allow_backspace` is True, backspaces remove the last
    character typed.

    This function is a generator, so you can pass an infinite stream of events
    and convert them to strings in real time.

    Note this functions is merely an heuristic. Windows for example keeps per-
    process keyboard state such as keyboard layout, and this information is not
    available for our hooks.

        get_type_strings(record()) #-> ['This is what', 'I recorded', '']
    """
    backspace_name = "delete" if _platform.system() == "Darwin" else "backspace"

    shift_pressed = False
    capslock_pressed = False
    string = ""
    for event in events:
        name = event.name

        # Space is the only key that we _parse_hotkey to the spelled out name
        # because of legibility. Now we have to undo that.
        if event.name == "space":
            name = " "

        if "shift" in event.name:
            shift_pressed = event.event_type == "down"
        elif event.name == "caps lock" and event.event_type == "down":
            capslock_pressed = not capslock_pressed
        elif (
            allow_backspace
            and event.name == backspace_name
            and event.event_type == "down"
        ):
            string = string[:-1]
        elif event.event_type == "down":
            if len(name) == 1:
                if shift_pressed ^ capslock_pressed:
                    name = name.upper()
                string = string + name
            else:
                yield string
                string = ""
    yield string


_recording = None


def start_recording(recorded_events_queue=None):
    """
    Starts recording all keyboard events into a global variable, or the given
    queue if any. Returns the queue of events and the hooked function.

    Use `stop_recording()` or `unhook(hooked_function)` to stop.
    """
    recorded_events_queue = recorded_events_queue or _queue.Queue()
    global _recording
    _recording = (recorded_events_queue, hook(recorded_events_queue.put))
    return _recording


def stop_recording():
    """
    Stops the global recording of events and returns a list of the events
    captured.
    """
    global _recording
    if not _recording:
        raise ValueError('Must call "start_recording" before.')
    recorded_events_queue, hooked = _recording
    _recording = None
    unhook(hooked)
    return list(recorded_events_queue.queue)


def record(until="escape", suppress=False, trigger_on_release=False):
    """
    Records all keyboard events from all keyboards until the user presses the
    given hotkey. Then returns the list of events recorded, of type
    `keyboard.KeyboardEvent`. Pairs well with
    `play(events)`.

    Note: this is a suppressing function.
    Note: for more details on the keyboard hook and events see `hook`.
    """
    start_recording()
    wait(until, suppress=suppress, trigger_on_release=trigger_on_release)
    return stop_recording()


def play(events, speed_factor=1.0):
    """
    Plays a sequence of recorded events, maintaining the relative time
    intervals. If speed_factor is <= 0 then the actions are replayed as fast
    as the OS allows. Pairs well with `record()`.

    Note: the current keyboard state is cleared at the beginning and restored at
    the end of the function.
    """
    state = stash_state()

    last_time = None
    for event in events:
        if speed_factor > 0 and last_time is not None:
            _time.sleep((event.time - last_time) / speed_factor)
        last_time = event.time

        key = event.scan_code or event.name
        press(key) if event.event_type == KEY_DOWN else release(key)

    restore_modifiers(state)


replay = play


def add_word_listener(
    word, callback, triggers=["space"], match_suffix=False, timeout=2
):
    """
    Invokes a callback every time a sequence of characters is typed (e.g. 'pet')
    and followed by a trigger key (e.g. space). Modifiers (e.g. alt, ctrl,
    shift) are ignored.

    - `word` the typed text to be matched. E.g. 'pet'.
    - `callback` is an argument-less function to be invoked each time the word
    is typed.
    - `triggers` is the list of keys that will cause a match to be checked. If
    the user presses some key that is not a character (len>1) and not in
    triggers, the characters so far will be discarded. By default the trigger
    is only `space`.
    - `match_suffix` defines if endings of words should also be checked instead
    of only whole words. E.g. if true, typing 'carpet'+space will trigger the
    listener for 'pet'. Defaults to false, only whole words are checked.
    - `timeout` is the maximum number of seconds between typed characters before
    the current word is discarded. Defaults to 2 seconds.

    Returns the event handler created. To remove a word listener use
    `remove_word_listener(word)`, `remove_word_listener(handler)`, or
    `returned.disable()`.

    Note: all actions are performed on key down. Key up events are ignored.
    Note: word matches are **case sensitive**.
    """
    state = _State()
    state.current = ""
    state.time = -1

    def handler(event):
        name = event.name
        if event.event_type == KEY_UP or name in all_modifiers:
            return

        if timeout and event.time - state.time > timeout:
            state.current = ""
        state.time = event.time

        matched = state.current == word or (
            match_suffix and state.current.endswith(word)
        )
        if name in triggers and matched:
            callback()
            state.current = ""
        elif len(name) > 1:
            state.current = ""
        else:
            state.current += name

    return hook(handler, suppress=False, extra_ids=[word, callback])


def add_abbreviation(source_text, replacement_text, match_suffix=False, timeout=2):
    """
    Registers a hotkey that replaces one typed text with another. For example

        add_abbreviation('tm', u'™')

    Replaces every "tm" followed by a space with a ™ symbol (and no space). The
    replacement is done by sending backspace events.

    - `match_suffix` defines if endings of words should also be checked instead
    of only whole words. E.g. if true, typing 'carpet'+space will trigger the
    listener for 'pet'. Defaults to false, only whole words are checked.
    - `timeout` is the maximum number of seconds between typed characters before
    the current word is discarded. Defaults to 2 seconds.

    For more details see `add_word_listener`.
    """
    replacement = "\b" * (len(source_text) + 1) + replacement_text
    callback = lambda: write(replacement)
    return add_word_listener(
        source_text, callback, match_suffix=match_suffix, timeout=timeout
    )


# Aliases.
register_word_listener = add_word_listener
register_abbreviation = add_abbreviation

# Start listening threads.
_listener = _KeyboardListener()
start()

import atexit as _atexit

# Release all pressed keys on exit, to avoid stuck keys.
_atexit.register(release_all_keys)
