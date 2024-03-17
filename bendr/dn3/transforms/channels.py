from collections import OrderedDict

import numpy as np
import torch
from mne.io.constants import FIFF

# Not crazy about this approach..
from mne.utils._bunch import NamedInt

# Careful this doesn't overlap with future additions to MNE, might have to coordinate
DEEP_1010_SCALE_CH = NamedInt("DN3_DEEP1010_SCALE_CH", 3000)
DEEP_1010_EXTRA_CH = NamedInt("DN3_DEEP1010_EXTRA_CH", 3001)

_LEFT_NUMBERS = list(reversed(range(1, 9, 2)))
_RIGHT_NUMBERS = list(range(2, 10, 2))

_EXTRA_CHANNELS = 5

DEEP_1010_CHS_LISTING = [
    # EEG
    "NZ",
    "FP1",
    "FPZ",
    "FP2",
    "AF7",
    "AF3",
    "AFZ",
    "AF4",
    "AF8",
    "F9",
    *[f"F{n}" for n in _LEFT_NUMBERS],
    "FZ",
    *[f"F{n}" for n in _RIGHT_NUMBERS],
    "F10",
    "FT9",
    "FT7",
    *[f"FC{n}" for n in _LEFT_NUMBERS[1:]],
    "FCZ",
    *[f"FC{n}" for n in _RIGHT_NUMBERS[:-1]],
    "FT8",
    "FT10",
    "T9",
    "T7",
    "T3",
    *[f"C{n}" for n in _LEFT_NUMBERS[1:]],
    "CZ",
    *[f"C{n}" for n in _RIGHT_NUMBERS[:-1]],
    "T4",
    "T8",
    "T10",
    "TP9",
    "TP7",
    *[f"CP{n}" for n in _LEFT_NUMBERS[1:]],
    "CPZ",
    *[f"CP{n}" for n in _RIGHT_NUMBERS[:-1]],
    "TP8",
    "TP10",
    "P9",
    "P7",
    "T5",
    *[f"P{n}" for n in _LEFT_NUMBERS[1:]],
    "PZ",
    *[f"P{n}" for n in _RIGHT_NUMBERS[:-1]],
    "T6",
    "P8",
    "P10",
    "PO7",
    "PO3",
    "POZ",
    "PO4",
    "PO8",
    "O1",
    "OZ",
    "O2",
    "IZ",
    # EOG
    "VEOGL",
    "VEOGR",
    "HEOGL",
    "HEOGR",
    # Ear clip references
    "A1",
    "A2",
    "REF",
    # SCALING
    "SCALE",
    # Extra
    *[f"EX{n}" for n in range(1, _EXTRA_CHANNELS + 1)],
]
EEG_INDS = list(range(DEEP_1010_CHS_LISTING.index("VEOGL")))
EOG_INDS = [
    DEEP_1010_CHS_LISTING.index(ch) for ch in ["VEOGL", "VEOGR", "HEOGL", "HEOGR"]
]
REF_INDS = [DEEP_1010_CHS_LISTING.index(ch) for ch in ["A1", "A2", "REF"]]
EXTRA_INDS = list(
    range(len(DEEP_1010_CHS_LISTING) - _EXTRA_CHANNELS, len(DEEP_1010_CHS_LISTING))
)
SCALE_IND = -len(EXTRA_INDS) + len(DEEP_1010_CHS_LISTING)
_NUM_EEG_CHS = (
    len(DEEP_1010_CHS_LISTING) - len(EOG_INDS) - len(REF_INDS) - len(EXTRA_INDS) - 1
)

DEEP_1010_CH_TYPES = (
    ([FIFF.FIFFV_EEG_CH] * _NUM_EEG_CHS)
    + ([FIFF.FIFFV_EOG_CH] * len(EOG_INDS))
    + ([FIFF.FIFFV_EEG_CH] * len(REF_INDS))
    + [DEEP_1010_SCALE_CH]
    + ([DEEP_1010_EXTRA_CH] * _EXTRA_CHANNELS)
)


def _deep_1010(map, names, eog, ear_ref, extra):
    for i, ch in enumerate(names):
        if ch not in eog and ch not in ear_ref and ch not in extra:
            try:
                map[i, DEEP_1010_CHS_LISTING.index(str(ch).upper())] = 1.0
            except ValueError:
                print(
                    f"Warning: channel {ch} not found in standard layout. Skipping..."
                )
                continue

    # Normalize for when multiple values are mapped to single location
    summed = map.sum(axis=0)[np.newaxis, :]
    mapping = torch.from_numpy(
        np.divide(map, summed, out=np.zeros_like(map), where=summed != 0)
    ).float()
    mapping.requires_grad_(False)
    return mapping


def _valid_character_heuristics(name, informative_characters):
    possible = "".join(c for c in name.upper() if c in informative_characters).replace(
        " ", ""
    )
    if possible == "":
        print(
            f"Could not use channel {name}. Could not resolve its true label, rename first."
        )
        return None
    return possible


def _check_num_and_get_types(type_dict: OrderedDict):
    type_lists = list()
    for ch_type, max_num in zip(
        ("eog", "ref"), (len(EOG_INDS), len(REF_INDS)), strict=False
    ):
        channels = [ch_name for ch_name, _type in type_dict.items() if _type == ch_type]

        for name in channels[max_num:]:
            print(
                f"Losing assumed {ch_type} channel {name} because there are too many."
            )
            type_dict[name] = None
        type_lists.append(channels[:max_num])
    return type_lists[0], type_lists[1]


def _heuristic_eog_resolution(eog_channel_name):
    return _valid_character_heuristics(eog_channel_name, "VHEOGLR")


def _heuristic_ref_resolution(ref_channel_name: str):
    ref_channel_name = ref_channel_name.replace("EAR", "")
    ref_channel_name = ref_channel_name.replace("REF", "")
    if ref_channel_name.find("A1") != -1:
        return "A1"
    elif ref_channel_name.find("A2") != -1:
        return "A2"

    if ref_channel_name.find("L") != -1:
        return "A1"
    elif ref_channel_name.find("R") != -1:
        return "A2"
    return "REF"


def _heuristic_eeg_resolution(eeg_ch_name: str):
    eeg_ch_name = eeg_ch_name.upper()
    # remove some common garbage
    eeg_ch_name = eeg_ch_name.replace("EEG", "")
    eeg_ch_name = eeg_ch_name.replace("REF", "")
    informative_characters = set(
        [c for name in DEEP_1010_CHS_LISTING[:_NUM_EEG_CHS] for c in name]
    )
    return _valid_character_heuristics(eeg_ch_name, informative_characters)


def _likely_eeg_channel(name):
    if name is not None:
        for ch in DEEP_1010_CHS_LISTING[:_NUM_EEG_CHS]:
            if ch in name.upper():
                return True
    return False


def _heuristic_resolution(old_type_dict: OrderedDict):
    resolver = {
        "eeg": _heuristic_eeg_resolution,
        "eog": _heuristic_eog_resolution,
        "ref": _heuristic_ref_resolution,
        "extra": lambda x: x,
        None: lambda x: x,
    }

    new_type_dict = OrderedDict()

    for old_name, ch_type in old_type_dict.items():
        if ch_type is None:
            new_type_dict[old_name] = None
            continue

        new_name = resolver[ch_type](old_name)
        if new_name is None:
            new_type_dict[old_name] = None
        else:
            while new_name in new_type_dict.keys():
                print(
                    f"Deep1010 Heuristics resulted in duplicate entries for {new_name}, incrementing name, but will be lost "
                    "in mapping"
                )
                new_name = new_name + "-COPY"
            new_type_dict[new_name] = old_type_dict[old_name]

    assert len(new_type_dict) == len(old_type_dict)
    return new_type_dict


def map_named_channels_deep_1010(
    channel_names: list, EOG=None, ear_ref=None, extra_channels=None
):
    """
    Maps channel names to the Deep1010 format, will automatically map EOG and extra channels if they have been
    named according to standard convention. Otherwise provide as keyword arguments.

    Parameters
    ----------
    channel_names : list
                   List of channel names from dataset
    EOG : list, str
         Must be a single channel name, or left and right EOG channels, optionally vertical L/R then horizontal
         L/R for four channels.
    ear_ref : Optional, str, list
               One or two channels to be used as references. If two, should be left and right in that order.
    extra_channels : list, None
                     Up to 6 extra channels to include. Currently not standardized, but could include ECG, respiration,
                     EMG, etc.

    Returns
    -------
    mapping : torch.Tensor
              Mapping matrix from previous channel sequence to Deep1010.
    """
    map = np.zeros((len(channel_names), len(DEEP_1010_CHS_LISTING)))

    if isinstance(EOG, str):
        EOG = [EOG] * 4
    elif len(EOG) == 1:
        EOG = EOG * 4
    elif EOG is None or len(EOG) == 0:
        EOG = []
    elif len(EOG) == 2:
        EOG = EOG * 2
    else:
        assert len(EOG) == 4
    for eog_map, eog_std in zip(EOG, EOG_INDS, strict=False):
        try:
            map[channel_names.index(eog_map), eog_std] = 1.0
        except ValueError:
            raise ValueError(f"EOG channel {eog_map} not found in provided channels.")

    if isinstance(ear_ref, str):
        ear_ref = [ear_ref] * 2
    elif ear_ref is None:
        ear_ref = []
    else:
        assert len(ear_ref) <= len(REF_INDS)
    for ref_map, ref_std in zip(ear_ref, REF_INDS, strict=False):
        try:
            map[channel_names.index(ref_map), ref_std] = 1.0
        except ValueError:
            raise ValueError(
                f"Reference channel {ref_map} not found in provided channels."
            )

    if isinstance(extra_channels, str):
        extra_channels = [extra_channels]
    elif extra_channels is None:
        extra_channels = []
    assert len(extra_channels) <= _EXTRA_CHANNELS
    for ch, place in zip(extra_channels, EXTRA_INDS, strict=False):
        if ch is not None:
            map[channel_names.index(ch), place] = 1.0

    return _deep_1010(map, channel_names, EOG, ear_ref, extra_channels)


def map_dataset_channels_deep_1010(channels: np.ndarray, exclude_stim=True):
    """
    Maps channels as stored by a :any:`DN3ataset` to the Deep1010 format, will automatically map EOG and extra channels
    by type.

    Parameters
    ----------
    channels : np.ndarray
               Channels that remain a 1D sequence (they should not have been projected into 2 or 3D grids) of name and
               type. This means the array has 2 dimensions:
               ..math:: N_{channels} \by 2
               With the latter dimension containing name and type respectively, as is constructed by default in most
               cases.
    exclude_stim : bool
                   This option allows the stim channel to be added as an *extra* channel. The default (True) will not do
                   this, and it is very rare if ever where this would be needed.

    Warnings
    --------
    If for some reason the stim channel is labelled with a label from the `DEEP_1010_CHS_LISTING` it will be included
    in that location and result in labels bleeding into the observed data.

    Returns
    -------
    mapping : torch.Tensor
              Mapping matrix from previous channel sequence to Deep1010.
    """
    if len(channels.shape) != 2 or channels.shape[1] != 2:
        raise ValueError(
            "Deep1010 Mapping: channels must be a 2 dimensional array with dim0 = num_channels, dim1 = 2."
            f" Got {channels.shape}"
        )
    channel_types = OrderedDict()

    # Use this for some semblance of order in the "extras"
    extra = [None for _ in range(_EXTRA_CHANNELS)]
    extra_idx = 0

    for name, ch_type in channels:
        # Annoyingly numpy converts them to strings...
        ch_type = int(ch_type)
        if ch_type == FIFF.FIFFV_EEG_CH and _likely_eeg_channel(name):
            channel_types[name] = "eeg"
        elif ch_type == FIFF.FIFFV_EOG_CH or name in [
            DEEP_1010_CHS_LISTING[idx] for idx in EOG_INDS
        ]:
            channel_types[name] = "eog"
        elif ch_type == FIFF.FIFFV_STIM_CH:
            if exclude_stim:
                channel_types[name] = None
                continue
            # if stim, always set as last extra
            channel_types[name] = "extra"
            extra[-1] = name
        elif (
            "REF" in name.upper()
            or "A1" in name.upper()
            or "A2" in name.upper()
            or "EAR" in name.upper()
        ):
            channel_types[name] = "ref"
        else:
            if extra_idx == _EXTRA_CHANNELS - 1 and not exclude_stim:
                print(f"Stim channel overwritten by {name} in Deep1010 mapping.")
            elif extra_idx == _EXTRA_CHANNELS:
                print(f"No more room in extra channels for {name}")
                continue
            channel_types[name] = "extra"
            extra[extra_idx] = name
            extra_idx += 1

    revised_channel_types = _heuristic_resolution(channel_types)
    eog, ref = _check_num_and_get_types(revised_channel_types)

    return map_named_channels_deep_1010(
        list(revised_channel_types.keys()), eog, ref, extra
    )


def stringify_channel_mapping(original_names: list, mapping: np.ndarray):
    result = ""
    heuristically_mapped = list()

    def match_old_new_idx(old_idx, new_idx_set: list):
        new_names = [
            DEEP_1010_CHS_LISTING[i]
            for i in np.nonzero(mapping[old_idx, :])[0]
            if i in new_idx_set
        ]
        return ",".join(new_names)

    for inds, label in zip(
        [list(range(_NUM_EEG_CHS)), EOG_INDS, REF_INDS, EXTRA_INDS],
        ["EEG", "EOG", "REF", "EXTRA"],
        strict=False,
    ):
        result += f"{label} (original(new)): "
        for idx, name in enumerate(original_names):
            news = match_old_new_idx(idx, inds)
            if len(news) > 0:
                result += f"{name}({news}) "
                if news != name.upper():
                    heuristically_mapped.append(f"{name}({news}) ")
        result += "\n"

    result += "Heuristically Assigned: " + " ".join(heuristically_mapped)

    return result


def make_map(in_channels, out_channels, force_mapping=False):
    """
    Make a mapping of the matching in_channels to the appropriate out_channels.

    Parameters
    ----------
    in_channels: ndarray
             An N x 2 array of channels as typically returned by a :any:`DN3ataset`
    out_channels: ndarray
            An M x 2 array of channels as typically returned by a :any:`DN3ataset`
    force_mapping: bool
                   If set to True, this will return a mapping even if subset and superset are the same (returns
                   identity matrix). Otherwise returns None
    Returns
    -------
    mapping
    """
    # Ignore the channel types, might be worth reconsidering this.
    in_channels = in_channels[:, 0]
    out_channels = out_channels[:, 0]
    if len(out_channels) == len(in_channels) and np.all(out_channels == in_channels):
        return None
    mapping = torch.zeros(len(in_channels), len(out_channels))
    _, in_ind, out_ind = np.intersect1d(in_channels, out_channels, return_indices=True)
    mapping[in_ind, out_ind] = 1
    return mapping
