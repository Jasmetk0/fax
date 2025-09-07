from collections import OrderedDict

BandMap = dict[str, list[int]]


def md_anchor_map(draw_size: int) -> BandMap:
    """
    Kanonické kotvy pro seedy v MD dle specifikace (1-indexované sloty).
    Podporované: 16, 32, 64. (MD128+ doplníme později.)
    """
    if draw_size == 16:
        return OrderedDict(
            {
                "1": [1],
                "2": [16],
                "3-4": [9, 8],
                "5-8": [4, 5, 12, 13],
                "9-16": [2, 3, 6, 7, 10, 11, 14, 15],
            }
        )
    if draw_size == 32:
        return OrderedDict(
            {
                "1": [1],
                "2": [32],
                "3-4": [17, 16],
                "5-8": [8, 9, 24, 25],
                "9-16": [4, 5, 12, 13, 20, 21, 28, 29],
            }
        )
    if draw_size == 64:
        return OrderedDict(
            {
                "1": [1],
                "2": [64],
                "3-4": [33, 32],
                "5-8": [16, 17, 48, 49],
                "9-16": [8, 9, 24, 25, 40, 41, 56, 57],
                "17-32": [4, 5, 12, 13, 20, 21, 28, 29, 36, 37, 44, 45, 52, 53, 60, 61],
            }
        )
    raise ValueError(f"Unsupported draw_size {draw_size}. Use 16/32/64 for now.")


def band_sequence_for_S(draw_size: int, seeds_count: int) -> list[str]:
    """
    Vrátí pořadí bandů, které se použijí pro daný počet seedů S.
    Např. MD32 + S=8 → ['1','2','3-4','5-8'].
    """
    anchors = md_anchor_map(draw_size)
    order = list(anchors.keys())
    out: list[str] = []
    remaining = seeds_count
    for band in order:
        size = len(anchors[band])
        if remaining <= 0:
            break
        take = min(size, remaining)
        if take == size:
            out.append(band)
        else:
            # S je v praxi mocnina 2, bandy se nekrájí
            raise ValueError("seeds_count does not align with band sizes.")
        remaining -= size
    if remaining != 0:
        raise ValueError("seeds_count does not match sum of selected bands.")
    return out
