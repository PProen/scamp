from .settings import playback_settings
import logging

ABJAD_MINIMUM_VERSION = "3.0.0"


try:
    # first choice: import using an installed version of pyfluidsynth
    import fluidsynth
except (ImportError, AttributeError):
    # if this fails, use the local, tweaked copy that catches a possible attribute error
    # and loads up the local copy of the windows .dll if one can't be found on the system
    from .thirdparty import fluidsynth
except ImportError:
    # if we're here, it's probably because fluidsynth wasn't installed
    fluidsynth = None
    logging.warning("Fluidsynth could not be loaded; synth output will not be available.")

if fluidsynth is not None and playback_settings.default_audio_driver == "auto":
    print("Testing for working audio driver...")
    found_driver = False
    for driver in ['alsa', 'coreaudio', 'dsound', 'Direct Sound', 'oss', 'pulseaudio', 'jack', 'portaudio', 'sndmgr']:
        test_synth = fluidsynth.Synth()
        test_synth.start(driver=driver)
        if test_synth.audio_driver is not None:
            playback_settings.default_audio_driver = driver
            playback_settings.make_persistent()
            found_driver = True
            test_synth.delete()
            print("Found audio driver '{}'. This has been made the default, but it can be altered via "
                  "the playback settings.".format(driver))
            break
        test_synth.delete()
    if not found_driver:
        logging.warning("No working audio driver was found; synth output will not be available.")

try:
    from sf2utils.sf2parse import Sf2File
except ImportError:
    Sf2File = None
    logging.warning("sf2utils was not found; info about soundfont presets will not be available.")

try:
    import pythonosc
    import pythonosc.udp_client
    import pythonosc.dispatcher
    import pythonosc.osc_server
except ImportError:
    pythonosc = None
    logging.warning("pythonosc was not found; OSCScampInstrument will not function.")

try:
    import rtmidi
except ImportError:
    rtmidi = None
    logging.warning("python-rtmidi was not found; streaming midi input / output will not be available.")


def abjad():
    # we make this a function that returns the abjad module so that we don't have to load it unless we need it
    # (since it's kinda slow to load)
    try:
        import abjad as abjad_library
        if abjad_library.__version__ < ABJAD_MINIMUM_VERSION:
            logging.warning(
                "abjad version {} found, but version must be at least {}. "
                "Lilypond output will not be available".format(abjad_library.__version__, ABJAD_MINIMUM_VERSION)
            )
            abjad_library = None
    except ImportError:
        abjad_library = None
        logging.warning("abjad was not found; lilypond output will not be available.")
    return abjad_library


try:
    import pynput
except ImportError:
    pynput = None
    logging.warning("pynput was not found; mouse and keyboard input will not be available.")
