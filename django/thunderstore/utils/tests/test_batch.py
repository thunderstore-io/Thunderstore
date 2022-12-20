from thunderstore.utils.batch import batch


def test_batch():
    data = [1, 2, 3, 4, 5, 6, 7]
    batches = list(batch(2, data))
    assert batches == [[1, 2], [3, 4], [5, 6], [7]]
