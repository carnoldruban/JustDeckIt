import logging

# Configure logging for this module.
# In a larger application, this might be configured centrally.
# Using print for now for tool compatibility, but logging is better practice.
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG) # Or use INFO as default
# handler = logging.StreamHandler()
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)
# logger.propagate = False # Prevent duplicate logging if root logger is also configured


# --- Configuration & Constants for Parsing ---

# General keywords for card ranks. These are broad to catch common speech.
# The VALUE_WORD_TO_CARD map provides more specific (and misheard) mappings.
CARD_KEYWORDS = [
    "ace", "king", "queen", "jack", "ten", "nine", "eight", "seven",
    "six", "five", "four", "three", "two", "one" # "one" often for Ace, but handled by VALUE_WORD_TO_CARD
]

# Keywords for suits, mapping various spoken forms (including common mispronunciations)
# to a single character representation (S, H, D, C).
SUIT_KEYWORDS = {
    "spade": "S", "spades": "S", "speed": "S", "spaid": "S", "spaids": "S", "spay": "S",
    "spayde": "S", "paid": "S", "slade": "S", "space": "S", "spake": "S", "spate": "S",
    "sped": "S", "spied": "S", "sprayed": "S", "spud": "S", "spurred": "S", "stade": "S",
    "staid": "S", "stayed": "S", "suede": "S", "swayed": "S", "spader": "S", "spain": "S",
    "spey": "S", "speyer": "S", "said": "S", # Added "said" as it's a common mishearing for spade

    "heart": "H", "hearts": "H", "hart": "H", "hard": "H", "harts": "H", "hot": "H",
    "art": "H", "cart": "H", "carte": "H", "chart": "H", "dart": "H", "haar": "H",
    "hark": "H", "harl": "H", "harm": "H", "haro": "H", "harp": "H", "harped": "H",
    "harsh": "H", "hearth": "H", "hearty": "H", "hopped": "H", "mart": "H", "part": "H",
    "tart": "H", "harn": "H", "hott": "H", "bart": "H", "harte": "H",

    "diamond": "D", "diamonds": "D", "dice": "D", "dime": "D", "dimond": "D", "damon": "D",

    "club": "C", "clubs": "C", "clover": "C", "clovers": "C", "clab": "C", "clabs": "C",
    "clav": "C", "clubbed": "C", "cluck": "C", "clung": "C", "clutch": "C", "cub": "C",
    "clubby": "C", "clum": "C", "clove": "C" # Added "clove"
}

# Mapping of rank spoken words (including many variations and common mishearings)
# to the canonical string representation of the rank (e.g., "A", "K", "10", "2").
VALUE_WORD_TO_CARD = {
    "ace": "A", "yes": "A", "is": "A", "ass": "A", "aise": "A", "base": "A", "brace": "A",
    "case": "A", "chace": "A", "dace": "A", "face": "A", "grace": "A", "lace": "A", "mace": "A",
    "pace": "A", "place": "A", "race": "A", "space": "A", "trace": "A", "vase": "A", "chase": "A",
    "graisse": "A", "praiss": "A", "saice": "A", "wace": "A", "east": "A", # Added "east"

    "king": "K", "k": "K", "kin": "K", "bing": "K", "ching": "K", "cling": "K", "ding": "K",
    "ging": "K", "hing": "K", "jing": "K", "kang": "K", "kick": "K", "kier": "K", "kill": "K",
    "kings": "K", "kip": "K", "kir": "K", "kis": "K", "kiss": "K", "kitsch": "K", "kitt": "K",
    "kling": "K", "ling": "K", "ming": "K", "qing": "K", "ring": "K", "shing": "K", "sing": "K",
    "thing": "K", "ting": "K", "wing": "K", "wring": "K", "zing": "K", "kibbe": "K", "kid": "K",
    "kidd": "K", "kish": "K", "kit": "K", "kung": "K", "kyd": "K", "ping": "K", "singh": "K",

    "queen": "Q", "q": "Q", "que": "Q", "careen": "Q", "clean": "Q", "corinne": "Q", "keen": "Q",
    "kuan": "Q", "quin": "Q", "wean": "Q", "quina": "Q", "kean": "Q", "keene": "Q", "queens": "Q",
    "quine": "Q", "wien": "Q", "quinn": "Q", # Added "quinn"

    "jack": "J", "j": "J", "jak": "J", "dak": "J", "hack": "J", "jab": "J", "jacked": "J",
    "jacko": "J", "jacks": "J", "jacky": "J", "jake": "J", "jam": "J", "jamb": "J", "jann": "J",
    "jazz": "J", "jerk": "J", "jock": "J", "joke": "J", "juke": "J", "knack": "J", "lac": "J",
    "lack": "J", "lak": "J", "mac": "J", "mack": "J", "mak": "J", "pac": "J", "pack": "J",
    "rack": "J", "sac": "J", "sack": "J", "shack": "J", "tack": "J", "whack": "J", "wrack": "J",
    "yak": "J", "jass": "J", "wack": "J", "back": "J", "geck": "J", "yack": "J",

    "ten": "10", "t": "10", "ben": "10", "chen": "10", "den": "10", "hen": "10", "jen": "10",
    "ken": "10", "men": "10", "pen": "10", "sten": "10", "tan": "10", "tear": "10", "tec": "10",
    "tech": "10", "ted": "10", "teen": "10", "tell": "10", "tench": "10", "tend": "10", "tenor": "10",
    "tens": "10", "tense": "10", "tent": "10", "tenth": "10", "tet": "10", "tete": "10", "then": "10",
    "tin": "10", "tine": "10", "ton": "10", "tonne": "10", "toon": "10", "town": "10", "tune": "10",
    "turn": "10", "venn": "10", "wen": "10", "when": "10", "yen": "10", "zen": "10", "benne": "10",
    "tenner": "10", "fenn": "10", "lehn": "10", "penn": "10", "sen": "10", "tone": "10", "tyne": "10", "wren": "10",

    "nine": "9", "n": "9", "niner": "9", "dine": "9", "fein": "9", "fine": "9", "gneiss": "9",
    "hine": "9", "jain": "9", "knife": "9", "knight": "9", "known": "9", "line": "9", "mine": "9",
    "nene": "9", "night": "9", "nines": "9", "ninth": "9", "nite": "9", "none": "9", "noon": "9",
    "noun": "9", "nun": "9", "pine": "9", "shine": "9", "sign": "9", "sine": "9", "thine": "9",
    # "tine": "9", # "tine" is already mapped to 10, prefer specific over ambiguous
    "vine": "9", "whine": "9", "wine": "9", "zine": "9", "heine": "9", "nan": "9", "nice": "9",
    "nile": "9", "rhein": "9", "rhine": "9", # "tyne": "9", also mapped to 10

    "eight": "8", "e": "8", "ate": "8", "hate": "8", "freight": "8", "gate": "8", "great": "8", # Added more for "eight"
    "ait": "8", "eights": "8", "eighth": "8", "eta": "8", "freight": "8", "heit": "8",
    "kate": "8", "late": "8", "mate": "8", "nate": "8", "pate": "8", "plate": "8",
    "rate": "8", "skate": "8", "slate": "8", "state": "8", "straight": "8", "tait": "8",
    "tate": "8", "trait": "8", "wait": "8", "weight": "8", "yate": "8", "yates": "8",

    "seven": "7", "heaven": "7", "leaven": "7", "levan": "7", "session": "7", "sevens": "7",
    "seventh": "7", "sevin": "7", "devon": "7", "seton": "7", # Added "seton"

    "six": "6", "sex": "6", "chicks": "6", "dicks": "6", "fix": "6", "kicks": "6", "knicks": "6",
    "licks": "6", "mix": "6", "nicks": "6", "nix": "6", "picks": "6", "pix": "6", "ricks": "6",
    "rix": "6", "sacks": "6", "sacs": "6", "sakes": "6", "sax": "6", "seeks": "6", "sic": "6",
    "sick": "6", "sicker": "6", "sikes": "6", "sikhs": "6", "silks": "6", "since": "6", "sinks": "6",
    "sips": "6", "sis": "6", "sits": "6", "sixth": "6", "slicks": "6", "soaks": "6", "socks": "6",
    "sox": "6", "sticks": "6", "styx": "6", "sucks": "6", "sykes": "6", "ticks": "6", "tics": "6",
    "wicks": "6", "dix": "6", "hicks": "6", "ickes": "6", "sachs": "6", "saxe": "6",

    "five": "5", "fiv": "5", "arrive": "5", "dive": "5", "fein": "5", "feis": "5", "fight": "5",
    "file": "5", "fine": "5", "fite": "5", "fives": "5", "hive": "5", "jive": "5", "live": "5",
    "fike": "5", "fyke": "5", "phyle": "5", "shive": "5", "fife": "5", "fire": "5",

    "four": "4", "for": "4", "fore": "4", "boar": "4", "boer": "4", "bore": "4", "chore": "4",
    "cor": "4", "core": "4", "corps": "4", "door": "4", "fair": "4", "fall": "4", "far": "4",
    "fare": "4", "fawn": "4", "fear": "4", "fier": "4", "floor": "4", "flor": "4", "fob": "4",
    "fop": "4", "fora": "4", "foray": "4", "force": "4", "forge": "4", "fork": "4", "form": "4",
    "fort": "4", "fought": "4", "fours": "4", "fourth": "4", "hoar": "4", "lor": "4", "lore": "4",
    "mohr": "4", "mor": "4", "nor": "4", "pore": "4", "pour": "4", "roar": "4", "shore": "4",
    "soar": "4", "sore": "4", "thor": "4", "tor": "4", "tore": "4", "torr": "4", "war": "4",
    "whore": "4", "wore": "4", "yore": "4", "your": "4", "faught": "4", "bohr": "4", "dore": "4",
    "dorr": "4", "faure": "4", "ford": "4", "forth": "4", "gore": "4", "hoare": "4", "more": "4", "pharr": "4",

    "three": "3", "tree": "3", "bree": "3", "cree": "3", "free": "3", "pree": "3", "prix": "3",
    "shri": "3", "sri": "3", "threes": "3", "threw": "3", "through": "3", "throw": "3", "thru": "3",
    "brea": "3", "brie": "3", "thee": "3", # Added "thee"

    "two": "2", "too": "2", "to": "2", "do": "2", "tu": "2", "due": "2", "dew": "2", # Added "due", "dew"

    # "one" can be ambiguous with Ace ("A one" vs "Ace one").
    # Ace is often just "Ace" or a mishearing like "yes".
    # "one" as rank "1" is not standard in Blackjack rank strings (usually "A").
    # If "one" is meant for Ace, it's already covered by "ace" and its variants.
    # If "one" is meant for a specific card value (like a 1 point card if Ace is 11),
    # this parser is for rank identification, not value assignment beyond standard ranks.
    # For now, mapping "one" to "A" if it's a common way users might refer to Ace.
    "one": "A", "once": "A", # Re-evaluate if "one" should be separate or if Ace is always "Ace"
}

# Keywords for commands (e.g., starting a new round).
ROUND_START_KEYWORDS = [
    "new round", "next round", "round", "next", "new", "around", "bound", "browned",
    "crowned", "downed", "drowned", "found", "frowned", "ground", "hound", "mound",
    "rained", "reigned", "reined", "rind", "rounder", "rounds", "roused", "sound",
    "wound", "rund", "pound", "rand", "necked", "necks", "nest", "sexed", "text",
    "vexed", "nixed", "gnu", "knew", "nu"
]

def parse_cards_from_text(text_input: str) -> list[tuple[str, str]]:
    """
    Extracts card rank and suit representations from a line of recognized speech.

    The method attempts to identify card mentions like "Ace of Spades", "King Hearts",
    "Ten Clubs", etc., handling various spoken forms and some common mispronunciations
    defined in `VALUE_WORD_TO_CARD` and `SUIT_KEYWORDS`.

    Args:
        text_input (str): The text string transcribed from speech.

    Returns:
        list[tuple[str, str]]: A list of tuples, where each tuple contains:
            - rank_str (str): The canonical string for the rank (e.g., "A", "K", "10", "2").
            - suit_char_internal (str): A single character for the suit (e.g., "S", "H", "D", "C").
        Returns an empty list if no valid cards are identified.
    """
    # Using print for debug messages for compatibility with the tool environment
    print(f"DEBUG voice_parser.parse_cards_from_text received: '{text_input}'")

    text = text_input.lower().strip()
    # Normalize common separators and filler words.
    text = text.replace(",", " ").replace(".", " ").replace(" and ", " ")
    text = text.replace(" of ", " ") # "X of Y" becomes "X Y"
    text = " ".join(text.split()) # Condense multiple spaces to single spaces

    words = text.split()
    parsed_card_data: list[tuple[str, str]] = []
    i = 0
    while i < len(words):
        word1 = words[i]
        # Try to map the word to a canonical rank string (e.g., "ace" -> "A")
        rank1_str = VALUE_WORD_TO_CARD.get(word1)

        # If not found in VALUE_WORD_TO_CARD, check if it's a direct digit (e.g., "10", "2")
        # This is secondary to word mapping to catch numbers not covered by common speech words.
        if rank1_str is None and word1.isdigit():
            if word1 == "10": rank1_str = "10"
            # For single digits 2-9, the digit itself is the rank string.
            elif word1 in ['2','3','4','5','6','7','8','9']: rank1_str = word1
            # Note: "1" is handled by VALUE_WORD_TO_CARD mapping to "A" if desired.

        if rank1_str: # A potential rank was identified
            suit_char = None
            consumed_words_count = 1 # Number of words consumed for this card (rank + optional suit word)

            # Look ahead for a suit keyword in the next word.
            if i + 1 < len(words):
                word2 = words[i+1]
                potential_suit_char = SUIT_KEYWORDS.get(word2)
                if potential_suit_char:
                    suit_char = potential_suit_char
                    consumed_words_count = 2 # Consumed both rank and suit words

            if suit_char: # Both rank and suit were successfully identified
                parsed_card_data.append((rank1_str, suit_char))
                print(f"DEBUG voice_parser: Parsed card: {(rank1_str, suit_char)} from phrase: '{' '.join(words[i:i+consumed_words_count])}'")
                i += consumed_words_count # Advance index by number of words consumed for this card
                continue # Continue to look for more cards
            else:
                # Rank found, but no recognizable suit followed immediately.
                # This rank word might be part of a different phrase or a parsing error.
                print(f"DEBUG voice_parser: Rank '{rank1_str}' (from word '{word1}') found, but no valid suit followed. Discarding as a card.")

        i += 1 # Move to the next word if current word didn't start a valid card, or after processing a card.

    if parsed_card_data:
        print(f"DEBUG voice_parser.parse_cards_from_text final result: {parsed_card_data}")
    else:
        print(f"DEBUG voice_parser.parse_cards_from_text: No cards extracted from input: '{text_input}'.")

    return parsed_card_data

# Example usage and test cases when running this file directly.
if __name__ == '__main__':
    print("Running voice_parser.py tests...")
    test_phrases = [
        "Ace of Spades", "king hearts", "ten of clubs and five diamonds",
        "Jack Spade", "Queen Heart", "Ace Diamond", "Two Club",
        "Ace of Spades and King of Hearts",
        "Ace Spades King Hearts",
        "Deal me an ace of spades", "Player has king of hearts",
        "Dealer shows a ten of clubs", "next card is five of diamonds",
        "Ace yes paid", # "yes" -> A (from VALUE_WORD_TO_CARD), "paid" -> S (from SUIT_KEYWORDS)
        "One of Clubs", "one club", # "one" currently maps to "A"
        "two of spades", "3 hearts", "four D", "five C", "six S", "7 H", "8 D", "9 C", "10 S",
        "No cards here", "Player dealer other", "New round", "Stop listening",
        "Ace of Speed", "King of Hart", "Queen of Dime", "Jack of Clover",
        "Said ace", # Should parse "ace" if "said" is not a rank, or "said" as "S" if followed by rank
        "Ace said", # Should parse Ace of Spades
        "Dealer has queen of clovers and a five of speed",
        "My card is a two of harts",
        "Player shows king of paid",
        "Next is ace of space",
        "The card is a seven of dice", # dice -> D
        "Player one has ace of hearts", # "one" here is part of phrase, not card
        "The one card is ace of spades", # "one" here is part of phrase
        "Card is one", # "one" -> A, no suit
        "Card is one of paid" # "one" -> A, "paid" -> S => AS
    ]
    for phrase in test_phrases:
        print(f"\nInput: \"{phrase}\"")
        cards = parse_cards_from_text(phrase)
        if cards:
            # Format for display, e.g., "AS, KH"
            formatted_cards = [f"{rank}{suit}" for rank, suit in cards]
            print(f"  Output Cards: {', '.join(formatted_cards)}   (Raw: {cards})")
        else:
            print("  Output Cards: None")
        print("-" * 30)