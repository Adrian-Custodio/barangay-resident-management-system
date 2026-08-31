"""
Fuzzy resident lookup, shared between ResidentListView's search box and
documents.WalkInIssueView's "does this person already have an account?"
check on the "Print without an account" flow -- both are the same
operation (rank residents by how well their name matches a typed query),
so it lives in one place rather than being written twice.
"""
from django.db.models import Case, When
from thefuzz import process

# Below this score (0-100, thefuzz's similarity scale) a match is more
# likely coincidence than a real hit on a misspelled/misremembered name.
# Chosen empirically rather than derived: low enough to survive a
# transposed letter or missing middle name, high enough that a two-letter
# query doesn't return half the barangay.
FUZZY_MATCH_THRESHOLD = 60


def fuzzy_search_residents(query, queryset, limit=50):
    """
    Ranks `queryset` (expected: active Residents) by fuzzy match against
    `query`, best match first. Returns queryset.none() for a blank query
    or when nothing clears FUZZY_MATCH_THRESHOLD, so callers never need a
    separate "was there even a query" branch -- an empty/no-match result
    always looks the same.
    """
    query = (query or "").strip()
    if not query:
        return queryset.none()

    # Fuzzy search happens in Python, over this request's queryset, rather
    # than as a DB query -- see the note on Resident.full_name. Fine at
    # barangay scale (hundreds to a few thousand residents); it would need
    # to move to a real search index well before it became a bottleneck.
    candidates = {resident.pk: resident.full_name for resident in queryset}
    if not candidates:
        return queryset.none()

    matches = process.extract(query, candidates, limit=limit)
    matched_pks = [pk for _, score, pk in matches if score >= FUZZY_MATCH_THRESHOLD]
    if not matched_pks:
        return queryset.none()

    # Preserve thefuzz's best-match-first ordering -- without this, the
    # DB's default ordering (last_name, first_name) would silently discard
    # the ranking that made the search useful in the first place.
    preserve_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(matched_pks)])
    return queryset.filter(pk__in=matched_pks).order_by(preserve_order)
