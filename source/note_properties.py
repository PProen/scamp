from playcorder.playback_adjustments import *
from playcorder.utilities import SavesToJSON
from playcorder.settings import playback_settings
from copy import deepcopy
import logging


class NotePropertiesDictionary(dict, SavesToJSON):

    def __init__(self, **kwargs):
        if "articulations" not in kwargs:
            kwargs["articulations"] = []
        if "noteheads" not in kwargs:
            kwargs["noteheads"] = ["normal"]
        if "notations" not in kwargs:
            kwargs["notations"] = []
        if "text" not in kwargs:
            kwargs["text"] = []
        if "playback adjustments" not in kwargs:
            kwargs["playback adjustments"] = []
        if "temp" not in kwargs:
            # this is a throwaway directory that is not kept when we save to json
            kwargs["temp"] = {}

        super().__init__(**kwargs)

    @classmethod
    def from_unknown_format(cls, properties):
        """
        Interprets a number of data formats as a NotePropertiesDictionary
        :param properties: can be of several formats:
            - a dictionary of note properties, using the standard format
            - a list of properties, each of which is a string or a NotePlaybackAdjustment. Each string may be
            colon-separated key / value pair (e.g. "articulation: staccato"), or simply the value (e.g. "staccato"),
            in which case an attempt is made to guess the key.
            - a string of comma-separated properties, which just gets split and treated like a list
            - a NotePlaybackAdjustment, which just put in a list and treated like a list input
        :return: a newly constructed NotePropertiesDictionary
        """
        if isinstance(properties, str):
            return NotePropertiesDictionary.from_string(properties)
        elif isinstance(properties, NotePlaybackAdjustment):
            return NotePropertiesDictionary.from_list([properties])
        elif isinstance(properties, list):
            return NotePropertiesDictionary.from_list(properties)
        elif properties is None:
            return cls()
        else:
            assert isinstance(properties, dict), "Properties argument wrongly formatted."
            return cls(**properties)

    @classmethod
    def from_string(cls, properties_string):
        assert isinstance(properties_string, str)
        return NotePropertiesDictionary.from_list(properties_string.split(","))

    @classmethod
    def from_list(cls, properties_list):
        assert isinstance(properties_list, (list, tuple))
        properties_dict = cls()

        for note_property in properties_list:
            if isinstance(note_property, NotePlaybackAdjustment):
                properties_dict["playback adjustments"].append(note_property)
            elif isinstance(note_property, str):
                # if there's a colon, it represents a key / value pair, e.g. "articulation: staccato"
                if ":" in note_property:
                    colon_index = note_property.index(":")
                    key, value = note_property[:colon_index].replace(" ", ""), note_property[colon_index+1:].strip()
                    if "articulation" in key:
                        if value in PlaybackDictionary.all_articulations:
                            properties_dict["articulations"].append(value)
                        else:
                            logging.warning("Articulation {} not understood".format(value))

                    if "noteheads" in key:
                        properties_dict["noteheads"] = []
                        for notehead in value.split("/"):
                            notehead = notehead.strip()
                            if notehead in PlaybackDictionary.all_noteheads:
                                properties_dict["noteheads"].append(notehead)
                            else:
                                properties_dict["noteheads"].append("normal")
                                logging.warning("Notehead {} not understood".format(notehead))

                    elif "notehead" in key:
                        if value in PlaybackDictionary.all_noteheads:
                            properties_dict["noteheads"] = [value]
                        else:
                            logging.warning("Notehead {} not understood".format(value))

                    if "notation" in key:
                        if value in PlaybackDictionary.all_notations:
                            properties_dict["notations"].append(value)
                        else:
                            logging.warning("Notation {} not understood".format(value))

                else:
                    note_property = note_property.replace(" ", "")
                    # otherwise, we try to figure out what kind of property we're dealing with
                    if note_property in PlaybackDictionary.all_articulations:
                        properties_dict["articulations"].append(note_property)
                    elif note_property in PlaybackDictionary.all_noteheads:
                        properties_dict["noteheads"] = [note_property]
                    elif note_property in PlaybackDictionary.all_notations:
                        properties_dict["notations"].append(note_property)

        return properties_dict

    @property
    def articulations(self):
        return self["articulations"]

    @articulations.setter
    def articulations(self, value):
        self["articulations"] = value

    @property
    def noteheads(self):
        return self["noteheads"]

    @noteheads.setter
    def noteheads(self, value):
        self["noteheads"] = value

    @property
    def notations(self):
        return self["notations"]

    @notations.setter
    def notations(self, value):
        self["notations"] = value

    @property
    def text(self):
        return self["text"]

    @text.setter
    def text(self, value):
        self["text"] = value

    @property
    def playback_adjustments(self):
        return self["playback adjustments"]

    @playback_adjustments.setter
    def playback_adjustments(self, value):
        self["playback_adjustments"] = value

    def starts_tie(self):
        return "_starts_tie" in self and self["_starts_tie"]

    def ends_tie(self):
        return "_ends_tie" in self and self["_ends_tie"]

    @property
    def temp(self):
        return self["temp"]

    def apply_playback_adjustments(self, pitch, volume, length, include_notation_derived=True):
        """
        Applies both explicit and (if flag is set) derived playback adjustments to the given pitch, volume, and length
        :param pitch: unadjusted pitch
        :param volume: unadjusted volume
        :param length: unadjusted length
        :param include_notation_derived: if true, include adjustments based on notations like staccato, by searching
        the playback_settings.adjustments dictionary
        :return: adjusted pitch, volume and length
        """
        # first apply all of the explicit playback adjustments
        for adjustment in self.playback_adjustments:
            assert isinstance(adjustment, NotePlaybackAdjustment)
            pitch, volume, length = adjustment.adjust_parameters(pitch, volume, length)

        if include_notation_derived:
            for notation_category in ["articulations", "noteheads", "notations"]:
                for applied_notation in self[notation_category]:
                    notation_derived_adjustment = playback_settings.adjustments.get(applied_notation)
                    if notation_derived_adjustment is not None:
                        assert isinstance(notation_derived_adjustment, NotePlaybackAdjustment)
                        pitch, volume, length = notation_derived_adjustment.adjust_parameters(pitch, volume, length)

        return pitch, volume, length

    def mergeable_with(self, other_properties_dict):
        assert isinstance(other_properties_dict, NotePropertiesDictionary)
        return self.articulations == other_properties_dict.articulations and \
               self.notations == other_properties_dict.notations and \
               self.playback_adjustments == other_properties_dict.playback_adjustments and \
               self.text == other_properties_dict.text

    def to_json(self):
        json_friendly_dict = deepcopy(self)
        json_friendly_dict["playback adjustments"] = [x.to_json() for x in self.playback_adjustments]
        del json_friendly_dict["temp"]

        # remove entries that contain no information for conciseness. They will be reconstructed when reloading.
        if len(self.articulations) == 0:
            del json_friendly_dict["articulations"]
        if len(self.noteheads) == 1 and self.noteheads[0] == "normal":
            del json_friendly_dict["noteheads"]
        if len(self.notations) == 0:
            del json_friendly_dict["notations"]
        if len(self.text) == 0:
            del json_friendly_dict["text"]
        if len(self.playback_adjustments) == 0:
            del json_friendly_dict["playback adjustments"]

        return json_friendly_dict

    @classmethod
    def from_json(cls, json_object):
        # convert all adjustments from dictionaries to NotePlaybackAdjustments
        json_object["playback adjustments"] = [NotePlaybackAdjustment.from_json(x)
                                               for x in json_object["playback adjustments"]]
        return cls(**json_object)
