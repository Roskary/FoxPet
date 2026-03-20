import os
import random
import traceback  # 用于打印真实报错
from PyQt5.QtWidgets import QLabel, QMainWindow, QApplication
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap, QTransform  # 修复了 QTransform 的导入
from conf import *


class FoxPet(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.image_label = QLabel(self)

        self.current_state = None
        self.tick_count = 0  # 动画变速齿轮
        self.state_timer = 0  # 局部状态存活时间
        self.frame_index = 0

        self.dx = 0
        self.dy = 0
        self.is_dragged = False
        self.is_facing_right = False  # 角色默认面朝左
        # 动作图库与寿命字典
        self.states = {
            'IDLE':             {'frames': ['idle_01.png', 'idle_02.png'], 'speed': 15, 'loop': True, 'duration': (1.0, 6.0)},
            'STAND_TWO_FOOT':   {'frames': ['stand_two_foot.png'], 'speed': 15, 'loop': False, 'duration': (1.0, 5.0)},
            'BLINK':            {'frames': ['blink.png'], 'speed': 15, 'loop': True, 'duration': (0.5, 2.0)},
            'WALK':             {'frames': ['walk_01.png', 'walk_02.png'], 'speed': 4, 'loop': True, 'duration': (1.0, 5.0)},
            # 鼠标事件
            'DRAG':             {'frames': ['dragged.png'], 'speed': 15, 'loop': True, 'duration': (99, 99)},
            'FALL':             {'frames': ['fall.png'], 'speed': 10, 'loop': False, 'duration': (99, 99)},
            'LAND':             {'frames': ['land.png'], 'speed': 10, 'loop': False, 'duration': (99, 99)}
        }
        # 状态转移字典：定义每个动作结束后，接下来能干嘛，以及对应的概率（权重）
        # 格式 -> '当前状态': {'下一个状态A': 权重, '下一个状态B': 权重}
        self.transitions = {
            'IDLE':             {'STAND_TWO_FOOT': 60, 'WALK': 40},  # 发呆完：大概率去溜达，小概率睡觉
            'STAND_TWO_FOOT':   {'IDLE': 70, 'WALK': 30},  # 站完：大概率继续发呆，小概率走动
            'WALK':             {'IDLE': 60, 'STAND_TWO_FOOT': 40},  # 走完：停下来发呆或站立
            'LAND':             {'IDLE': 100},  # 落地后：100% 必定进入发呆
            # 'SLEEP': {'IDLE': 100}  # 睡醒后：100% 必定进入发呆
        }
        self.change_state('IDLE')

        self.move(500, 500)
        self.show()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_loop)
        self.timer.start(REFRESH_RATE)

    def update_loop(self):
        try:
            # 修复 2：拎起时依然要刷新动画，只是跳过物理计算
            # if self.is_dragged:
            #   self.animate()
            #  return

            # ------ 【命运轮盘区】 抽签决定下一个state------
            if self.state_timer >= self.current_duration:
                # 1. 查字典，看看当前状态接下来有哪些路可以走
                next_options = self.transitions.get(self.current_state)
                if next_options:
                    # 2. 把选项和对应的权重拆开
                    choices = list(next_options.keys())
                    weights = list(next_options.values())
                    # 3. 【核心抽签】：random.choices 会根据权重帮你掷骰子，选出一个结果！
                    # 加上 [0] 是因为这个函数默认返回一个列表，我们只需要抽出的那一个词
                    next_state = random.choices(choices, weights=weights)[0]
                    # 4. 切换状态，并将大脑秒表清零！
                    self.change_state(next_state)

            # ------ 【物理引擎区】 ------
            if not self.is_dragged:
                self.dy += GRAVITY
                floor_y = QApplication.primaryScreen().geometry().height() - PET_SIZE - TASKBAR_HEIGHT
                # 水平撞墙检测 (只在走路时生效)
                if self.current_state == 'WALK':
                    screen_width = QApplication.primaryScreen().geometry().width()
                    # 如果撞到了左边界 (x <= 0) 或者右边界
                    if self.x() <= 0 or self.x() >= screen_width - PET_SIZE:
                        self.dx = -self.dx  # 物理速度反转
                        self.is_facing_right = (self.dx > 0)  # 脸部朝向立刻反转！
                        self.animate()  # 强制立刻刷新一下图片，防止出现倒退走的滑步
                    # 如果没撞墙，掷骰子决定要不要突然回头！
                    # random.random() 会生成一个 0 到 1 之间的小数
                    elif random.random() < 0.005:
                        self.dx = -self.dx
                        self.is_facing_right = (self.dx > 0)
                        self.animate()
                # 移动执行
                if self.y() >= floor_y:
                    self.dy = 0
                    self.move(self.x() + self.dx, floor_y)
                    # 【新增逻辑】：如果是在掉落状态踩到了地板，就恢复成待机
                    if self.current_state == 'FALL':
                        self.change_state('LAND')
                else:
                    self.move(self.x() + self.dx, self.y() + self.dy)

            # 节拍器跳动
            self.tick_count += 1
            # 实时去字典里查狐狐现在的动作应该配多快的齿轮
            # （加个 .get 保底，万一字典写漏了默认给 10）
            current_speed = self.states.get(self.current_state, {}).get('speed', 10)
            # 只有节拍器走到专属设定的倍数时，才执行换图
            if self.tick_count >= current_speed:
                self.animate()
                self.tick_count = 0  # 触发换图后清零

            # 每次循环，状态生存时间 +1
            self.state_timer += 1

        except Exception as e:
            # 终极防爆门：打印出真正的报错原因，不再静默崩溃
            print("Python 代码执行出错：")
            traceback.print_exc()

    def animate(self):
        # 1. 拿到当前动作的信息包
        state_info = self.states.get(self.current_state, {'frames': ['idle_01.png'], 'speed': 10, 'loop': True})
        frames = state_info['frames']
        is_loop = state_info.get('loop', True)  # 查一下这个动作需不需要循环

        # ==========================================
        # 【插在这里！终极防弹衣】
        # 强制查验：如果记录的页码超出了当前动作的实际总张数，立刻归零！
        if self.frame_index >= len(frames):
            self.frame_index = 0
        # ==========================================

        img_path = os.path.join(ASSET_DIR, frames[self.frame_index])
        if not os.path.exists(img_path):
            return

        # 1. 洗出照片，并强行无损压缩到 conf.py 里设定的 PET_SIZE
        pixmap = QPixmap(img_path).scaled(
            PET_SIZE, PET_SIZE,
            Qt.KeepAspectRatio,  # 保持原图的长宽比例，绝不拉伸变形
            Qt.SmoothTransformation  # 【关键】开启平滑抗锯齿，保证缩小后依然清晰锐利！
        )

        if pixmap.isNull():
            return

        # 修复 1：正确的 QTransform 调用
        if self.is_facing_right:
            pixmap = pixmap.transformed(QTransform().scale(-1, 1))

        self.image_label.setPixmap(pixmap)
        self.image_label.resize(pixmap.size())
        self.resize(pixmap.size())

        # 3. 【核心改造】：算下一帧的序号
        if is_loop:
            # 如果是循环动作（走路、发呆），无限取余数轮转
            self.frame_index = (self.frame_index + 1) % len(frames)
        else:
            # 如果是不循环动作（落地、打哈欠）
            # 只要没播到最后一张，就继续往下播；一旦播到最后一张，就卡死在这里不动了
            if self.frame_index < len(frames) - 1:
                self.frame_index += 1

    def change_state(self, new_state):
        # 状态切换的唯一指定通道（守门员）
        # 只有当新状态和现在的状态不一样时，才执行切换
        if self.current_state != new_state:
            self.current_state = new_state

            # 核心：只要经过这个门，所有附带变量强制全部清零重置！
            self.state_timer = 0  # 状态生命周期清零
            self.frame_index = 0  # 动画帧进度清零（保证从第0张图开始播）
            self.tick_count = 0

            # 1. 查字典，拿到的是人类能看懂的秒数区间，比如 (1.0, 6.0)
            duration_sec_range = self.states.get(new_state, {}).get('duration', (1.0, 1.0))
            # 2. 摇骰子，抽签出一个具体的秒数（用 random.uniform 可以抽出带小数的秒数，比如 2.3秒）
            target_seconds = random.uniform(duration_sec_range[0], duration_sec_range[1])
            # 3. 【消灭魔法数字】：引擎自动把“秒”翻译成“拍”！
            # 比如 2.3秒 * 1000 / 20ms = 115 拍。强制转成整数 int() 喂给计时器。
            self.current_duration = int((target_seconds * 1000) / REFRESH_RATE)

            # 【新增：自动刹车机制】
            # 只要切入这几个静态动作，强行消除水平速度，绝不给它滑行的机会
            if new_state in ['IDLE', 'STAND_TWO_FOOT', 'LAND']:
                self.dx = 0
            elif new_state == 'WALK':
                # 动态动作：起步瞬间，随机决定往左走还是往右走！
                self.dx = random.choice([-2, 2])
                # 根据速度的正负，立刻决定狐狐的朝向
                self.is_facing_right = (self.dx > 0)

            # 顺便还可以把马上要用到的动画图立刻刷出来
            self.animate()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragged = True
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.change_state('DRAG')

    def mouseMoveEvent(self, event):
        if self.is_dragged:
            self.move(event.globalPos() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        self.is_dragged = False
        self.dy = 0  # 物理重置归物理管
        # 一句话呼叫守门员！狐狐瞬间变成坠落状态
        self.change_state('FALL')
