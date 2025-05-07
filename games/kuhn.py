from data_structures.trees import Tree, Node, ChanceNode
import copy
from queue import Queue

Action = ['p', 'b']

def build_kuhn_tree(num_players, rank):
    """
    Build a tree for the game of Kuhn with a given number of players and a given number of ranks in the deck (i.e. how
    many cards).
    """
    root = ChanceNode(0)
    
    tree = Tree(num_players, 0, root)

    tree.ranks=rank

    hands = build_all_possible_hands(num_players, list(range(rank)))
    hand_probability = 1 / len(hands)
    for hand in hands:
        n = tree.addNode(0, parent = root, probability = hand_probability, actionName = str(hand))
        build_kuhn_hand_tree(hand, [], 0, n, tree)
        
    for i in range(len(hands)):
        for j in range(i+1, len(hands)):
            players_to_merge = []
            for p in range(num_players):
                if(hands[i][p] == hands[j][p]):
                    players_to_merge.append(p)
            create_information_sets(root.children[i], root.children[j], players_to_merge)
            
    return tree

#信息集归并，原树
def create_information_sets(node1, node2, players_to_merge):
    """
    Takes two identically shaped trees (rooted at node1 and node2) and put all the nodes
    belonging to players in players_to_merge in pairwise information sets.
    """
    if(node1.isLeaf()):
        return

    if(node1.player in players_to_merge):
        iset_id = min(node1.information_set, node2.information_set)
        node1.information_set = iset_id
        node2.information_set = iset_id

    # print("对比：",node1.id,":",len(node1.children),node2.id,":",len(node2.children))
    for i in range(len(node1.children)):
        create_information_sets(node1.children[i], node2.children[i], players_to_merge)


def build_kuhn_hand_tree(hand, previous_moves, current_player, current_node, tree):
    """
    Recursively build the subtree for the Kuhn game where the hand is fixed.
    """

    #print("previous_moves: " + str(previous_moves))
    actionPrefix = 'p' + str(current_player)
    num_players = len(hand)
    
    next_player = (current_player + 1) % num_players
    #while(previous_moves[next_player] in ['b', 'f']):
    #    next_player = (next_player + 1) % num_players

    for action in Action:
        previous_moves.append(action)
        if (((len(previous_moves) == num_players) and 'b' not in previous_moves) or
            ((len(previous_moves) == num_players) and previous_moves[next_player] == 'b') or
            ((len(previous_moves) > num_players) and previous_moves[next_player] == 'b')):
            tree.addLeaf(current_node, kuhn_utility(hand, previous_moves), actionName = actionPrefix + action)
            previous_moves.pop()
        else:
            newNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + action)
            build_kuhn_hand_tree(hand, previous_moves.copy(), next_player, newNode, tree)
            previous_moves.pop()


    # There was a bet, so I can only call or fold
    # if('b' in previous_moves):
    #     # If the current and the next player are the same, we are at the last decision node of the game
    #     if(current_player == next_player):
    #         previous_moves[current_player] = 'b'
    #         tree.addLeaf(current_node, kuhn_utility(hand, previous_moves), actionName = actionPrefix + 'b')
            
    #         previous_moves[current_player] = 'f'
    #         tree.addLeaf(current_node, kuhn_utility(hand, previous_moves), actionName = actionPrefix + 'f')
            
    #         return
        
    #     callNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'b')
    #     previous_moves[current_player] = 'b'
    #     build_kuhn_hand_tree(hand, previous_moves.copy(), next_player, callNode, tree)
        
    #     foldNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'f')
    #     previous_moves[current_player] = 'f'
    #     build_kuhn_hand_tree(hand, previous_moves.copy(), next_player, foldNode, tree)
    
    # else: # No bet yet, so I can check or bet
    #     previous_moves[current_player] = 'c'
    #     if(len(list(filter(lambda el: el == 'c', previous_moves))) == num_players):
    #         tree.addLeaf(current_node, kuhn_utility(hand, previous_moves), actionName = actionPrefix + 'c')
    #     else:        
    #         checkNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'c')
    #         build_kuhn_hand_tree(hand, previous_moves.copy(), next_player, checkNode, tree)
            
    #     betNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'b')
    #     previous_moves[current_player] = 'b'
    #     build_kuhn_hand_tree(hand, previous_moves.copy(), next_player, betNode, tree)

def kuhn_utility(hand, moves):
    """
    Get the utility of a Kuhn game given the hand and how the players have played.
    """

    num_players = len(hand)
    
    #pot = num_players + len(list(filter(lambda el: el == 'b', moves)))
    if 'b' in moves:
        showdown_participants = [p % num_players for p in range(len(moves)) if moves[p] == 'b']
    else:
        showdown_participants = [p for p in range(num_players)]
    winner = max(showdown_participants, key = lambda el: hand[el])

    pot = [1] * num_players
    for p in showdown_participants:
        pot[p] += 1
    
    utility = [0] * num_players
    winning = 0
    if winner == 0:
        for p in range(1, num_players):
            winning += pot[p]
        utility[0] = winning
        for i in range(1, num_players):
            utility[i] = -winning/(num_players-1)
    else:
        winning = pot[0]
        utility[0] = -winning
        for i in range(1, num_players):
            utility[i] = winning/(num_players-1)

    return utility

def build_all_possible_hands(num_players, ranks):
    """
    Build all the possible hands for the game of Kuhn with a given number of players and a given set of cards.
    """

    if(num_players <= 0):
        return [[]]
    
    smaller_hands = build_all_possible_hands(num_players-1, ranks)
    hands = []
    
    for hand in smaller_hands:
        remaining_ranks = list(filter(lambda el: el not in hand, ranks))
        for r in remaining_ranks:
            hands.append(hand + [r])
            
    return hands


#多人转换算法（0704+）
#rank仅用于团队成员转化
def pub_team_convert_kuhn(ori_tree,rank,num_players):
    global hands
    #先构建一颗新树，再转化内部的节点
    new_root = ChanceNode(0)
    new_tree = Tree(2, 0, new_root)
    new_tree.ori_numOfPlayers = ori_tree.numOfPlayers

    #手牌
    hands = build_all_possible_hands(num_players, list(range(rank)))
    # hands=[]
    # for i in ori_tree.root.actionNames:
    #     hand=[]
    #     for j in range(len(i)):
    #         cha = i[j]
    #         if ord(cha)>=48 and ord(cha)<=57 :
    #             hand.append(int(cha))
    #     hands.append(hand)

    #修改转换版本，v2为原论文方法，v3为开会提出方法，v4为课题方法
    version = 4
    pub_convert_v4(ori_tree.root,None,new_tree,rank)
    new_tree.convert_version = 4
    
    pre=len(ori_tree.root.children)
    new_tree.root.distribution=[1/pre]*pre
    root=new_tree.root
    #将转换后树的根节点的玩家置为-1，用于区分sequence时和虚拟机会节点的差异
    root.player = -1
    #对比用例
    # compare_tree = copy.deepcopy(new_tree)

    if version == 4:
        new_tree.print_tree("conver_kuhn_tree_v"+str(version))
        return new_tree

    #转换后需要使用新的信息集归并方式,适用于v2,v3
    for i in range(len(hands)):
        for j in range(i+1, len(hands)):
            players_to_merge = []
            for p in range(num_players):
                if(hands[i][p] == hands[j][p]):
                    players_to_merge.append(p) 
            # create_information_sets(root.children[i], root.children[j], players_to_merge)
            create_information_sets_in_convert(root.children[i], root.children[j], players_to_merge)

    #把树存本地看一下
    new_tree.print_tree("conver_kuhn_tree_v"+str(version))
    return new_tree

#信息集归并，v3转换方法
def create_information_sets_in_convert(node1, node2, players_to_merge):
    """
    Takes two identically shaped trees (rooted at node1 and node2) and put all the nodes
    belonging to players in players_to_merge in pairwise information sets.
    """
    if(node1.isLeaf()):
        return

    #改成转换后两人博弈的V3方法时使用
    if node1.player != 0 and node1.player != -42: #敌人为0时不会出现信息集问题
        player=int(node1.ori_player)
        # if node1.id ==327 and node2.id == 1017 or node2.id ==327 and node1.id == 1017 :
        #     print(player)
    else:
        player = node1.player
    # player = node1.player
    # print("p is :",player)

    if(player in players_to_merge):
        iset_id = min(node1.information_set, node2.information_set)
        node1.information_set = iset_id
        node2.information_set = iset_id

    # print("对比：",node1.id,":",len(node1.children),node2.id,":",len(node2.children))
    for i in range(len(node1.children)):
        create_information_sets_in_convert(node1.children[i], node2.children[i], players_to_merge)

def pub_convert_v4(ori_node,parent_node,new_tree,rank):
  #叶节点
  if ori_node.isLeaf():
    new_tree.addLeaf(parent_node, ori_node.utility,actionName =ori_node.incoming_action_name)

  #机会节点和敌手节点
  elif ori_node.player == 0 or ori_node.isChance():
    
    if ori_node.isChance():#leduc也只有根节点会是chance
        for i in range(len(ori_node.children)):
            pub_convert_v4(ori_node.children[i], new_tree.root, new_tree, rank)
    if ori_node.player == 0:
        new_node = new_tree.addNode(ori_node.player,parent = parent_node,actionName=ori_node.incoming_action_name)
        new_node.ori_player = ori_node.player
        for i in range(len(ori_node.children)):
            pub_convert_v4(ori_node.children[i], new_node, new_tree,rank)


  #团队玩家
  elif ori_node.player != 0:
    new_node = new_tree.addNode(1,parent = parent_node,actionName=ori_node.incoming_action_name) 
    new_node.ori_player = ori_node.player

    #寻找原树的每一个子节点，通过动作来将原树该动作下的子节点进行转换，并接到转换后的树上
    for i in range(len(ori_node.children)) :
        pub_convert_v4(ori_node.children[i],new_node,new_tree,rank)
        #至此，转换完毕

