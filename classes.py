# -*- encoding=utf8 -*-
from copy import deepcopy
from util import PriorityQueue, manhattanDistance
import time
from math import exp
class Judge(object):
    """docstring for Judge"""

    def __init__(self):
        super(Judge, self).__init__()
        self.time = set()  # 存放出发时间
        self.car_No = []  # 存放车辆编号
        self.road_No = []  # 存放道路编号
        self.cross_No = []  # 存放路口编号
        self.car_info = {}  # 存放车辆特征
        self.road_info = {}  # 存放道路特征
        self.cross_info = {}  # 存放路口特征
        self.plan_info = {}  # 存放行车计划
        self.StartTimeBin = {}  # 按照实际出发时间为车辆分桶

    def get_car_info(self, file):
        # car.txt
        # print('get car info, filename is ', file)
        with open(file) as f:
            for line in f.readlines():
                if line[0] == '#':
                    continue
                line = self.convert2list(line)

                [car_id, start, end, speed, planTime] = [int(i) for i in line]
                self.car_No.append(car_id)
                if self.plan_info:
                    self.car_info[car_id] = Car(car_id,
                                            [start, end, speed, planTime], self.plan_info[car_id])
                else:
                    self.car_info[car_id] = Car(car_id,
                                                [start, end, speed, planTime], [0, []])

    def convert2list(self, line):
        line.strip()
        line = line.replace('(', '')
        line = line.replace(')', '')
        return line.split(',')

    def get_road_info(self, file):
        # road.txt
        #        print('get road info, filename is ', file)
        with open(file) as f:
            for line in f.readlines():
                if line[0] == '#':
                    continue
                line = self.convert2list(line)
                [road_id, length, speed, channel, start, end, isDuplex] = [int(i) for i in line]
                self.road_No.append(road_id)
                self.road_info[road_id] = Road(road_id,
                                               [length, speed, channel, start, end, isDuplex])

    def get_cross_info(self, file):
        # cross.txt
        with open(file) as f:
            for line in f.readlines():
                if line[0] == '#':
                    continue
                line = self.convert2list(line)
                [cross_id, roadId1, roadId2, roadId3, roadId4] = [int(i) for i in line]
                self.cross_No.append(cross_id)
                self.cross_info[cross_id] = Cross(cross_id,
                                                  [roadId1, roadId2, roadId3, roadId4])
                # 1，2，3，4代表北、东、南、西

    def parse_Plan_info(self, file):
        # answer.txt
        with open(file) as f:
            for line in f.readlines():
                if line[0] == '#':
                    continue
                line = self.convert2list(line)
                info = [int(i) for i in line]
                # carId,StartTime,RoadId...RoadId
                car_id = info[0]
                StartTime = info[1]

                # 将车辆按出发时间分桶
                if not self.StartTimeBin.get(StartTime):
                    self.StartTimeBin[StartTime] = []
                self.StartTimeBin[StartTime].append(car_id)

                RoadSequence = info[2:]
                self.time.add(StartTime)
                self.plan_info[car_id] = [StartTime] + RoadSequence

    def simulate(self):
        start_time = time.time()
        self.result = 0  # 系统调度时间
        self.tick = -1  # 车辆运行时间

        self.active_stack = []  # 存放当前时刻应被处理的车辆编号
        self.active_road = []  # 存放当前时刻有车的道路编号
        self.final_stack = []
        while True:
            if self.tick >= max(self.time) and not self.active_stack:
                break
            self.step()
        print('''Totol arrange time is {} tick, the program run time is {} s.'''.format(self.tick + 16,
                                                                                        round(time.time() - start_time,
                                                                                              2)))

    def step(self, input_cars=None):

        self.tick += 1  # 表往后走一秒
        # 当前未处理车辆，车到终点后弹出
        dead_stack = []  # 储存本时刻已经被处理的车辆
        # 规则一：系统先调度在行驶的车辆，再调度等待上路的车辆
        if input_cars == None:
            garage_stack = sorted(self.StartTimeBin.get(self.tick, []))  # 车库里将要上路的车
        else:
            garage_stack = sorted(input_cars)
        # 规则二：按照车辆ID升序进行调度
        # 第一步：道路调度，进行一次
        # print('Arrange Roads...')
        for road_id in self.road_No:
            # print('Now processing road No.', road_id)
            # print(S.road_info[5014].WhichCar())
            road = self.road_info[road_id]
            car_list, rev_car_list = road.WhichCar()
            # print(car_list, rev_car_list)
            for car_id in car_list:
                # print(car_id)
                dead_stack, self.car_info[car_id], signal = road.DriveCar(self.car_info[car_id], dead_stack, self)
            for car_id in rev_car_list:
                dead_stack, self.car_info[car_id], signal = road.DriveCar(self.car_info[car_id], dead_stack, self,
                                                                          reversed=True)
        # 道路调度后，调度时间+1
        self.result += 1
        # 第二步：路口调度，直到所有车辆被标记为final
        # print('Arrange Cross...')
        while len(self.active_stack) != len(dead_stack):
            # if result == 155:
            #     print(0)
            handled_signal = 0
            # 此时意味着车道上的车辆全部处理完了,继续使车库里的车上路
            for cross_id in self.cross_No:
                # print('Now processing cross No.', cross_id)
                # if cross_id == 31:
                #     print(0)
                cross = self.cross_info[cross_id]
                # print('Arrange cross No {}'.format(cross.id))
                # handled=True表示有车的状态发生变化
                tmp1 = len(dead_stack)
                tmp2 = handled_signal
                dead_stack, handled = cross.crossArrange(dead_stack, self)
                handled_signal |= handled
            if len(self.active_stack) != len(dead_stack):
                assert handled_signal, 'Dead Lock Happened!'
                self.result += 1  # 每次路口的循环需要调度时间+1
        # 第三步：车库发车
        # print('Place Car from garage...')
        for car_id in garage_stack:
            # print('Now place car No.', car_id)
            car = self.car_info[car_id]
            dead_stack, signal = car.PlaceCar_FromGarage(self, dead_stack)
            if signal:
                self.active_stack.append(car.id)
        self.result += 1
        # 道路调度完成，此时判断各个车辆是否到达其终点
        # 若到达终点，从active_stack中剔除，若未到达终点，将其state刷新为wait
        for car_id in dead_stack:
            car = self.car_info[car_id]
            if car.reachFinal(self):
                # print('No {} car reached final.'.format(car.id))
                self.active_stack.remove(car_id), self.final_stack.append(car_id)
            else:
                car.reflush()
        # 如果时刻超过了planTime的最大值且没有未到终点的车辆，意味着时间结束

        return True


class Car(object):
    def __init__(self, _id, _car_info, plan_info):
        [start, end, speed, planTime] = _car_info
        self.id = _id
        self.start = start
        self.end = end
        self.speed = speed
        self.planTime = planTime
        self.StartTime = plan_info[0]  # 记录实际出发时间
        self.RoadSequence = plan_info[1:]  # 记录途径道路顺序
        self.road_index = 0  # 记录当前所处道路在Seq中的位置
        self.road_pos = 0  # 记录在当前道路上的位置
        self.lane = 0  # 记录在当前道路上的车道编号
        self.state = 'wait'  # 当前车辆为等待状态或终止'final'

    def reflush(self):
        # Checked...
        self.state = 'wait'

    def get_road(self, S):
        # Checked...
        road = S.road_info[self.RoadSequence[self.road_index]]
        cross_end = S.cross_info[road.end]
        cross_start = S.cross_info[road.start]
        if road.id != self.RoadSequence[-1]:
            print('Next road', self.RoadSequence[self.road_index + 1],
                  'from {} to {}'.format(S.road_info[self.RoadSequence[self.road_index + 1]].start,
                                         S.road_info[self.RoadSequence[self.road_index + 1]].end))
        else:
            print('This car will reach its destination.')
        print("""Current road {} from {} to {}. \ncross {} linked {}, \ncross {} linked {}.""".format(road.id,
                                                                                                      cross_start.id,
                                                                                                      cross_end.id,
                                                                                                      cross_start.id,
                                                                                                      cross_start.roads,
                                                                                                      cross_end.id,
                                                                                                      cross_end.roads))
        return S.road_info[self.RoadSequence[self.road_index]]

    def PlaceCar_FromGarage(self, S: Judge, dead_stack):
        # Checked...
        road_id = self.RoadSequence[0]
        road = S.road_info[road_id]
        if road.start == self.start:
            lane = road.lane
        elif road.end == self.start:
            lane = road.lane_rev
        v = min(self.speed, road.speed)
        for i in range(road.channel):
            tmp = -1
            for j in range(v):
                if lane[i][j] != 0:
                    if j == 0:
                        break
                    lane[i][j - 1] = self
                    self.lane = i
                    self.road_pos = j - 1
                    self.state = 'final'
                    dead_stack.append(self.id)
                    S.road_info[road_id] = road
                    S.car_info[self.id] = self
                    return dead_stack, True
                else:
                    if j >= tmp:
                        # 找到当前道路能到达的最远的空位置
                        tmp = j
            if tmp >= 0:
                lane[i][tmp] = self
                self.lane = i
                self.road_pos = tmp
                self.state = 'final'
                dead_stack.append(self.id)
                S.road_info[road_id] = road
                S.car_info[self.id] = self
                return dead_stack, True
        # print('Fail to place the car.', self.id)
        self.planTime += 1
        if self.planTime in S.StartTimeBin:
            S.StartTimeBin[self.planTime].append(self.id)
        else:
            S.StartTimeBin[self.planTime] = [self.id]
        return dead_stack, False

    def reachFinal(self, S: Judge):
        # Checked...
        # 车辆到达终点的标记：road_pos = final_road.length， road=final_road
        road = self.RoadSequence[self.road_index]
        if road == self.RoadSequence[-1] and self.road_pos == S.road_info[road].length:
            return True
        return False

    def __str__(self):
        string = "(" + str(self.id) + "," + str(self.StartTime)
        for road_id in self.RoadSequence:
            # print(road_id)
            string += "," + str(road_id)
        string += ")\n"
        return string

class Road(object):
    def __init__(self, _id, _road_info):
        # Checked...
        [length, speed, channel, start, end, isDuplex] = _road_info
        self.id = _id
        self.length = length
        self.speed = speed
        self.channel = channel
        self.start = start
        self.end = end
        self.isDuplex = isDuplex
        self.lane = [[0 for i in range(self.length)] for i in range(self.channel)]  # 车道用全0矩阵表示
        self.wait_stack = []
        # 处理反向车道
        if self.isDuplex == 1:
            self.lane_rev = [[0 for i in range(self.length)] for i in range(self.channel)]
        else:
            self.lane_rev = []
        # 说明：对于self.lane而言，最前面的表示靠近start cross的位置，最后的表示靠近end cross的位置

    def DriveCar(self, car: Car, dead_stack, S: Judge, reversed=False):
        # 行驶的函数：区分通过路口和不通过路口
        # 规则：通过路口时，优先占据编号小的车道，不通过路口时，保持现有车道
        # 核心规则：在本车道上的行驶距离S2 <= V2 - S1 (V2为此车道限速，S1为前一车道剩余距离)
        # 核心规则决定了本车在速度超过当前车道可行驶距离时， 能不能进入下一车道
        # Checked...
        if self.id == 5009:
            self.lane_id()
        if car.state == 'final':
            return dead_stack, car, False
        #        print('No {} car is drived.'.format(car.id))
        # 调试代码
        # if car.id in [10001, 10009]:
        #     print(self.lane_id())
        #     print('Monitor here', car.get_road(S).id, car.road_pos)
        if not reversed:
            lane = self.lane
            cross_id = self.end
        else:
            assert self.isDuplex, 'Wrong reversed option.'  # 如果输入反向而道路单行，说明输入错误
            lane = self.lane_rev  # 如果是反向行驶，调整self.lane
            cross_id = self.start
        # Case 0，马上到达终点
        if self.id == car.RoadSequence[-1]:
            #            print('The car {} may reach its final.'.format(car.id))
            for j in range(car.road_pos + 1, self.length):
                for i in range(self.channel):
                    if i == car.lane and j == car.road_pos:
                        break
                    if lane[i][j] and lane[i][j].state == 'wait':
                        car.state = 'wait'
                        return dead_stack, car, False
                if lane[car.lane][j] and lane[car.lane][j].state == 'final':
                    lane[car.lane][car.road_pos] = 0
                    car.road_pos = min(car.road_pos + min(self.speed, car.speed), j - 1)
                    lane[car.lane][car.road_pos] = car
                    car.state = 'final'
                    dead_stack.append(car.id)
                    return dead_stack, car, True
                elif j == self.length - 1:
                    lane[car.lane][car.road_pos] = 0
                    if car.road_pos + min(self.speed, car.speed) >= self.length:
                        car.road_pos = self.length
                    else:
                        car.road_pos = car.road_pos + min(self.speed, car.speed)
                        lane[car.lane][car.road_pos] = car
                    car.state = 'final'
                    dead_stack.append(car.id)
                    return dead_stack, car, True
            if car.road_pos == self.length - 1:
                lane[car.lane][car.road_pos] = 0
                car.road_pos = self.length
                car.state = 'final'
                dead_stack.append(car.id)
                return dead_stack, car, True
        else:
            next_Road_id = car.RoadSequence[car.road_index + 1]
            next_Road = S.road_info[next_Road_id]
        #        print(car.id, car.RoadSequence, car.road_index, car.get_road(S).lane_id(), car.state, self.id)
        assert car.RoadSequence[car.road_index] == self.id, 'Car not in this road.'

        # Case1, 若前方有等待行驶的车，自身也不能行驶
        for j in range(self.length - 1, car.road_pos, -1):
            for i in range(self.channel):
                if i == car.lane and j == car.road_pos:
                    break
                if lane[i][j] and lane[i][j].state == 'wait':
                    car.state = 'wait'
                    return dead_stack, car, False
        # Case2, 同车道有前车
        for i in range(car.road_pos + 1, self.length):
            if lane[car.lane][i] != 0:  # 找到最近的前车
                lane[car.lane][car.road_pos] = 0
                car.road_pos = min(car.road_pos + min(self.speed, car.speed), i - 1)
                lane[car.lane][car.road_pos] = car
                car.state = 'final'
                dead_stack.append(car.id)
                return dead_stack, car, True
        # Case3, 没有前车且不需要经过路口时，车辆保持车道往前移动
        if car.road_pos + min(self.speed, car.speed) < self.length:
            lane[car.lane][car.road_pos] = 0
            car.road_pos += min(self.speed, car.speed)
            lane[car.lane][car.road_pos] = car
            car.state = 'final'
            dead_stack.append(car.id)
            return dead_stack, car, True
        # Case4, 没有前车，理论上需要经过路口但受到核心规则限制而不能通过(S1 = 车道长度-当前位置-1)
        elif self.length - 1 - car.road_pos >= min(next_Road.speed, car.speed):
            # print('No {} car will pass the cross but get S2 restrict'.format(car.id))
            lane[car.lane][car.road_pos] = 0
            car.road_pos = self.length - 1  # 到达车道最前端
            lane[car.lane][car.road_pos] = car
            car.state = 'final'
            dead_stack.append(car.id)
            return dead_stack, car, True
        # Case5, 没有前车，可以通过路口
        else:
            # print('No {} car will pass the cross.'.format(car.id))
            # print('s1 v2 = ', self.length-1-car.road_pos, min(next_Road.speed, car.speed) )
            car.state = 'wait'
            S.cross_info[cross_id].need_arrange = True
            return dead_stack, car, False

    def lane_id(self):
        if self.isDuplex:
            return [[s.id if s != 0 else 0 for s in self.lane[j]] for j in range(self.channel)], [
                [s.id if s != 0 else 0 for s in self.lane_rev[j]] for j in range(self.channel)]
        else:
            return [[s.id if s != 0 else 0 for s in self.lane[j]] for j in range(self.channel)]

    # def passCross(self, dead_stack, S: Judge, reversed=False):
    #     # 通过路口的逻辑, reversed表示处理该条道路的反向通道
    #     car_list, rev_car_list = self.WhichCar()
    #     handled = 0  # 表示有车被调度，用于判断死锁
    #     if not reversed:
    #         lane = self.lane
    #         cross_id = self.end
    #         todo_list = deepcopy(car_list)
    #     else:
    #         assert self.isDuplex == 1, 'Error reversed option for passCross.'
    #         lane = self.lane_rev
    #         cross_id = self.start
    #         todo_list = deepcopy(rev_car_list)
    #     four_road = S.cross_info[cross_id].roads  # 对于当前路口连接的四条道路
    #     for car_id in todo_list:
    #         # if car_id == 18273:
    #         #     print(0)
    #         car = S.car_info[car_id]
    #         lane_prev = car.lane
    #         deadstack, car, signal = self.DriveCar(car, dead_stack, S, reversed)
    #         if signal:
    #             continue
    #         if car.state == 'wait':
    #             # 若到达了最后一条路
    #             if self.id == car.RoadSequence[-1]:
    #                 dead_stack, S, signal = self.DriveCar(car, dead_stack, S)
    #                 if signal:
    #                     handled = 1
    #                 return dead_stack, S, handled
    #             next_road_id = car.RoadSequence[car.road_index + 1]
    #             next_road = S.road_info[next_road_id]
    #             # 判断要进入的下一条路是进逆车道或是顺车道
    #             if next_road.start == cross_id:
    #                 next_lane = next_road.lane
    #             elif next_road.end == cross_id:
    #                 assert next_road.isDuplex, "Next road reversed option false..."
    #                 next_lane = next_road.lane_rev
    #             direction = (four_road.index(next_road_id) - four_road.index(self.id)) % 4
    #             '''-----------------------------------Debuged here'''
    #             # direction含义：1：左拐，2：直行，3：右拐
    #             # 若前方没有wait状态的车辆，如果是同一道路直行
    #             # 此调度发生于DriveCar或者passCross问题后的DriveCar中，不需要额外设计情况
    #             # 考虑需要通过路口的情况
    #             # 确定下个位置
    #             v1 = min(car.speed, self.speed)
    #             v2 = min(car.speed, next_road.speed)
    #             s1 = self.length - car.road_pos - 1
    #             s2 = v2 - s1
    #             # print('s1, s2, v1, v2, car.id, direction', s1, s2, v1, v2, car.id, direction)
    #             assert s2 > 0, 'passCross get s2 limited!'
    #             next_pos = s2 - 1
    #             flag = 0  # 0表示可通行，1表示不可通行，2表示已经通行完毕
    #             next_state = 1  # next_state为1表示后续所有的位置都被final的车占据了
    #             if direction == 2:
    #                 # 直行到下一条路
    #                 for i in range(next_road.channel):
    #                     tmp = -1
    #                     for j in range(next_pos + 1):
    #                         if next_lane[i][j] != 0:
    #                             if next_lane[i][j].state == 'wait':
    #                                 # 表示前进道路上有等待的车，自己也等待
    #                                 next_state = 0
    #                                 flag = 1
    #                                 break
    #                             else:
    #                                 tmp = j - 1
    #                                 break
    #                         elif next_lane[i][j] == 0:
    #                             if j >= tmp:
    #                                 tmp = j  # tmp记录在最小车道上能到达最远的位置
    #                     if tmp >= 0:
    #                         next_state = 0
    #                         lane[car.lane][car.road_pos] = 0
    #                         next_lane[i][tmp] = car
    #                         car.lane = i
    #                         car.road_pos = tmp
    #                         car.road_index += 1
    #                         car.state = 'final'
    #                         dead_stack.append(car.id)
    #                         S.car_info[car.id] = car
    #                         flag = 2
    #                         break
    #                     if flag:
    #                         break
    #                 # 后面所有可能位置全被final车辆占据，只能走到道路最前端，标为final
    #                 if next_state:
    #                     handled = 1
    #                     lane[car.lane][car.road_pos] = 0
    #                     car.road_pos = self.length - 1
    #                     lane[car.lane][car.road_pos] = car
    #                     car.state = 'final'
    #                     dead_stack.append(car.id)
    #                     S.car_info[car.id] = car
    #                     flag = 2
    #                 # 已经通行完毕（无论过没过路口），本车道全部需要DriveCar
    #                 if flag == 2:
    #                     handled = 1
    #                     #                        print('{} Success pass cross {}, start DriveCar for rest Car.'.format(car.id, cross_id))
    #                     # 当成功调度路口后，马上调度这条车道上所有的车。
    #                     #                        print('After Straightpass the cross, Drive all cars in this lane.')
    #                     for j in range(self.length - 2, -1, -1):
    #                         if lane[lane_prev][j]:
    #                             dead_stack, car, signal = self.DriveCar(lane[lane_prev][j], dead_stack, S, reversed)
    #                             S.car_info[car.id] = car
    #             elif direction == 3:
    #                 # 右拐具有最低的优先级，需要考虑针对目标道路左拐和直行的有无冲突，没有则行车，否则等待下次调度
    #                 straight_road_id = four_road[(four_road.index(next_road_id) - 2) % 4]
    #                 left_road_id = four_road[(four_road.index(next_road_id) - 1) % 4]
    #                 if straight_road_id != -1:
    #                     straight_road = S.road_info[straight_road_id]
    #                     straight_car_list, straight_rev_car_list = straight_road.WhichCar()
    #                 if left_road_id != -1:
    #                     left_road = S.road_info[left_road_id]
    #                     left_car_list, left_rev_car_list = left_road.WhichCar()
    #                 # 处理直行道路是否逆行道路
    #                 if straight_road_id != -1:
    #                     if straight_road.end != cross_id:
    #                         straight_todo_list = deepcopy(straight_rev_car_list)
    #                     else:
    #                         straight_todo_list = deepcopy(straight_car_list)
    #                 else:
    #                     straight_todo_list = []
    #                 # 处理左拐道路是否逆行道路
    #                 if left_road_id != -1:
    #                     if left_road.end != cross_id:
    #                         left_todo_list = deepcopy(left_rev_car_list)
    #                     else:
    #                         left_todo_list = deepcopy(left_car_list)
    #                 else:
    #                     left_todo_list = []
    #                 # 如果直行道上最高优先级的车辆要去目标道路，flag立起来，本车不能通行。
    #                 for car_id in straight_todo_list:
    #                     if S.car_info[car_id].state == 'wait' and S.car_info[car_id].RoadSequence[
    #                         S.car_info[car_id].road_index + 1] == next_road_id:
    #                         flag = 1
    #                         break
    #                     if S.car_info[car_id].state == 'wait' and S.car_info[car_id].RoadSequence[
    #                         S.car_info[car_id].road_index + 1] != next_road_id:
    #                         flag = 0
    #                         break
    #                 # 如果直行道上没有，如果左转最高优先级的车辆要去目标道路，flag立起来，本车不能通行。
    #                 if not flag:
    #                     for car_id in left_todo_list:
    #                         if S.car_info[car_id].state == 'wait' and S.car_info[car_id].RoadSequence[
    #                             S.car_info[car_id].road_index + 1] == next_road_id:
    #                             flag = 1
    #                             break
    #                         if S.car_info[car_id].state == 'wait' and S.car_info[car_id].RoadSequence[
    #                             S.car_info[car_id].road_index + 1] != next_road_id:
    #                             flag = 0
    #                             break
    #                 if flag == 0:  # 可以右拐
    #                     for i in range(next_road.channel):
    #                         tmp = -1
    #                         for j in range(next_pos + 1):
    #                             if next_lane[i][j] != 0 and next_lane[i][j].state == 'wait':
    #                                 # 表示前进道路上有等待的车，自己也等待，后续不能开flag=1
    #                                 next_state = 0
    #                                 flag = 1
    #                                 break
    #                             elif next_lane[i][j] and next_lane[i][j].state == 'final':
    #                                 tmp = j - 1  # 最近的一辆final的车，如果能走，走到它后面，如果不能，进入下一个车道
    #                                 break
    #                             elif next_lane[i][j] == 0:
    #                                 if j >= tmp:
    #                                     tmp = j  # tmp记录在最小车道上车辆能到达的最远的位置
    #                         if tmp >= 0:
    #                             next_state = 0
    #                             lane[car.lane][car.road_pos] = 0
    #                             next_lane[i][tmp] = car
    #                             car.lane = i
    #                             car.road_pos = tmp
    #                             car.road_index += 1
    #                             car.state = 'final'
    #                             dead_stack.append(car.id)
    #                             S.car_info[car.id] = car
    #                             flag = 2
    #                             break
    #                         if flag:
    #                             break
    #                 if next_state:
    #                     handled = 1
    #                     lane[car.lane][car.road_pos] = 0
    #                     lane[car.lane][-1] = car
    #                     car.road_pos = self.length - 1
    #                     car.state = 'final'
    #                     dead_stack.append(car.id)
    #                     S.car_info[car.id] = car
    #                     flag = 2
    #                 if flag == 2:
    #                     handled = 1
    #                     # print('{} Success pass cross {}, start DriveCar for rest Car.'.format(car.id, cross_id))
    #                     # 当成功调度路口后，马上调度这条车道上所有的车。
    #                     # print('After Rightpass the cross, Drive all cars in this lane.')
    #                     for j in range(self.length - 1, -1, -1):
    #                         if lane[lane_prev][j] != 0:
    #                             dead_stack, car, signal = self.DriveCar(lane[lane_prev][j], dead_stack, S, reversed)
    #                             S.car_info[car.id] = car
    #             elif direction == 1:
    #                 next_state = 1
    #                 flag = 0  # 若flag为0，表示可正常拐弯
    #                 # 左拐具有比直行低的优先级，需要考虑针对目标道路直行的有无冲突，没有则行车，否则等待下次调度
    #                 straight_road_id = four_road[(four_road.index(next_road_id) - 2) % 4]
    #                 if straight_road_id != -1:
    #                     straight_road = S.road_info[straight_road_id]
    #                     straight_car_list, straight_rev_car_list = straight_road.WhichCar()
    #                 # 处理直行道路是否逆行道路
    #                 if straight_road_id != -1:
    #                     if straight_road.end != cross_id:
    #                         straight_todo_list = straight_rev_car_list
    #                     else:
    #                         straight_todo_list = straight_car_list
    #                 else:
    #                     straight_todo_list = []
    #                 # 如果直行道上最高优先级的车辆要去目标道路，flag立起来，本车不能通行。
    #                 for car_id in straight_todo_list:
    #                     if S.car_info[car_id].state == 'wait' and S.car_info[car_id].RoadSequence[
    #                         S.car_info[car_id].road_index + 1] == next_road_id:
    #                         flag = 1
    #                         break
    #                     if S.car_info[car_id].state == 'wait' and S.car_info[car_id].RoadSequence[
    #                         S.car_info[car_id].road_index + 1] != next_road_id:
    #                         flag = 0
    #                         break
    #                 if flag == 0:  # 可以左拐
    #                     for i in range(next_road.channel):
    #                         tmp = -1
    #                         for j in range(next_pos + 1):
    #                             if next_lane[i][j] != 0 and next_lane[i][j].state == 'wait':
    #                                 # 表示前进道路上有等待的车，自己也等待，后续不能开，flag=1
    #                                 next_state = 0
    #                                 flag = 1
    #                                 break
    #                             elif next_lane[i][j] and next_lane[i][j].state == 'final':
    #                                 tmp = j - 1  # 最近的一辆final的车
    #                                 break
    #                             elif next_lane[i][j] == 0:
    #                                 if j >= tmp:
    #                                     tmp = j  # tmp记录在最小车道上车辆能到达的最远的位置
    #                         if tmp >= 0:
    #                             next_state = 0
    #                             lane[car.lane][car.road_pos] = 0
    #                             next_lane[i][tmp] = car
    #                             car.lane = i
    #                             car.road_pos = tmp
    #                             car.road_index += 1
    #                             car.state = 'final'
    #                             dead_stack.append(car.id)
    #                             S.car_info[car.id] = car
    #                             flag = 2
    #                             break
    #                         if flag:
    #                             break
    #                 if next_state:
    #                     handled = 1
    #                     lane[car.lane][car.road_pos] = 0
    #                     lane[car.lane][-1] = car
    #                     car.road_pos = self.length - 1
    #                     car.state = 'final'
    #                     dead_stack.append(car.id)
    #                     S.car_info[car.id] = car
    #                     flag = 2
    #                 if flag == 2:
    #                     handled = 1
    #                     #                        print('{} Success pass cross {}, start DriveCar for rest Car.'.format(car.id, cross_id))
    #                     # 当成功调度路口后，马上调度这条车道上所有的车。
    #                     #                        print('After Leftpass the cross, Drive all cars in this lane.')
    #                     for j in range(self.length - 1, -1, -1):
    #                         if lane[lane_prev][j] != 0:
    #                             dead_stack, car, signal = self.DriveCar(lane[lane_prev][j], dead_stack, S, reversed)
    #                             S.car_info[car.id] = car
    #             if flag == 1:  # 表示未能成功通行，其后的所有车都无法通行。
    #                 handled = 0
    #                 return dead_stack, handled
    #         else:
    #             continue
    #     return dead_stack, handled
    def passCross(self, dead_stack, S: Judge, reversed=False):
        # 通过路口的逻辑, reversed表示处理该条道路的反向通道
        car_list, rev_car_list = self.WhichCar()
        handled = 0  # 表示有车被调度，用于判断死锁
        if not reversed:
            lane = self.lane
            cross_id = self.end
            todo_list = deepcopy(car_list)
        else:
            assert self.isDuplex == 1, 'Error reversed option for passCross.'
            lane = self.lane_rev
            cross_id = self.start
            todo_list = deepcopy(rev_car_list)
        four_road = S.cross_info[cross_id].roads  # 对于当前路口连接的四条道路
        for car_id in todo_list:
            # if car_id == 18273:
            #     print(0)
            car = S.car_info[car_id]
            lane_prev = car.lane
            deadstack, car, signal = self.DriveCar(car, dead_stack, S, reversed)
            if signal:
                continue
            if car.state == 'wait':
                # 若到达了最后一条路
                if self.id == car.RoadSequence[-1]:
                    dead_stack, S, signal = self.DriveCar(car, dead_stack, S)
                    if signal:
                        handled = 1
                    return dead_stack, S, handled
                next_road_id = car.RoadSequence[car.road_index + 1]
                next_road = S.road_info[next_road_id]
                # 判断要进入的下一条路是进逆车道或是顺车道
                if next_road.start == cross_id:
                    next_lane = next_road.lane
                elif next_road.end == cross_id:
                    assert next_road.isDuplex, "Next road reversed option false..."
                    next_lane = next_road.lane_rev
                direction = (four_road.index(next_road_id) - four_road.index(self.id)) % 4
                '''-----------------------------------Debuged here'''
                # direction含义：1：左拐，2：直行，3：右拐
                # 若前方没有wait状态的车辆，如果是同一道路直行
                # 此调度发生于DriveCar或者passCross问题后的DriveCar中，不需要额外设计情况
                # 考虑需要通过路口的情况
                # 确定下个位置
                v1 = min(car.speed, self.speed)
                v2 = min(car.speed, next_road.speed)
                s1 = self.length - car.road_pos - 1
                s2 = v2 - s1
                # print('s1, s2, v1, v2, car.id, direction', s1, s2, v1, v2, car.id, direction)
                # assert s2 > 0, 'passCross get s2 limited!'
                # if self.length - 1 - car.road_pos >= min(next_Road.speed, car.speed):
                #     # print('No {} car will pass the cross but get S2 restrict'.format(car.id))
                #     lane[car.lane][car.road_pos] = 0
                #     car.road_pos = self.length - 1  # 到达车道最前端
                #     lane[car.lane][car.road_pos] = car
                #     car.state = 'final'
                #     dead_stack.append(car.id)
                #     return dead_stack, True
                next_pos = s2 - 1
                flag = 0  # 0表示可通行，1表示不可通行，2表示已经通行完毕
                next_state = 1  # next_state为1表示后续所有的位置都被final的车占据了
                if direction == 2:  # 直行到下一条路
                    # s2限制
                    if s2 <= 0:
                        # print('No {} car will pass the cross but get S2 restrict'.format(car.id))
                        lane[car.lane][car.road_pos] = 0
                        car.road_pos = self.length - 1  # 到达车道最前端
                        lane[car.lane][car.road_pos] = car
                        car.state = 'final'
                        dead_stack.append(car.id)
                        next_state = 0
                        flag == 2
                    else:
                        for i in range(next_road.channel):
                            tmp = -1
                            for j in range(next_pos + 1):
                                if next_lane[i][j] != 0:
                                    if next_lane[i][j].state == 'wait':
                                        # 表示前进道路上有等待的车，自己也等待
                                        next_state = 0
                                        flag = 1
                                        break
                                    else:
                                        tmp = j - 1
                                        break
                                elif next_lane[i][j] == 0:
                                    if j >= tmp:
                                        tmp = j  # tmp记录在最小车道上能到达最远的位置
                            if tmp >= 0:
                                next_state = 0
                                lane[car.lane][car.road_pos] = 0
                                next_lane[i][tmp] = car
                                car.lane = i
                                car.road_pos = tmp
                                car.road_index += 1
                                car.state = 'final'
                                dead_stack.append(car.id)
                                S.car_info[car.id] = car
                                flag = 2
                                break
                            if flag:
                                break
                    # 后面所有可能位置全被final车辆占据，只能走到道路最前端，标为final
                    if next_state:
                        handled = 1
                        lane[car.lane][car.road_pos] = 0
                        car.road_pos = self.length - 1
                        lane[car.lane][car.road_pos] = car
                        car.state = 'final'
                        dead_stack.append(car.id)
                        S.car_info[car.id] = car
                        flag = 2
                    # 已经通行完毕（无论过没过路口），本车道全部需要DriveCar
                    if flag == 2:
                        handled = 1
                        #                        print('{} Success pass cross {}, start DriveCar for rest Car.'.format(car.id, cross_id))
                        # 当成功调度路口后，马上调度这条车道上所有的车。
                        #                        print('After Straightpass the cross, Drive all cars in this lane.')
                        for j in range(self.length - 2, -1, -1):
                            if lane[lane_prev][j]:
                                dead_stack, car, signal = self.DriveCar(lane[lane_prev][j], dead_stack, S, reversed)
                                S.car_info[car.id] = car
                elif direction == 3:
                    # 右拐具有最低的优先级，需要考虑针对目标道路左拐和直行的有无冲突，没有则行车，否则等待下次调度
                    straight_road_id = four_road[(four_road.index(next_road_id) - 2) % 4]
                    left_road_id = four_road[(four_road.index(next_road_id) - 1) % 4]
                    if straight_road_id != -1:
                        straight_road = S.road_info[straight_road_id]
                        straight_car_list, straight_rev_car_list = straight_road.WhichCar()
                    if left_road_id != -1:
                        left_road = S.road_info[left_road_id]
                        left_car_list, left_rev_car_list = left_road.WhichCar()
                    # 处理直行道路是否逆行道路
                    if straight_road_id != -1:
                        if straight_road.end != cross_id:
                            straight_todo_list = deepcopy(straight_rev_car_list)
                        else:
                            straight_todo_list = deepcopy(straight_car_list)
                    else:
                        straight_todo_list = []
                    # 处理左拐道路是否逆行道路
                    if left_road_id != -1:
                        if left_road.end != cross_id:
                            left_todo_list = deepcopy(left_rev_car_list)
                        else:
                            left_todo_list = deepcopy(left_car_list)
                    else:
                        left_todo_list = []
                    # 如果直行道上最高优先级的车辆要去目标道路，flag立起来，本车不能通行。
                    for car_id in straight_todo_list:
                        if S.car_info[car_id].state == 'wait' and S.car_info[car_id].RoadSequence[
                            S.car_info[car_id].road_index + 1] == next_road_id:
                            flag = 1
                            break
                        if S.car_info[car_id].state == 'wait' and S.car_info[car_id].RoadSequence[
                            S.car_info[car_id].road_index + 1] != next_road_id:
                            flag = 0
                            break
                    # 如果直行道上没有，如果左转最高优先级的车辆要去目标道路，flag立起来，本车不能通行。
                    if not flag:
                        for car_id in left_todo_list:
                            if S.car_info[car_id].state == 'wait' and S.car_info[car_id].RoadSequence[
                                S.car_info[car_id].road_index + 1] == next_road_id:
                                flag = 1
                                break
                            if S.car_info[car_id].state == 'wait' and S.car_info[car_id].RoadSequence[
                                S.car_info[car_id].road_index + 1] != next_road_id:
                                flag = 0
                                break
                    if flag == 0:  # 可以右拐
                        if s2 <= 0:
                            # print('No {} car will pass the cross but get S2 restrict'.format(car.id))
                            lane[car.lane][car.road_pos] = 0
                            car.road_pos = self.length - 1  # 到达车道最前端
                            lane[car.lane][car.road_pos] = car
                            car.state = 'final'
                            dead_stack.append(car.id)
                            next_state = 0
                            flag == 2
                        else:
                            for i in range(next_road.channel):
                                tmp = -1
                                for j in range(next_pos + 1):
                                    if next_lane[i][j] != 0 and next_lane[i][j].state == 'wait':
                                        # 表示前进道路上有等待的车，自己也等待，后续不能开flag=1
                                        next_state = 0
                                        flag = 1
                                        break
                                    elif next_lane[i][j] and next_lane[i][j].state == 'final':
                                        tmp = j - 1  # 最近的一辆final的车，如果能走，走到它后面，如果不能，进入下一个车道
                                        break
                                    elif next_lane[i][j] == 0:
                                        if j >= tmp:
                                            tmp = j  # tmp记录在最小车道上车辆能到达的最远的位置
                                if tmp >= 0:
                                    next_state = 0
                                    lane[car.lane][car.road_pos] = 0
                                    next_lane[i][tmp] = car
                                    car.lane = i
                                    car.road_pos = tmp
                                    car.road_index += 1
                                    car.state = 'final'
                                    dead_stack.append(car.id)
                                    S.car_info[car.id] = car
                                    flag = 2
                                    break
                                if flag:
                                    break
                    if next_state:
                        handled = 1
                        lane[car.lane][car.road_pos] = 0
                        lane[car.lane][-1] = car
                        car.road_pos = self.length - 1
                        car.state = 'final'
                        dead_stack.append(car.id)
                        S.car_info[car.id] = car
                        flag = 2
                    if flag == 2:
                        handled = 1
                        # print('{} Success pass cross {}, start DriveCar for rest Car.'.format(car.id, cross_id))
                        # 当成功调度路口后，马上调度这条车道上所有的车。
                        # print('After Rightpass the cross, Drive all cars in this lane.')
                        for j in range(self.length - 1, -1, -1):
                            if lane[lane_prev][j] != 0:
                                dead_stack, car, signal = self.DriveCar(lane[lane_prev][j], dead_stack, S, reversed)
                                S.car_info[car.id] = car
                elif direction == 1:
                    next_state = 1
                    flag = 0  # 若flag为0，表示可正常拐弯
                    # 左拐具有比直行低的优先级，需要考虑针对目标道路直行的有无冲突，没有则行车，否则等待下次调度
                    straight_road_id = four_road[(four_road.index(next_road_id) - 2) % 4]
                    if straight_road_id != -1:
                        straight_road = S.road_info[straight_road_id]
                        straight_car_list, straight_rev_car_list = straight_road.WhichCar()
                    # 处理直行道路是否逆行道路
                    if straight_road_id != -1:
                        if straight_road.end != cross_id:
                            straight_todo_list = straight_rev_car_list
                        else:
                            straight_todo_list = straight_car_list
                    else:
                        straight_todo_list = []
                    # 如果直行道上最高优先级的车辆要去目标道路，flag立起来，本车不能通行。
                    for car_id in straight_todo_list:
                        if S.car_info[car_id].state == 'wait' and S.car_info[car_id].RoadSequence[
                            S.car_info[car_id].road_index + 1] == next_road_id:
                            flag = 1
                            break
                        if S.car_info[car_id].state == 'wait' and S.car_info[car_id].RoadSequence[
                            S.car_info[car_id].road_index + 1] != next_road_id:
                            flag = 0
                            break
                    if flag == 0:  # 可以左拐
                        if s2 <= 0:
                            # print('No {} car will pass the cross but get S2 restrict'.format(car.id))
                            lane[car.lane][car.road_pos] = 0
                            car.road_pos = self.length - 1  # 到达车道最前端
                            lane[car.lane][car.road_pos] = car
                            car.state = 'final'
                            dead_stack.append(car.id)
                            next_state = 0
                            flag == 2
                        else:
                            for i in range(next_road.channel):
                                tmp = -1
                                for j in range(next_pos + 1):
                                    if next_lane[i][j] != 0 and next_lane[i][j].state == 'wait':
                                        # 表示前进道路上有等待的车，自己也等待，后续不能开，flag=1
                                        next_state = 0
                                        flag = 1
                                        break
                                    elif next_lane[i][j] and next_lane[i][j].state == 'final':
                                        tmp = j - 1  # 最近的一辆final的车
                                        break
                                    elif next_lane[i][j] == 0:
                                        if j >= tmp:
                                            tmp = j  # tmp记录在最小车道上车辆能到达的最远的位置
                                if tmp >= 0:
                                    next_state = 0
                                    lane[car.lane][car.road_pos] = 0
                                    next_lane[i][tmp] = car
                                    car.lane = i
                                    car.road_pos = tmp
                                    car.road_index += 1
                                    car.state = 'final'
                                    dead_stack.append(car.id)
                                    S.car_info[car.id] = car
                                    flag = 2
                                    break
                                if flag:
                                    break
                    if next_state:
                        handled = 1
                        lane[car.lane][car.road_pos] = 0
                        lane[car.lane][-1] = car
                        car.road_pos = self.length - 1
                        car.state = 'final'
                        dead_stack.append(car.id)
                        S.car_info[car.id] = car
                        flag = 2
                    if flag == 2:
                        handled = 1
                        #                        print('{} Success pass cross {}, start DriveCar for rest Car.'.format(car.id, cross_id))
                        # 当成功调度路口后，马上调度这条车道上所有的车。
                        #                        print('After Leftpass the cross, Drive all cars in this lane.')
                        for j in range(self.length - 1, -1, -1):
                            if lane[lane_prev][j] != 0:
                                dead_stack, car, signal = self.DriveCar(lane[lane_prev][j], dead_stack, S, reversed)
                                S.car_info[car.id] = car
                if flag == 1:  # 表示未能成功通行，其后的所有车都无法通行。
                    handled = 0
                    return dead_stack, handled
            else:
                continue
        return dead_stack, handled
    def WhichCar(self):
        # 返回当前道路上所有车辆的编号，按照调度顺序排列
        car_list = []
        rev_car_list = []
        j = self.length - 1
        while j >= 0:
            tmp = []
            for i in range(self.channel):
                if self.lane[i][j]:
                    tmp.append(self.lane[i][j].id)
            car_list += tmp
            j -= 1
        j = self.length - 1
        if self.lane_rev:
            while j >= 0:
                tmp = []
                for i in range(self.channel):
                    if self.lane_rev[i][j]:
                        tmp.append(self.lane_rev[i][j].id)
                rev_car_list += tmp
                j -= 1
        return car_list, rev_car_list


class Cross(object):
    """docstring for Cross"""

    def __init__(self, _id: int, cross_info: list):
        super(Cross, self).__init__()
        self.id = _id
        self.roads = sorted(cross_info)  # 存放连接该路口的四条路的编号
        self.need_arrange = False  # 是否需要调度

    def crossArrange(self, dead_stack, S: Judge):
        # 此处是调度各个路口的逻辑
        handled = 0
        for road_id in self.roads:
            if road_id == -1:
                tmp = 0
                continue
            else:
                road = S.road_info[road_id]
                if road.end == self.id:  # 出路口道路
                    dead_stack, tmp = road.passCross(dead_stack, S)
                elif road.start == self.id and road.isDuplex:  # 双向车道出路口
                    # print('process rev road, id is {}'.format(road_id))
                    dead_stack, tmp = road.passCross(dead_stack, S, reversed=True)
            handled |= tmp
        return dead_stack, handled

    def get_lane_and_car(self, S):
        for road_id in self.roads:
            if road_id != -1:
                road = S.road_info[road_id]
                print(road.id)
                print(road.lane_id())
                print('Next Road...')
        return 0


class Arranger():
    def __init__(self, judge: Judge):
        self.judge = judge
        self.init_cross_position()

    def get_turn_direction(self, cross_id, this_road, next_road):
        if this_road == 0:
            return 2
        four_road = self.judge.cross_info[cross_id].roads
        direction = (four_road.index(next_road) - four_road.index(this_road)) % 4
        return direction

    def init_cross_position(self):
        visited = []
        self.list = {}
        initcross = list(self.judge.cross_info.keys())[0]
        self.list[initcross] = [0, 0]
        stack = []
        stack.append([initcross, 0, 0])
        while stack:
            crossid, x, y = stack.pop()
            cross = self.judge.cross_info[crossid]
            visited.append(crossid)
            # print(crossid)
            for i, road_id in enumerate(cross.roads):
                if road_id == -1:
                    continue
                road = self.judge.road_info[road_id]

                if road.end == crossid:  # get another cross
                    nextcross = road.start
                elif road.start == crossid:
                    nextcross = road.end

                if i == 0:  # north
                    if nextcross not in visited:
                        stack.append([nextcross, x, y + 1])
                        self.list[nextcross] = [x, y + 1]
                elif i == 1:  # east
                    if nextcross not in visited:
                        stack.append([nextcross, x + 1, y])
                        self.list[nextcross] = [x + 1, y]
                elif i == 2:  # south
                    if nextcross not in visited:
                        stack.append([nextcross, x, y - 1])
                        self.list[nextcross] = [x, y - 1]
                elif i == 3:  # west
                    if nextcross not in visited:
                        stack.append([nextcross, x - 1, y])
                        self.list[nextcross] = [x - 1, y]

    def get_load(self, road_id, direction):

        road = self.judge.road_info[road_id]
        totalcars = 0
        if direction == 0:
            for lane in road.lane:
                totalcars += sum(list(map(lambda x: 0 if x == 0 else 1, lane)))
            load = totalcars / road.length / road.channel
        else:
            for lane in road.lane_rev:
                totalcars += sum(list(map(lambda x: 0 if x == 0 else 1, lane)))
            load = totalcars / road.length / road.channel
        return load

    def get_cost(self, road_id, car):
        road = self.judge.road_info[road_id]
        cost = (road.length / min(road.speed, car.speed) + 2)

        return cost

    def get_direction(self, from_cross_id, road_id):
        road = self.judge.road_info[road_id]
        if road.end == from_cross_id:
            # 逆向行驶
            if road.isDuplex == 1:
                nextcross = road.start
                direction = 1
            else:
                assert "wrong way"
        elif road.start == from_cross_id:
            nextcross = road.end
            direction = 0

        return nextcross, direction

    def can_move(self, time, car):
        if time < car.planTime:
            return False
        nextcross = car.start
        for road_id in car.RoadSequence:
            # print(roadmap.road_list[road_id].get_load())
            nextcross, direction = self.get_direction(nextcross, road_id)
            if self.get_load(road_id, direction) > 0.5:
                return False

        return True

    def h(self, this_cross, to_cross):

        this_position = self.list[this_cross]
        to_position = self.list[to_cross]
        return manhattanDistance(this_position, to_position) * 4

    def g_only_cost(self, road_id, car, direction, turn_direction):
        return self.get_cost(road_id, car)

    def g(self, road_id, car, direction, turn_direction):
        return self.get_cost(road_id, car) * exp(self.get_load(road_id, direction) * 5)

    def g_turn_left(self, last_road, road_id, car, direction, turn_direction):
        # direction含义：1：左拐，2：直行，3：右拐
        if turn_direction == 1:
            turn_cost = 2
        elif turn_direction == 2:
            turn_cost = 0
        elif turn_direction == 3:
            turn_cost = 10
        cost = self.get_cost(road_id, car) * exp(self.get_load(road_id, direction) * 5)
        if last_road == 0:
            return cost
        else:
            last = self.judge.road_info[last_road]
            this = self.judge.road_info[road_id]
            from math import ceil
            cost *= ceil(last.channel / this.channel)
            if this.channel == 1:
                cost *= 3

            return cost


    def A_star(self, car: Car, gfunc, hfunc):
        """
        :param car:
        :return:
        #calculate the path of the car using A* method
        """
        from_id, to_id = car.start, car.end
        car.RoadSequence = []
        # print(cross_copy,self.cross_list)
        closeset = []
        openset = []
        myPQ = PriorityQueue()
        start = from_id
        gcost = {}
        gcost[start] = 0
        fcost = {}
        fcost[start] = hfunc(start, to_id)
        myPQ.push((start, []), fcost[start])
        while not myPQ.isEmpty():
            cross_id, path = myPQ.pop()
            closeset.append(cross_id)
            if path:
                last_road = path[-1]
            else:
                last_road = 0
            if cross_id == to_id:  # arrived
                car.RoadSequence = path
                return

            for road_id in self.judge.cross_info[cross_id].roads:

                if road_id == -1:
                    continue

                if last_road == road_id:
                    continue
                road = self.judge.road_info[road_id]
                if road.end == cross_id:
                    # 逆向行驶
                    if road.isDuplex == 1:
                        nextcross = road.start
                        direction = 1
                    else:
                        continue
                elif road.start == cross_id:
                    nextcross = road.end
                    direction = 0
                    # 正向行驶
                else:
                    nextcross = 0
                    print("the cross don't have the road")

                turn_direction = self.get_turn_direction(cross_id, last_road, road_id)

                cost = gfunc(last_road, road_id, car, direction, turn_direction)

                if nextcross not in closeset:
                    if nextcross in openset:
                        if gcost[cross_id] + cost < gcost[nextcross]:
                            gcost[nextcross] = gcost[cross_id] + cost
                            myPQ.push((nextcross, path + [road_id]), gcost[nextcross] + hfunc(nextcross, to_id))
                    else:
                        openset.append(nextcross)
                        gcost[nextcross] = gcost[cross_id] + cost
                        myPQ.push((nextcross, path + [road_id]), gcost[nextcross] + hfunc(nextcross, to_id))

    def arrange(self):
        """

        :return:
        """
        car_list = list(self.judge.car_info.values())
        car_list.sort(key=lambda x: x.speed, reverse=True)
        # 车从快到慢出发

        mytime = 1
        count = 0
        runinglist = []

        start_time = time.time()
        self.judge.result = 0  # 系统调度时间
        self.judge.tick = 0  # 车辆运行时间

        self.judge.active_stack = []  # 存放当前时刻应被处理的车辆编号
        self.judge.active_road = []  # 存放当前时刻有车的道路编号
        self.judge.final_stack = []

        while car_list:

            car = car_list.pop()
            # print(car.can_move(roadmap,time))
            self.A_star(car, self.g_turn_left, self.h)
            if self.can_move(mytime, car):
                car.StartTime = mytime
                runinglist.append(car.id)

            else:
                #
                if car.planTime > mytime:
                    count += 1
                    car_list.insert(-200 * (car.planTime - mytime), car)
                    # TODO 性能可能有些问题
                else:
                    count += 1
                    car_list.insert(-1000, car)
            if count == 200 or len(runinglist) >= 50:
                # time up
                print(mytime, len(car_list), len(runinglist))
                count = 0
                if not self.judge.step(runinglist):
                    break
                runinglist = []
                # TODO put car into the
                mytime += 1
        print('Totol arrange time is {} tick, the program run time is {} s.'.format(self.judge.tick + 16,
                                                                                        round(time.time() - start_time,
                                                                                              2)))

    def arrange_try_catch(self):
        car_list = list(self.judge.car_info.keys())
        car_list.sort(key=lambda x: self.judge.car_info[x].speed, reverse=True)
        # 车从快到慢出发

        mytime = 0
        count = 0
        runinglist = []

        start_time = time.time()
        self.judge.result = 0  # 系统调度时间
        self.judge.tick = 0  # 车辆运行时间

        self.judge.active_stack = []  # 存放当前时刻应被处理的车辆编号
        self.judge.active_road = []  # 存放当前时刻有车的道路编号
        self.judge.final_stack = []
        max_per_tick = 50
        baklist = []
        baklist.append([mytime, deepcopy(self.judge), car_list.copy()])
        while car_list:
            car_id = car_list.pop()
            car = self.judge.car_info[car_id]
            self.A_star(car, self.g_turn_left, self.h)
            if self.can_move(mytime, car):
                car.StartTime = mytime
                runinglist.append(car_id)

            else:
                #
                if car.planTime > mytime:
                    count += 1
                    car_list.insert(-200 * (car.planTime - mytime), car_id)
                    # TODO 性能可能有些问题
                else:
                    count += 1
                    car_list.insert(-1000, car_id)
            if count == 200 or len(runinglist) >= max_per_tick:
                # time up
                print(mytime, len(car_list), len(runinglist))

                try:
                    self.judge.step(runinglist)

                except:
                    print("***********deadlock*************")
                    max_per_tick /= 2
                    mytime, self.judge, car_list = baklist.pop()
                    self.judge.step([])
                finally:
                    mytime += 1
                    count = 0
                    runinglist = []
                if mytime % 30 == 0:
                    baklist.append([mytime, deepcopy(self.judge), car_list.copy()])
                    max_per_tick = 50
                # TODO put car into the

        print('Totol arrange time is {} tick, the program run time is {} s.'.format(self.judge.tick + 16,
                                                                                    round(time.time() - start_time,
                                                                                          2)))

    def Method4(self):
        car_list = list(self.judge.car_info.keys())
        # Method4: 按照notconflict_pairs形成car_list#
        car_list.sort(key=lambda x: x.planTime, reverse=True)
        car_list2 = []
        carno_list2 = []
        set_stack = []
        while car_list:
            car1 = car_list.pop()
            set1 = self.notconflict_car[car1.id]
            tmp = set1
            set_stack.append(set1)
            car_list2.append(car1)
            carno_list2.append(car1.id)
            while set_stack:
                try:
                    car2_id = tmp.pop()
                    if car2_id in carno_list2:
                        continue
                    car_list2.append(self.judge.car_info[car2_id])
                    carno_list2.append(car2_id)
                    car_list.remove(self.judge.car_info[car2_id])
                    set2 = self.notconflict_car[car2_id]
                    tmp = set2 & set1
                    set_stack.append(tmp)
                    set2 = set1
                except Exception:
                    tmp = set_stack.pop()
        car_list = car_list2[::-1]

    # ++++++++++++++++++++#

    def write_answers(self, answer_path):
        answer = open(answer_path, 'w')
        for car in self.judge.car_info.values():
            answer.writelines(str(car))
            pass
