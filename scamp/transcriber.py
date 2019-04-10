from .performance import Performance
from expenvelope import *
from typing import Sequence
from clockblocks import Clock, TempoEnvelope
from .instruments2 import ScampInstrument


class Transcriber:

    def __init__(self):
        self._transcriptions_in_progress = []

    def start_recording(self, instruments: Sequence[ScampInstrument], clock: Clock, units="beats"):
        """
        Starts recording new performance on the given clock, consisting of the given instrument
        :param instruments: the instruments we notate in this Performance
        :param clock: which clock all timings are relative to, or "absolute" to mean time on the master clock
        :param units: one of ["beats", "time"]. Do we use the beats of the clock or the time?
        :return: the Performance that this transcription writes to, which will be updated as notes are played and acts
        as a handle when calling stop_recording.
        """
        assert units in ("beats", "time")

        performance = Performance()
        for instrument in instruments:
            performance.new_part(instrument)
            if self not in instrument._transcribers_to_notify:
                instrument._transcribers_to_notify.append(self)

        self._transcriptions_in_progress.append(
            (performance, clock, clock.beats(), units)
        )

        return performance

    def register_note(self, instrument, note_info):
        """
        Called when an instrument wants to register that it finished a note, records note in all transcriptions
        :param instrument: the ScampInstrument that played the note
        :param note_info: the note info dictionary on that note, containing time stamps, parameter changes, etc.
        """
        assert note_info["end_time"] is not None, "Cannot register unfinished note!"
        param_change_segments = note_info["parameter_change_segments"]

        # loop through all the transcriptions in progress
        for performance, clock, clock_start_beat, units in self._transcriptions_in_progress:
            # figure out the start_beat and length relative to this transcription's clock and start beat
            note_start_beat = Transcriber._resolve_time_stamp(note_info["start_time"], clock, units) - clock_start_beat

            # handle split points (if applicable) by creating a note length sections tuple
            note_length_sections = None
            if len(note_info["split_points"]) > 0:
                note_length_sections = []
                last_split = note_start_beat
                for split_point in note_info["split_points"]:
                    split_point_beat = Transcriber._resolve_time_stamp(split_point, clock, units)
                    note_length_sections.append(split_point_beat - last_split)
                    last_split = split_point_beat
                end_beat = Transcriber._resolve_time_stamp(note_info["end_time"], clock, units)
                if end_beat > last_split:
                    note_length_sections.append(end_beat-last_split)
                note_length_sections = tuple(note_length_sections)

            note_length = Transcriber._resolve_time_stamp(note_info["end_time"], clock, units) - note_start_beat

            # get curves for all the parameters
            extra_parameters = {}
            for param in note_info["parameter_start_values"]:
                if param in param_change_segments and len(param_change_segments[param]) > 0:
                    levels = [note_info["parameter_start_values"][param]]
                    beat_of_last_level_recorded = note_start_beat  # keep track of this in case of gaps between segments
                    durations = []
                    curve_shapes = []
                    for param_change_segment in param_change_segments[param]:
                        start_beat_in_clock = Transcriber._resolve_time_stamp(param_change_segment.start_time_stamp,
                                                                              clock, units)
                        end_beat_in_clock = Transcriber._resolve_time_stamp(param_change_segment.end_time_stamp,
                                                                              clock, units)

                        # if there's a gap between the last level we recorded and this segment, we need to fill it with
                        # a flat segment that holds the last level recorded
                        if start_beat_in_clock > beat_of_last_level_recorded:
                            durations.append(start_beat_in_clock - beat_of_last_level_recorded)
                            levels.append(levels[-1])
                            curve_shapes.append(0)

                        durations.append(end_beat_in_clock - start_beat_in_clock)
                        levels.append(param_change_segment.end_level)
                        curve_shapes.append(param_change_segment.curve_shape)

                        beat_of_last_level_recorded = end_beat_in_clock

                    # again, if we end the curve early, then we need to add a flat filler segment
                    if beat_of_last_level_recorded < note_start_beat + note_length:
                        durations.append(note_start_beat + note_length - beat_of_last_level_recorded)
                        levels.append(levels[-1])
                        curve_shapes.append(0)

                    # assign to specific variables for pitch and volume, otherwise put in a dictionary of extra params
                    if param == "pitch":
                        pitch = Envelope.from_levels_and_durations(levels, durations, curve_shapes)
                    elif param == "volume":
                        volume = Envelope.from_levels_and_durations(levels, durations, curve_shapes)
                    else:
                        extra_parameters[param] = Envelope.from_levels_and_durations(levels, durations, curve_shapes)
                else:
                    # assign to specific variables for pitch and volume, otherwise put in a dictionary of extra params
                    if param == "pitch":
                        pitch = note_info["parameter_start_values"]["pitch"]
                    elif param == "volume":
                        volume = note_info["parameter_start_values"]["volume"]
                    else:
                        extra_parameters[param] = note_info["parameter_start_values"][param]

            for instrument_part in performance.get_parts_by_instrument(instrument):
                # it'd be kind of weird for more than one part to have the same instrument, but if they did,
                # I suppose that each part should record the note
                instrument_part.new_note(
                    note_start_beat, note_length_sections if note_length_sections is not None else note_length,
                    pitch, volume, note_info["properties"]
                )

    @staticmethod
    def _resolve_time_stamp(time_stamp, clock, units):
        assert units in ("beats", "time")
        return time_stamp.beat_in_clock(clock) if units == "beats" else time_stamp.time_in_clock(clock)

    def stop_recording(self, which_performance=None, tempo_envelope_tolerance=0.001) -> Performance:
        transcription = None
        if which_performance is None:
            if len(self._transcriptions_in_progress) == 0:
                raise ValueError("Cannot stop recording performance, as none has been started!")
            transcription = self._transcriptions_in_progress.pop(0)
        else:
            for i, transcription in enumerate(self._transcriptions_in_progress):
                if transcription[0] == which_performance:
                    transcription = self._transcriptions_in_progress.pop(i)
                    break
            if transcription is None:
                raise ValueError("Cannot stop recording given performance, as it was never started!")

        recorded_performance, recording_clock, recording_start_beat, units = transcription
        if units == "beats":
            recorded_performance.tempo_envelope = recording_clock.extract_absolute_tempo_envelope(
                recording_start_beat, tolerance=tempo_envelope_tolerance
            )
        elif recording_clock.is_master():
            # recording time on master, so just copy the tempo envelope
            recorded_performance.tempo_envelope = TempoEnvelope()
        else:
            recorded_performance.tempo_envelope = recording_clock.parent.extract_absolute_tempo_envelope(
                recording_start_beat, tolerance=tempo_envelope_tolerance
            )
        return recorded_performance