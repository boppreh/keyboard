"""
This script allows you to record keyboard events in segments, then replay them
back with pauses between the segments.

It's useful for presentations, to ensure typing accuracy while still giving you
time to speak between segments.
"""
import sys
sys.path.append('../')
import keyboard
import pickle
import os

if len(sys.argv) == 1:
    filename = input('Enter filename to save/load events: ')
else:
    filename = sys.argv[1]

if os.path.exists(filename):
    segments = pickle.load(open(filename, 'rb'))
    for i, segment in enumerate(segments):
        print('Press F1 to play segment {}/{}'.format(i+1, len(segments)))
        print('Duration: {:.02} seconds'.format(segment[-1].time - segment[0].time))
        keyboard.wait('F1')
        keyboard.play(segment)

else:
    print('Press F1 to save this fragment. Press F2 to discard it. Press F3 to stop recording.')

    segments = []
    segment = []

    def handle_event(event):
        global segment

        if keyboard.matches(event, 'F1'):
            if event.event_type == keyboard.KEY_DOWN:
                if segment:
                    segments.append(segment)
                segment = []
                print('Saved', len(segments))
        elif keyboard.matches(event, 'F2'):
            if event.event_type == keyboard.KEY_DOWN:
                segment = []
                print('Discarded')
        else:
            segment.append(event)

    keyboard.hook(handle_event)
    keyboard.wait('F3')
    keyboard.hook(handle_event)

    pickle.dump(segments, open(filename, 'wb'))
    print('Saved {} segments to {}'.format(len(segments), filename))