from collections import OrderedDict

BandMap = dict[str, list[int]]


def _serpentine_positions(draw_size: int) -> list[int]:
    """Return slot order for seeds 1..draw_size using serpentine seeding."""
    if draw_size == 1:
        return [1]
    prev = _serpentine_positions(draw_size // 2)
    out: list[int] = []
    for p in prev:
        out.append(p)
        out.append(draw_size + 1 - p)
    return out


def _band_ranges(n: int) -> list[tuple[str, int, int]]:
    """Generate band labels and start/end seed numbers."""
    ranges: list[tuple[str, int, int]] = []
    start = 1
    prev_size = 1
    while start <= n:
        size = 1 if start <= 2 else prev_size * 2
        end = min(n, start + size - 1)
        label = str(start) if start == end else f"{start}-{end}"
        ranges.append((label, start, end))
        prev_size = size
        start = end + 1
    return ranges


def md_anchor_map(draw_size: int) -> BandMap:
    """Kanonické kotvy pro seedy v MD dle specifikace (1-indexované sloty)."""
    if draw_size not in {16, 32, 64, 128}:
        raise ValueError("Unsupported draw_size {draw_size}. Use 16/32/64/128.")
    positions = _serpentine_positions(draw_size)
    mid = draw_size // 2
    anchors: BandMap = OrderedDict()
    for label, start, end in _band_ranges(draw_size):
        subset = positions[start - 1 : end]
        top = sorted(p for p in subset if p <= mid)
        bottom = sorted(p for p in subset if p > mid)
        anchors[label] = bottom + top if label == "3-4" else top + bottom
    return anchors


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
