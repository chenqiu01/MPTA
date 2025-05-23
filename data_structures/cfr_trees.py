from functools import reduce
from data_structures.trees import Tree, Node, Leaf, randomTree
import random
import math
import re
import time

class CFRTree:
    """
    Wrapper around an extensive-form tree for holding additional CFR-related code and data.
    """

    def __init__(self, base_tree):
        """
        Create a CFRTree starting from a base Tree.
        """

        self.root = CFRChanceNode(base_tree.root) if base_tree.root.isChance() else CFRNode(base_tree.root)
        #information_sets为{信息集编号：对应节点1，对应节点2... ，信息集编号：对应节点1，对应节点2...}
        self.information_sets = {}
        self.numOfActions = 0
        self.numOfPlayers = base_tree.numOfPlayers
        self.convert_version = base_tree.convert_version
        self.ori_numOfPlayers = base_tree.ori_numOfPlayers

        nodes_to_expand = [ self.root ]

        while(len(nodes_to_expand) > 0):
            node = nodes_to_expand.pop()
            # if node.base_node.id == 1746 :
            #     print(node.base_node.id,"sequence test is :",node.base_node.getSequence(None,self.convert_version))
                # print("distribution is :",node.base_node.distribution)

            if(node.isChance()):
                for child in node.children:
                    nodes_to_expand.append(child)
                continue

            iset_id = node.base_node.information_set
            if(iset_id < 0):
                # This is a leaf (or an error has occurred)
                continue

            for child in node.children:
                nodes_to_expand.append(child)
                self.numOfActions += 1

            if(iset_id in self.information_sets):
                node.information_set = self.information_sets[iset_id]
                node.information_set.addNode(node)
            else:
                #此处node.player会在内部找到转换前玩家的，用于归并信息集
                iset = CFRInformationSet(iset_id, node.player, len(node.children), node.base_node.getSequence(node.player,self.convert_version), self)
                iset.addNode(node)
                self.information_sets[iset_id] = iset
                node.information_set = iset
        # print("做完了")

        # print("self.information_sets.values() is ",self.information_sets.values())
        self.infosets_by_player = []
        # print("信息集长度",len(self.information_sets))
        for p in range(self.ori_numOfPlayers):
            p_isets = list(filter(lambda i: i.nodes[0].ori_player == p, self.information_sets.values()))
            self.infosets_by_player.append(p_isets)
        #分成n位玩家的信息集列表[[玩家0的信息集]，[玩家1的信息集]]
        # print("self.infosets_by_player is ",self.infosets_by_player)


        for iset in self.information_sets.values():
            seq = iset.sequence
            tag=0
            for n in iset.nodes: #要让信息集内每个节点的sequence都一样
                tag+=1
                if(n.base_node.getSequence(iset.player,self.convert_version) != seq)  : #sequency返回{信息集id:来自第几个动作}
                    print("n.base_node.id is :",n.base_node.id,",getSequence :",n.base_node.getSequence(iset.player,self.convert_version),"iset.player is :",iset.player, ",seq is :",seq)
                    print("Sequences = ")
                    for node in iset.nodes:
                        print(node.base_node.getSequence(iset.player,self.convert_version))
                    raise Exception("ERROR: This tree is not a game with perfect recall. Nodes of information set "
                                    + str(iset.id) + " (" + reduce(lambda acc, el: str(el.base_node.id) + ', ' + acc, iset.nodes, "") + \
                                    ") have different sequences.")

            # Setup children leaves and children infosets for this information set
            iset.children_infoset = []
            iset.children_leaves = []

            for a in range(iset.action_count):
                #找的孩子信息集是和当前信息集属于同一个玩家执行的
                iset.children_infoset.append(list(iset.getChildrenInformationSets(a)))
                iset.children_leaves.append(list(iset.getChildrenLeaves(a)))

    def sampleActionPlan(self):
        """
        Sample a joint action plan from the tree (one action per each information set).
        """

        actionPlan = {}
        for id in self.information_sets:
            actionPlan[id] = self.information_sets[id].sampleAction()
        return actionPlan

    def getUtility(self, joint):
        """
        Get the utility obtained by the players when playing a given joint strategy over this tree.
        """

        utility = [0] * self.numOfPlayers

        for actionPlanString in joint.plans:
            actionPlan = CFRJointStrategy.stringToActionPlan(actionPlanString)
            frequency = joint.plans[actionPlanString] / joint.frequencyCount

            leafUtility = self.root.utilityFromActionPlan(actionPlan, default = [0] * self.numOfPlayers)
            for i in range(len(utility)):
                utility[i] += leafUtility[i] * frequency

        return utility

    #暂未用到
    def checkEquilibrium(self, joint):

        epsilons = self.getUtility(joint)

        for p in range(self.numOfPlayers):
            self.root.clearMarginalizedUtility()

            for (actionPlanString, frequency) in joint.plans.items():
                self.root.marginalizePlayer(CFRJointStrategy.stringToActionPlan(actionPlanString),
                                            frequency / joint.frequencyCount, p)
            #找出玩家P信息集的节点中，历史动作为空的节点
            root_infosets = list(filter(lambda i: i.sequence == {}, self.infosets_by_player[p]))

            epsilons[p] -= sum(map(lambda i: i.V(), root_infosets))

        return epsilons

    def checkMarginalsEpsilon(self):
        #迭代某个轮次时的根节点对应收益
        epsilons = self.root.getExpectedUtility()
        # print(epsilons)

        for p in range(self.ori_numOfPlayers):
            #把所有叶节点的边缘利益清为0
            self.root.clearMarginalizedUtility()
            #该节点为h，每个叶节点的边缘利益更新，值为(该玩家的利益*除了玩家p的其他玩家从h到达该叶节点的概率)
            self.root.marginalizePlayerFromBehaviourals(1, p)
            #过滤出infosets_by_player.sequence == {}的信息集类，每个信息集内所有节点的sequence是一样的.这些信息集是该玩家首次做出动作
            #转换后树过滤出首位玩家（默认玩家1）首次执行动作的信息集
            root_infosets = list(filter(lambda i: i.sequence == {}, self.infosets_by_player[p]))
            # if p == 0:
            #     root_infosets = list(filter(lambda i: i.sequence == {}, self.infosets_by_player[p]))
            # else :
            #     # print("test:",i.nodes[0].base_node.ori_player)
            #     root_infosets = list(filter(lambda i: i.sequence == {}  and i.nodes[0].base_node.ori_player == 1, self.infosets_by_player[p]))
            #     # print(len(root_infosets))
            # print(p,":",root_infosets)
            # # if p == 2 :
            # print(len(self.infosets_by_player[p]),len(root_infosets))
            #对过滤出的每一个信息集类求.V,再求和，得到该玩家的可利用度。.V()理论上应该求的是best response的value
            res_sum = 0
            
            for i in root_infosets:
                res = i.V()
                res_sum += res
                # if p == 2 :
                #     print("2's children leaves:",len(i.children_leaves))
            # if p ==2 :
            #     print("V is",res_sum)
            epsilons[p] -= res_sum
            # epsilons[p] -= sum(map(lambda i: i.V(), root_infosets))
        for i in range(len(epsilons)):
            epsilons[i] = -epsilons[i]
        print("epsilon: ", epsilons)
        
        all_ep=0
        for i in range(1,len(epsilons)):
            all_ep+=epsilons[i]
        all_ep = all_ep/len(epsilons)
        all_ep = (all_ep + epsilons[0])/2
        return all_ep

        # # epsilons = self.root.getExpectedUtility()
        # nash_value = [0.0] * self.numOfPlayers

        # for p in range(self.numOfPlayers):
        #     self.root.clearMarginalizedUtility()
        #     self.root.marginalizePlayerFromBehaviourals(1, p)

        #     root_infosets = list(filter(lambda i: i.sequence == {}, self.infosets_by_player[p]))
        #     nash_value[p] = sum(map(lambda i: i.V(), root_infosets))
        #     # epsilons[p] -= sum(map(lambda i: i.V(), root_infosets))

        # # return sum(nash_value)/self.numOfPlayers
        # return nash_value
        
    def buildJointFromMarginals(self, select_optimal_plan = True):

        leaves = set()
        self.root.find_terminals(leaves)

        all_players_plan_distributions = []

        for p in range(self.numOfPlayers):
            self.root.buildRealizationForm(p, 1)
            player_plan_distribution = []

            nonZeroLeaf = True
            while nonZeroLeaf:
                # for l in leaves:
                #     print((l.id, l.base_node.getSequence(p,self.convert_version), l.omega))

                best_plan = None
                best_plan_value = 0
                best_plan_leaf = None

                for l in leaves:
                    if l.omega == 0:
                        continue

                    (plan, val) = self.builSupportingPlan(l, p)
                    if val > best_plan_value:
                        best_plan = plan
                        best_plan_value = val
                        best_plan_leaf = l

                        if not select_optimal_plan:
                            break

                if best_plan == None:
                    for l in leaves:
                        print((l.id, l.base_node.getSequence(p,self.convert_version), l.omega))
                    raise Exception("ERROR")

                for t in self.root.terminalsUnderPlan(p, best_plan):
                    t.omega -= best_plan_value

                nonZeroLeaf = False
                for l in leaves:
                    if l.omega > 0.001:
                        nonZeroLeaf = True
                        break

                player_plan_distribution.append((best_plan, best_plan_value))

            all_players_plan_distributions.append(player_plan_distribution)

        # Merge plans of all players into a single joint distribution (cross product)
        joint_distribution = all_players_plan_distributions[0]

        for p in range(1, self.numOfPlayers):
            new_joint_distribution = []
            for j in joint_distribution:
                for d in all_players_plan_distributions[p]:
                    joint_plan = {**j[0], **d[0]}
                    joint_probability = j[1] * d[1]
                    new_joint_distribution.append((joint_plan, joint_probability))
            joint_distribution = new_joint_distribution

        reduced_joint_distribution = []

        for (joint_plan, joint_probability) in joint_distribution:
            reduced_joint_plan = CFRJointStrategy.reduceActionPlan(joint_plan, self)
            reduced_joint_distribution.append((reduced_joint_plan, joint_probability))

        return reduced_joint_distribution

    def buildJointFromMarginals_AllPlayersTogether(self):

        leaves = set()
        self.root.find_terminals(leaves)

        self.root.buildRealizationForm(None, 1)
        plan_distribution = []

        nonZeroLeaf = True
        i = 0
        while nonZeroLeaf and i < 10:

            best_plan = None
            best_plan_value = 0
            best_plan_leaf = None

            for l in leaves:
                if l.omega == 0:
                    continue

                (plan, val) = self.builSupportingPlan(l, None)
                if val > best_plan_value:
                    best_plan = plan
                    best_plan_value = val
                    best_plan_leaf = l

            if best_plan == None:
                for l in leaves:
                    print((l.id, l.base_node.getSequence(None,self.convert_version), l.omega))
                raise Exception("ERROR")

            for t in self.root.terminalsUnderPlan(None, best_plan):
                t.omega -= best_plan_value

            i += 1
            nonZeroLeaf = False
            for l in leaves:
                if l.omega > 0.001:
                    nonZeroLeaf = True
                    break

            plan_distribution.append((best_plan, best_plan_value))

        return plan_distribution

    def builSupportingPlan(self, leaf, targetPlayer):

        if targetPlayer != None:
            player_infosets = self.infosets_by_player[targetPlayer]
        else:
            player_infosets = list(self.information_sets.values())

        for iset in player_infosets:
            iset.supportingPlanInfo = None   

        plan = leaf.base_node.getSequence(targetPlayer,self.convert_version)
        weight = leaf.omega

        for (iset_id, action) in plan.items():
            self.information_sets[iset_id].supportingPlanInfo = (action, leaf.omega)

        for iset in player_infosets:
            iset.updateSupportingPlan(targetPlayer)
            (a, w) = iset.supportingPlanInfo
            plan[iset.id] = a
            weight = min(weight, w)

        weight = min(self.root.terminalsUnderPlan(targetPlayer, plan), key = lambda t: t.omega).omega

        return (plan, weight)

class CFRNode:
    """
    Wrapper around an extensive-form node for holding additional CFR-related code and data.
    """

    def __init__(self, base_node, parent = None):
        """
        Create a CFRNode starting from a base Node.
        It recursively creates also all the CFRNodes from the children of the base Node, up to the leaves.
        """

        self.id = base_node.id
        self.parent = parent
        self.player = base_node.player
        self.children = []
        self.incoming_action = base_node.incoming_action
        self.ori_player=base_node.ori_player

        for child in base_node.children:
            n = CFRChanceNode(child, self) if child.isChance() else CFRNode(child, self)
            self.children.append(n)

        self.visits = 0
        self.base_node = base_node

        self.is_leaf = len(self.children) == 0

        if(self.isLeaf()):
            self.utility = base_node.utility

    def isLeaf(self):
        return self.is_leaf

    def isChance(self):
        return False

    def getAllLeafVisits(self):
        if(self.isLeaf()):
            return self.visits
        else:
            return reduce(lambda x, y: x + y, map(lambda i: i.getAllLeafVisits(), self.children))

    def getLeafDistribution(self, norm_factor):
        """
        Returns the distribution over the leaves under this node, normalized by a given norm_factor.
        It uses the number of visits of the node stored by the execution of the CFR code.
        """

        if(self.isLeaf()):
            return str(self.visits / norm_factor) + ":" + str(self.base_node) + "\n"
        else:
            return reduce(lambda x, y: x + y,
                          map(lambda i: i.getLeafDistribution(norm_factor), self.children))

    def utilityFromActionPlan(self, actionPlan, default = None):
        """
        Return the utility from the leaf reached following actionPlan and starting from this node.
        If no leaf is reached, return the default value.
        """

        if(self.isLeaf()):
            return self.utility
        elif(self.information_set.id not in actionPlan):
            return default
        else:
            return self.children[actionPlan[self.information_set.id]].utilityFromActionPlan(actionPlan, default)

    def utilityFromJointSequence(self, js):
        """
        Return the expected utility when players follow the joint sequence 'js'. (Chance's actions are not considered in 'js')
        """
        if(self.isLeaf()):
            return self.utility
        elif(self.information_set.id not in js[self.player]):
            return tuple(0 for p in js)
        else:
            cur_player = self.player
            cur_infoset = self.information_set.id
            new_action = js[cur_player][cur_infoset]

            return self.children[new_action].utilityFromJointSequence(js)

    def find_terminals(self, terminals):
        if(self.isLeaf()):
            terminals.add(self)
        else:
            for child in self.children:
                child.find_terminals(terminals)

    def reachableTerminals(self, js):
        """
        returns the set of leaves reachable with the given joint sequences
        """
        if(self.isLeaf()):
            return {self.id}
        elif(self.information_set.id in js[self.player]):
            cur_player = self.player
            cur_infoset = self.information_set.id
            new_action = js[cur_player][cur_infoset]

            return self.children[new_action].reachableTerminals(js)

        return set()

    def utilityFromModifiedActionPlan(self, actionPlan, modification, default = None):
        """
        Return the utility from the leaf reached following a modification of actionPlan and starting from this node.
        Action listed in modification are followed first, if no one is found then actionPlan is followed.
        If no leaf is reached, return the default value.
        """

        if(self.isLeaf()):
            return self.utility

        id = self.information_set.id

        if(id in modification and modification[id] >= 0):
            # As if actionPlan[id] was overwritten
            return self.children[modification[id]].utilityFromModifiedActionPlan(actionPlan, modification, default)
        if(id in modification and modification[id] < 0):
            # As if actionPlan[id] was deleted
            return default
        if(id in actionPlan):
            return self.children[actionPlan[id]].utilityFromModifiedActionPlan(actionPlan, modification, default)

        return default

    def computeReachability(self, actionPlan, pi):
        """
        Computes the reachability of this node and its descendants under the given action plan, provided a vector
        pi containing the probability of reaching this node from the point of view of each player.
        """

        if(self.isLeaf() or sum(pi) == 0):
            return

        self.information_set.reachability = max(self.information_set.reachability, pi[self.player])

        sampled_action = actionPlan[self.information_set.id]

        for a in range(len(self.children)):
            if a == sampled_action:
                self.children[sampled_action].computeReachability(actionPlan, pi)
            else:
                self.children[a].computeReachability(actionPlan, pi[:self.player] + [ 0 ] + pi[self.player+1:])

    def buildRealizationForm(self, targetPlayer, p):
        """
        Builds the realization form, i.e. a distribution over the leaves of the tree that is
        equivalent to the current marginal strategy of targetPlayer.
        """

        if self.isLeaf():
            self.omega = p
            return

        if self.player != targetPlayer and targetPlayer != None:
            for node in self.children:
                node.buildRealizationForm(targetPlayer, p)
            return

        for a in range(len(self.children)):
            a_prob = self.information_set.current_strategy[a]
            self.children[a].buildRealizationForm(targetPlayer, p * a_prob)

    def terminalsUnderPlan(self, targetPlayer, plan):
        if self.isLeaf():
            return [ self ]

        terminals = []

        if targetPlayer == None or self.player == targetPlayer:
            action = plan[self.information_set.id]
            terminals = self.children[action].terminalsUnderPlan(targetPlayer, plan)
        else:
            for node in self.children:
                terminals += node.terminalsUnderPlan(targetPlayer, plan)

        return terminals

    def isActionPlanLeadingToInfoset(self, actionPlan, targetInfoset):
        """
        Returns true if the path obtained by the given action plan leads to the target information set.
        """

        if(self.information_set == targetInfoset):
            return True

        if(not self.information_set.id in actionPlan):
            return False

        action = actionPlan[self.information_set.id]

        if(action == -1 or self.children[action].isLeaf()):
            return False
        else:
            return self.children[action].isActionPlanLeadingToInfoset(actionPlan, targetInfoset)

    def clearMarginalizedUtility(self):
        """
        Clear the marginalized utility in the leaves.
        """

        if self.isLeaf():
            self.marginalized_utility = 0
        else:
            for child in self.children:
                child.clearMarginalizedUtility()

    def marginalizePlayer(self, actionPlan, frequency, marginalized_player):
        """
        Propagate up to the leaves the frequency of an action plan, ignoring the actions
        of the player to be marginalized (as he is the one for which we are searching a best reponse).
        """

        if self.isLeaf():
            self.marginalized_utility += frequency * self.utility[marginalized_player]
        elif self.player == marginalized_player:
            for child in self.children:
                child.marginalizePlayer(actionPlan, frequency, marginalized_player)
        else:
            self.children[actionPlan[self.information_set.id]].marginalizePlayer(actionPlan, frequency, marginalized_player)

    def marginalizePlayerFromBehaviourals(self, p, marginalized_player):
        """
        Propagate up to the leaves the current average behavioural strategies, ignoring the actions
        of the player to be marginalized (as he is the one for which we are searching a best reponse).
        将当前的平均行为策略传播到叶子，忽略要被边缘化的玩家的行为（因为他是我们正在寻找最佳响应的人）。
        """

        if self.isLeaf():
            self.marginalized_utility += p * self.utility[marginalized_player]
        elif self.ori_player == marginalized_player:
            for child in self.children:
                child.marginalizePlayerFromBehaviourals(p, marginalized_player)
        else:
            #getAverageStrategy会根据累积遗憾值求得（这轮的）策略（而非平均策略）
            s = self.distribution if self.isChance() else self.information_set.getAverageStrategy()
            #打印看机会节点的分布是否有问题
            # if self.isChance() and s != [1]:
            # print(self.id,"is",s)
            for a in range(len(self.children)):
                self.children[a].marginalizePlayerFromBehaviourals(p * s[a], marginalized_player)

    def getChildrenInformationSets(self, action, player):
        """
        Get all the information sets of the given player directly reachable (e.g. no other infoset of the same player in between)
        by here when the given action was played in the parent information set of the given player.
        获得该节点以下执行action动作的孩子的信息集
        """

        if self.isLeaf():
            return set()

        if action < 0 and self.base_node.ori_player == player:#当action为-1，则表示进入子节点了，可以返回信息集
            return set([self.information_set])
        
        if self.base_node.ori_player == player:#首次执行的节点是自己，所以进入self.children[action]
            return self.children[action].getChildrenInformationSets(-1, player)
        else:
            res = set()
            for child in self.children:
                res.update(child.getChildrenInformationSets(action, player))
            return res

    def getChildrenLeaves(self, action, player):
        """
        Get all the leaves directly reachable (e.g. no other infoset of the same player in between)
        by here when the given action was played in the parent information set of the given player.
        返回该信息集孩子信息集（同属一个玩家）中的叶节点，该节点包含的叶节点中间不能隔了玩家依然是自己的信息集。
        """

        if self.isLeaf():
            return set([self])

        if action < 0 and self.base_node.ori_player == player:
            return set()

        if self.base_node.ori_player == player:
            return self.children[action].getChildrenLeaves(-1, player)
        else:
            res = set()
            for child in self.children:
                res.update(child.getChildrenLeaves(action, player))
            return res

    def getExpectedUtility(self):
        """
        Get the expected utility from this node on under the current average behavioural strategies.
        """

        if self.isLeaf():
            return self.utility

        u = None
        s = self.distribution if self.isChance() else self.information_set.getAverageStrategy()

        for a in range(len(self.children)):
            child_u = self.children[a].getExpectedUtility()

            if u == None:
                u = [cu * s[a] for cu in child_u]
            else:
                for p in range(len(child_u)):
                    u[p] += child_u[p] * s[a]

        return u

class CFRChanceNode(CFRNode):
    """
    Wrapper around an extensive-form chance node for holding additional CFR-related code and data.
    """

    def __init__(self, base_node, parent = None):
        CFRNode.__init__(self, base_node, parent)
        self.distribution = base_node.distribution

    def isChance(self):
        return True

    def sampleAction(self):
        """
        Sample an action from the static distribution of this chance node.
        """

        r = random.random()
        count = 0

        for i in range(len(self.distribution)):
            count += self.distribution[i]
            if(r < count):
                return i

    def computeReachability(self, actionPlan, pi):
        """
        Computes the reachability of this node and its descendants under the given action plan, provided a vector
        pi containing the probability of reaching this node from the point of view of each player.
        """

        for a in range(len(self.children)):
            self.children[a].computeReachability(actionPlan, pi)

    def buildRealizationForm(self, targetPlayer, p):
        """
        Builds the realization form, i.e. a distribution over the leaves of the tree that is
        equivalent to the current marginal strategy of targetPlayer.
        """

        for a in range(len(self.children)):
            self.children[a].buildRealizationForm(targetPlayer, p)  # Do not factorize chance in

    def utilityFromActionPlan(self, actionPlan, default = None):
        """
        Return the utility from the leaf reached following actionPlan and starting from this node.
        If no leaf is reached, return the default value.
        """

        u = default

        for i in range(len(self.children)):
            childUtility = self.children[i].utilityFromActionPlan(actionPlan, default)

            if(u == default):
                u = childUtility.copy()
                for p in range(len(childUtility)):
                    u[p] *= self.distribution[i]
            else:
                for p in range(len(childUtility)):
                    u[p] += childUtility[p] * self.distribution[i]

        return u

    def utilityFromJointSequence(self, js):
        """
        Returns the convex combination of expected utilities obtained from actions at the current chance node.
        """
        expected_utility = [0.0 for p in js]

        for child_id in range(len(self.children)):
            observed_utility = self.children[child_id].utilityFromJointSequence(js)
            for p in range(len(js)):
                expected_utility[p] += observed_utility[p] * self.distribution[child_id]

        return tuple(expected_utility)

    def find_terminals(self, terminals):
        for child_id in range(len(self.children)):
            self.children[child_id].find_terminals(terminals)

    def reachableTerminals(self, js):
        """
        returns the set of reachable terminals given the joint sequence 'js'.
        At chance nodes, we perform the union of terminals reachable through each of the chance moves
        """
        cum=set()
        for child in self.children:
            cum = cum.union(child.reachableTerminals(js))
        return cum


    def utilityFromModifiedActionPlan(self, actionPlan, modification, default = None):
        """
        Return the utility from the leaf reached following a modification of actionPlan and starting from this node.
        Action listed in modification are followed first, if no one is found then actionPlan is followed.
        If no leaf is reached, return the default value.
        """

        u = default

        for i in range(len(self.children)):
            childUtility = self.children[i].utilityFromModifiedActionPlan(actionPlan, modification, default)

            if(u == default):
                for p in range(len(childUtility)):
                    u[p] = childUtility[p] * self.distribution[i]
            else:
                for p in range(len(childUtility)):
                    u[p] += childUtility[p] * self.distribution[i]

        return u

    def isActionPlanLeadingToInfoset(self, actionPlan, targetInfoset):
        """
        Returns true if the path obtained by the given action plan leads to the target information set.
        """

        res = False
        for child in self.children:
            res = res or child.isActionPlanLeadingToInfoset(actionPlan, targetInfoset)
        return res

    def clearMarginalizedUtility(self):
        """
        Clear the marginalized utility in the leaves.
        """

        for child in self.children:
            child.clearMarginalizedUtility()

    def marginalizePlayer(self, actionPlan, frequency, marginalized_player):
        """
        Propagate up to the leaves the frequency of an action plan, ignoring the actions
        of the player to be marginalized (as he is the one for which we are searching a best reponse)
        """

        for (p, child) in zip(self.distribution, self.children):
            child.marginalizePlayer(actionPlan, frequency * p, marginalized_player)

class CFRInformationSet:
    """
    Represents an information set and all the code and data related to it when used for the CFR algorithm.
    """

    def __init__(self, id, player, action_count, sequence, cfr_tree, random_initial_strategy = False):
        """
        Create an information set with a given id, player, action_count (i.e. number of actions available in its nodes),
        sequence and cfr_tree it belongs to.
        If random_initial_strategy is True, it is initialized with a random local strategy; otherwise is uses the usual
        uniform distribution over actions.
        每个信息集有对应的sequence
        """

        self.id = id
        self.player = player
        self.action_count = action_count
        self.sequence = sequence
        self.nodes = []
        self.cfr_tree = cfr_tree

        self.cumulative_regret = [0 for a in range(self.action_count)]
        self.cumulative_strategy = [0 for a in range(self.action_count)]
        self.current_strategy = [1 / self.action_count for a in range(self.action_count)]
        self.cumulative_pi = 0

        if(random_initial_strategy):
            self.current_strategy = [random.random() for a in range(self.action_count)]
            sum = reduce(lambda x, y: x + y, self.current_strategy, 0)
            self.current_strategy = [self.current_strategy[a] / sum for a in range(self.action_count)]

        self.cached_V = None

    def __str__(self):
        return "<InfoSet" + str(self.id) + " - Player" + str(self.player) + ">"

    def __repr__(self):
        return str(self)

    def addNode(self, node):
        self.nodes.append(node)

    def updateCurrentStrategy(self):
        """
        Recalculate the current strategy based on the cumulative regret.
        """

        sum = reduce(lambda x, y: x + max(0, y), self.cumulative_regret, 0)

        for a in range(0, self.action_count):
            if(sum > 0):
                self.current_strategy[a] = max(0, self.cumulative_regret[a]) / sum
            else:
                self.current_strategy[a] = 1 / self.action_count

    def getAverageStrategy(self):
        """
        Get the average strategy experienced so far.
        """

        #将累积遗憾值转换为和为1的策略形式
        norm = reduce(lambda x, y: x + y, self.cumulative_strategy)
        if(norm > 0):
            return [self.cumulative_strategy[a] / norm for a in range(self.action_count)]
        else:
            return [1 / self.action_count for a in range(self.action_count)]

    def sampleAction(self):
        """
        Sample an action from the current strategy.
        """

        if(self.nodes[0].isChance()):
            return self.nodes[0].sampleAction()

        r = random.random()
        count = 0

        for i in range(len(self.current_strategy)):
            count += self.current_strategy[i]
            if(r < count):
                return i

    #相当于从树叶开始比较，选择对于当前信息集边缘利益最大的动作，返回执行该动作的边缘利益
    def V(self): 

        v = [0 for a in range(self.action_count)]

        for a in range(self.action_count):
            # temp=sum(map(lambda i: i.V(), self.children_infoset[a]))
            # print("temp is ",temp)
            # v[a] += temp
            v[a] += sum(map(lambda i: i.V(), self.children_infoset[a]))
            temp = sum(map(lambda l: l.marginalized_utility, self.children_leaves[a]))
            # if self.nodes[0].ori_player != 2:
            #     temp = sum(map(lambda l: l.marginalized_utility, self.children_leaves[a]))
            # else :
            #     temp=0
            #     for i in self.children_leaves[a]:
            #         temp_value = i.marginalized_utility
            #         temp+=temp_value
            #         print(temp_value)
            v[a] += temp

        # print(self.id," is v:",v)
        return max(v)

    def getChildrenOfPlayer(self, player):
        """
        Get all the information sets (including this one) of the given player and descendants of this information set.
        """

        children = set()
        for node in self.nodes:
            for child in node.children:
                if(not child.isLeaf()):
                    children.update(child.information_set.getChildrenOfPlayer(player))
        if(self.player == player):
            children.add(self)
        return children

    def getChildrenInformationSets(self, action):
        """
        Get all the information sets of the given player directly reachable (e.g. no other infoset of the same player in between)
        by this one when the given action was played in the parent information set of the given player.
        对这个信息集中每个结点，执行action动作后可达的信息集取并集
        """
        
        res = set()
        #取并集
        for node in self.nodes:
            res.update(node.getChildrenInformationSets(action, self.nodes[0].ori_player))
        return res

    def getChildrenLeaves(self, action):
        """
        Get all the leaves directly reachable (e.g. no other infoset of the same player in between)
        by this information set when the given action was played in the parent information set of the given player.
        """

        res = set()
        for node in self.nodes:
            res.update(node.getChildrenLeaves(action, self.nodes[0].ori_player))
        return res

    def updateSupportingPlan(self, targetPlayer):
        # TODO: implement also the "targetPlayer == None" case

        if self.supportingPlanInfo != None:
            return

        action = -1

        for a in range(self.action_count):

            if targetPlayer != None:
                children_infosets = self.children_infoset[a]
                children_leaves = self.children_leaves[a]
            else:
                children_infosets = set()
                children_leaves = []

                for node in self.nodes:
                    child = node.children[a]
                    if child.isLeaf():
                        children_leaves.append(child)
                    else:
                        children_infosets.add(child.information_set)

                children_infosets = list(children_infosets)

            a_omega = 1
            for iset in children_infosets:
                iset.updateSupportingPlan(targetPlayer)
                (_, w) = iset.supportingPlanInfo
                a_omega = min(a_omega, w)
            for leaf in children_leaves:
                a_omega = min(a_omega, leaf.omega)

            if action == -1 or a_omega > omega:
                action = a
                omega = a_omega

        self.supportingPlanInfo = (action, omega)

    def computeReachability(self, actionPlan):

        self.reachability = 1
        sampled_action = actionPlan[self.id]

        for iset in self.children_infoset[sampled_action]:
            iset.computeReachability(actionPlan)

class CFRJointStrategy:
    """
    A joint strategy progressively built by the SCFR algorithm.
    """

    def __init__(self, maxPlanCount = -1):
        """
        Create a joint strategy able to hold a maximum of maxPlanCount plans.
        If the value is not given, it is able to hold an arbitrary number of plans.
        """

        self.maxPlanCount = maxPlanCount
        self.frequencyCount = 0
        self.plans = {}

        CFRJointStrategy.action_plans_cache = {}

    def addActionPlan(self, actionPlan, weight = 1):
        """
        Add an action plan (a dictionary from information set id to action) to the joint strategy.
        Optionally a weight can be provided, to insert non-uniformly sampled plans.
        """

        string = CFRJointStrategy.actionPlanToString(actionPlan)

        if(string in self.plans):
            self.plans[string] += weight
            self.frequencyCount += weight
        elif(self.maxPlanCount == -1 or len(self.plans) < self.maxPlanCount):
            self.plans[string] = weight
            self.frequencyCount += weight
        else:
            # Remove the least frequent plan
            plan = min(self.plans, key = lambda p: self.plans[p])
            self.frequencyCount -= self.plans[plan]
            del self.plans[plan]

            # Add the new one
            self.plans[string] = weight
            self.frequencyCount += weight

    def addJointDistribution(self, jointDistribution):
        """

        """

        for (plan, prob) in jointDistribution:
            self.addActionPlan(plan, prob)

    def actionPlanToString(actionPlan):
        """
        Transform an action plan in dictionary representation to the corresponding string representation.
        """

        string = ""

        for infoset in actionPlan:
            string += "a" + str(infoset) + "." + str(actionPlan[infoset])

        return string

    action_plans_cache = {}

    def stringToActionPlan(string):
        """
        Transform an action plan in string representation to the corresponding dictionary representation.
        """

        if(string in CFRJointStrategy.action_plans_cache):
            return CFRJointStrategy.action_plans_cache[string]

        actions = string.split("a")[1:]
        actionPlan = {}

        for a in actions:
            (infoset, action) = a.split(".")
            actionPlan[int(infoset)] = int(action)

        CFRJointStrategy.action_plans_cache[string] = actionPlan

        return actionPlan

    def reduceActionPlan(actionPlan, tree):
        """
        Transform an action plan into a reduced one, in the given tree.
        """

        reducedActionPlan = {}

        for iset in tree.information_sets.values():
            iset.reachability = 0

        #tree.root.computeReachability(actionPlan, [1 for _ in range(tree.numOfPlayers)])

        for iset in tree.information_sets.values():
            if len(iset.sequence) == 0:
                iset.computeReachability(actionPlan)

        for (id, iset) in tree.information_sets.items():
            # reachability = max(map(lambda n: n.reachability, iset.nodes))
            if(iset.reachability > 0):
                reducedActionPlan[id] = actionPlan[id]

        return reducedActionPlan
