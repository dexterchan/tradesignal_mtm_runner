from tradesignal_mtm_runner.data_struct import BTree
import pytest
import logging
import math
logger = logging.getLogger(__name__)

# @pytest.fixture()
# def generate_sample_bt():
#     """Sample pytest test function with the pytest fixture as an argument."""
#     bt = BTree(10)
#     bt.insert(20)
#     bt.insert(30)
#     bt.insert(40)
#     bt.insert(50)
#     bt.insert(60)
#     bt.insert(70)
#     bt.insert(80)
#     bt.insert(90)
#     bt.insert(100)
#     bt.insert(110)
#     bt.insert(120)
#     bt.insert(130)
#     bt.insert(140)
#     bt.insert(150)
#     bt.insert(160)
#     bt.insert(170)
#     bt.insert(180)
#     bt.insert(190)
#     bt.insert(200)
#     bt.insert(210)
#     bt.insert(220)
#     bt.insert(230)
#     bt.insert(240)
#     bt.insert(250)
#     bt.insert(260)
#     bt.insert(270)
#     bt.insert(280)
#     bt.insert(290)
#     bt.insert(300)
#     bt.insert(310)
#     bt.insert(320)
#     bt.insert(330)
#     bt.insert(340)
#     bt.insert(350)
#     bt.insert(360)
#     bt.insert(370)
#     bt.insert(380)
#     bt.insert(390)
#     bt.insert(400)
#     bt.insert(410)
#     bt.insert(420)
#     bt.insert(430)
#     bt.insert(440)
#     bt.insert(450)
#     bt.insert(460)
#     bt.insert(470)
#     bt.insert(480)
#     bt.insert(490)
#     bt.insert(500)
#     bt.insert(510)
#     bt.insert(520)
#     bt.insert(530)
#     bt.insert(540)
#     bt.insert(550)
#     bt.insert(560)
#     bt.insert(570)
#     bt.insert(580)
#     bt.insert(590)
#     bt.insert(600)
#     bt.insert(610)
#     bt.insert(620)
#     bt.insert(630)
#     bt.insert(640)
#     bt.insert(650)
#     bt.insert(660)
#     bt.insert(670)
#     bt.insert(680)
#     bt.insert(690)
#     bt.insert(700)
#     bt.insert(710)
#     bt.insert(720)
#     bt.insert(730)
#     bt.insert(740)
#     bt.insert(750)
#     bt.insert(760)
#     bt.insert(770)
#     return bt


# def test_btree_search(generate_sample_bt) ->None:
#     bt = generate_sample_bt

#     # print(bt.search(10))
#     # print(bt.search(71))

#     print(bt.range_search(10, 50))


from tradesignal_mtm_runner.data_struct import IndexedList, SearchResultType, Node
def test_node_struct() -> None:
    test_samples: list = [5, 3, 1, 8, 7, 6, 10, 2, 9, 11, 4]
    payload_map: dict = {c: chr(c + 64) for c in test_samples}
    node: Node = Node(test_samples[0], org_inx=0, payload=payload_map[test_samples[0]])
    for i in range(1, len(test_samples)):
        c = test_samples[i]
        node.insert(c, i, payload_map[c])

    n, s = node.search_value(10)
    assert n.payload == chr(10 + 64)
    assert n.org_inx == 6
    assert s == SearchResultType.Exact

    n, s = node.search_value(7.5)
    assert n.payload == chr(7 + 64)
    assert s == SearchResultType.LargestValueJustSmaller

    n, s = node.search_value(1.5)
    assert n.payload == chr(2 + 64)
    assert s == SearchResultType.SmallestValueJustLarger

    for inx in range(len(test_samples)):
        sample = test_samples[inx]
        n, s = node.search_value(sample)
        assert n.payload == chr(sample + 64)
        assert n.org_inx == inx
        assert s == SearchResultType.Exact
    pass

def test_null_list() -> None:
    test_samples = []
    payload_map: dict = {}
    indexed_list = IndexedList(base_list=test_samples)
    indexed_list._index_the_list()
    l = indexed_list.search_value_left(5)
    assert l == []

    test_samples = [0]
    indexed_list = IndexedList(base_list=test_samples)
    indexed_list._index_the_list()
    l = indexed_list.search_value_left(5)
    assert l == [0]

def test_index_the_list() -> None:
    test_size = 10
    test_samples: list = [int(i * (i + 1) / 2) for i in range(test_size)]

    indexed_list = IndexedList(base_list=test_samples)
    node: Node = indexed_list._index_the_list()
    # logger.debug(node)

    for inx in range(len(test_samples)):
        sample = test_samples[inx]
        n, s = node.search_value(sample)
        assert n.value == sample
        assert n.org_inx == inx
        assert n.payload == sample
        assert n.org_inx == int((math.sqrt(1 + 4 * sample * 2) - 1) / 2)
        assert s == SearchResultType.Exact

    n = indexed_list.search_value(value=test_samples[len(test_samples) - 1])
    assert n.payload == test_samples[len(test_samples) - 1]
    assert n.org_inx == len(test_samples) - 1

    pick_inx = int(test_size / 2)
    chk_value = test_samples[pick_inx]
    values = indexed_list.search_value_left(value=chk_value)
    # logger.debug(values)
    assert values == test_samples[: pick_inx + 1]

    values = indexed_list.search_value_left(value=chk_value - 1)
    assert values == test_samples[:pick_inx]

    values = indexed_list.search_value_left(value=chk_value + 1)
    assert values == test_samples[: pick_inx + 1]

    values = indexed_list.search_value_right(value=chk_value)
    assert values == test_samples[pick_inx:]

    values = indexed_list.search_value_right(value=chk_value + 1)
    assert values == test_samples[pick_inx + 1 :]
    pass
