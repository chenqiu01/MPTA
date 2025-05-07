import random
from enum import Enum
from queue import Queue
import json

class Tree:
    """
    Tree representation of an extensive-form game.
    Supports an arbitrary number of players, including chance.
    """

    def __init__(self, numOfPlayers = 2, first_player = 0, root = None):
        """
        Create a tree with a specified root node (or with a new node as root if None is given)
        """

        if(root == None):
            root = Node(first_player, 0, 0)
        self.root = root
        self.node_count = 1
        self.infoset_count = 1
        self.max_infoset = 0
        self.numOfPlayers = numOfPlayers
        self.max_depth = 0
        self.convert_version=0
        self.suits=0
        self.ranks=0
        
    def addNode(self, player, information_set = -1, parent = None, probability = -1, actionName = None):
        """
        Add a decision node for a given player to the tree.
        If no information set is given, a new unique id is generated.
        If no parent is given, the parent is set to be the root.
        If the node is a children of a chance node, the probability to play the action leading to this node must be given.
        If no action name is given, a default string is generated.
        """

        if(self.root == None):
            print("ERROR: root should not be None")
            return None
        
        if(information_set == -1):
            information_set = self.infoset_count
            self.infoset_count += 1
        self.max_infoset = max(self.max_infoset, information_set)
        
        if(parent == None):
            parent = self.root
        
        node = Node(player, self.node_count, information_set, parent)
        self.max_depth = max(self.max_depth, node.depth)
        
        if(parent.isChance()):
            parent.addChild(node, probability, actionName)
        else:
            parent.addChild(node, actionName)
        self.node_count += 1
        
        return node
    
    def addLeaf(self, parent, utility, actionName = None):
        """
        Add a leaf node with a given utility to the tree.
        If no action name is given, a default string is generated.
        """

        # if(len(utility) != self.numOfPlayers):
        #     print("ERROR: trying to create a leaf with a utility vector of the wrong size.")
            # return
        
        leaf = Leaf(self.node_count, utility, parent)
        self.max_depth = max(self.max_depth, leaf.depth)
        parent.addChild(leaf, actionName = actionName)
        self.node_count += 1
        return leaf
    
    def addChanceNode(self, parent = None, actionName = None):
        """
        Add a chance node to the tree.
        If no parent is given, the parent is set to be the root.
        If no action name is given, a default string is generated.
        """

        if(self.root == None):
            print("ERROR: root should not be None")
            return None
        
        if(parent == None):
            parent = self.root
        
        chanceNode = ChanceNode(self.node_count, parent)
        self.max_depth = max(self.max_depth, chanceNode.depth)
        if(parent.isChance()):
            parent.addChild(chanceNode, probability, actionName)#leduc时可能要改，如果敌人为玩家1，会出现二轮直接到玩家1的情况
        else:
            parent.addChild(chanceNode, actionName)
        self.node_count += 1
        
        return chanceNode
    
    def display(self):
        print(self.root)
        self.root.displayChildren()

    #保存节点信息，
    def print_tree(self,file_name):
        num_o = 0
        num_co = 0
        num_dummy = 0
        num_all = 0
        q=Queue()
        q.put(self.root)
        outcome = []
        #区分一下该节点类型，l表示叶子，c表示机会节点，p表示玩家节点
        while q.empty() == 0:
            node=q.get()
            if node.isLeaf():
                outcome.append({node.id:[{"role":'l'},{"from action":node.incoming_action_name},{"parent id":str(node.parent.id)},{"utility":node.utility},{"imformation_set_id":node.information_set}]})
            elif node.isChance() :
                if node.parent == None: #根节点
                    outcome.append({node.id:[{"role":'c'},len(node.children),{"from action":node.actionNames}]})
                else : #虚拟机会节点
                    outcome.append({node.id:[{"role":'dc'},{"player_id":node.player},{"from action":node.incoming_action_name},{"parent id":str(node.parent.id)},{"legal action":node.actionNames}]})
                    num_dummy += 1
            else :
                outcome.append({node.id:[{"role":'p'},{"player_id":node.player},{"from action":node.incoming_action_name},{"parent id":str(node.parent.id)},{"legal action":node.actionNames},{"imformation_set_id":str(node.information_set)}]})
                if node.player == 0 :
                    num_o +=1
                else :
                    num_co+=1
            
            if node.isLeaf() != 1:
                for i in range(len(node.children)):
                    q.put(node.children[i])
            num_all+=1
        #保存到本地
        info_json = json.dumps(outcome,sort_keys=False, indent=4, separators=(',', ': '))
        # f = open('./'+str(file_name)+'.json', 'w')
        # f.write(info_json)
        #保存到本地
        print("敌手节点数量：",num_o)
        print("协调者节点数量：",num_co)
        print("虚拟机会节点节点数量：",num_dummy)
        print("总节点数量：",num_all)


class Node:
    """
    Represents a decision node for a given player in an extensive-form tree.
    """

    def __init__(self, player, id, information_set, parent = None):
        """
        Create a decision node for a given player, with a given id and a given information set.
        """

        self.id = id
        self.parent = parent
        self.player = player
        self.depth = 0
        if parent != None:
            self.depth = parent.depth + 1
        self.children = []
        self.actionNames = []
        self.information_set = information_set
        self.incoming_action = None #是父节点的第几个孩子
        self.incoming_action_name = None #是来自父节点的哪个动作
        self.ori_player=-42 #转换后玩家节点由哪位玩家转化而来
        self.remain_cards = [] #only for goofspiel

    def __str__(self):
        return self.__repr__()
    
    def __repr__(self):
        s = "Player " + str(self.player) +             " - Infoset " + str(self.information_set) +             " - Node " + str(self.id) 
        if(self.parent != None):
            s += " (children of Node" + str(self.parent.id) + " via Action " +                    str(self.incoming_action_name) + ")"
        return s
        
    def addChild(self, child, actionName = None):
        """
        Add a child node.
        If no action name is passed, a default one is generated.
        """

        self.children.append(child)
        child.parent = self
        if(actionName == None):
            actionName = str(self.information_set) + "." + str(len(self.children) - 1)
        self.actionNames.append(actionName)
        child.incoming_action = len(self.children) - 1
        child.incoming_action_name = actionName
            
    def getChild(self, action):
        return self.action_to_child_dict[action]
        
    def isLeaf(self):
        return False
    
    def isChance(self):
        return False
    
    def getSequence(self, in_player,convert_version):
        """
        Returns the sequence of actions (for a given player) that leads to this node.
        """

        node_player = self.player
        if isinstance(in_player,int) and node_player == -1 :
            player = in_player
        elif isinstance(in_player,int) and  int(self.ori_player)>=0 :
            player = int(self.ori_player)
        elif in_player == None :
            player = None
        else :
            print("self.id is:",self.id)
            print("self.player is:",self.player)
            print("self.ori_player is:",self.ori_player)
            print("in_player is:",in_player)
            raise Exception("There are something wrong in player")
            
        if convert_version == 4:
            return
        if convert_version == 3:
            return self.getSequence_v3(player)
        elif convert_version == 2:
            return self.getSequence_v2(player)
        else :
            raise Exception("There are something wrong in version")
        

        # # 原始方法，将history中，这名玩家做过的动作，以及做动作节点的信息集编号存入字典，{信息集编号：第几个动作}
        # if(self.parent == None):
        #     return {}
        # if(self.parent.player != player and player != None):
        #     return self.parent.getSequence(player,3)


        # sequence = self.parent.getSequence(player,3) 
        # sequence[self.parent.information_set] = self.incoming_action
        # return sequence

    def getSequence_v3(self, player):
        if(self.parent == None): #根节点
            return {}
        if self.parent.player == -42 : #父节点是dc的玩家节点
            if(int(self.parent.parent.ori_player) != player and player != None): #爷节点是玩家节点，但并不是要找的玩家（此时不可能是根下的p0，已排除）
                return self.parent.parent.getSequence_v3(player)
            else :#爷节点是要找的玩家节点
                sequence = self.parent.parent.getSequence_v3(player) 
                sequence[self.parent.parent.information_set] = self.parent.incoming_action_name
                return sequence
        if self.parent.parent == None: #父节点是根节点的p0玩家
            if player!= None:
                return self.parent.getSequence_v3(player)
            else :
                sequence = self.parent.getSequence_v3(player) 
                sequence[self.parent.information_set] = self.incoming_action_name
                return sequence
        if(int(self.parent.ori_player) != player and player != None): #父节点是玩家节点，但并不是要找的玩家（此时不可能是根下的p0，已排除）
            return self.parent.getSequence_v3(player)


        sequence = self.parent.getSequence_v3(player) 
        sequence[self.parent.information_set] = self.incoming_action_name

        return sequence   

    def getSequence_v2(self, player):
        if(self.parent == None): #根节点
            return {}
        if self.parent.player == -42 : #父节点是dc的玩家节点
            if(int(self.parent.parent.ori_player) != player and player != None): #爷节点是玩家节点，但并不是要找的玩家（此时不可能是根下的p0，已排除）
                return self.parent.parent.getSequence_v2(player)
            else :#爷节点是要找的玩家节点
                sequence = self.parent.parent.getSequence_v2(player) 
                sequence[self.parent.parent.information_set] = self.parent.incoming_action_name
                return sequence
        if self.parent.parent == None: #父节点是根节点的p0玩家
            if player!= None:
                return self.parent.getSequence_v2(player)
            else :
                sequence = self.parent.getSequence_v2(player) 
                sequence[self.parent.information_set] = self.incoming_action_name
                return sequence
        if(int(self.parent.ori_player) != player and player != None): #父节点是玩家节点，但并不是要找的玩家（此时不可能是根下的p0，已排除）
            return self.parent.getSequence_v2(player)


        sequence = self.parent.getSequence_v2(player) 
        sequence[self.parent.information_set] = self.incoming_action_name

        return sequence
    
    def displayChildren(self):
        for child in self.children:
            print(child)
        for child in self.children:
            child.displayChildren()
            
    def getActionLeadingToNode(self, targetNode):
        """
        Returns the action (of this node) in the path from this node to the target node.
        """

        if(targetNode.parent == None):
            return None
        if(targetNode.parent == self):
            return targetNode.incoming_action
        return self.getActionLeadingToNode(targetNode.parent)

    def getNodeFollowJointSequence(self, joint_sequence):
        """
        Returns the leaf reached when following the given joint sequence.
        """

        if(self.isLeaf()):
            return self
        
        sequence = joint_sequence[self.player]

        if(self.information_set not in sequence):
            return self

        action = sequence[self.information_set]
        
        return self.children[action].getNodeFollowJointSequence(joint_sequence)

class Leaf(Node):
    """
    Represents a leaf node in an extensive-form tree.
    """

    def __init__(self, id, utility, parent):
        Node.__init__(self, -1, id, -1 , parent)
        self.utility = utility
        
    def __repr__(self):
        s = "Leaf" + str(self.id) 
        if(self.parent != None):
            s += " (children of Node" + str(self.parent.id) + " via Action " + str(self.incoming_action_name) + ") - " +                    " utility is " + str(self.utility)
        return s
    
    def isLeaf(self):
        return True

class ChanceNode(Node):
    """
    Represents a chance node in an extensive-form tree.
    """

    def __init__(self, id, parent = None):
        Node.__init__(self, -42, id, -42, parent)
        self.distribution = []
    
    def isChance(self):
        return True
    
    def addChild(self, child, probability = 1, actionName = None):
        """
        Add a child node, that is reached by a given (fixed) probability.
        If no action name is passed, a default one is generated.
        """

        self.children.append(child)
        self.distribution.append(probability)
        child.parent = self
        child.incoming_action = len(self.children) - 1
        if(actionName == None):
            actionName = "c." + str(len(self.children) - 1)
        self.actionNames.append(actionName)
        child.incoming_action_name = actionName
        
# --------------------------------------------------------------------------------

class PlayerSwapMethod(Enum):
    Random = 0
    RoundRobin = 1
    RandomWithoutSame = 2

def randomTree(depth, branching_factor = 2, info_set_probability = 1, player_count = 2,
               first_player = -1, min_utility = 0, max_utility = 100, int_utility = True, swap_method = PlayerSwapMethod.RoundRobin):
    """
    Create a random extensive-form tree.
    depth = the depth of the tree.
    branching_factor = how many actions each node has.
    info_set_probability = the probability that a newly added node will be added to an already existing information set.
    player_count = the number of players.
    first_player = the first player to play (if no one is given, it is chosen randomly).
    min_utility = the minimum utility achievable by each player.
    max_utility = the maximum utility achievable by each player.
    int_utility = wether the utility is a random integer or not.
    swap_method = how to alternate players during the game (either round robin or random).
    """
    
    # Player swap subroutine
    def swapPlayers(current_player, player_count, swap_method):
        if(swap_method == PlayerSwapMethod.RoundRobin):
            return (current_player + 1) % player_count
        if(swap_method == PlayerSwapMethod.Random):
            return random.randint(0, player_count - 1)
        if(swap_method == PlayerSwapMethod.RandomWithoutSame):
            p = random.randint(0, player_count - 2)
            if(p >= current_player):
                p += 1
            return p
    
    # Randomly choose first player if it is not already set
    if(first_player < 0 or first_player >= player_count):    
        player = random.randint(0, player_count - 1)
    else:
        player = first_player
        
    # Initialize the tree
    tree = Tree(player_count, player)
    nodes_to_expand = [ tree.root ]
    information_set = 0
    
    for d in range(0, depth - 1):
        # Change player
        player = swapPlayers(player, player_count, swap_method)
        
        new_nodes_to_expand = []
        for parent in nodes_to_expand:
            # Change information set (children of different nodes always are in different information sets)
            # -- because of perfect recall
            information_set += 1
                
            # Generate a new node for each action
            for a in range(branching_factor):
                node = tree.addNode(player, information_set, parent)
                if(a != branching_factor - 1 and random.random() <= info_set_probability):
                    information_set += 1
                
                new_nodes_to_expand.append(node)
                
        nodes_to_expand = new_nodes_to_expand
        
    # Nodes in nodes_to_expand have only leaves as children at this point
    for node in nodes_to_expand:
        for a in range(branching_factor):
            if(int_utility):
                utility = [random.randint(min_utility, max_utility) for p in range(player_count)]
            else:
                utility = [random.uniform(min_utility, max_utility) for p in range(player_count)]
            tree.addLeaf(node, utility)
        
    return tree