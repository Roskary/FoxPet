import os

# ==========================================
# 【桌宠引擎：核心物理与系统参数】
# ==========================================
REFRESH_RATE = 20                # 系统刷新率 (毫秒)，20ms = 1秒50帧
DRAG_PAUSE_THRESHOLD = 0.15      # 拖拽停顿判定阈值 (秒)：抓着不动超过此时间，视为放弃投掷
THROW_BOOST_X = 1.5              # 横向臂力放大器：决定左右甩的爆发力
THROW_BOOST_Y = 1.5              # 纵向臂力放大器：决定上下甩的爆发力
# ==========================================

GRAVITY = 1          # 重力稍微加大一点
WALK_SPEED = 3       # 帧率高了，走路步伐就得调小，不然飞出去了

PET_SIZE = 128          # 像素图大小
TASKBAR_HEIGHT = 40     # 任务栏高度
WALL_OFFSET = 48      # 角色挂在墙上减去的宽度

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, 'assets')


