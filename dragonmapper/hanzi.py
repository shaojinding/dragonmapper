# -*- coding: utf-8 -*-
"""Identification and transliteration functions for Chinese characters."""

from __future__ import unicode_literals
import re

import zhon.cedict
import zhon.hanzi
import zhon.pinyin

import dragonmapper.data
from dragonmapper.transcriptions import (
    accented_to_numbered,
    pinyin_to_ipa,
    pinyin_to_zhuyin
)

try:
    str = unicode
except NameError:
    pass


UNKNOWN = 0
TRAD = TRADITIONAL = 1
SIMP = SIMPLIFIED = 2
BOTH = 3
MIXED = 4


_TRADITIONAL_CHARACTERS = set(list(zhon.cedict.traditional))
_SIMPLIFIED_CHARACTERS = set(list(zhon.cedict.simplified))
_SHARED_CHARACTERS = _TRADITIONAL_CHARACTERS.intersection(
    _SIMPLIFIED_CHARACTERS)
_ALL_CHARACTERS = zhon.cedict.all

_READING_SEPARATOR = '/'


def _load_data():
    """Load the word and character mapping data into a dictionary.

    In the data files, each line is formatted like this:
        HANZI   PINYIN_READING/PINYIN_READING

    So, lines need to be split by '\t' and then the Pinyin readings need to be
    split by '/'.

    """
    data = {}
    for name, file_name in (('words', 'hanzi_pinyin_words.tsv'),
                            ('characters', 'hanzi_pinyin_characters.tsv')):
        # Split the lines by tabs: [[hanzi, pinyin]...].
        lines = [line.split('\t') for line in
                 dragonmapper.data.load_data_file(file_name)]
        # Make a dictionary: {hanzi: [pinyin, pinyin]...}.
        data[name] = {hanzi: pinyin.split('/') for hanzi, pinyin in lines}
    return data

print("Loading word/character data files.")
_HANZI_PINYIN_MAP = _load_data()
_CHARACTERS = _HANZI_PINYIN_MAP['characters']
_WORDS = _HANZI_PINYIN_MAP['words']


def _get_hanzi(s):
    """Extract a string's Chinese characters."""
    return set(re.sub('[^%s]' % _ALL_CHARACTERS, '', s))


def identify(s):
    """Identify what kind of Chinese characters a string contains.

    *s* is a string to examine. The string's Chinese characters are tested to
    see if they are compatible with the Traditional or Simplified characters
    systems, compatible with both, or contain a mixture of Traditional and
    Simplified characters. The :data:`TRADITIONAL`, :data:`SIMPLIFIED`,
    :data:`BOTH`, or :data:`MIXED` constants are returned to indicate the
    string's identity. If *s* contains no Chinese characters, then :data:`NONE`
    is returned.

    All characters in a string that aren't found in the CC-CEDICT dictionary
    are ignored.

    Because the Traditional and Simplified Chinese character systems overlap, a
    string containing Simplified characters could identify as
    :data:`SIMPLIFIED` or :data:`BOTH` depending on if the characters are also
    Traditional characters. To make testing the identity of a string easier,
    the functions :func:`is_traditional` and :func:`is_simplified` are
    provided.

    """
    chinese = _get_hanzi(s)
    if not chinese:
        return UNKNOWN
    if chinese.issubset(_SHARED_CHARACTERS):
        return BOTH
    if chinese.issubset(_TRADITIONAL_CHARACTERS):
        return TRADITIONAL
    if chinese.issubset(_SIMPLIFIED_CHARACTERS):
        return SIMPLIFIED
    return MIXED


def has_chinese(s):
    """Check if a string has Chinese characters in it.

    This is a faster version of:
        >>> identify('foo') is not UNKNOWN

    """
    return bool(_get_hanzi(s))


def is_traditional(s):
    """Check if a string's Chinese characters are Traditional.

    This is equivalent to:
        >>> identify('foo') in (TRADITIONAL, BOTH)

    """
    return identify(s) in (TRADITIONAL, BOTH)


def is_simplified(s):
    """Check if a string's Chinese characters are Simplified.

    This is equivalent to:
        >>> identify('foo') in (SIMPLIFIED, BOTH)

    """
    return identify(s) in (SIMPLIFIED, BOTH)


def _hanzi_to_pinyin(hanzi):
    """Return the Pinyin reading for a Chinese word.

    If the given string *hanzi* matches a CC-CEDICT word, the return value is
    formatted like this: [WORD_READING1, WORD_READING2, ...]

    If the given string *hanzi* doesn't match a CC-CEDICT word, the return
    value is formatted like this: [[CHAR_READING1, CHAR_READING2 ...], ...]

    When returning character readings, if a character wasn't recognized, the
    original character is returned, e.g. [[CHAR_READING1, ...], CHAR, ...]

    """
    try:
        return _HANZI_PINYIN_MAP['words'][hanzi]
    except KeyError:
        return [_CHARACTERS.get(character, character) for character in hanzi]


def to_pinyin(s, delimiter=' ', all_readings=False, accented=True):
    """Convert a string's Chinese characters to Pinyin readings.

    *s* is a string containing Chinese characters. *accented* is a
    :data:`bool` indicating whether to return accented or numbered Pinyin
    readings.

    *delimiter* is the character used to indicate word boundaries in *hanzi*.
    This is used to differentiate between words and characters so that a more
    accurate Pinyin reading can be returned.

    *all_readings* is a :data:`bool` indicating whether or not to return all
    possible readings in the case of words/characters that have multiple
    readings.

    Characters not recognized as Chinese are left untouched.

    """
    hanzi = s
    pinyin = ''

    # Process the given string.
    while hanzi:

        # Get the next match in the given string.
        match = re.search('[^%s%s]+' % (delimiter, zhon.hanzi.punctuation),
                          hanzi)

        # There are no more matches, but the string isn't finished yet.
        if match is None and hanzi:
            pinyin += hanzi
            break

        match_start, match_end = match.span()

        # Process the punctuation marks that occur before the match.
        if match_start > 0:
            pinyin += hanzi[0:match_start]

        # Get the Chinese word/character readings.
        readings = _hanzi_to_pinyin(match.group())

        # Process the returned word readings.
        if match.group() in _WORDS:
            if all_readings:
                reading = '[%s]' % _READING_SEPARATOR.join(readings)
            else:
                reading = readings[0]
            pinyin += reading

        # Process the returned character readings.
        else:
            # Process each character individually.
            for character in readings:
                # Don't touch unrecognized characters.
                if isinstance(character, str):
                    pinyin += character
                # Format multiple readings.
                elif isinstance(character, list) and all_readings:
                        pinyin += '[%s]' % _READING_SEPARATOR.join(character)
                # Select and format the most common reading.
                elif isinstance(character, list) and not all_readings:
                    # Add an apostrophe to separate syllables.
                    if (pinyin and character[0][0] in zhon.pinyin.vowels and
                            pinyin[-1] in zhon.pinyin.lowercase):
                        pinyin += "'"
                    pinyin += character[0]

        # Move ahead in the given string.
        hanzi = hanzi[match_end:]

    if accented:
        return pinyin
    else:
        return accented_to_numbered(pinyin)


def to_zhuyin(s, delimiter=' ', all_readings=False):
    """Convert a string's Chinese characters to Zhuyin readings."""
    numbered_pinyin = to_pinyin(s, delimiter, all_readings, False)
    zhuyin = pinyin_to_zhuyin(numbered_pinyin)
    return zhuyin


def to_ipa(s, delimiter=' ', all_readings=False):
    """Convert a string's Chinese characters to IPA."""
    numbered_pinyin = to_pinyin(s, delimiter, all_readings, False)
    ipa = pinyin_to_ipa(numbered_pinyin)
    return ipa
