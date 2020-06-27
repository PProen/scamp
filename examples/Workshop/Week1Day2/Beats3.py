from scamp import *


s = Session(tempo=100, default_soundfont="beats")

s.print_default_soundfont_presets()

bass = s.new_part("bass shot")
snare = s.new_part("snare")


while True:
    s.tempo = 100
    pitch = 60
    
    while pitch < 80:  # Do this forever!
        bass.play_note(pitch, 1.0, 1)
        snare.play_note(pitch, 0.5, 1)
        wait(0.5)
        bass.play_note(pitch, 0.7, 0.5)
        snare.play_note(pitch, 0.5, 1)
        pitch += 5
        s.tempo *= 1.1