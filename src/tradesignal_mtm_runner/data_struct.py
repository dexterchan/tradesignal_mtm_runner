from __future__ import annotations
from dataclasses import dataclass
from collections import deque, namedtuple
from typing import List, Any, Tuple
from enum import Enum
#https://iq.opengenus.org/b-tree-searching-insertion/

class BPlusTree:
    def __init__(self, data):
        self.data = data
        self.left = None
        self.right = None

class BTree:
    def __init__(self, data):
        self.data = data
        self.left = None
        self.right = None

    def insert(self, data):
        if self.data:
            if data < self.data:
                if self.left is None:
                    self.left = BTree(data)
                else:
                    self.left.insert(data)
            elif data > self.data:
                if self.right is None:
                    self.right = BTree(data)
                else:
                    self.right.insert(data)
        else:
            self.data = data

    def print_tree(self):
        if self.left:
            self.left.print_tree()
        print(self.data)
        if self.right:
            self.right.print_tree()

    def search(self, val):
        if val < self.data:
            if self.left is None:
                return str(val)+" Not Found"
            return self.left.search(val)
        elif val > self.data:
            if self.right is None:
                return str(val)+" Not Found"
            return self.right.search(val)
        else:
            print(str(self.data) + ' is found')
            return self.data #add by me, copilot missed the return
    
    def range_search(self, begin, end) -> list:
        """ range search from begin to end

        Args:
            begin (_type_): _description_
            end (_type_): _description_

        Returns:
            list: _description_
        """
        # Generate by co-pilot....
        # travese the whole tree to get the result
        # cost is O(n)
        ret = []
        #print(self.data)
        if self.left:
            ret.extend(self.left.range_search(begin, end))
        if self.data >= begin and self.data <= end:
            print(self.data)
            ret.append(self.data)
        if self.right:
            ret.extend(self.right.range_search(begin, end))
        return ret

class SearchResultType(Enum):
    Exact = 0
    SmallestValueJustLarger = 1
    LargestValueJustSmaller = 2
    EmptyList = 4


class Node:
    def __init__(self, value: Any, org_inx: int, payload: Any) -> None:
        """Binary Tree

        Args:
            value (Any): value for comparison
            org_inx(int): original index
            payload (Any): payload referenced by value
        """
        self.value: Any = value
        self.org_inx: int = org_inx
        self.payload: Any = payload
        self._left: Node = None
        self._right: Node = None
        pass

    def insert(self, v: Any, org_inx: int, payload: Any) -> Node:
        process_queue: deque = deque()

        def insert_to_node(node: Node, value: Any, org_inx: int, payload: Any):
            if node.value > value:
                if node._left is None:
                    node._left = Node(value=value, org_inx=org_inx, payload=payload)
                else:
                    process_queue.append((node._left, value, org_inx, payload))
                pass
            else:
                if node._right is None:
                    node._right = Node(value=value, org_inx=org_inx, payload=payload)
                else:
                    process_queue.append((node._right, value, org_inx, payload))
                pass
            pass

        process_queue.append((self, v, org_inx, payload))

        while len(process_queue) > 0:
            _node, _v, _org_inx, _payload = process_queue.pop()
            insert_to_node(node=_node, value=_v, org_inx=_org_inx, payload=_payload)
            pass
        pass

    def search_value(self, v) -> Tuple[Node, SearchResultType]:
        """_summary_

        Args:
            v (_type_): _description_

        Returns:
            Tuple[Node, SearchResultType]: _description_
        """
        process_queue: deque = deque()
        process_queue.append(self)
        found_result = None
        while len(process_queue) > 0:
            node: Node = process_queue.pop()
            if v < node.value:
                if node._left is not None:
                    process_queue.append(node._left)
                else:
                    # the smallest value just larger than v is found
                    found_result = node, SearchResultType.SmallestValueJustLarger
                    break
            elif node.value < v:
                if node._right is not None:
                    process_queue.append(node._right)
                else:
                    # the largest value just smaller is found
                    found_result = node, SearchResultType.LargestValueJustSmaller
                    break
            else:
                found_result = node, SearchResultType.Exact
                break
        return found_result

    def __repr__(self) -> str:
        return f'{{"value":"{str(self.value)+"("+str(self.payload)+")" if self.value is not None else "None"}",\
             "left":{self._left.__repr__() if self._left is not None else "None" },\
            "right":{self._right.__repr__() if self._right is not None else "None"} }}'

class IndexedList:
    """Indexed List to speed up the searching the value with Binary Tree:
    search for the index for
    a) the exact value
    b) the largest value just smaller than a value
    c) the smallest value just larger than a value
    This indexed list should be immutable
    Suppport the search time cost with log(N)
    and storage cost with N
    """

    def __init__(self, base_list: List[Any], get_value_func=lambda v: v) -> None:
        """_summary_
        Args:
            base_list (List[Any]): The list to optimize searching
            get_value_func (_type_, optional): get the value for comparison. Defaults to lambdav:v.
        """
        self._list: List[Any] = base_list
        self.get_value_func = get_value_func
        self.node: Node = self._index_the_list()
        pass

    def _index_the_list(self) -> Node:
        """index the list

        Returns:
            Node: Binary tree
        """
        # binary division the list to balance the tree
        _range = (0, len(self._list))
        process_q = deque()
        process_q.append(_range)
        node = None
        while len(process_q) > 0:
            begin, end = process_q.pop()
            mid = int((begin + end) / 2)
            if mid >= len(self._list):
                break
            insert_value = self.get_value_func(self._list[mid])
            if node is None:
                node = Node(value=insert_value, org_inx=mid, payload=(self._list[mid]))
            else:
                node.insert(v=insert_value, org_inx=mid, payload=(self._list[mid]))

            if begin < mid:
                process_q.append((begin, mid))
            if mid + 1 < end:
                process_q.append((mid + 1, end))
            pass
        pass
        return node

    def search_closet_value(self, value: Any) -> Tuple(Node, SearchResultType):
        if self.node is None:
            return None, SearchResultType.EmptyList
        node, s = self.node.search_value(v=self.get_value_func(value))
        return node, s

    def search_value(self, value: Any) -> Node:
        node, s = self.search_closet_value(value)
        if s == SearchResultType.Exact:
            return node
        else:
            return None

    def search_value_left(self, value: Any) -> List:
        node, s = self.search_closet_value(value=value)
        node: Node = node
        if node is None:
            return []
        inx = node.org_inx
        if s == SearchResultType.Exact or s == SearchResultType.LargestValueJustSmaller:
            return self._list[: inx + 1]
        else:
            return self._list[:inx]

    def search_value_right(self, value: Any) -> List:
        node, s = self.search_closet_value(value=value)
        node: Node = node
        if node is None:
            return []
        inx = node.org_inx
        if s == SearchResultType.Exact or s == SearchResultType.SmallestValueJustLarger:
            return self._list[inx:]
        else:
            return self._list[inx + 1 :]