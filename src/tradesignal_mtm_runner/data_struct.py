from dataclasses import dataclass

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

