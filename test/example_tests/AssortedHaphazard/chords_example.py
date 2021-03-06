from scamp import *

session = Session()
session.fast_forward_in_beats(float("inf"))

piano = session.new_part("piano")

session.start_transcribing()

# this makes the whole chord diamond noteheads
handle = piano.start_chord(([60, 56], 64, 69), 0.5, "notehead: diamond")

handle.change_pitch((62, 58, 60), (1/3, 1/3, 1/3), transition_curve_shape_or_shapes=(5, 5, 5))

engraving_settings.glissandi.control_point_policy = "split"

wait(2)
handle.end()
engraving_settings.glissandi.consider_non_extrema_control_points = True

# this gives separate noteheads for separate pitches
piano.play_chord((60, 64, 69), 0.5, 2.0, "noteheads: diamond / normal / cross")

# noteheads are assigned in the order of the pitch tuple given, not in order from low to high
# so here, middle C has a normal notehead, E has a diamond, and A has a cross
piano.play_chord((64, 60, 69), 0.5, 2.0, "noteheads: diamond / normal / cross")

# This line would throw an error, because the wrong number of noteheads is given for the chord
# piano.play_chord((64, 60, 69), 0.5, 2.0, "noteheads: diamond / normal")

session.wait(0)
performance = session.stop_transcribing()


def test_results():
    old_engraving_settings = engraving_settings.duplicate()
    engraving_settings.glissandi.control_point_policy = "split"
    engraving_settings.glissandi.consider_non_extrema_control_points = True
    out = (
        performance,
        performance.to_score()
    )
    engraving_settings.glissandi.control_point_policy = old_engraving_settings.glissandi.control_point_policy
    engraving_settings.glissandi.consider_non_extrema_control_points = \
        old_engraving_settings.glissandi.consider_non_extrema_control_points
    return out

