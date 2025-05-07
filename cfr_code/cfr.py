from functools import reduce
import time
import json


def CFR(node, player, pi, use_cfr_plus = False, use_dcfr = False, iteration = 0):
    """
    Vanilla CFR algorithm.
    pi是从根节点访问到该节点，每位玩家贡献的概率
    """

    n_players = len(pi)
    node.visits += reduce(lambda x, y: x * y, pi, 1)

    if node.isChance():
        res = 0
        for (p, child) in zip (node.distribution, node.children):
            # print(child.id)
            res += CFR(child, player, pi, use_cfr_plus, use_dcfr, iteration) * p
        return res
    
    if(node.isLeaf()):
        u=0
        if player == 0 :
            u=node.utility[player]
        else :
            team_numofplayers=len(node.utility)-1
            u = node.utility[player] * team_numofplayers
        return u
        # return node.utility[player]
    
    #v是该节点的虚拟价值（反事实值），v_alt是每个分支的虚拟价值（反事实值），但此时未乘其他玩家从根节点到该节点的概率(Π -i (h) )
    iset = node.information_set
    v = 0
    v_alt = [0 for a in node.children]
    
    for a in range(len(node.children)):
        
        old_pi = pi[iset.player]
        pi[iset.player] *= iset.current_strategy[a]
        v_alt[a] = CFR(node.children[a], player, pi, use_cfr_plus, use_dcfr, iteration)    #给每个孩子送参数概率，但没有了cfr+的标志,已修改    
        pi[iset.player] = old_pi
            
        v += v_alt[a] * iset.current_strategy[a]
    
    if(iset.player == player):
        pi_other = 1
        for i in range(len(pi)):
            if(i != player):
                pi_other *= pi[i] #其他玩家到达该节的概率累乘

        #累积遗憾值即使出现负值，在更新策略时会先和0比，取大的，所以没问题
        #cumulative_regret是个列表，包含该信息集能做出动作的累计遗憾值，如[0.1,0.2]
        for a in range(len(node.children)):
            if use_cfr_plus:
                #iset.cumulative_regret[a] += pi[player] * max(0, (v_alt[a] - v)) # CFR+
                # iset.cumulative_regret[a] = max(iset.cumulative_regret[a] + pi_other * (v_alt[a] - v), 0) #(pi_other *v_alt[a]） 是采取某动作的瞬时遗憾值，(pi_other *v）是该节点的瞬时遗憾值
                # iset.cumulative_regret[a] += max(pi_other * (v_alt[a] - v), 0)
                iset.cumulative_regret[a] = max(iset.cumulative_regret[a] + pi_other * (v_alt[a] - v), 0)
            if use_dcfr:
                iset.cumulative_regret[a] += pi_other * (v_alt[a] - v)
                if iset.cumulative_regret[a] >= 0:
                    iset.cumulative_regret[a] *= ((iteration**1.5) / (iteration**1.5 + 1))
                else:
                    iset.cumulative_regret[a] *= (((iteration+1)**-100) / ((iteration+1)**-100 + 1))
            else:
                #iset.cumulative_regret[a] += pi[player] * (v_alt[a] - v)
                iset.cumulative_regret[a] += pi_other * (v_alt[a] - v)
                # iset.cumulative_regret[a] = max(iset.cumulative_regret[a],0)
            iset.cumulative_strategy[a] += pi[player] * iset.current_strategy[a]
            
        iset.cumulative_pi += pi[player]

    return v

def SolveWithCFR(cfr_tree, iterations, perc = 10, show_perc = False, checkEveryIteration = -1, 
                 check_callback = None, use_cfr_plus = False, use_dcfr = False):
    # Graph data
    graph_data = []

    start_time = time.time()
    last_checkpoint_time = start_time

    player_count = cfr_tree.numOfPlayers

    #停止迭代的方式，0表示按迭代轮次停止，1表示按时间停止
    check_fun = 0
    file_name="31G3_V3_iteration"
    stop_time = 100000
    checkEveryTime = 10 #多久输出一次迭代结果
    time_order = 1 #中间变量
    i = 0 #终止条件记录，轮次时记录迭代次数，时间时记录已运行时间
    it = 0 #迭代轮次
    if check_fun == 0 :
        flag = iterations + 1
    elif check_fun == 1 :
        flag = stop_time + 20
    while i < flag :
        if(show_perc and i % (flag / 100 * perc) == 0):
            print(str(i / (flag / 100 * perc) * perc) + "%")

        # Run CFR for each player,res是根节点的虚拟价值（反事实值）
        for p in range(player_count):
            res = CFR(cfr_tree.root, p, [1] * player_count, use_cfr_plus, use_dcfr, it)
            # print("p"+str(p),"CFR result is :",res)
            
        # Update the current strategy for each information set
        for infoset in cfr_tree.information_sets.values():
            infoset.updateCurrentStrategy()

        if(check_fun == 0 and checkEveryIteration > 0 and i % checkEveryIteration == 0):
            duration = time.time() - last_checkpoint_time
            data = {'epsilon': cfr_tree.checkMarginalsEpsilon(),
                    'iteration_number': it,
                    'duration': duration,
                    'to_time': time.time() - start_time,
                    'utility': cfr_tree.root.getExpectedUtility()}
            #保存到本地
            info_json = json.dumps(data,sort_keys=False, indent=4, separators=(',', ': '))
            f = open('./'+str(file_name)+'.json', 'a')
            f.write(info_json)
            f.close()

            graph_data.append(data)

            if(check_callback != None):
                check_callback(data)
        elif(check_fun == 1 and checkEveryTime > 0 and i >= time_order * checkEveryTime):
            time_order += 1
            duration = time.time() - last_checkpoint_time
            data = {'epsilon': cfr_tree.checkMarginalsEpsilon(),
                    'iteration_number': it,
                    'duration': duration,
                    'to_time': time.time() - start_time,
                    'utility': cfr_tree.root.getExpectedUtility()}
            #保存到本地
            info_json = json.dumps(data,sort_keys=False, indent=4, separators=(',', ': '))
            f = open('./'+str(file_name)+'.json', 'a')
            f.write(info_json)
            f.close()
            graph_data.append(data)

            if(check_callback != None):
                check_callback(data)

        last_checkpoint_time = time.time()
        
        #每轮迭代后累积条件更新
        it += 1
        if check_fun == 0 :
            i += 1
        elif check_fun == 1 :
            i = time.time() - start_time

    # for i in range(1, iterations + 1):
    #     if(show_perc and i % (iterations / 100 * perc) == 0):
    #         print(str(i / (iterations / 100 * perc) * perc) + "%")

    #     # Run CFR for each player,res是根节点的虚拟价值（反事实值）
    #     for p in range(player_count):
    #         res = CFR(cfr_tree.root, p, [1] * player_count, use_cfr_plus)
    #         # print("p"+str(p),"CFR result is :",res)
            
    #     # Update the current strategy for each information set
    #     for infoset in cfr_tree.information_sets.values():
    #         infoset.updateCurrentStrategy()

    #     if(checkEveryIteration > 0 and i % checkEveryIteration == 0):
    #         data = {'epsilon': cfr_tree.checkMarginalsEpsilon(),
    #                 'iteration_number': i,
    #                 'duration': time.time() - last_checkpoint_time,
    #                 'to_time': time.time() - start_time,
    #                 'utility': cfr_tree.root.getExpectedUtility()}
    #         graph_data.append(data)

    #         if(check_callback != None):
    #             check_callback(data)
                
    #         last_checkpoint_time = time.time()
        
    for i in range(len(graph_data)):
        print(graph_data[i])
        
    return {'utility': cfr_tree.root.getExpectedUtility(), 'graph_data': graph_data, 'tot_time': time.time() - start_time}