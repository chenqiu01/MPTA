from data_structures.trees import Tree, Node, ChanceNode
import copy

def build_leduc_tree(num_players, num_of_suits, num_of_ranks, betting_parameters):
    """
    Build a tree for the game of Leduc with a given number of players, suits, ranks and betting parameters.
    """

    root = ChanceNode(0)
    
    tree = Tree(num_players, 0, root)

    tree.suits=num_of_suits
    tree.ranks=num_of_ranks

    hands = build_all_possible_hands(num_players, [c for c in range(0,num_of_ranks) for _ in range(num_of_suits)])
    hand_probability = 1 / len(hands)
    all_nodes = []
    # print(hands)
    for hand in hands:
        n = tree.addNode(0, parent = root, probability = hand_probability, actionName = str(hand))
        all_nodes.append(n)
        empty_previous_moves = [['n' for _ in range(num_players)], ['n' for _ in range(num_players)]] # 第零轮和第一轮，玩家最后一次行动的记录
        # print(empty_previous_moves)
        all_nodes += build_leduc_hand_tree(hand, empty_previous_moves, 0, 0, n, betting_parameters, tree)
        
    # Merge nodes into infosets based on the available information at each node
    for i in range(len(hands)):
        for j in range(i+1, len(hands)):
            create_information_sets(root.children[i], root.children[j])
            
    return tree

def build_leduc_hand_tree(hand, previous_moves, current_player, current_round, current_node, betting_parameters, tree):
    """
    Recursively build the subtree for the Leduc game where the hand is fixed.
    """

    #手牌信息在第0轮和第一轮不同，因为揭露公共牌
    if(current_round == 0):
        current_node.known_information = (hand[current_player], -1)
    else:
        current_node.known_information = (hand[current_player], hand[len(hand) - 1])

    actionPrefix = 'p' + str(current_player)
    num_players = len(hand)-1
    
    next_player = (current_player + 1) % num_players

    #下一个玩家已经bet or flod，则跳过该玩家；公共牌揭露后，这名玩家在第0轮已经弃牌，则跳过该玩家
    while(previous_moves[current_round][next_player] in ['b', 'f'] or (current_round == 1 and previous_moves[0][next_player] == 'f')):
        next_player = (next_player + 1) % num_players

    nodes = []
    
    # There was a bet, so I can only call or fold
    if('b' in previous_moves[current_round]):
        # If the current and the next player are the same, we are at the last decision node of this round
        if(current_player == next_player):
            if(current_round == 0):
                last_player = current_player

                # ---------------------------------------------
                # CASE 1: the last player of round 1 calls,最后一名执行动作的玩家选择了跟注
                # ---------------------------------------------
                non_folded_players = [p for p in range(num_players) if previous_moves[0][p] != 'f'] #在场玩家
                current_player = non_folded_players[0]
                next_player = non_folded_players[1]
                current_round = 1
                # actionPrefix = 'p' + str(current_player)
                temp_actionPrefix = actionPrefix

                previous_moves[0][last_player] = 'b'
                lastCallNode = tree.addNode(current_player, parent = current_node, actionName = actionPrefix + 'b')#第一轮的首个玩家执行动作的节点
                lastCallNode.known_information = (hand[current_player], hand[len(hand) - 1])
                nodes.append(lastCallNode)



                actionPrefix = 'p' + str(current_player)

                #孩子走call情况
                previous_moves[current_round][current_player] = 'c'  
                checkNode1 = tree.addNode(next_player, parent = lastCallNode, actionName = actionPrefix + 'c')
                nodes.append(checkNode1)
                nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, checkNode1, betting_parameters, tree)

                #孩子走bet情况
                previous_moves[current_round][current_player] = 'b'
                betNode1 = tree.addNode(next_player, parent = lastCallNode, actionName = actionPrefix + 'b')
                nodes.append(betNode1)
                nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, betNode1, betting_parameters, tree)

                # ---------------------------------------------
                # CASE 2: the last player of round 1 folds,最后一名执行动作的玩家选择了弃牌
                # ---------------------------------------------

                previous_moves[current_round][current_player] = 'n' # Clear data from CASE 1
                if(len(non_folded_players) == 2):
                    # I am one of the two played that have not folded during the first round, so if I fold the game is over
                    previous_moves[0][last_player] = 'f'
                    foldLeaf = tree.addLeaf(current_node, leduc_utility(hand, previous_moves, betting_parameters), actionName = temp_actionPrefix + 'f')
                else:
                    if(last_player == non_folded_players[0]): #从玩家x结束，而其他玩家都执行完动作后，又到了玩家x在这里弃牌，则揭开公共牌后应从x的未弃牌下家开始
                        current_player = non_folded_players[1]
                        next_player = non_folded_players[2]
                    elif(last_player == non_folded_players[1]):#玩家x弃牌了，跳过玩家x顺序执行
                        next_player = non_folded_players[2]

                    previous_moves[0][last_player] = 'f'
                    lastFoldNode = tree.addNode(current_player, parent = current_node, actionName = temp_actionPrefix + 'f')

                    lastFoldNode.known_information = (hand[current_player], hand[len(hand) - 1])
                    nodes.append(lastFoldNode)

                    actionPrefix = 'p' + str(current_player)

                    previous_moves[current_round][current_player] = 'c'
                    checkNode2 = tree.addNode(next_player, parent = lastFoldNode, actionName = actionPrefix + 'c')
                    nodes.append(checkNode2)
                    nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, checkNode2, betting_parameters, tree)
                    
                    previous_moves[current_round][current_player] = 'b'
                    betNode2 = tree.addNode(next_player, parent = lastFoldNode, actionName = actionPrefix + 'b')
                    nodes.append(betNode2)
                    nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, betNode2, betting_parameters, tree)
            #第1轮
            else:
                # We are at the last move of the last round, so generate leaves
                previous_moves[current_round][current_player] = 'b'
                l = tree.addLeaf(current_node, leduc_utility(hand, previous_moves, betting_parameters), actionName = actionPrefix + 'b')
                nodes.append(l)

                previous_moves[current_round][current_player] = 'f'
                l = tree.addLeaf(current_node, leduc_utility(hand, previous_moves, betting_parameters), actionName = actionPrefix + 'f')
                nodes.append(l)
            
            return nodes
        
        #不是当前轮次的终结位，前置玩家bet后，我可以bet or fold
        previous_moves[current_round][current_player] = 'b'
        callNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'b')
        nodes.append(callNode)
        nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, callNode, betting_parameters, tree)
        
        foldNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'f')
        nodes.append(foldNode)
        previous_moves[current_round][current_player] = 'f'
        nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, foldNode, betting_parameters, tree)
    
    #这轮中还未有玩家bet
    else: # No bet yet, so I can check or bet
        previous_moves[current_round][current_player] = 'c'
        num_players_that_checked = len(list(filter(lambda el: el == 'c', previous_moves[current_round]))) #call过的玩家
        num_players_in_game = len(list(filter(lambda el: el != 'f', previous_moves[0]))) if current_round == 1 else num_players #未弃牌的玩家
        #所有玩家都call
        if(num_players_that_checked == num_players_in_game):
            if(current_round == 0):

                lastCheckNode = tree.addNode(0, parent = current_node, actionName = actionPrefix + 'c')
                lastCheckNode.known_information = (hand[0], hand[len(hand) - 1])
                nodes.append(lastCheckNode)

                # This is the start of the second betting round, so we restart from the check/bet choice of the first player
                new_current_player = 0
                new_next_player = 1
                new_current_round = 1
                new_actionPrefix = 'p' + str(new_current_player)

                previous_moves[new_current_round][new_current_player] = 'c'  
                checkNode = tree.addNode(new_next_player, parent = lastCheckNode, actionName = new_actionPrefix + 'c')
                nodes.append(checkNode)
                nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), new_next_player, new_current_round, checkNode, betting_parameters, tree)
                    
                previous_moves[new_current_round][new_current_player] = 'b'
                betNode = tree.addNode(new_next_player, parent = lastCheckNode, actionName = new_actionPrefix + 'b')
                nodes.append(betNode)
                nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), new_next_player, new_current_round, betNode, betting_parameters, tree)

                previous_moves[new_current_round][new_current_player] = 'n' # Cleanup for the code after the end of the if
            else:
                l = tree.addLeaf(current_node, leduc_utility(hand, previous_moves, betting_parameters), actionName = actionPrefix + 'c')
                nodes.append(l)
        # 前置位玩家都call，且当前玩家选择call
        else:        
            checkNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'c')
            nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, checkNode, betting_parameters, tree)
            nodes.append(checkNode)

        # 前置位玩家都call，且当前玩家选择bet 
        previous_moves[current_round][current_player] = 'b'
        betNode = tree.addNode(next_player, parent = current_node, actionName = actionPrefix + 'b')
        nodes.append(betNode)
        nodes += build_leduc_hand_tree(hand, copy.deepcopy(previous_moves), next_player, current_round, betNode, betting_parameters, tree)

    return nodes

def create_information_sets(node1, node2):
    """
    Takes two identically shaped trees (rooted at node1 and node2) and put all the nodes
    belonging to the same player and having access to the same information in pairwise information sets.
    """

    if(node1.isLeaf()):
        return
    
    if node1.player != -42:#当该节点不是虚拟机会节点，虚拟节点是chance node，Player为-42
        if(node1.player == node2.player and node1.known_information == node2.known_information):
            iset_id = min(node1.information_set, node2.information_set)
            node1.information_set = iset_id
            node2.information_set = iset_id
    
    for i in range(len(node1.children)):
        create_information_sets(node1.children[i], node2.children[i])

#V2,V3转换时使用
def create_information_sets_in_convert(node1, node2, players_to_merge): #待修改
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
    if(player in players_to_merge):
        iset_id = min(node1.information_set, node2.information_set)
        node1.information_set = iset_id
        node2.information_set = iset_id
    
    # print("对比：",node1.id,":",len(node1.children),node2.id,":",len(node2.children))
    for i in range(len(node1.children)):
        create_information_sets_in_convert(node1.children[i], node2.children[i], players_to_merge)

def build_all_possible_hands(num_players, cards):
    """
    Build all the possible hands for the game of Leduc with a given number of players and a given set of cards.
    Returns a list of lists, where each inner list has one card per player plus one public card.
    """

    unique_cards = list(set(cards))

    if(num_players <= 0):
        return [[card] for card in unique_cards]
    
    smaller_hands = build_all_possible_hands(num_players-1, cards)
    hands = []
    
    for hand in smaller_hands:

        for card in hand:
            cards.remove(card)

        unique_remaining_cards = list(set(cards))

        for card in unique_remaining_cards:
            hands.append(hand + [card])

        for card in hand:
            cards.append(card)
            
    return hands

def leduc_utility(hand, previous_moves, betting_parameters):
    """
    Get the utility of a Leduc game given the hand, how the players have played and the betting parameters.
    betting_parameters是第零轮和第一轮加注的最小筹码大小
    """

    num_players = len(hand) - 1
    public_card = hand[num_players]

    pot = num_players + len(list(filter(lambda el: el == 'b', previous_moves[0]))) * betting_parameters[0] + \
                        len(list(filter(lambda el: el == 'b', previous_moves[1]))) * betting_parameters[1]
    showdown_participants = [p for p in range(num_players) if previous_moves[0][p] != 'f' and previous_moves[1][p] != 'f']
    winners = list(filter(lambda p: hand[p] == public_card, showdown_participants))

    if(len(winners) == 0):
        max_card = max([hand[i] for i in showdown_participants])
        winners = list(filter(lambda p: hand[p] == max_card, showdown_participants))

    utility = [-1] * num_players
    for p in range(num_players):
        if previous_moves[0][p] == 'b':
            utility[p] -= betting_parameters[0]        
        if previous_moves[1][p] == 'b':
            utility[p] -= betting_parameters[1]
        if(p in winners):
            utility[p] += pot / len(winners)

    #三个个人收益转换为团队均分利益
    u=[utility[0]]
    for p in range(1, num_players):
        u.append(-u[0]/(num_players-1))
    # print(u)
    return u
    # return utility



#多人转换算法（0704+）
#rank仅用于团队成员转化
#leduc 动作为3个，raise(r),fold(f),call(c)
def pub_team_convert_leduc(ori_tree,rank,num_players):

    global hands
    #取出手牌信息
    num_of_ranks=ori_tree.ranks
    num_of_suits=ori_tree.suits
    hands = build_all_possible_hands(num_players, [c for c in range(0,num_of_ranks) for _ in range(num_of_suits)])
    # hands=[]
    # for i in ori_tree.root.actionNames:
    #     hand=[]
    #     for j in range(len(i)):
    #         cha = i[j]
    #         if ord(cha)>=48 and ord(cha)<=57 :
    #             hand.append(int(cha))
    #     hands.append(hand)
    # print(hands)

    #先构建一颗新树，再转化内部的节点
    new_root = ChanceNode(0)
    new_tree = Tree(2, 0, new_root)
    new_tree.ori_numOfPlayers = ori_tree.numOfPlayers
    #修改转换版本，v2为原论文方法，v3为开会提出方法
    version = 4
    if version == 2:
        pub_convert_leduc_v2(ori_tree.root,None,new_tree,rank)
        new_tree.convert_version =2
    elif version == 3:
        pub_convert_leduc_v3(ori_tree.root,None,new_tree,rank, [0]*ori_tree.numOfPlayers)
        new_tree.convert_version =3
    elif version == 4:
        pub_convert_leduc_v4(ori_tree.root,None,new_tree,rank)
        new_tree.convert_version =4
    print("use convert version is ",version)
    #根节点分配分支的概率，也就是发牌各牌型概率
    pre=len(ori_tree.root.children)
    new_tree.root.distribution=[1/pre]*pre

    #将转换后树的根节点的玩家置为-1，用于区分sequence时和虚拟机会节点的差异
    new_tree.root.player = -1

    root=new_tree.root
    if version == 4:
        new_tree.print_tree("conver_leduc_tree_v"+str(version))
        return new_tree
    
    #转换后需要使用新的信息集归并方式,适用于v3,v2
    for i in range(len(hands)):
        for j in range(i+1, len(hands)):
            players_to_merge = []
            for p in range(num_players):
                if(hands[i][p] == hands[j][p]):
                    players_to_merge.append(p)  
            # create_information_sets(root.children[i], root.children[j], players_to_merge)
            create_information_sets_in_convert(root.children[i], root.children[j], players_to_merge)
    
    #把树一些信息保存到本地
    new_tree.print_tree("conver_leduc_tree_v"+str(version))

    return new_tree

#转换多人团队博弈到二人零和博弈,3.0想法,（复制从而新加函数时，内部递归函数名记得修改）（1028+）
#rank仅用于团队成员转化 
def pub_convert_leduc_v4(ori_node,parent_node,new_tree,rank):
  #叶节点
  if ori_node.isLeaf():
    new_tree.addLeaf(parent_node, ori_node.utility,actionName =ori_node.incoming_action_name)

  #机会节点和敌手节点
  elif ori_node.player == 0 or ori_node.isChance():
    
    if ori_node.isChance():#leduc也只有根节点会是chance
        for i in range(len(ori_node.children)):
            pub_convert_leduc_v4(ori_node.children[i], new_tree.root, new_tree, rank)
    if ori_node.player == 0:
        new_node = new_tree.addNode(ori_node.player,parent = parent_node,actionName=ori_node.incoming_action_name)
        new_node.ori_player = ori_node.player
        new_node.known_information=ori_node.known_information
        for i in range(len(ori_node.children)):
            pub_convert_leduc_v4(ori_node.children[i], new_node, new_tree,rank)


  #团队玩家
  elif ori_node.player != 0:
    new_node = new_tree.addNode(1,parent = parent_node,actionName=ori_node.incoming_action_name) 
    new_node.known_information=ori_node.known_information
    new_node.ori_player = ori_node.player

    #寻找原树的每一个子节点，通过动作来将原树该动作下的子节点进行转换，并接到转换后的树上
    for i in range(len(ori_node.children)) :
        pub_convert_leduc_v4(ori_node.children[i],new_node,new_tree,rank)
        #至此，转换完毕


#转换多人团队博弈到二人零和博弈,2.0想法,（复制从而新加函数时，内部递归函数名记得修改）（0629+）
#rank仅用于团队成员转化 #2071个节点
def pub_convert_leduc_v3(ori_node,parent_node,new_tree,rank,flags):
  #叶节点
  if ori_node.isLeaf():
    new_tree.addLeaf(parent_node, ori_node.utility,actionName =ori_node.incoming_action_name)

  #机会节点和敌手节点,针对Kuhn
  elif ori_node.player == 0 or ori_node.isChance():
    
    if ori_node.isChance():#leduc也只有根节点会是chance
        for i in range(len(ori_node.children)):
            pub_convert_leduc_v3(ori_node.children[i], new_tree.root, new_tree, rank, [0]*new_tree.ori_numOfPlayers)
    if ori_node.player == 0:
        new_node = new_tree.addNode(ori_node.player,parent = parent_node,actionName=ori_node.incoming_action_name)
        new_node.ori_player = ori_node.player
        new_node.known_information=ori_node.known_information
        for i in range(len(ori_node.children)):
            pub_convert_leduc_v3(ori_node.children[i], new_node, new_tree,rank, flags)


  #团队玩家
  elif ori_node.player != 0:
    new_node = new_tree.addChanceNode(parent = parent_node,actionName=ori_node.incoming_action_name)
    first_infset_id =-1
    if flags[ori_node.player] == 0:
        flags[ori_node.player] = 1
        for i in range(rank):
            #中间的dummy 节点,其下孩子归属同一信息集
            if first_infset_id == -1 :
                temp_chance_node = new_tree.addNode(1,parent = new_node,probability=1/rank,actionName=str([i+1])) 
                temp_chance_node.known_information=ori_node.known_information
                first_infset_id = temp_chance_node.information_set
                temp_chance_node.ori_player = ori_node.player
            else:
                temp_chance_node = new_tree.addNode(1,information_set=first_infset_id,parent = new_node,probability=1/rank,actionName=str([i+1])) 
                temp_chance_node.known_information=ori_node.known_information
                temp_chance_node.ori_player = ori_node.player

            #寻找原树的每一个子节点，通过动作来将原树该动作下的子节点进行转换，并接到转换后的树上
            for i in range(len(ori_node.children)) :
                pub_convert_leduc_v3(ori_node.children[i],temp_chance_node,new_tree,rank,flags)
            #至此，转换中间的chance节点（temp_chance_node）转换完毕
    else:#前面已经知道该玩家拿什么手牌，所以在这里只走一条分支，即剪枝
        temp_chance_node = new_tree.addNode(1,parent = new_node,probability=1,actionName=ori_node.known_information[0]) 
        temp_chance_node.known_information=ori_node.known_information
        first_infset_id = temp_chance_node.information_set
        temp_chance_node.ori_player = ori_node.player
        for i in range(len(ori_node.children)) :
            pub_convert_leduc_v3(ori_node.children[i],temp_chance_node,new_tree,rank,flags)


#数字转换为动作，用于历史记录时从legal_action（数字）转到call,bet,fold,raise（字符）,玩家为团队成员时使用
def num2act(num):
    if num == 0 :
        return 'c'
    elif num == 1:
        return 'b'
    elif num == 2 :
        return 'f'
    elif num == 4 :
        return 'r'
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

#生成处方,返回['AAA','AAB',...,'BBB']类型的处方,leduc需要修改,不同类游戏的num2act构建自己的数字对字符的动作对应，使用时选择自己的legal_action
def build_prescription(legal_actions,num_prescription_place,player,hand):
    # temp_legal_action=[]
    # for a in legal_actions:
    #     temp_legal_action.append(num2act(a))
    temp_legal_action = legal_actions
    temp_prescription=[]
    history=''
    build_prescription_pro(temp_legal_action,num_prescription_place,temp_prescription,history)
    #处方有序，选中动作相同的放在一起，如pp[p],bb[p]放在一起，pp[b],pb[b]放在一起，再合并.不然会出问题，见日志07/12
    prescription_action=[]
    for i in range(len(legal_actions)):
        prescription_action.append([])
    for i in range(len(temp_prescription)):
        for j in range(len(legal_actions)):
            if temp_prescription[i][hand[player]] == legal_actions[j] :
                prescription_action[j].append(temp_prescription[i])
                break
    prescription=[]
    for i in range(len(prescription_action)):
        prescription += prescription_action[i]
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
hand=[]
index=0
def pub_convert_leduc_v2(ori_node,parent_node,new_tree,rank):

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
                pub_convert_leduc_v2(ori_node.children[i], new_tree.root, new_tree,rank)
        if ori_node.player == 0:
            #如果玩家0父节点为根节点，会在根节点最后处理；如果父节点是dc，则概率为1
            new_node = new_tree.addNode(ori_node.player,probability = 1,parent = parent_node,actionName=ori_node.incoming_action_name)
            new_node.ori_player = ori_node.player
            for i in range(len(ori_node.children)):
                pub_convert_leduc_v2(ori_node.children[i], new_node, new_tree,rank)


    #团队玩家
    elif ori_node.player != 0:
        #如果玩家0不是敌人时，逻辑需要修改，概率为1是给虚拟机会连接时用的
        if parent_node.player == 0:
            new_node = new_tree.addNode(1,parent = parent_node,probability = 1,actionName=ori_node.incoming_action_name)
            new_node.ori_player = ori_node.player
        else :
            new_node = new_tree.addNode(1,parent = parent_node,probability = 1,actionName=parent_node.incoming_action_name[hand[parent_node.parent.ori_player]])
            new_node.ori_player = ori_node.player
        
        #判一下处方的合法动作通过哪几个动作构成
        legal_actions = []
        for i in range(len(ori_node.actionNames)):
            legal_actions.append(ori_node.actionNames[i][-1])

        prescription = build_prescription(legal_actions,rank,ori_node.player,hand)
        for i in range(len(prescription)):
            #中间的dummy chance节点
            temp_chance_node = new_tree.addChanceNode(parent = new_node,actionName=prescription[i]) 
            #寻找原树的每一个子节点，通过动作来将原树该动作下的子节点进行转换，并接到转换后的树上
            for j in range(len(legal_actions)):
                if prescription[i][hand[ori_node.player]] == legal_actions[j]:
                    pub_convert_leduc_v2(ori_node.children[j],temp_chance_node,new_tree,rank)
            #至此，转换中间的chance节点（temp_chance_node）转换完毕
