import os
import sys

# ==========================================
# 【核心修复：防打包路径漂移神技】
# ==========================================
if getattr(sys, 'frozen', False):
    # 如果程序是被 PyInstaller 打包成了 .exe
    # sys.executable 就是你生成的那个 .exe 文件的绝对路径
    # dirname 就会精确定位到 .exe 所在的文件夹！
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 如果你是在 PyCharm/开发环境下跑源码
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ASSET_DIR = os.path.join(BASE_DIR, 'assets')

# ==========================================
# 【桌宠引擎：核心物理与系统参数】
# ==========================================
DRAG_PAUSE_THRESHOLD = 0.1  # 拖拽停顿判定阈值 (秒)：抓着不动超过此时间，视为放弃投掷
THROW_BOOST_X = 1.0  # 横向臂力放大器：决定左右甩的爆发力
THROW_BOOST_Y = 1.0  # 纵向臂力放大器：决定上下甩的爆发力
GRAVITY = 1  # 重力
REFRESH_RATE = 20  # 系统刷新率 (毫秒)，20ms = 1秒50帧
PET_SIZE = 128  # 像素图大小
WALL_OFFSET = 48  # 角色挂在墙上减去的宽度

# ==========================================
# 【狐狐运动基因库 (速度与概率)】
# ==========================================
SPEED_WALK = 2  # 正常溜达的水平速度
SPEED_RUN = 3  # 发现目标时的赶路速度
SPEED_CLIMB = 2  # 爬墙的垂直速度
SPEED_CEILING = 2  # 天花板倒立漫步的速度
SPEED_JUMP_X = 8  # 决定跳得有多远
SPEED_JUMP_Y = 16  # 决定跳得有多高
SPEED_HUNT_X = 4        # 捕猎扑击的水平前冲力 (比跳墙小一半，显得短促有力)
SPEED_HUNT_Y = 14       # 捕猎起跳的垂直爆发力 (恰好能跃起一个漂亮的抛物线)
PROB_TURN_AROUND = 0.005  # 地面漫步时，每帧随机掉头的概率
PROB_CEILING_DROP = 0.008  # 天花板漫步时，每帧随机掉落的概率

# ==========================================
# 【状态字典：动作图库与寿命】
# ==========================================
# 提示：如果 loop: False 且不填 duration，引擎将自动精确计算播完这套动画需要的时间，并在播完瞬间无缝切换状态！
STATES = {
    # 地面区
    'IDLE':             {'frames': ['idle_01.png', 'idle_02.png'], 'speed': 15, 'loop': True, 'duration': (1.0, 6.0)},
    'STAND_TWO_FOOT':   {'frames': ['stand_two_foot.png'], 'speed': 15, 'loop': False, 'duration': (1.0, 5.0)},
    'STAND_FOUR_FOOT':  {'frames': ['stand_four_foot.png'], 'speed': 15, 'loop': False, 'duration': (1.0, 5.0)},
    'STAND_UP':         {'frames': ['stand_four_foot.png', 'stand_up.png', 'stand_two_foot.png'], 'speed': 10, 'loop': False,
                         'duration': (1.0, 5.0)},
    'DROP_DOWN':        {'frames': ['stand_two_foot.png', 'drop_down.png', 'stand_four_foot.png'], 'speed': 10, 'loop': False,
                         'duration': (1.0, 5.0)},
    'SIT':              {'frames': ['sit.png'], 'speed': 5, 'loop': False, 'duration': (0.5, 2.0)},
    'BLINK':            {'frames': ['blink.png', 'idle_02.png'], 'speed': 5, 'loop': True, 'duration': (0.5, 2.0)},
    'SMILE':            {'anim_pools': [['smile_01.png'], ['smile_02.png']], 'speed': 5, 'loop': False, 'duration': (0.5, 2.0)},
    'WALK':             {'frames': ['walk_01.png', 'stand_two_foot.png', 'walk_02.png', 'stand_two_foot.png'], 'speed': 10,
                         'loop': True, 'duration': (1.0, 5.0)},
    'WALK_FOUR_FOOT':   {'frames': ['walk_four_foot_01.png', 'walk_four_foot_02.png'], 'speed': 10, 'loop': True,
                         'duration': (1.0, 5.0)},
    'GO_TO_WALL':       {'frames': ['walk_01.png', 'walk_02.png'], 'speed': 3, 'loop': True, 'duration': (99, 99)},
    'JUMP_TO_WALL':     {'frames': ['jump_to_wall.png'], 'speed': 99, 'loop': False, 'duration': (99, 99)},  # 物理打断，用99保底
    'POKED':            {'frames': ['poked.png'], 'speed': 3, 'loop': False, 'duration': (99, 99)},

    # === 【精准匹配区】：删除了 duration，引擎会自动计算它播放完毕的准确时间并切状态 ===
    'HUNT':             {'frames': ['hunt_01.png', 'hunt_02.png', 'hunt_03.png', 'hunt_04.png', 'hunt_05.png', 'hunt_06.png',
                                    'hunt_07.png', 'hunt_08.png', 'hunt_09.png', 'hunt_10.png'], 'speed': 15, 'loop': False},
    'LAND':             {'frames': ['land.png'], 'speed': 10, 'loop': False},

    # 墙壁区 (不倒立)
    'CLIMB_UP':         {'frames': ['climb_01.png', 'climb_02.png'], 'speed': 6, 'loop': True, 'duration': (2.0, 8.0)},
    'CLIMB_DOWN':       {'frames': ['climb_01.png', 'climb_02.png'], 'speed': 6, 'loop': True, 'duration': (2.0, 8.0)},
    'WALL_IDLE':        {'anim_pools': [['wall_idle.png'], ['wall_lick.png']], 'speed': 15, 'loop': True, 'duration': (2.0, 5.0)},

    # 天花板区 (要倒立)
    'CEILING_ENTER':    {'frames': ['ceiling_enter.png'], 'speed': 10, 'loop': False, 'duration': (0.5, 0.5)},
    'CEILING_EXIT':     {'frames': ['ceiling_exit.png'], 'speed': 10, 'loop': False, 'duration': (0.5, 0.5)}, # 下墙拐弯中间态
    'CEILING_WALK':     {'frames': ['ceiling_walk_01.png', 'ceiling_walk_02.png'], 'speed': 5, 'loop': True,
                         'duration': (2.0, 6.0)},
    'CEILING_IDLE':     {'anim_pools': [['ceiling_idle_01.png'], ['ceiling_idle_02.png'],['ceiling_swing_01.png'],
                                        ['ceiling_swing_02.png', 'ceiling_swing_03.png',
                                         'ceiling_swing_04.png', 'ceiling_swing_03.png', 'ceiling_swing_02.png',
                                         'ceiling_swing_05.png', 'ceiling_swing_06.png', 'ceiling_swing_05.png',],
                                        ['ceiling_swing_11.png', 'ceiling_swing_12.png', 'ceiling_swing_13.png',
                                         'ceiling_swing_14.png', 'ceiling_swing_15.png']
                                        ],
                         'speed': 10, 'loop': True, 'duration': (3.0, 8.0)},

    # 鼠标事件 (因为主要靠物理打断，所以保留无限长的 99)
    'DRAG': {
        'anim_pools': [['drag_struggle_04.png'], ['drag_struggle_01.png', 'drag_struggle_02.png'], ['drag_look_01.png'],
                       ['drag_look_02.png', 'drag_look_03.png'],
                       {'frames': ['drag_dangle_01.png', 'drag_dangle_02.png', 'drag_dangle_03.png'], 'loop': False}],
        'speed': 15, 'loop': True, 'duration': (99, 99)},
    'FALL': {'frames': ['fall.png'], 'speed': 10, 'loop': False, 'duration': (99, 99)},
}

# ==========================================
# 【状态转移字典：AI思维导图】
# ==========================================
TRANSITIONS = {
    # 地面区
    # ==========================================
    #   test
    # 'IDLE':             {'GO_TO_WALL': 100},
    # 'WALL_IDLE':        {'CLIMB_UP': 100},
    # 'CEILING_IDLE':     {'CEILING_WALK': 100},
    # ==========================================
    'IDLE': {'STAND_TWO_FOOT': 30, 'STAND_FOUR_FOOT': 30, 'BLINK': 10, 'SMILE': 10, 'GO_TO_WALL': 10,
             'JUMP_TO_WALL': 10},

    'SIT': {'IDLE': 100},
    'BLINK': {'IDLE': 100},
    'SMILE': {'IDLE': 100},
    'STAND_TWO_FOOT': {'IDLE': 50, 'WALK': 30, 'DROP_DOWN': 20},
    'STAND_FOUR_FOOT': {'IDLE': 20, 'WALK_FOUR_FOOT': 20, 'STAND_UP': 20, 'SIT': 20, 'HUNT': 20},
    'DROP_DOWN': {'STAND_FOUR_FOOT': 100},
    'STAND_UP': {'STAND_TWO_FOOT': 100},
    'WALK': {'IDLE': 60, 'STAND_TWO_FOOT': 40},
    'WALK_FOUR_FOOT': {'IDLE': 60, 'STAND_FOUR_FOOT': 40},
    'LAND': {'IDLE': 100},
    'HUNT': {'STAND_FOUR_FOOT': 100},
    'POKED': {'STAND_FOUR_FOOT': 100},

    # 墙壁单行道
    'WALL_IDLE': {'CLIMB_UP': 45, 'CLIMB_DOWN': 45, 'FALL': 10},
    'CLIMB_UP': {'WALL_IDLE': 100},
    'CLIMB_DOWN': {'WALL_IDLE': 100},

    # 天花板单行道
    'CEILING_ENTER':    {'CEILING_WALK': 100},
    'CEILING_EXIT':     {'CLIMB_DOWN': 100},     # 翻越完成后，开始往下爬
    'CEILING_IDLE':     {'CEILING_WALK': 90, 'FALL': 10},
    'CEILING_WALK':     {'CEILING_IDLE': 100},
}