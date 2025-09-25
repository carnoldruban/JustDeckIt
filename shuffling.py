import random
from collections import deque
from itertools import chain

def _riffle(chunk1, chunk2):
    """
    Human-like riffle shuffle of two chunks of cards (lower-variance bursts).

    Instead of a perfect interleave, we take small random bursts from each side, with
    a bias to avoid starving a side. Bursts are now lower-variance to reduce long
    runs (e.g., mostly 1–2 cards; 3-card bursts are rare on large piles).
    """
    result = []
    deck1 = deque(chunk1)
    deck2 = deque(chunk2)

    while deck1 or deck2:
        # Decide which side to pull from next, biased by remaining sizes
        len1, len2 = len(deck1), len(deck2)
        if len1 == 0 and len2 == 0:
            break
        if len1 == 0:
            take_from_a = False
        elif len2 == 0:
            take_from_a = True
        else:
            # Bias toward the side with more remaining cards
            bias = len1 / (len1 + len2)
            take_from_a = random.random() < bias

        # Lower-variance random burst size
        total = len1 + len2
        if total > 30:
            r = random.random()
            if r < 0.70:
                burst = 1
            elif r < 0.98:
                burst = 2
            else:
                burst = 3
        elif total > 10:
            burst = 1 if random.random() < 0.75 else 2
        else:
            burst = 1 if random.random() < 0.85 else 2

        if take_from_a:
            for _ in range(burst):
                if deck1:
                    result.append(deck1.popleft())
                else:
                    break
        else:
            for _ in range(burst):
                if deck2:
                    result.append(deck2.popleft())
                else:
                    break

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


def _strip_cut_shuffle(deck, min_strip=3, max_strip=7):
    """
    Strip cut shuffle (O(N)):
    - Partition the deck into variable-size strips from the top (sizes in [min_strip, max_strip], clamped),
    - Return the concatenation of strips in reverse order, preserving intra-strip order.
    - Always returns a permutation of the input (no loss or duplication).
    """
    deck = list(deck)
    n = len(deck)
    if n == 0:
        return []
    strips = []
    i = 0
    while i < n:
        remaining = n - i
        # Respect min_strip only when enough cards remain
        low = 1 if remaining < min_strip else min_strip
        high = max(low, min(max_strip, remaining))
        k = random.randint(low, high)
        strips.append(deck[i:i+k])
        i += k
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
