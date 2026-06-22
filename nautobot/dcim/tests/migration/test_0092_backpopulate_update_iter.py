"""
Test harness for the chunked bulk_update loop.

Scenario under test:
    If the total number of items is an exact multiple of CHUNK_SIZE, does the
    final flush at `if updates:` get skipped — and if so, does that mean any
    items were missed?

Verdict: No bug exists.  When len(updates) hits CHUNK_SIZE the batch is
flushed *inside* the loop, so `updates` is empty when the loop finishes and
the trailing `if updates:` is correctly skipped.  Every item has already been
processed.

IMPORTANT NOTE ON MOCK DESIGN
------------------------------
The real bulk_update receives a *list* which is later mutated (updates.clear()).
A naive MagicMock records a reference to that list, so after .clear() every
recorded call_args shows an empty list.  All spy functions here capture a
*copy* (list(batch)) at call time to avoid this.
"""

import unittest


class FakeDevice:
    def __init__(self, pk):
        self.pk = pk

    def __repr__(self):
        return f"<Device pk={self.pk}>"


class FakeModuleBay:
    def __init__(self, pk):
        self.pk = pk
        self.parent_device = None
        # wire up:  bay.parent_module.parent_module_bay.parent_device
        device = FakeDevice(pk=f"dev-{pk}")
        module_bay = type("ModuleBay", (), {"parent_device": device})()
        module = type("Module", (), {"parent_module_bay": module_bay})()
        self.parent_module = module

    def __repr__(self):
        return f"<ModuleBay pk={self.pk}>"


def make_bays(n):
    return [FakeModuleBay(pk=i) for i in range(n)]


# ---------------------------------------------------------------------------
# Spy bulk_update factory
# Records a *snapshot* (copy) of each batch at the moment of the call.
# ---------------------------------------------------------------------------


class BulkUpdateSpy:
    """Replaces ModuleBay.objects.using(db).bulk_update in tests."""

    def __init__(self):
        self.calls = []  # list of (snapshot_of_batch, fields)
        self.call_count = 0

    def __call__(self, batch, fields):
        self.calls.append((list(batch), list(fields)))  # ← copy here
        self.call_count += 1

    def all_flushed_pks(self):
        """Flat list of every pk passed across all calls, in order."""
        return [b.pk for snapshot, _ in self.calls for b in snapshot]

    def batch_sizes(self):
        return [len(snapshot) for snapshot, _ in self.calls]


def run_loop(bays, chunk_size, bulk_update_fn):
    """
    Mirrors the migration loop exactly.
    bulk_update_fn replaces ModuleBay.objects.using(db).bulk_update.
    """
    updates = []

    for bay in iter(bays):
        bay.parent_device = bay.parent_module.parent_module_bay.parent_device
        updates.append(bay)

        if len(updates) >= chunk_size:
            bulk_update_fn(updates, ["parent_device"])
            updates.clear()

    if updates:
        bulk_update_fn(updates, ["parent_device"])


class TestChunkFlushBug(unittest.TestCase):
    def _run(self, n_items, chunk_size):
        bays = make_bays(n_items)
        spy = BulkUpdateSpy()
        run_loop(bays, chunk_size, spy)
        return bays, spy

    def _assert_all_flushed(self, bays, spy):
        """Every bay must appear in bulk_update exactly once, in order."""
        expected_pks = [b.pk for b in bays]
        self.assertEqual(
            spy.all_flushed_pks(),
            expected_pks,
            f"Flushed pks don't match.\n  Expected : {expected_pks}\n  Got      : {spy.all_flushed_pks()}",
        )
        for bay in bays:
            self.assertIsNotNone(bay.parent_device, f"Bay {bay.pk} never had parent_device assigned")

    def test_exact_one_chunk(self):
        """n == CHUNK_SIZE: single flush inside loop, trailing `if` skipped."""
        bays, spy = self._run(n_items=5, chunk_size=5)
        self._assert_all_flushed(bays, spy)
        self.assertEqual(spy.call_count, 1, "Expected exactly 1 flush")

    def test_exact_two_chunks(self):
        """n == 2 * CHUNK_SIZE: two flushes inside loop, trailing `if` skipped."""
        bays, spy = self._run(n_items=10, chunk_size=5)
        self._assert_all_flushed(bays, spy)
        self.assertEqual(spy.call_count, 2, "Expected exactly 2 flushes")

    def test_exact_ten_chunks(self):
        bays, spy = self._run(n_items=50, chunk_size=5)
        self._assert_all_flushed(bays, spy)
        self.assertEqual(spy.call_count, 10)

    def test_exact_large_chunk_size(self):
        """Realistic CHUNK_SIZE (2 000) with an exact multiple."""
        CHUNK_SIZE = 2_000
        bays, spy = self._run(n_items=CHUNK_SIZE * 3, chunk_size=CHUNK_SIZE)
        self._assert_all_flushed(bays, spy)
        self.assertEqual(spy.call_count, 3)

    # -----------------------------------------------------------------------
    # Non-multiples
    # -----------------------------------------------------------------------

    def test_less_than_one_chunk(self):
        """n < CHUNK_SIZE: no mid-loop flush; trailing `if` handles everything."""
        bays, spy = self._run(n_items=3, chunk_size=5)
        self._assert_all_flushed(bays, spy)
        self.assertEqual(spy.call_count, 1, "Expected exactly 1 flush (trailing)")

    def test_one_remainder(self):
        """n == CHUNK_SIZE + 1: one in-loop flush, one trailing flush."""
        bays, spy = self._run(n_items=6, chunk_size=5)
        self._assert_all_flushed(bays, spy)
        self.assertEqual(spy.call_count, 2)
        self.assertEqual(spy.batch_sizes(), [5, 1])

    def test_arbitrary_remainder(self):
        """13 items, chunk 5 → batches of [5, 5, 3]."""
        bays, spy = self._run(n_items=13, chunk_size=5)
        self._assert_all_flushed(bays, spy)
        self.assertEqual(spy.call_count, 3)
        self.assertEqual(spy.batch_sizes(), [5, 5, 3])

    # -----------------------------------------------------------------------
    # Edge cases
    # -----------------------------------------------------------------------

    def test_zero_items(self):
        """Empty queryset: bulk_update never called."""
        _, spy = self._run(n_items=0, chunk_size=5)
        self.assertEqual(spy.call_count, 0)

    def test_chunk_size_one(self):
        """Every item is its own chunk (flush on every iteration)."""
        bays, spy = self._run(n_items=5, chunk_size=1)
        self._assert_all_flushed(bays, spy)
        self.assertEqual(spy.call_count, 5)
        self.assertEqual(spy.batch_sizes(), [1, 1, 1, 1, 1])

    def test_flush_order_preserved(self):
        """Items reach bulk_update in the same order as the queryset."""
        _, spy = self._run(n_items=12, chunk_size=5)
        self.assertEqual(spy.all_flushed_pks(), list(range(12)))

    # -----------------------------------------------------------------------
    # The exact-multiple
    # -----------------------------------------------------------------------

    def test_exact_multiple_trailing_if_is_correctly_skipped(self):
        """Verify buffer is flushed correctly if result is a multiple of chunk size"""
        CHUNK_SIZE = 4
        n = CHUNK_SIZE * 3  # 12 items — exact multiple

        bays = make_bays(n)
        flushed_during_loop = []
        flushed_after_loop = []
        in_loop = True

        def spy(batch, fields):
            snapshot = [b.pk for b in batch]
            if in_loop:
                flushed_during_loop.extend(snapshot)
            else:
                flushed_after_loop.extend(snapshot)

        updates = []
        for bay in iter(bays):
            bay.parent_device = bay.parent_module.parent_module_bay.parent_device
            updates.append(bay)
            if len(updates) >= CHUNK_SIZE:
                spy(updates, ["parent_device"])
                updates.clear()

        in_loop = False  # loop is done; mark the phase boundary

        if updates:
            spy(updates, ["parent_device"])

        self.assertEqual(flushed_during_loop, list(range(12)), "All 12 items should have been flushed during the loop")
        self.assertEqual(
            flushed_after_loop, [], "The trailing `if updates:` block should not fire for an exact multiple"
        )

    def test_parent_device_actually_assigned(self):
        """
        Spot-check that the assignment
            bay.parent_device = bay.parent_module.parent_module_bay.parent_device
        really propagates the right object.
        """
        bays, _ = self._run(n_items=7, chunk_size=3)
        for bay in bays:
            expected_device = bay.parent_module.parent_module_bay.parent_device
            self.assertIs(bay.parent_device, expected_device, f"Bay {bay.pk}: parent_device not set correctly")


if __name__ == "__main__":
    unittest.main(verbosity=2)
