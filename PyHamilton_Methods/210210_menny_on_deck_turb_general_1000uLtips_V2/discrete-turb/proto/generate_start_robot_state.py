from statesearch import RobotStateNode

def empty_robot_state():
    state = RobotStateNode()

    tips = state.phys_state.tips
    vessels = state.phys_state.vessels
    instruments = state.phys_state.instruments

    for ch_num in range(8):
        channel = instruments.ch_1ml.channels[str(ch_num)]
        channel.mounted = None
        channel.capacity = 1000
        channel.vert_align = '0'
        channel.horiz_align = str(ch_num)

    for col in range(12):
        for row in range(8):
            ch_num = col*8 + row
            channel = instruments.head_96ch.channels[str(ch_num)]
            channel.mounted = None
            channel.capacity = 1000
            channel.vert_align = str(col)
            channel.horiz_align = str(row)

    return state

if __name__ == '__main__':
    with open('default_state.json', 'w+') as f:
        f.write(empty_robot_state().dump_state())

