import os

REFRESH_RATE = 30    # 提升到 33 帧/秒，告别卡顿
GRAVITY = 2          # 重力稍微加大一点
WALK_SPEED = 3       # 帧率高了，走路步伐就得调小，不然飞出去了
ANIMATION_DELAY = 5  # 【新增】规定每 5 个物理帧，才切一次图片
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, 'assets')

PET_SIZE = 256          # 像素图大小
TASKBAR_HEIGHT = 40     # 任务栏高度
