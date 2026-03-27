import os
import random
import traceback  # 用于打印真实报错
import time
from PyQt5.QtWidgets import QLabel, QMainWindow, QApplication, QSystemTrayIcon, QMenu, QAction, qApp, QStyle
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap, QTransform, QIcon  # 修复了 QTransform 的导入
from conf import *

class FoxPet(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.image_label = QLabel(self)

        # 【地形勘测：缓存屏幕可用尺寸】
        screen_geo = QApplication.primaryScreen().availableGeometry()
        self.screen_width = screen_geo.width()
        self.screen_height = screen_geo.height()
        # ==========================================

        self.current_state = None
        self.tick_count = 0  # 动画变速齿轮
        self.state_timer = 0  # 局部状态存活时间
        self.frame_index = 0
        self.current_frames = []
        self.current_is_loop = True  # 【新增】记住当前动作要不要循环
        self.current_speed = 10  # 【新增】记住当前动作的播放速度 数字越大动作越慢

        self.dx = 0
        self.dy = 0
        self.is_dragged = False
        self.is_facing_right = False  # 角色默认面朝左
        self.is_upside_down = False   # 记住现在是不是倒立状态（在天花板上）

        # 鼠标互动的幽灵变量提前占位！
        self.drag_pos = None
        self.last_global_pos = None
        # 丢狐狐
        self.drag_pos = None
        self.mouse_history = []  # 【新增】：速度黑匣子
        # 狐狐图片大小，原PET_SIZE
        self.current_size = None
        self.floor_y = None

        # 动作图库与寿命字典
        self.states = {
            # 地面区
            'IDLE':             {'frames': ['idle_01.png', 'idle_02.png'], 'speed': 15, 'loop': True, 'duration': (1.0, 6.0)},
            'STAND_TWO_FOOT':   {'frames': ['stand_two_foot.png'], 'speed': 15, 'loop': False, 'duration': (1.0, 5.0)},
            'BLINK':            {'frames': ['blink.png', 'idle_01.png'], 'speed': 5, 'loop': True, 'duration': (0.5, 2.0)},
            'WALK':             {'frames': ['walk_01.png', 'stand_two_foot.png', 'walk_02.png', 'stand_two_foot.png'],
                                 'speed': 10, 'loop': True, 'duration': (1.0, 5.0)},
            'GO_TO_WALL': {'frames': ['walk_01.png', 'walk_02.png'], 'speed': 3, 'loop': True, 'duration': (99, 99)},
            'JUMP_TO_WALL': {'frames': ['jump_to_wall.png'], 'speed': 99, 'loop': False, 'duration': (99, 99)},
            # 墙壁区 (不倒立)
            'CLIMB_UP': {'frames': ['climb_01.png', 'climb_02.png'], 'speed': 6, 'loop': True, 'duration': (1.0, 8.0)},
            'CLIMB_DOWN': {'frames': ['climb_01.png', 'climb_02.png'], 'speed': 6, 'loop': True, 'duration': (1.0, 8.0)},
            'WALL_IDLE': {
                'anim_pools': [['wall_idle.png'], ['wall_lick.png']],
                'speed': 15, 'loop': True, 'duration': (2.0, 5.0)
            },

            # 天花板区 (要倒立)
            'CEILING_ENTER': {'frames': ['ceiling_enter.png'], 'speed': 10, 'loop': False, 'duration': (0.5, 0.5)},
            'CEILING_WALK': {'frames': ['ceiling_walk_01.png', 'ceiling_walk_02.png'], 'speed': 5, 'loop': True,
                             'duration': (2.0, 6.0)},
            'CEILING_IDLE': {
                'anim_pools': [['ceiling_idle.png'], ['ceiling_swing_01.png', 'ceiling_swing_02.png']],
                'speed': 10, 'loop': True, 'duration': (3.0, 8.0)
            },

            # 鼠标事件
            'DRAG':             {'frames': ['dragged.png'], 'speed': 15, 'loop': True, 'duration': (99, 99)},
            'FALL':             {'frames': ['fall.png'], 'speed': 10, 'loop': False, 'duration': (99, 99)},
            'LAND':             {'frames': ['land.png'], 'speed': 10, 'loop': False, 'duration': (0.5, 1.0)}
        }
        # 状态转移字典：定义每个动作结束后，接下来能干嘛，以及对应的概率（权重）
        # 格式 -> '当前状态': {'下一个状态A': 权重, '下一个状态B': 权重}
        self.transitions = {
            # 地面区
            'IDLE':             {'STAND_TWO_FOOT': 30, 'WALK': 30, 'BLINK': 10, 'GO_TO_WALL': 15, 'JUMP_TO_WALL':15},  # 发呆完：大概率去溜达，小概率眨眼
            # 'IDLE': {'STAND_TWO_FOOT': 0, 'WALK': 50, 'BLINK': 0, 'GO_TO_WALL': 0, 'JUMP_TO_WALL': 50},#test
            'BLINK':            {'IDLE': 100},
            'STAND_TWO_FOOT':   {'IDLE': 70, 'WALK': 30},  # 站完：大概率继续发呆，小概率走动
            'WALK':             {'IDLE': 60, 'STAND_TWO_FOOT': 40},  # 走完：停下来发呆或站立
            'LAND':             {'IDLE': 100},  # 落地后：100% 必定进入发呆
            # 'GO_TO_WALL':       {'CLIMB_UP': 100},
            # 'SLEEP': {'IDLE': 100}  # 睡醒后：100% 必定进入发呆

            # 墙壁单行道
            'WALL_IDLE': {'CLIMB_UP': 50, 'CLIMB_DOWN': 30, 'FALL': 20},
            'CLIMB_UP': {'WALL_IDLE': 100},
            'CLIMB_DOWN': {'WALL_IDLE': 100},

            # 天花板单行道
            'CEILING_ENTER': {'CEILING_WALK': 100},
            'CEILING_IDLE': {'CEILING_WALK': 70, 'FALL': 30},
            'CEILING_WALK': {'CEILING_IDLE': 100},
        }
        # 【狐狐出场】
        self.set_scale(1.0)

        # ==========================================
        # 【极简版托盘中枢】
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.png"))  # 必须同目录下有一张 icon.png！
        # self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))

        tray_menu = QMenu(self)

        # 1. 召唤按钮
        summon_action = QAction("🦊 召唤狐狐", self)
        summon_action.triggered.connect(self.summon_fox)
        tray_menu.addAction(summon_action)

        # 2. 体型缩放子菜单
        scale_menu = QMenu("🔍 狐狐体型", self)

        action_large = QAction("大 (150%)", self)
        action_large.triggered.connect(lambda: self.set_scale(1.5))
        scale_menu.addAction(action_large)

        action_medium = QAction("中 (100% 默认)", self)
        action_medium.triggered.connect(lambda: self.set_scale(1.0))
        scale_menu.addAction(action_medium)

        action_small = QAction("小 (75%)", self)
        action_small.triggered.connect(lambda: self.set_scale(0.75))
        scale_menu.addAction(action_small)

        tray_menu.addMenu(scale_menu)

        # 3. 退出按钮
        quit_action = QAction("❌ 退出", self)
        quit_action.triggered.connect(qApp.quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        # ==========================================

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_loop)
        self.timer.start(REFRESH_RATE)

    def set_scale(self, scale_factor):
        # 1. 重新计算当前应该占用的像素大小
        self.current_size = int(PET_SIZE * scale_factor)
        # 2. 强行改变窗口的物理大小，贴图引擎会自动适应拉伸！
        self.setFixedSize(self.current_size, self.current_size)
        # 3. 极其关键：重新计算地板的 Y 坐标，防止变大后双腿陷进水泥地里
        self.floor_y = self.screen_height - self.current_size
        # 4. 暴力美学：为了防止它在墙角变大时卡进墙里，改变体型后直接触发大召唤术！
        self.summon_fox()

    def summon_fox(self):
        # ==========================================
        # 【大召唤术/出场/虚空打捞 统一接口】
        spawn_x = int(self.screen_width * 0.5 - self.current_size / 2)
        spawn_y = int(-self.screen_height * 0.1)
        self.move(spawn_x, spawn_y)
        self.dx = 0
        self.dy = 0
        # 3. 确保显示（这句极其关键！以后我们如果在托盘做了“隐藏狐狐”功能，
        # 点击召唤就能顺便把它从隐藏状态拉出来！）
        self.show()
        self.change_state('FALL')

    def update_loop(self):
        try:
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
                # ==========================================
                # 【新增：终极防丢安全网 (虚空打捞)】
                if (self.y() > self.screen_height * 1.2 or
                        self.y() < -self.screen_height * 0.2 or
                        self.x() < -self.screen_width * 0.2 or
                        self.x() > self.screen_width * 1.2):
                    self.summon_fox()
                    return  # 触发了打捞，这一帧后面的物理计算直接跳过，下班！
                # ==========================================

                # 1. 垂直受力分析 (重力)
                special_states = ['CLIMB_UP', 'CLIMB_DOWN', 'WALL_IDLE',
                                  'CEILING_ENTER', 'CEILING_WALK', 'CEILING_IDLE']
                # 只有非特种状态才受重力。千万别写 else: dy=0，会把爬墙的动力吃掉！
                if self.current_state not in special_states:
                    self.dy += GRAVITY

                # 2. 【核心改造】：预判下一步的坐标 (用临时变量，先不真走)
                next_x = self.x() + self.dx
                next_y = self.y() + self.dy

                # 3. 碰撞拦截与状态切换
                # 真正的物理墙壁坐标（允许窗口边框超出屏幕外）
                left_bound = -WALL_OFFSET
                right_bound = self.screen_width - PET_SIZE + WALL_OFFSET

                # ==========================================
                # A. 左右墙壁物理碰撞 (坚决不混入AI逻辑)
                # ==========================================
                if self.current_state in ['WALK', 'FALL', 'GO_TO_WALL', 'JUMP_TO_WALL']:

                    # 撞左墙
                    if next_x < left_bound and self.y() > -self.screen_height * 0.2:
                        next_x = left_bound

                        self.dx = 0  # 【必须踩死刹车！】
                        self.dy = 0
                        self.is_facing_right = False  # 【修正】：左墙脸朝右！

                        if self.current_state == 'GO_TO_WALL':
                            self.change_state('CLIMB_UP')
                        else:
                            self.change_state('WALL_IDLE')

                    # 撞右墙
                    elif next_x > right_bound and self.y() > -self.screen_height * 0.2:
                        next_x = right_bound

                        self.dx = 0  # 【必须踩死刹车！】
                        self.dy = 0
                        self.is_facing_right = True  # 【修正】：右墙脸朝左！

                        if self.current_state == 'GO_TO_WALL':
                            self.change_state('CLIMB_UP')
                        else:
                            self.change_state('WALL_IDLE')

                    # 闲逛时的随机掉头
                    elif self.current_state == 'WALK' and random.random() < PROB_TURN_AROUND :
                        self.dx = -self.dx
                        self.is_facing_right = (self.dx > 0)
                        self.animate()

                # ==========================================
                # A+. 独立的自动寻路 AI 系统 (清清爽爽)
                # ==========================================
                if self.current_state == 'GO_TO_WALL':
                    if self.x() < self.screen_width / 2:
                        self.dx = -SPEED_RUN  # 往左赶路
                        self.is_facing_right = False
                    else:
                        self.dx = SPEED_RUN  # 往右赶路
                        self.is_facing_right = True

                # ==========================================
                # B. 天花板边缘防穿模 (倒立走)
                # ==========================================
                elif self.current_state == 'CEILING_WALK':
                    if next_x <= 0 and self.dx < 0:
                        self.dx = -self.dx
                        self.is_facing_right = True
                    elif next_x >= self.screen_width - PET_SIZE and self.dx > 0:
                        self.dx = -self.dx
                        self.is_facing_right = False
                    elif random.random() < PROB_CEILING_DROP:
                        self.change_state('CEILING_IDLE')

                # ==========================================
                # C. 上下极限防穿模 (砸地板 / 爬到顶)
                # ==========================================
                if next_y >= self.floor_y and self.dy >= 0:
                    next_y = self.floor_y
                    self.dy = 0
                    if self.current_state == 'FALL':
                        self.dx = 0
                        self.change_state('LAND')
                    elif self.current_state == 'CLIMB_DOWN':
                        self.change_state('LAND')
                    elif self.current_state == 'JUMP_TO_WALL':
                        self.change_state('LAND')

                elif next_y <= 0 and self.current_state == 'CLIMB_UP':
                    next_y = 0
                    self.change_state('CEILING_ENTER')

                # 4. 【最终批准】：统一位移！
                self.move(int(next_x), int(next_y))

            # 节拍器跳动
            self.tick_count += 1

            # 只有节拍器走到专属设定的倍数时，才执行换图
            if self.tick_count >= self.current_speed:
                self.animate()
                self.tick_count = 0  # 触发换图后清零

            # 每次循环，状态生存时间 +1
            self.state_timer += 1

        except Exception as e:
            # 终极防爆门：打印出真正的报错原因，不再静默崩溃
            print("Python 代码执行出错：")
            traceback.print_exc()

    def animate(self):
        # 【修改这里】：直接用刚才守门员抽好的胶片！
        # 直接拿身体里的现成变量！
        frames = self.current_frames
        is_loop = self.current_is_loop

        # 防御性代码：如果这卷胶片是空的，直接罢工
        if not frames:
            return

        # 强制查验：如果记录的页码超出了当前动作的实际总张数，立刻归零！
        if self.frame_index >= len(frames):
            self.frame_index = 0

        img_path = os.path.join(ASSET_DIR, frames[self.frame_index])
        if not os.path.exists(img_path):
            return

        # 1. 洗出照片，并强行无损压缩到 conf.py 里设定的 PET_SIZE
        pixmap = QPixmap(img_path).scaled(
            self.current_size, self.current_size,
            Qt.KeepAspectRatio,  # 保持原图的长宽比例，绝不拉伸变形
            Qt.SmoothTransformation  # 【关键】开启平滑抗锯齿，保证缩小后依然清晰锐利！
        )

        if pixmap.isNull():
            return

        # ==========================================
        # 【翻转滤镜组装区】
        # 1. 先拿出一个空白的、什么都不做的基础滤镜
        transform = QTransform()

        # 2. 如果脸朝右，给滤镜加上“左右翻转”的功能
        if self.is_facing_right:
            transform.scale(-1, 1)

        # 3. 如果在天花板上，给滤镜再叠加“上下翻转”的功能
        if self.is_upside_down:
            transform.scale(1, -1)

        # 4. 如果这个滤镜被动过手脚（不是初始的空白状态了），就把滤镜狠狠地拍在照片上！
        if not transform.isIdentity():
            pixmap = pixmap.transformed(transform)
        # ==========================================

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
        # 实时打印：旧状态 -> 新状态
        # print(f"【状态切换】{self.current_state} -> {new_state}")

        # 状态切换的唯一指定通道（守门员）
        # 只有当新状态和现在的状态不一样时，才执行切换
        if self.current_state != new_state:
            self.current_state = new_state

            # 核心：只要经过这个门，所有附带变量强制全部清零重置！
            self.state_timer = 0  # 状态生命周期清零
            self.frame_index = 0  # 动画帧进度清零（保证从第0张图开始播）
            self.tick_count = 0

            # ==========================================
            # 【核心改造：选角抽卡】
            state_info = self.states.get(new_state, {})

            self.current_speed = state_info.get('speed', 10)
            self.current_is_loop = state_info.get('loop', True)

            # 抽盲盒（有 anim_pools）
            if 'anim_pools' in state_info:
                self.current_frames = random.choice(state_info['anim_pools'])
            else:
                self.current_frames = state_info.get('frames', [])
            # ==========================================

            # 1. 查字典，拿到的是人类能看懂的秒数区间，比如 (1.0, 6.0)
            duration_sec_range = self.states.get(new_state, {}).get('duration', (1.0, 1.0))
            # 2. 摇骰子，抽签出一个具体的秒数（用 random.uniform 可以抽出带小数的秒数，比如 2.3秒）
            target_seconds = random.uniform(duration_sec_range[0], duration_sec_range[1])
            # 3. 【消灭魔法数字】：引擎自动把“秒”翻译成“拍”！
            # 比如 2.3秒 * 1000 / 20ms = 115 拍。强制转成整数 int() 喂给计时器。
            self.current_duration = int((target_seconds * 1000) / REFRESH_RATE)

            # 【每次切状态，默认关闭倒立，防止从天花板掉下来还头朝下】
            self.is_upside_down = False
            #self.dy = 0

            # 1. 墙壁区 (只管上下，绝不倒立)
            if new_state == 'CLIMB_UP':
                self.dx = 0
                self.dy = -SPEED_CLIMB  # 负数是向上爬
            elif new_state == 'CLIMB_DOWN':
                self.dx = 0
                self.dy = SPEED_CLIMB  # 正数是向下滑 (你要求的，不翻转！)
            elif new_state == 'WALL_IDLE':
                self.dx = 0
                self.dy = 0

            # 2. 天花板区 (强制倒立)
            elif new_state in ['CEILING_ENTER', 'CEILING_WALK', 'CEILING_IDLE']:
                self.is_upside_down = True  # 【核心】：开启倒立！
                self.dy = 0
                if new_state == 'CEILING_WALK':
                    self.dx = random.choice([-SPEED_CEILING, SPEED_CEILING])
                    self.is_facing_right = (self.dx > 0)
                else:
                    self.dx = 0

            # 3. 地面区 (强制倒立)
            # 只要切入这几个静态动作，强行消除水平速度，绝不给它滑行的机会
            elif new_state in ['IDLE', 'STAND_TWO_FOOT', 'LAND']:
                self.dx = 0
            elif new_state == 'WALK':
                # 动态动作：起步瞬间，随机决定往左走还是往右走！
                self.dx = random.choice([-SPEED_WALK, SPEED_WALK])
                # 根据速度的正负，立刻决定狐狐的朝向
                self.is_facing_right = (self.dx > 0)
            # ==========================================
            # 【新增：起跳上墙的专属弹射器】
            elif new_state == 'JUMP_TO_WALL':
                self.dy = -SPEED_JUMP_Y  # 强力对抗重力，起飞！

                # 雷达索敌：判断哪边墙近，直接锁定轰炸！
                if self.x() < self.screen_width / 2:
                    self.dx = -SPEED_JUMP_X
                    self.is_facing_right = False
                else:
                    self.dx = SPEED_JUMP_X
                    self.is_facing_right = True
            # ==========================================
            # 顺便还可以把马上要用到的动画图立刻刷出来
            self.animate()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragged = True
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.change_state('DRAG')
            # 【新增】：清空黑匣子，记录抓起瞬间的时间和坐标
            self.mouse_history = [(time.time(), event.globalPos())]

    def mouseMoveEvent(self, event):
        if self.is_dragged:
            # 1. 记录当前时间和坐标
            current_time = time.time()
            current_pos = event.globalPos()

            # 2. 塞进黑匣子
            self.mouse_history.append((current_time, current_pos))

            # 3. 永远只保留最近的 5 笔记录（大概 0.1 秒的窗口，完美过滤掉松手时的刹车！）
            if len(self.mouse_history) > 5:
                self.mouse_history.pop(0)

            # 4. 只管移动，不在这里算速度了！
            self.move(current_pos - self.drag_pos)

    def mouseReleaseEvent(self, event):
        self.is_dragged = False
        self.change_state('FALL')
        # ==========================================
        # 【核心：黑匣子结算真实速度】
        if len(self.mouse_history) >= 2:
            old_time, old_pos = self.mouse_history[0]  # 0.1秒前的位置
            new_time, new_pos = self.mouse_history[-1]  # 现在的最后位置

            dt = new_time - old_time  # 经历了多少秒

            # 如果你抓着不动停了超过 0.15 秒才松手，说明你不想扔，动能清零
            if dt > 0 and (time.time() - new_time) < DRAG_PAUSE_THRESHOLD:
                # 算出一秒钟能飞多少像素 (像素/秒)
                vx = (new_pos.x() - old_pos.x()) / dt
                vy = (new_pos.y() - old_pos.y()) / dt

                frame_seconds = REFRESH_RATE / 1000.0
                # 转换成咱们引擎的每帧速度 (假设刷新率是 20ms，即 0.02秒)
                # 直接乘个爽快系数！横向 1.5 倍，纵向 2.5 倍！
                self.dx = vx * frame_seconds * THROW_BOOST_X
                self.dy = vy * frame_seconds * THROW_BOOST_Y

                # 暴力限速，防止飞出银河系报错
                self.dx = max(-100, min(100, self.dx))
                self.dy = max(-200, min(100, self.dy))

            else:
                self.dx = 0
                self.dy = 0
        else:
            self.dx = 0
            self.dy = 0
        # ==========================================

