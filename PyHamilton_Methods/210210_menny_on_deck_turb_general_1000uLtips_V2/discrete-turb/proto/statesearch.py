from heapq import heappush, heappop
import json
from dotmap import DotMap
import random
import cmdlib
from cmdlib import Position
from pace_util import LayoutManager

DEFAULT_ACTION_COST = 10.0
DEFAULT_SUBACTION_COST = 3.5


class TaskNode:
    def __init__(self, constraint=None, **kwargs):
        self.constraint = constraint
        self._prereqs = set()
        for prereq in self.prereqs(**kwargs):
            self.add_prereq(prereq)
        self._dependents = set()
        self.unique_id = str(random.random())

    def prereqs(self, **kwargs): # override this
        return self._prereqs

    def all_dependents(self):
        return self._dependents.union(*(dep.all_dependents() for dep in self._dependents))

    def add_prereq(self, prereq):
        prereq._dependents.add(self.unique_id)
        for dep in self.all_dependents:
            prereq._dependents.add(self.unique_id)
        self._prereqs.add(prereq)

    def dependent_on(self, other):
        return self.unique_id in other._dependents

    def copy(self):
        copy = TaskNode(self.constraint)
        copy._prereqs = set(self._prereqs)
        copy._dependents = set(self._dependents)
        copy.unique_id = self.unique_id
        return copy


class TaskGraph:
    def __init__(self, goal_tasks=[]):
        self.terminal_nodes = set()
        self.finished_ids = set()
        for goal in goal_tasks:
            self.end_condition(goal)

    def finish(self, node):
        self.finished_ids.add(node.unique_id)
        return self

    def topo_sort(self, condition=lambda _: True):
        tsort = []
        task_queue = list(self.terminal_nodes)
        while task_queue:
            task = task_queue.pop(0)
            if condition(task):
                tsort.append(task)
            for pre_task in task.prereqs:
                task_queue.append(pre_task)
        return tsort

    def accessible_tasks(self):
        return self.topo_sort(condition=lambda t: all(p.unique_id in self.finished_ids for p in n.prereqs()))
    
    def end_condition(self, node):
        self.terminal_nodes.add(node)
        return self

    def copy(self):
        copy = TaskGraph()
        already_copied = {}
        for task in self.topo_sort():
            if task.unique_id in already_copied:
                raise RuntimeError('Apparently topological sort didn\'t work.')
            new_task = task.copy()
            for prereq in task.prereqs():
                if prereq.unique_id in already_copied:
                    new_task._prereqs.remove(prereq)
                    new_task._prereqs.add(already_copied[prereq.unique_id])
            already_copied[task.unique_id] = new_task
        copy.terminal_nodes = set((already_copied[t] for t in self.terminal_nodes))
        copy.finished_ids = set(self.finished_ids)
        return copy


class TaskConstraint:
    def __init__(self, liquids=None, contacted=None, instruments=None, **exact_match):
        self.liquids = None # at least one of these liquids (strings) needs to be involved
        self.contacted = [] # strings representing things it's allowed to have touched
        self.instruments = None # options for what instrument to use
        self.exact_match = exact_match

    def satisfied_by(self, other_constraint):
        if other_constraint.instruments is not None:
            if all(inst not in self.instruments for other_constraint
        if self.liquids is not None:
            for liquid in other_constraint.liquids:
                if liquid not in self.liquids:
                    return False
        for item in other_constraint.contacted:
            if item not in self.contacted:
                return False
        for match in other_constraint.exact_match:
            if (match in self.exact_match
                    and self.exact_match[match] != other_constraint.exact_match[match]):
                return False
        return True


class Start(TaskNode):
    pass # no prereqs


class ChannelFree(TaskNode):
    pass # no prereqs


class TipMounted(TaskNode):
    def prereqs(self, constraint=None):
        return set((ChannelFree(constraint=constraint),))


class TipVolumeIncrease(TaskNode):
    pass


class MoveLiquid(TaskNode):
    def prereqs(self, origin=None, to=None, vol=None, **kwargs):
        try:
            tos = list(to)
        except TypeError:
            tos = [to]
        try:
            froms = list(origin)
        except TypeError:
            froms = [origin]
        if not vol:
            raise ValueError('cannot move unspecified or zero volume of liquid')
        return set(())


class IncompatibleStateChangeError(ValueError):
    pass

def load_pos(pos_str, state):
    lmgr = LayoutManager.get_manager(state.layfile.checksum)
    layout_name, idx_str = pos_str.split(', ')
    return Position(lmgr.resources[layout_name], int(idx_str))

class RobotStep:
    def __init__(self):
        pass # override; constructor must take no arguments

    def incorporate(self, state_change):
        if self.packed or state_change.step != self.__class__:
            raise IncompatibleStateChangeError()
        self._incorporate(state_change)

    def _incorporate(self, eject_change, state):
        pass # override; raises IncompatibleStateChangeError

    def send_command(self, robot_interface):
        pass # override

    def copy(self):
        pass # override


class RobotStateChange:
    step_class = None # must override
    def __init__(self, **params):
        self.params = params

    def operate(self, state):
        # override. mutate the state in place (assume already copied), return none
        pass

    def needed_param(self, param_name, errmsg='')
        if param_name not in params or params[param_name] is None:
            raise ValueError(errmsg)
        return self.params[param_name]

    def copy(self):
        return RobotStateChange(json.loads(json.dumps(self.params)))


class EjectStep(RobotStep): # for the 1ml channels
    def __init__(self):
        self.packed = False
        self.positions = [None]*16
        self.ejtype = None
        self.vert_aligns = set()
        # TODO: Can't model out-of-order channel costs
        # TODO: because no position order between different labware
        self.order_cost = 0

    def _incorporate(self, eject_change, state):
        if eject_change.instrument != 'ch_1ml':
            raise IncompatibleStateChangeError()
        additional_cost = 0
        position = eject_change.dest_position 
        change_ejtype = 'default' if position is None else 'position'
        if self.ejtype is None:
            self.ejtype = change_ejtype
            additional_cost += DEFAULT_ACTION_COST
        elif self.ejtype != change_ejtype:
            raise IncompatibleStateChangeError()
        channels = state[eject_change.instrument].channels
        channel_idx = channels.index(eject_change.channel_name)
        if self.positions[channel_idx] is not None:
            raise IncompatibleStateChangeError()
        new_valigns = state.vert_aligns[str(Position)]
        if all((va not in self.vert_aligns for va in new_valigns)):
            additional_cost += DEFAULT_ACTION_COST
            self.vert_aligns = self.vert_aligns.union(new_valigns)
        self.positions[channel_idx] = position if position else True
        if len([p for p in self.positions if p is not None]) == len(channels):
            self.packed = True
        # TODO: this would be rewritten to give a subtler order cost
        if self.order_cost != 0:
            order = 0
            for pos in self.positions:
                if pos.idx <= order:
                    self.order_cost = DEFAULT_SUBACTION_COST
                    self.additional_cost += self.order_cost
                    break
                order = pos.idx
        return additional_cost

    def send_command(self, robot_interface):
        if self.ejtype is None: # step has never been initialized
            raise RuntimeError()
        return cmdlib.tip_eject(robot_interface, self.positions, default=self.ejtype=='default')

    def copy(self):
        es = EjectStep()
        es.packed = self.packed
        es.positions = list(self.positions)
        es.ejtype = self.ejtype
        es.vert_aligns = set(self.vert_aligns)
        es.order_cost = self.order_cost
        return es


class EjectStateChange(RobotStateChange): # can be used to resolve a ChannelFree or TODO: exists? TipPut
    step_class = EjectStep
    def __init__(self, **params):
        self.instrument = self.needed_param('instrument', 'to eject, must specify instrument.')
        self.channel_name = self.needed_param('channel', 'to eject, must specify which channel.')
        self.dest_position = params.get('destination', None)
        self.params = params

    def operate(self, state):
        channel = state[self.instrument].channels[self.channel_name]
        tipid = channel.mounted
        if not tipid:
            raise ValueError('tip not mounted, cannot eject')
        tip = state.tips[tipid]
        tip.position = self.dest_position
        channel.mounted = None


class PickUpStep(RobotStep):
    def __init__(self):
        pass # override; constructor must take no arguments

    def _incorporate(self, pickup_change, state):
        if pickup_change.instrument != 'ch_1ml':
            raise IncompatibleStateChangeError()
        additional_cost = 0
        position = state.tips[pickup_change.tipid].position
        change_ejtype = 'default' if position is None else 'position'
        if self.ejtype is None:
            self.ejtype = change_ejtype
            additional_cost += DEFAULT_ACTION_COST
        elif self.ejtype != change_ejtype:
            raise IncompatibleStateChangeError()
        channels = state[eject_change.instrument].channels
        channel_idx = channels.index(eject_change.channel_name)
        if self.positions[channel_idx] is not None:
            raise IncompatibleStateChangeError()
        new_valigns = state.vert_aligns[str(Position)]
        if all((va not in self.vert_aligns for va in new_valigns)):
            additional_cost += DEFAULT_ACTION_COST
            self.vert_aligns = self.vert_aligns.union(new_valigns)
        self.positions[channel_idx] = load_pos(position, state) if position else True
        if len([p for p in self.positions if p is not None]) == len(channels):
            self.packed = True
        # TODO: this would be rewritten to give a subtler order cost
        if self.order_cost != 0:
            order = 0
            for pos in self.positions:
                if pos.idx <= order:
                    self.order_cost = DEFAULT_SUBACTION_COST
                    self.additional_cost += self.order_cost
                    break
                order = pos.idx
        return additional_cost
        pass # override; raises IncompatibleStateChangeError

    def send_command(self, robot_interface):
        pass # override

    def copy(self):
        pass # override


class PickUpStateChange(RobotStateChange):
    step_class = PickUpStep
    def __init__(self, **params):
        self.instrument = self.needed_param('instrument', 'to pick up, must specify instrument.')
        self.channel_name = self.needed_param('channel', 'to pick up, must specify which channel.')
        self.tip = self.needed_param('tipid', 'to pick up, must specify tip id.')
        self.params = params

    def operate(self, state):
        channel = state[self.instrument].channels[self.channel_name]
        if channel.mounted:
            raise ValueError('tip already mounted, cannot pick up')
        state.tips[self.tipid].position = None
        channel.mounted = self.tipid


class RobotStateNode:

    @staticmethod
    def parse_state(state):
        if state is None:
            state = {}
        else:
            try:
                state = json.loads(state)
            except TypeError:
                pass
        return DotMap(state)

    def __init__(self, state=None, tasks=None):
        self.phys_state = self.parse_state(state)
        self.task_graph = tasks
        self.step_path = []
        self.active_steps = []

    def path(self):
        return self.step_path + self.active_steps

    def apply_change(self, state_change, finish_task=None):
        for step in self.active_steps:
            try:
                cost = step.incorporate(state_change)
                if step.packed:
                    self.active_steps.remove(step)
                    self.step_path.append((self.cost() + cost, step))
                break
            except IncompatibleStateChangeError:
                continue
        else:
            self.active_steps.append(state_change.step_class())
        state_change.operate(self.state)
        if finish_task:
            self.task_graph.finish(finish_task)

    def dump_state(self):
        return json.dumps(self.phys_state.toDict())

    def cost(self):
        if not step_path:
            return 0
        cost, action = step_path[-1]
        return cost

    def copy(self):
        copy = RobotStateNode(self.dump_state(), self.tasks.copy())
        copy.step_path = [step.copy() for step in self.step_path]
        copy.active_steps = [step.copy() for step in self.active_steps]
        return copy


class RobotOptimizer:
    def __init__(self, start_state, layout_manager):
        start_state = RobotStateNode.parse_state(start_state)
        chsum = start_state.layfile.checksum
        if isinstance(chsum, str) and chsum != layout_manager.checksum:
            raise ValueError('start state is associated with the wrong layout file.')
        start_state.layfile.checksum = layout_manager.checksum

    def expand_state(state):
        next_states = [] # tuples (cost, possible next state)
        #def extend_path(step):
        #    next_states.append(
        for task in state.task_graph.accessible_tasks():
            if isinstance(task, ChannelFree):
                # could clear a channel on any instrument
                for instrument in state.instruments:
                    if task.constraint.instruments and instrument not in task.constraint.instruments:
                        continue
                    #if any channels are open, we're fine
                    for ch_name, channel in instruments[instrument].channels.iteritems():
                        if channel.mounted is None:
                            new_state = state.copy()
                            new_state.finish(task)
                            next_states.append(new_state)
                            break
                    else: # no channels were free
                        for ch_name, channel in instruments[instrument].channels.iteritems():
                            new_state = state.copy()
                            new_state.apply_change(EjectStateChange(instrument=instrument, channel=ch_name), finish_task=task)
                            next_states.append(new_state)
            if isinstance(task, ChannelFree):

    def least_cost_path(robot_state, task_graph):
        pqueue = [RobotStateNode(None, task_graph)]
        task_graph.accessible_tasks()
        seach_step = 0
        while pqueue:
            search_step += 1
            p, _, _, state = heappop(a)

if __name__ == '__main__':
    #moves = [{'from': [['agar1', [0, 1, 3, 4]], ['agar2', [0, 1, 3, 4]]], 'to':[['plate_0', i]], 'vol':230, {'match':'from_liquid':'agar'}} for i in range(12)]
    explicit_tasks = []
    moves = [MoveLiquid(liquid='hard_agar', to=Position('plate_0', i), vol=230) for i in range(12)]
    sys_state = {'plate_0':None}

    tasks = TaskGraph(moves)

    auto_system.execute(tasks)

