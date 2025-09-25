import random
from collections import deque
from itertools import chain

def _riffle(chunk1, chunk2):
    """
    Performs a standard, perfect riffle shuffle of two chunks of cards.
    Interleaves one card from each chunk until one is exhausted, then appends the rest.
    """
    result = []
    deck1 = deque(chunk1)
    deck2 = deque(chunk2)

    while deck1 and deck2:
        result.append(deck1.popleft())
        result.append(deck2.popleft())

    # Append any remaining cards
    result.extend(deck1)
    result.extend(deck2)

    return result

def _hindu_shuffle(deck, num_cuts=5):
    """
    Simulates a Hindu shuffle by performing a series of small cuts.
    (Deprecated in favor of strip-cut for the final stage.)
    """
    deck = list(deck)
    for _ in range(num_cuts):
        # Cut a small, random portion from the top and place it on the bottom
        cut_size = random.randint(1, max(1, len(deck) // 4))
        cut = deck[:cut_size]
        del deck[:cut_size]
        deck.extend(cut)
    return deck


def _strip_cut_shuffle(deck, strip_size=7):
    """
    Standard strip cut shuffle (O(N)):
    - Partition the deck into fixed-size strips from the top.
    - Return the concatenation of strips in reverse order, preserving intra-strip order.
    """
    deck = list(deck)
    n = len(deck)
    if n == 0:
        return []
    strips = []
    i = 0
    while i < n:
        strips.append(deck[i:i+strip_size])
        i += strip_size
    # Reverse strip order and flatten
    return list(chain.from_iterable(reversed(strips)))

def perform_full_shuffle(shuffling_stack, num_iterations=4, num_chunks=8, seed=None):
    """
    Performs the full, multi-stage shuffling algorithm as specified.
    """
    if not shuffling_stack:
        return []

    # Ensure the stack is divisible by the required number of chunks for splitting
    required_size = num_chunks * 2
    if len(shuffling_stack) % required_size != 0:
        print(f"Warning: Shuffle stack size ({len(shuffling_stack)}) is not perfectly divisible by {required_size}.")
        # For safety, we'll proceed but the chunks may be slightly uneven.
        # A more robust implementation might pad the deck.

    current_stack = list(shuffling_stack)

    # Optional determinism for simulation/testing
    if seed is not None:
        random.seed(seed)

    for i in range(num_iterations):
        # Split stack into Side A and Side B
        half = len(current_stack) // 2
        side_a = current_stack[:half]
        side_b = current_stack[half:]

        # Split sides into chunks
        chunk_size_a = (len(side_a) + num_chunks - 1) // num_chunks # Ceiling division
        chunk_size_b = (len(side_b) + num_chunks - 1) // num_chunks
        chunks_a = [side_a[j:j + chunk_size_a] for j in range(0, len(side_a), chunk_size_a)]
        chunks_b = [side_b[j:j + chunk_size_b] for j in range(0, len(side_b), chunk_size_b)]

        final_chunks = []
        is_last_iteration = (i == num_iterations - 1)

        for j in range(num_chunks):
            # Riffle chunk j from A and B
            chunk_a = chunks_a[j] if j < len(chunks_a) else []
            chunk_b = chunks_b[j] if j < len(chunks_b) else []
            riffled_chunk = _riffle(chunk_a, chunk_b)

            if is_last_iteration:
                # Strip cut shuffle (final-stage replacement for Hindu)
                strip_shuffled = _strip_cut_shuffle(riffled_chunk)
                # Split and riffle again
                strip_half = len(strip_shuffled) // 2
                final_chunk = _riffle(strip_shuffled[:strip_half], strip_shuffled[strip_half:])
            else:
                final_chunk = riffled_chunk

            final_chunks.append(final_chunk)

        # Restack the final chunks, with chunk 8 (index 7) on top
        current_stack = []
        for chunk in reversed(final_chunks):
            current_stack.extend(chunk)

    # Final cut: bottom half on top
    final_half = len(current_stack) // 2
    final_stack = current_stack[final_half:] + current_stack[:final_half]

    return final_stack