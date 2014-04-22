def read_device_file():
    from pathlib import Path
    event_files = Path('/dev/input/by-id').glob('*-event-kbd')

    for event_file in event_files:
        if '-if01-' not in event_file.name:
            break

    with event_file.open('rb') as events:
        while True:
            yield events.read(1)

def listen(handlers):
    i = 0
    for byte in read_device_file():
        event = byte
        for handler in handlers:
            try:
                if handler(event):
                    # Stop processing this hotkey.
                    return 1
            except Exception as e:
                print(e)

if __name__ == '__main__':
    listen([])
