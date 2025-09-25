import sqlite3
import json
import os
from datetime import datetime

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'data', 'blackjack_data.db')
    print('DB:', db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Show last few rounds (by last_updated)
    cur.execute("SELECT game_id, shoe_name, last_updated FROM rounds ORDER BY last_updated DESC LIMIT 5")
    rows = cur.fetchall()
    print('Recent rounds (raw rows):')
    for r in rows:
        print('  ', r)

    # Show last few distinct game_ids by most recent update
    cur.execute("SELECT game_id, MAX(last_updated) FROM rounds GROUP BY game_id ORDER BY MAX(last_updated) DESC LIMIT 10")
    distinct_ids = cur.fetchall()
    print('\nRecent distinct game_ids:')
    for r in distinct_ids:
        print('  ', r)

    # Choose IDs to inspect (latest and previous if exists)
    inspect_ids = []
    if distinct_ids:
        inspect_ids.append(distinct_ids[0][0])
        if len(distinct_ids) > 1:
            inspect_ids.append(distinct_ids[1][0])

    def parse_cards(field):
        try:
            raw = json.loads(field) if isinstance(field, str) else (field or [])
        except Exception:
            raw = []
        vals = []
        times = []
        for c in raw:
            if isinstance(c, dict):
                vals.append(c.get('value'))
                times.append(c.get('t'))
            elif isinstance(c, str):
                vals.append(c)
                times.append(None)
        return vals, times

    for gid in inspect_ids:
        print('\n--- Round detail for game_id:', gid, '---')
        cur.execute("SELECT * FROM rounds WHERE game_id = ? ORDER BY last_updated DESC LIMIT 1", (gid,))
        row = cur.fetchone()
        if not row:
            print('  No row found')
            continue
        dealer_vals, dealer_t = parse_cards(row[3])
        print('  Dealer:', dealer_vals)
        for s in range(7):
            hand_idx = 5 + s*3
            seat_vals, seat_t = parse_cards(row[hand_idx])
            print(f'  Seat{s}:', seat_vals)
        print('  last_updated:', row[-1])

        # Recompute discard as per ShoeManager logic
        def parse_pairs(field, allow_hidden=False):
            pairs = []
            if not field:
                return pairs
            try:
                raw = json.loads(field) if isinstance(field, str) else (field or [])
                for c in raw:
                    if isinstance(c, dict):
                        v = c.get('value')
                        if v and (allow_hidden or v != '**'):
                            pairs.append((v, c.get('t', 0)))
                    elif isinstance(c, str):
                        if c and (allow_hidden or c != '**'):
                            pairs.append((c, 0))
            except Exception:
                pass
            return pairs
        def extras_desc(pairs):
            extras = pairs[2:] if len(pairs) > 2 else []
            return sorted(extras, key=lambda x: x[1] if x[1] is not None else 0, reverse=True)
        discard_block = []
        # Seats 6..1
        for seat in range(6, 1-1, -1):
            hand_idx = 5 + seat * 3
            seat_pairs = parse_pairs(row[hand_idx] if len(row) > hand_idx else None, allow_hidden=False)
            for v, _ in extras_desc(seat_pairs):
                if v and v != '**':
                    discard_block.append(v)
            if len(seat_pairs) >= 2 and seat_pairs[1][0] and seat_pairs[1][0] != '**':
                discard_block.append(seat_pairs[1][0])
            if len(seat_pairs) >= 1 and seat_pairs[0][0] and seat_pairs[0][0] != '**':
                discard_block.append(seat_pairs[0][0])
        # Seat 0
        seat_pairs_0 = parse_pairs(row[5] if len(row) > 5 else None, allow_hidden=False)
        for v, _ in extras_desc(seat_pairs_0):
            if v and v != '**':
                discard_block.append(v)
        if len(seat_pairs_0) >= 2 and seat_pairs_0[1][0] and seat_pairs_0[1][0] != '**':
            discard_block.append(seat_pairs_0[1][0])
        if len(seat_pairs_0) >= 1 and seat_pairs_0[0][0] and seat_pairs_0[0][0] != '**':
            discard_block.append(seat_pairs_0[0][0])
        # Dealer
        dealer_pairs_raw = parse_pairs(row[3] if len(row) > 3 else None, allow_hidden=True)
        for v, _ in extras_desc(dealer_pairs_raw):
            if v and v != '**':
                discard_block.append(v)
        if len(dealer_pairs_raw) >= 2:
            v2 = dealer_pairs_raw[1][0]
            if v2:
                discard_block.append(v2)
        if len(dealer_pairs_raw) >= 1:
            v1 = dealer_pairs_raw[0][0]
            if v1 and v1 != '**':
                discard_block.append(v1)
        print('  recomputed discard (pre-reverse):', discard_block)
        rev = list(reversed(discard_block))
        print('  recomputed discard (would prepend):', rev[:20], '... total', len(rev))

    # Show shoe_cards state
    print('\n--- shoe_cards for Shoe 1 ---')
    cur.execute("SELECT undealt_cards, dealt_cards, COALESCE(current_dealt_cards,'[]'), COALESCE(discarded_cards,'[]') FROM shoe_cards WHERE shoe_name='Shoe 1'")
    sc = cur.fetchone()
    if sc:
        undealt = json.loads(sc[0]) if sc[0] else []
        dealt = json.loads(sc[1]) if sc[1] else []
        current = json.loads(sc[2]) if sc[2] else []
        discarded = json.loads(sc[3]) if sc[3] else []
        print('  undealt:', len(undealt))
        print('  dealt  :', len(dealt))
        print('  current:', current)
        print('  discarded count:', len(discarded))
        print('  discarded first 20:', discarded[:20])
    else:
        print('  No row yet for Shoe 1')

    conn.close()

if __name__ == '__main__':
    main()

