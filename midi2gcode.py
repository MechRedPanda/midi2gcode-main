import math
import collections
import mido
from mido import MidiFile

# Load Midi Files
file_name = 'input.mid'
mid = MidiFile(file_name)
merged = mido.merge_tracks(mid.tracks)

# Read Tempo from the file.
# If it is missing then load the default value
tempos = []
for msg in mid.tracks[0]:
    if msg.type == 'set_tempo':
        tempos.append((msg.time, msg.tempo))
if len(tempos) == 0:
    tempos = [(0, 480000)]
tempos.sort(key=lambda y: y[0])

# Helper function to convert midi ticks to wall time.


def ticks2second(tick, tempos):
    ticks_per_beat = mid.ticks_per_beat
    if len(tempos) == 1:
        return mido.tick2second(tick, ticks_per_beat, tempos[0][1])
    time = 0.0
    for i in range(len(tempos)-1):
        tempo_t, tempo = tempos[i]
        tempo_t_next, tempo_next = tempos[i+1]
        if tick >= tempo_t and tick >= tempo_t_next:
            time += mido.tick2second(tempo_t_next -
                                     tempo_t, ticks_per_beat, tempo)
            continue
        if tick >= tempo_t and tick < tempo_t_next:
            time += mido.tick2second(tick-tempo_t, ticks_per_beat, tempo)
            return time
    tempo_t, tempo = tempos[-1]
    time += mido.tick2second(tick-tempo_t, ticks_per_beat, tempo)
    return time


notes_change_dict = {}
current_time = 0
for msg in merged:
    current_time += msg.time
    if msg.type == 'note_on' or msg.type == 'note_off':
        if current_time in notes_change_dict:
            notes_change_dict[current_time].append(msg)
        else:
            notes_change_dict[current_time] = [msg]

notes_change_by_timestamp = collections.OrderedDict(
    sorted(notes_change_dict.items()))

current_notes = dict()
notes_by_timestamp = dict()
max_num_notes = 0
for time, msgs in notes_change_by_timestamp.items():
    notes_counter_this_time = dict()
    for msg in msgs:
        if msg.type == 'note_on' and msg.velocity > 0:
            if msg.note not in notes_counter_this_time:
                notes_counter_this_time[msg.note] = 1
            else:
                notes_counter_this_time[msg.note] += 1
        elif msg.type == 'note_off' or msg.velocity == 0:
            if msg.note not in notes_counter_this_time:
                notes_counter_this_time[msg.note] = -1
            else:
                notes_counter_this_time[msg.note] -= 1
    for note, change in notes_counter_this_time.items():
        if change > 0:
            if note not in current_notes:
                current_notes[note] = change
        elif change < 0:
            if note in current_notes:
                del current_notes[note]
    notes_by_timestamp[time] = set(current_notes.keys())
    if len(current_notes.keys()) > max_num_notes:
        max_num_notes = len(current_notes.keys())
notes_by_timestamp = collections.OrderedDict(
    sorted(notes_by_timestamp.items()))

timestamps = []
all_notes = []
for key, value in notes_by_timestamp.items():
    timestamps.append(key)
    all_notes.append(value)
start_end_timestamps = []
for i in range(len(timestamps)-1):
    start_end_timestamps.append(timestamps[i:i+2])


def note_to_freq(note: int, base_freq=440):
    return base_freq*math.pow(2.0, (note-69)/12.0)


class Printer:
    def __init__(self):
        self.x_min = 10
        self.x_max = 110
        self.y_min = 10
        self.y_max = 110
        self.a_steps_per_mm = 160
        self.b_steps_per_mm = 160
        self.is_corexy = True
        self.current_pos = [self.x_min, self.y_min]
        self.current_dir = [1, 1]
        self.max_speed = 2000  # mm per min
        self.travel_speed = 1500

    def init_gcode(self):
        gcode = []
        gcode.append('G28 X Y')
        gcode.append(f'G1 X{self.x_min} Y{self.y_min} F{self.travel_speed}')
        gcode.append('G4 P1000')
        return gcode

    def move(self, x, y, feed_rate):
        if x >= self.x_max or x <= self.x_min:
            raise ValueError(f'x:{x}  y:{y}')
        if y >= self.y_max or y <= self.y_min:
            raise ValueError(f'x:{x}  y:{y}')

        return f'G1 X{x} Y{y}  F{feed_rate}'

    @classmethod
    def freq2feedrate(cls, freq, steps_per_mm):
        return 60*freq/steps_per_mm

    @classmethod
    def calculate_distance(cls, feedrate, duration):
        return feedrate/60*duration

    def freq2gcode(self, freqs, duration_s):
        if len(freqs) > 2:
            raise ValueError()
        if len(freqs) == 0:
            return f'G4 P{duration_s*1000}'
        if len(freqs) == 1:
            feed_rate_a = self.freq2feedrate(freqs[0], self.a_steps_per_mm)
            feed_rate_b = 0
        else:
            feed_rate_a = self.freq2feedrate(freqs[0], self.a_steps_per_mm)
            feed_rate_b = self.freq2feedrate(freqs[1], self.b_steps_per_mm)
        delta_a = self.calculate_distance(feed_rate_a, duration_s)
        delta_b = self.calculate_distance(feed_rate_b, duration_s)
        if self.is_corexy:
            delta_x = (delta_a + delta_b)/2 * self.current_dir[0]
            delta_y = (delta_b - delta_a)/2 * self.current_dir[1]
        else:
            delta_x = delta_a * self.current_dir[0]
            delta_y = delta_b * self.current_dir[1]
        new_x = self.current_pos[0] + delta_x
        if new_x >= self.x_max or new_x <= self.x_min:
            new_x = self.current_pos[0] - delta_x
            self.current_dir[0] = - self.current_dir[0]
        new_y = self.current_pos[1] + delta_y
        if new_y >= self.y_max or new_y <= self.y_min:
            new_y = self.current_pos[1] - delta_y
            self.current_dir[1] = - self.current_dir[1]
        feed_rate = math.sqrt(delta_x*delta_x + delta_y*delta_y)/duration_s*60
        self.current_pos = [new_x, new_y]
        try:
            moves = self.move(new_x, new_y, feed_rate)
            return moves
        except:
            print(freqs, duration_s)
            raise ValueError(f'delta_x {delta_x}')


num_channels = 2
num_runs = math.ceil(max_num_notes / num_channels)
for r in range(num_runs):
    note_index = [r * num_channels, r * num_channels + 1]
    voron = Printer()
    gcode_list = []
    gcode_list.extend(voron.init_gcode())
    for start_end, notes in zip(start_end_timestamps, all_notes):
        if len(notes) > 0:
            notes_sorted = list(notes)
            notes_sorted.sort(reverse=True)
            notes_to_play = []
            for ni in note_index:
                if ni >= len(notes_sorted):
                    continue
                else:
                    notes_to_play.append(notes_sorted[ni])
            freqs = [note_to_freq(n) for n in notes_to_play]
            duration = ticks2second(
                start_end[1], tempos) - ticks2second(start_end[0], tempos)
            while(duration > 5.0):
                gcode_list.append(voron.freq2gcode(freqs, 5.0))
                duration -= 5.0
            gcode_list.append(voron.freq2gcode(freqs, duration))

    with open(f'{file_name[:-4]}_{r}.gcode', 'w') as fp:
        for item in gcode_list:
            # write each item on a new line
            fp.write("%s\n" % item)
