from data_structures.trees import Tree, Node, ChanceNode
from functools import reduce
from enum import Enum
from games.utilities import all_permutations

class TieSolver(Enum):
    Accumulate = 0
    DiscardIfAll = 1
    DiscardIfHigh = 2
    DiscardAlways = 3
    CyclicUtility = 4 # More utility type than TieSolver...

def build_goofspiel_tree(num_players, rank, tie_solver = TieSolver.Accumulate):
    """
    Build a tree for the game of Goofspiel with a given number of players and a given number of ranks in the deck (i.e. how
    many cards).
    """

    root = ChanceNode(0)

    tree = Tree(num_players, 0, root)

    hands = all_permutations(list(range(1, rank+1)))
    hand_probability = 1 / len(hands)
    information_sets = {}
    
    for hand in hands:
        node_known_info = (0, 0, tuple(hand[:1]), tuple([() for p in range(num_players)]))
        if node_known_info in information_sets:
            information_set = information_sets[node_known_info]
        else:
            information_set = -1

        n = tree.addNode(0, parent = root, probability = hand_probability, actionName = str(hand), information_set = information_set)

        if information_set == -1:
            information_sets[node_known_info] = n.information_set

        #print("remaining card: ", [list(range(1, rank+1)) for p in range(num_players)])
        build_goofspiel_hand_tree(hand, [list(range(1, rank+1)) for p in range(num_players)],
                                  [[] for p in range(num_players)], 0, 0, n, tree, tie_solver, information_sets)
            
    return tree

def build_goofspiel_hand_tree(hand, remaining_cards, played_cards, current_round, current_player, current_node, tree, tie_solver,
                              information_sets):
    """
    Recursively build the subtree for the goofspiel game where the hand is fixed.
    """

    num_players = tree.numOfPlayers
    if(current_player == num_players-1):
        next_player = 0
        next_round = current_round + 1
    else:
        next_player = current_player + 1
        next_round = current_round
    
    # remaining_cards的格式是[1, 2, 3]，代表当前玩家剩下的分数牌
    current_player_cards = remaining_cards[current_player].copy()

    # Create a leaf as a children of the last effective decision node (there is no decision for players that
    # have only their last card in hand)
    if(len(remaining_cards[current_player]) == 2 and len(remaining_cards[next_player]) == 1):
        for card in current_player_cards:
            actionName = "p" + str(current_node.player) + "c" + str(card)
            remaining_cards[current_player].remove(card)
            #print("remaining_cards: ", remaining_cards)
            played_cards[current_player].append(card)
            #print("played_cards: ", played_cards)
            final_played_cards = [played_cards[i] + remaining_cards[i] for i in range(len(played_cards))]
            #print("final_played_cards: ", final_played_cards)
            l = tree.addLeaf(parent = current_node, utility = goofspiel_utility(hand, final_played_cards, tie_solver),
                             actionName = actionName)
            remaining_cards[current_player].append(card)
            played_cards[current_player].remove(card)
        return

    for card in current_player_cards:
        actionName = "p" + str(current_node.player) + "c" + str(card)

        node_known_info = (next_player, next_round, tuple(hand[:next_round+1]), tuple([tuple(c[:next_round]) for c in played_cards]))
        if node_known_info in information_sets:
            information_set = information_sets[node_known_info]
        else:
            information_set = -1

        n = tree.addNode(next_player, information_set, parent = current_node, actionName = actionName)
        n.remain_cards = remaining_cards[next_player].copy()

        if information_set == -1:
            information_sets[node_known_info] = n.information_set

        remaining_cards[current_player].remove(card)
        played_cards[current_player].append(card)
        build_goofspiel_hand_tree(hand, remaining_cards, played_cards, next_round, next_player, n, tree, tie_solver,
                                           information_sets)
        remaining_cards[current_player].append(card)
        played_cards[current_player].remove(card)

def build_all_possible_hands(num_players, ranks):
    """
    Build all the possible hands for the game of Goofspiel with a given number of players and a given set of cards.
    """
    perm = all_permutations(list(range(1, ranks+1)))

    if(num_players == 0):
        return list(map(lambda el: [el], perm))

    hands = []
    smaller_hands = build_all_possible_hands(num_players-1, ranks)

    for p in perm:
        for hand in smaller_hands:
            hands.append(hand + [p])

    #print("hand: ", hands)
    return hands

def goofspiel_utility(hand, moves, tie_solver = TieSolver.Accumulate):
    """
    Get the utility of a Goofspiel game given the hand and how the players have played.
    """
    #moves是玩家下注的顺序，比如[[3, 2, 1], [3, 1, 2], [3, 2, 1]]代表玩家0，1，2的下注顺序
    #这里表示第一轮下注是3，3，3 第二轮是2，1，2 第三轮是1，2，1
    num_players = len(moves)
    utility = [0] * num_players
    # additional_utility = 0

    #比较每一轮下注的大小，下注最大的玩家获得hand中的点数
    for i in range(len(hand)):
        round_moves = [moves[p][i] for p in range(num_players)]
        max_bet_per_round = max(round_moves)
        for j in range(num_players):
            if round_moves[j] == max_bet_per_round:
                utility[j] += hand[i]

    #print("former_utility: ", utility)

    utility_max = max(utility)

    # 所有人分数相等，没有赢家
    if len(set(utility)) == 1:
        return [0] * num_players

    # 分数不等的情况，只看玩家0即对手是不是赢家
    if utility[0] == utility_max:
        utility[0] = 1 * (num_players - 1)
        for i in range(1, num_players):
            utility[i] = -1
    else:
        utility[0] = -1 * (num_players - 1)
        for i in range(1, num_players):
            utility[i] = 1
    
    # for i in range(len(hand)):
    #     round_moves = [moves[p][i] for p in range(num_players)]
    #     winner = winner_player(round_moves, tie_solver)

    #     if(winner == -1):
    #         if tie_solver == TieSolver.Accumulate or tie_solver == TieSolver.CyclicUtility:
    #             additional_utility += hand[i]
    #     else:
    #         u[winner] += hand[i] + additional_utility
    #         additional_utility = 0

    # if tie_solver == TieSolver.CyclicUtility:
    #     round_zero_moves = [moves[p][0] for p in range(num_players)]
    #     first_cards_equal = (max(round_zero_moves) == min(round_zero_moves))
    #     highest_card = max(hand)
    #     tot = 0
    #     for (i, uval) in enumerate(u):
    #         tot += uval * (i + 1)
    #     u = [0 for _ in u]
    #     u[tot % num_players] = 2 if first_cards_equal else 1

    #print("later_utility: ", utility)

    return utility

def winner_player(round_moves, tie_solver):
    """
    Calculate the winner player given the cards that were played in a round.
    """

    moves_dict = {}
    for p in range(len(round_moves)):
        move = round_moves[p]
        if(move in moves_dict):
            moves_dict[move].append(p)
        else:
            moves_dict[move] = [p]

    single_moves = list(filter(lambda el: len(el[1]) == 1, moves_dict.items()))

    if(len(single_moves) == 0):
        return -1

    if(len(single_moves) < len(round_moves) and tie_solver == TieSolver.DiscardAlways):
        # At least two players have played the same card, so under the DiscardAlways tie solver we have no winner
        return -1

    winner = max(single_moves, key = lambda el: el[0])[1][0]

    if(round_moves[winner] != max(round_moves) and tie_solver == TieSolver.DiscardIfHigh):
        # There was a tie on the higher card played, so under the DiscardIfHigh tie solver we have no winner
        #print("move: ", round_moves)
        return -1

    #print("move: ", round_moves)
    #print("winner: ", winner)

    return winner

#多人转换算法（0704+）
#rank仅用于团队成员转化

def pub_team_convert_goofspiel(ori_tree,rank,num_players):
    global hands
    #先构建一颗新树，再转化内部的节点
    new_root = ChanceNode(0)
    new_tree = Tree(2, 0, new_root)
    new_tree.ori_numOfPlayers = ori_tree.numOfPlayers

    #手牌
    hands = all_permutations(list(range(1, rank + 1)))
    # print("hands in function pub_team_convert_goofspiel:", hands)
    # hands=[]
    # for i in ori_tree.root.actionNames:
    #     hand=[]
    #     for j in range(len(i)):
    #         cha = i[j]
    #         if ord(cha)>=48 and ord(cha)<=57 :
    #             hand.append(int(cha))
    #     hands.append(hand)

    #修改转换版本，v2为原论文方法，v3为开会提出方法
    version = 3
    if version ==2 :
        pub_convert_v2(ori_tree.root,None,new_tree,rank)
        new_tree.convert_version =2
    elif version == 3 :
        pub_convert_v3(ori_tree.root, None, new_tree, rank)
        new_tree.convert_version =3
    
    
    pre=len(ori_tree.root.children)
    new_tree.root.distribution=[1/pre]*pre
    root=new_tree.root
    #将转换后树的根节点的玩家置为-1，用于区分sequence时和虚拟机会节点的差异
    root.player = -1
    #对比用例
    # compare_tree = copy.deepcopy(new_tree)


    #转换后需要使用新的信息集归并方式,适用于v2,v3

    # for i in range(len(hands)):
    #     for j in range(i+1, len(hands)):
    #         players_to_merge = []
    #         for p in range(num_players):
    #             if(hands[i][p] == hands[j][p]):
    #                 players_to_merge.append(p) 
    #         # create_information_sets(root.children[i], root.children[j], players_to_merge)
    #         create_information_sets_in_convert(root.children[i], root.children[j], players_to_merge)
       

    # #对比纠错使用
    # for i in range(len(hands)):
    #     for j in range(i+1, len(hands)):
    #         players_to_merge = []
    #         for p in range(num_players):
    #             if(hands[i][p] == hands[j][p]):
    #                 players_to_merge.append(p)  
    #         create_information_sets(compare_tree.root.children[i], compare_tree.root.children[j], players_to_merge)
    #         # create_information_sets_in_convert(compare_tree.root.children[i], compare_tree.root.children[j], players_to_merge)


    new_tree.print_tree("conver_goofspiel_tree_v3")
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

    else :
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

#转换多人团队博弈到二人零和博弈,2.0想法,（复制从而新加函数时，内部递归函数名记得修改）（0629+）
#rank仅用于团队成员转化 #2071个节点
# hand = []
# index = 0
def pub_convert_v3(ori_node,parent_node,new_tree,rank):
  #叶节点
#   global hands, hand, index
#   if ori_node.parent != None:
#     if ori_node.parent.isChance():
#       hand=hands[index]
#       index += 1

  if ori_node.isLeaf():
    new_tree.addLeaf(parent_node, ori_node.utility, actionName =ori_node.incoming_action_name)

  #机会节点和敌手节点,针对goofspiel
  elif ori_node.player == 0 or ori_node.isChance():
    if ori_node.isChance():#goofspiel只有根节点会是chance
        for i in range(len(ori_node.children)):
            pub_convert_v3(ori_node.children[i], new_tree.root, new_tree,rank)
    if ori_node.player == 0:
        new_node = new_tree.addNode(ori_node.player,parent = parent_node,actionName=ori_node.incoming_action_name)
        new_node.ori_player = ori_node.player
        for i in range(len(ori_node.children)):
            pub_convert_v3(ori_node.children[i], new_node, new_tree,rank)

  #团队玩家
  elif ori_node.player != 0:
      new_node = new_tree.addChanceNode(parent = parent_node,actionName=ori_node.incoming_action_name)
      first_infset_id =-1
      for i in ori_node.remain_cards:
          #中间的dummy chance节点
          if first_infset_id == -1 :
              temp_chance_node = new_tree.addNode(1,parent = new_node,probability=1/len(ori_node.remain_cards),actionName=str([i]))
              #remain_card[ori_node.player].remove(i)
              first_infset_id = temp_chance_node.information_set
              temp_chance_node.ori_player = ori_node.player
          else :
              temp_chance_node = new_tree.addNode(1, information_set=first_infset_id, parent = new_node, probability=1/len(ori_node.remain_cards), actionName=str([i]))
              #remain_card[ori_node.player].remove(i)
              temp_chance_node.ori_player = ori_node.player
          #寻找原树的每一个子节点，通过动作来将原树该动作下的子节点进行转换，并接到转换后的树上
          for j in range(len(ori_node.children)) :
              pub_convert_v3(ori_node.children[j],temp_chance_node,new_tree,rank)
          #至此，转换中间的chance节点（temp_chance_node）转换完毕




#数字转换为动作，用于历史记录时从legal_action（数字）转到pass,bet（字符）,玩家为团队成员时使用
def num2act(num):
  if num == 0 :
    return 'p'
  elif num == 1:
    return 'b'
  return

#生成处方的中间过程(0613+),legal_actions:合法动作列表，num_prescription_place：处方长度
#prescription：初始传入一个空列表，用于存储生成的处方；history:初始传入空历史
#利用递归的树形思想形成固定长度的处方
def build_prescription_pro(legal_actions,num_prescription_place,prescription,history):
  if len(history) == num_prescription_place :
    prescription.append(history)
    return
  else :
    for i in legal_actions:
      build_prescription_pro(legal_actions,num_prescription_place,prescription,history+str(i))

#生成处方,返回['AAA','AAB',...,'BBB']类型的处方,leduc需要修改
def build_prescription(legal_actions,num_prescription_place,player,hand):
    temp_legal_action=[]
    for a in legal_actions:
        temp_legal_action.append(num2act(a))
    temp_prescription=[]
    history=''
    build_prescription_pro(temp_legal_action,num_prescription_place,temp_prescription,history)
    prescription_1=[]
    prescription_2=[]
    for i in range(len(temp_prescription)):
        if temp_prescription[i][hand[player]] == "p" :
            prescription_1.append(temp_prescription[i])
        else :
            prescription_2.append(temp_prescription[i])
    prescription = prescription_1 + prescription_2
    return prescription


#用于处理处方四个p，四个b信息集不同的问题
p_gra_id = -1 #p时的爷节点
b_gra_id = -1
p_inf_id = -1 #记录之前的infor_set_id
b_inf_id = -1
#转换多人团队博弈到二人零和博弈,原论文想法,（复制从而新加函数时，内部递归函数名记得修改）（0629+）
#rank仅用于团队成员转化
#add chance node的话会不会影响cfr的使用，因为以往只有根节点是机会节点
#hand为全局变量,记录分支下的手牌
#3张牌5395个节点
index=0
hand=[]
def pub_convert_v2(ori_node,parent_node,new_tree,rank):

    global hand,hands,p_gra_id,b_gra_id,p_inf_id,b_inf_id,index

    #递归到根节点的孩子时，一种新的手牌形式开始，进行记录
    if ori_node.parent != None:
        if ori_node.parent.isChance():
            hand=hands[index]
            index += 1

            # temp_hand =[]
            # #字符串处理，拿出其中的数字
            # for i in range(len(ori_node.incoming_action_name)):
            #     cha=ori_node.incoming_action_name[i]
            #     if ord(cha)>=48 and ord(cha)<=57 :
            #         temp_hand.append(int(cha))
            #         hand = temp_hand.copy()
    #叶节点
    if ori_node.isLeaf():
        new_node = new_tree.addLeaf(parent_node, ori_node.utility,actionName =ori_node.incoming_action_name)

    #机会节点和敌手节点,针对Kuhn
    elif ori_node.player == 0 or ori_node.isChance():

        if ori_node.isChance():#Kuhn只有根节点会是chance
            for i in range(len(ori_node.children)):
                pub_convert_v2(ori_node.children[i], new_tree.root, new_tree,rank)
        if ori_node.player == 0:
            #如果玩家0父节点为根节点，会在根节点最后处理；如果父节点是dc，则概率为1
            new_node = new_tree.addNode(ori_node.player,probability = 1,parent = parent_node,actionName=ori_node.incoming_action_name)
            new_node.ori_player = ori_node.player
            for i in range(len(ori_node.children)):
                pub_convert_v2(ori_node.children[i], new_node, new_tree, rank)

    #团队玩家
    elif ori_node.player != 0:
        #如果玩家0不是敌人时，逻辑需要修改，概率为1是给虚拟机会连接时用的
        if parent_node.player == 0:
            new_node = new_tree.addNode(1,parent = parent_node,probability = 1,actionName=ori_node.incoming_action_name)
            new_node.ori_player = ori_node.player
        else :
            new_node = new_tree.addNode(1,parent = parent_node,probability = 1,actionName=parent_node.incoming_action_name[hand[parent_node.parent.ori_player]])
            new_node.ori_player = ori_node.player

        prescription = build_prescription([0,1], rank, ori_node.player, hand)
        for i in range(len(prescription)):
            #中间的dummy chance节点
            temp_chance_node = new_tree.addChanceNode(parent = new_node,actionName=prescription[i]) 
            #寻找原树的每一个子节点，通过动作来将原树该动作下的子节点进行转换，并接到转换后的树上
            if prescription[i][hand[ori_node.player]] == 'p':
                pub_convert_v2(ori_node.children[0], temp_chance_node, new_tree,rank)
            else :
                pub_convert_v2(ori_node.children[1], temp_chance_node, new_tree,rank)

            #至此，转换中间的chance节点（temp_chance_node）转换完毕