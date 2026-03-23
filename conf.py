import os

REFRESH_RATE = 20    # 提升到 50 帧/秒，告别卡顿
GRAVITY = 2          # 重力稍微加大一点
WALK_SPEED = 3       # 帧率高了，走路步伐就得调小，不然飞出去了

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, 'assets')

PET_SIZE = 128          # 像素图大小
TASKBAR_HEIGHT = 40     # 任务栏高度
SIDEBARE_WIDE = 32      # 角色挂在墙上减去的宽度
