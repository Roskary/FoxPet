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

        self.states = {
            'IDLE': ['idle_01.png', 'idle_02.png'],
            'BLINK': ['blink.png'],
            'WALK': ['walk_01.png', 'walk_02.png'],
            'DRAG': ['dragged.png'],
            'FALL': ['fall.png'],
            'LAND': ['land.png']
        }
        self.current_state = 'IDLE'
        self.frame_index = 0
        self.dx = 0
        self.dy = 0
        self.is_dragged = False
        self.is_facing_right = False # 角色默认面朝左

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_loop)
        self.timer.start(REFRESH_RATE)

        self.move(500, 500)
        self.show()

        self.tick_count = 0  # 全局游戏节拍器
        self.state_timer = 0    # 局部状态存活时间

    def update_loop(self):
        try:
            # 修复 2：拎起时依然要刷新动画，只是跳过物理计算
            if self.is_dragged:
                self.animate()
                return

            # 状态切换逻辑
            if self.current_state == 'IDLE':
                if random.random() < 0.05:
                    self.change_state('WALK')
                    self.dx = random.choice([-WALK_SPEED, WALK_SPEED])
                    self.is_facing_right = (self.dx > 0)
            elif self.current_state == 'WALK':
                screen_width = QApplication.primaryScreen().geometry().width()
                if self.x() <= 0 or self.x() >= screen_width - PET_SIZE:
                    self.dx = -self.dx
                    self.is_facing_right = (self.dx > 0)
                if random.random() < 0.02:
                    self.change_state('IDLE')
            elif self.current_state == 'LAND':
                # self.state_timer += 1
                # 假设节拍器跳了 10 次（大概零点几秒），缓冲结束，站起来
                if self.state_timer >= 10:
                    self.current_state = 'IDLE'
                    self.state_timer = 0

            # 物理下落逻辑
            self.dy += GRAVITY
            floor_y = QApplication.primaryScreen().geometry().height() - PET_SIZE - TASKBAR_HEIGHT
            if self.y() >= floor_y:
                self.dy = 0
                self.move(self.x() + self.dx, floor_y)

                # 【新增逻辑】：如果是在掉落状态踩到了地板，就恢复成待机
                if self.current_state == 'FALL':
                    # self.current_state = 'LAND'
                    self.change_state('LAND')
            else:
                self.move(self.x() + self.dx, self.y() + self.dy)

            # 节拍器跳动
            self.tick_count += 1
            # 只有节拍器走到设定的倍数时，才换下一张图
            if self.tick_count % ANIMATION_DELAY == 0:
                self.animate()

            # 每次循环，状态生存时间 +1
            self.state_timer += 1

        except Exception as e:
            # 终极防爆门：打印出真正的报错原因，不再静默崩溃
            print("Python 代码执行出错：")
            traceback.print_exc()

    def animate(self):
        frames = self.states.get(self.current_state, ['idle_01.png'])
        self.frame_index = (self.frame_index + 1) % len(frames)
        img_path = os.path.join(ASSET_DIR, frames[self.frame_index])

        if not os.path.exists(img_path):
            return

        pixmap = QPixmap(img_path)
        if pixmap.isNull():
            return

        # 修复 1：正确的 QTransform 调用
        if self.is_facing_right:
            pixmap = pixmap.transformed(QTransform().scale(-1, 1))

        self.image_label.setPixmap(pixmap)
        self.image_label.resize(pixmap.size())
        self.resize(pixmap.size())

    def change_state(self, new_state):
        # 状态切换的唯一指定通道（守门员）
        # 只有当新状态和现在的状态不一样时，才执行切换
        if self.current_state != new_state:
            self.current_state = new_state

            # 核心：只要经过这个门，所有附带变量强制全部清零重置！
            self.state_timer = 0  # 状态生命周期清零
            self.frame_index = 0  # 动画帧进度清零（保证从第0张图开始播）

            # 【新增：自动刹车机制】
            # 只要切入这几个静态动作，强行消除水平速度，绝不给它滑行的机会
            if new_state in ['IDLE', 'LAND']:
                self.dx = 0

            # 顺便还可以把马上要用到的动画图立刻刷出来
            self.animate()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragged = True
            self.current_state = 'DRAG'
            self.frame_index = 0
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.animate()  # 点下去的瞬间立刻换图

    def mouseMoveEvent(self, event):
        if self.is_dragged:
            self.move(event.globalPos() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        self.is_dragged = False
        self.current_state = 'FALL'
        self.dy = 0  # 修复 3B：松手时重置速度，防止砸地板