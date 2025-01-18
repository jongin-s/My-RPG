# Referred to [Python pygame Game] RPG tutorial, Made by "PrintedLove"
# Referred to DaFluffyPotato's 'Physics - Pygame Tutorial: Making a Platformer'

import pygame, sys, os
from datafile import *
from pygame.locals import *
import pygame.mixer
import spidev
import RPi.GPIO as GPIO  # GPIO 라이브러리 임포트

# joystick 부분
# 축 채널 정의
vrx_channel = 0  # VRx 채널을 0으로 설정
vry_channel = 1  # VRy 채널을 1로 설정
# 값 읽기 간격을 몇 초로 할지 설정
delay = 0.5

# 스위치에 사용할 GPIO 핀 번호
swt_pin = 17

# GPIO 설정
GPIO.setmode(GPIO.BCM)  # BCM 번호 체계 사용
GPIO.setup(swt_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # 핀을 입력으로 설정하고 내부 풀업 저항 사용

# SPI 열기
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000

# MCP3008 채널을 0에서 7 사이로 읽는 함수
def readChannel(channel):
    val = spi.xfer2([1, (8 + channel) << 4, 0])
    data = ((val[1] & 3) << 8) + val[2]
    return data

# 게임 클래스
class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        #게임 컨트롤 변수
        pygame.display.set_caption('My RPG')    # 창 이름 설정
        self.clock = pygame.time.Clock()

        self.screen = pygame.display.set_mode(WINDOW_SIZE, 0, 32)
        self.screen_scaled = pygame.Surface((WINDOW_SIZE[0] / 4, WINDOW_SIZE[1] / 4))   # 확대한 스크린

        self.camera_scroll = [TILE_MAPSIZE[0] * 4, 0]   # 카메라 이동 좌표

        self.gameScore = 0          # 점수
        self.player_hp = 100        # 플레이어의 초기 HP 설정
        self.player_max_hp = 100    # 플레이어의 최대 HP 설정
        self.enemies = []           # 모든 적 객체를 저장하는 리스트
        self.player_lives = 3       # 플레이어의 라이프 값을 3으로 초기화
        
        self.game_clear = False     # 게임 클리어 상태 변수 추가
        self.game_over = False      # 게임 오버 상태를 위한 변수 추가
        
        # 색상 상수 정의
        SKY_BLUE = (135, 206, 235)
        BLACK = (0, 0, 0)
        
        # 그라데이션 배경 이미지를 생성하는 함수
        def createGradientBackground(width, height, top_color, bottom_color):
            background = pygame.Surface((width, height))
            for y in range(height):
                # 색상 비율 계산
                ratio = y / height
                # 비율에 따라 색상 계산
                r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
                g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
                b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
                pygame.draw.line(background, (r, g, b), (0, y), (width, y))
            return background

        # 리소스 불러오기
        self.spriteSheet_player = SpriteSheet('spriteSheet1.png', 16, 16, 8, 8, 12)      # 플레이어 스프라이트 시트
        self.spriteSheet_object = SpriteSheet('spriteSheet2.png', 8, 8, 16, 16, 45)      # 공통 오브젝트 스프라이트 시트
        self.spriteSheet_map1 = SpriteSheet('spriteSheet4.png', 8, 8, 16, 16, 87)        # 지형 1 스프라이트 시트

        self.spr_player = {}     # 플레이어 스프라이트 세트
        self.spr_player['stay'] = createSpriteSet(self.spriteSheet_player, [0])
        self.spr_player['run'] = createSpriteSet(self.spriteSheet_player, 1, 8)
        self.spr_player['jump'] = createSpriteSet(self.spriteSheet_player, [9, 10, 11])

        self.spr_effect = {}     # 효과 스프라이트 세트
        self.spr_effect['player_shot'] = createSpriteSet(self.spriteSheet_object, 37, 40)          
        self.spr_effect['player_shotBoom'] = createSpriteSet(self.spriteSheet_object, 41, 44)

        self.spr_enemy = {}      # 적 스프라이트 세트
        self.spr_enemy['slime'] = createSpriteSet(self.spriteSheet_map1, 81, 83)          
        #self.spr_enemy['snake'] = createSpriteSet(self.spriteSheet_map1, 84, 86)

        self.spr_map_struct = {}     # 구조물 스프라이트 세트
        self.spr_map_struct['leaf'] = [55, 56]
        self.spr_map_struct['flower'] = [57, 64]
        self.spr_map_struct['obj'] = [65, 70]
        self.spr_map_struct['sign'] = [71, 74]
        self.spr_map_struct['gravestone'] = [75, 78]
        self.spr_map_struct['skull'] = [79, 80]

        self.spr_coin = createSpriteSet(self.spriteSheet_object, [41, 42])    # 코인 스프라이트 세트

        createMapData() # 맵 데이터 초기화
        self.mapImage, self.mapImage_front = createMapImage(self.spriteSheet_map1, self.spr_map_struct) # 맵 이미지 생성
        self.backImage = createBackImage(self.spriteSheet_object)   # 배경 이미지 생성
        
        # 화면 크기에 맞게 그라데이션 배경 이미지 생성
        screen_width, screen_height = self.screen_scaled.get_size()
        self.backImage1 = createGradientBackground(screen_width, screen_height, SKY_BLUE, BLACK)

        #효과음
        self.sound_attack = pygame.mixer.Sound(os.path.join(DIR_SOUND, 'attack.wav'))
        self.sound_coin = pygame.mixer.Sound(os.path.join(DIR_SOUND, 'coin.wav'))
        #self.sound_footstep0 = pygame.mixer.Sound(os.path.join(DIR_SOUND, 'footstep0.wav'))
        #self.sound_footstep1 = pygame.mixer.Sound(os.path.join(DIR_SOUND, 'footstep1.wav'))
        self.sound_monster = pygame.mixer.Sound(os.path.join(DIR_SOUND, 'monster.wav'))

        # 적 생성
        for i in range(8):
            #obj_snake = createObject(self.spr_enemy['snake'], (random.randrange(170, 990), 100), 'snake', self)
            obj_slime = createObject(self.spr_enemy['slime'], (random.randrange(170, 990), 100), 'slime', self)
        
        # 조이스틱 연결 여부 확인
        self.joystick_connected = self.check_joystick()
        
        # 플레이어 컨트롤 변수
        self.keyLeft = False
        self.keyRight = False
        self.keyClear = False

        player_sponOK = True
        player_spon_x = TILE_MAPSIZE[0] // 2 - 1

        while(player_sponOK):
            player_spon_x += 1

            if floor_map[player_spon_x] != -1:
                player_sponOK = False

        self.player_rect = pygame.Rect((player_spon_x * 8, TILE_MAPSIZE[1] * 4 - 14), (6, 14))  # 플레이어 히트박스
        self.player_movement = [0, 0]            # 플레이어 프레임당 속도
        self.player_vspeed = 0                   # 플레이어 y가속도
        self.player_flytime = 0                  # 공중에 뜬 시간

        self.player_action = 'stay'              # 플레이어 현재 행동
        self.player_frame = 0                    # 플레이어 애니메이션 프레임
        self.player_frameSpeed = 1               # 플레이어 애니메이션 속도(낮을 수록 빠름. max 1)
        self.player_frameTimer = 0
        self.player_flip = False                 # 플레이어 이미지 반전 여부 (False: RIGHT)
        self.player_animationMode = True         # 애니메이션 모드 (False: 반복, True: 한번)
        self.player_walkSoundToggle = False
        self.player_walkSoundTimer = 0

        self.player_attack_timer = 0             # 플레이어 공격 타이머
        self.player_attack_speed = 15            # 플레이어 공격 속도

        # 배경음 실행
        pygame.mixer.music.load(os.path.join(DIR_SOUND, 'background.mp3'))
        pygame.mixer.music.play(loops = -1)

        # 게임 실행
        self.run()
        
    def check_joystick(self):
        try:
            # 조이스틱 채널에서 값을 읽어서 유효한 범위인지 확인
            vrx_pos = readChannel(vrx_channel)
            vry_pos = readChannel(vry_channel)
            if 300 <= vrx_pos <= 700 and 300 <= vry_pos <= 700:
                return True
            else:
                print("Joystick Error!")
                return False
        except Exception as e:
            print(f"Joystick not connected!: {e}")
            return False
    
    def check_enemies_status(self):
        if all(enemy.destroy for enemy in self.enemies) and self.game_over == False:
            self.game_clear = True
        
    def draw_player_hp(self):
        # HP 바 그리기
        hp_bar_width = 50  # HP 바의 너비
        hp_bar_height = 5  # HP 바의 높이
        hp_bar_x = 34  # HP 바의 x 좌표
        hp_bar_y = 10  # HP 바의 y 좌표
        hp_ratio = self.player_hp / self.player_max_hp  # HP 비율 계산
        draw_text(self.screen_scaled, "HP", 8, (238, 238, 230), 27, 7)

        # HP 바 배경 그리기
        pygame.draw.rect(self.screen_scaled, (132, 143, 147), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height))

        # HP 바 채우기
        pygame.draw.rect(self.screen_scaled, (37, 159, 200), (hp_bar_x, hp_bar_y, hp_bar_width * hp_ratio, hp_bar_height))
        
    def run(self):
        PLAYER_RESPAWN_POS = (50, 100)  # 플레이어의 초기 위치를 정의
        FALL_THRESHOLD = 300  # 플레이어가 이 y 좌표 이하로 떨어지면 리스폰

        # 플레이어와 카메라의 초기 위치 설정
        self.player_rect.x, self.player_rect.y = PLAYER_RESPAWN_POS
        self.camera_scroll = [PLAYER_RESPAWN_POS[0], PLAYER_RESPAWN_POS[1]]

        # 메인 루프
        while True:
            self.screen_scaled.fill(BACKGROUND_COLOR)  # 화면 초기화

            self.camera_scroll[0] += int((self.player_rect.x - self.camera_scroll[0] - WINDOW_SIZE[0] / 8 - 5) / 16)  # 카메라 이동
            self.camera_scroll[1] += int((self.player_rect.y - self.camera_scroll[1] - WINDOW_SIZE[1] / 8 - 2) / 16)

            self.screen_scaled.blit(self.backImage1, (0, 0))  # 배경 드로우
            self.screen_scaled.blit(self.backImage, (0, 0))  # 배경 드로우
            self.screen_scaled.blit(self.mapImage, (-self.camera_scroll[0], -self.camera_scroll[1]))  # 맵 드로우

            # 플레이어 컨트롤
            if self.player_attack_timer < self.player_attack_speed:
                self.player_attack_timer += 1
            self.player_movement = [0, 0]  # 플레이어 이동
            if self.keyLeft:
                self.player_movement[0] -= 2
            if self.keyRight:
                self.player_movement[0] += 2
            self.player_movement[1] += self.player_vspeed

            self.player_vspeed += 0.2
            if self.player_vspeed > 3:
                self.player_vspeed = 3

            if self.player_movement[0] != 0:  # 플레이어 걷기 애니메이션 처리 및 방향 전환
                if self.player_flytime == 0:
                    self.player_frame, self.player_action, self.player_frameSpeed, self.player_animationMode = change_playerAction(
                        self.player_frame, self.player_action, 'run', self.player_frameSpeed, 3, self.player_animationMode, True)

                    self.player_walkSoundTimer += 1

                    if self.player_walkSoundTimer > 1:
                        self.player_walkSoundTimer = 0

                        if self.player_walkSoundToggle:
                            self.player_walkSoundToggle = False
                            # self.sound_footstep0.play()
                        else:
                            self.player_walkSoundToggle = True
                            # self.sound_footstep1.play()
                if self.player_movement[0] > 0:
                    self.player_flip = False
                else:
                    self.player_flip = True
            else:
                self.player_walkSoundTimer = 0

                if self.player_flytime == 0:
                    self.player_frame, self.player_action, self.player_frameSpeed, self.player_animationMode = change_playerAction(
                        self.player_frame, self.player_action, 'stay', self.player_frameSpeed, 3, self.player_animationMode, True)

            self.player_rect, player_collision = move(self.player_rect, self.player_movement)

            if player_collision['bottom']:
                self.player_vspeed = 0
                self.player_flytime = 0
            else:
                self.player_flytime += 1

            self.player_frameTimer += 1  # 플레이어 애니메이션 타이머
            if self.player_frameTimer >= self.player_frameSpeed:
                self.player_frame += 1
                self.player_frameTimer = 0

                if self.player_frame >= len(self.spr_player[self.player_action]):
                    if self.player_animationMode == True:
                        self.player_frame = 0
                    else:
                        self.player_frame -= 1

            if self.player_rect.y > FALL_THRESHOLD:  # 플레이어가 떨어지면 리스폰
                self.player_rect.x, self.player_rect.y = PLAYER_RESPAWN_POS
                self.player_vspeed = 0
                self.player_flytime = 0
                
                # 라이프 감소
                self.player_lives -= 1
                if self.player_lives > 0:
                    self.player_hp = 100  # HP 초기화  
                if self.player_lives <= 0 and self.game_clear == False:
                    # 게임 오버 처리
                    self.player_hp = 0
                    self.game_over = True  # 게임 오버 상태 설정
                    
            for obj in objects:  # 오브젝트 이벤트 처리
                if obj.destroy:
                    obj.destroy_self()
                else:
                    obj.events()
                    obj.draw()
                    obj.physics_after()
                             
                # 플레이어와 적 충돌 처리
                if isinstance(obj, EnemyObject):
                    if self.player_rect.colliderect(obj.rect) and not obj.destroy:
                        self.player_hp -= 1  # 적과 충돌 시 플레이어 HP 감소
                        if self.player_hp <= 0 and self.player_lives > 0:
                            self.player_rect.x, self.player_rect.y = PLAYER_RESPAWN_POS
                            self.player_vspeed = 0
                            self.player_flytime = 0
                
                            # 라이프 감소
                            self.player_lives -= 1
                            if self.player_lives > 0:
                                self.player_hp = 100  # HP 초기화
                            if self.player_lives <= 0 and self.game_clear == False:
                                # 게임 오버 처리
                                self.game_over = True  # 게임 오버 상태 설정
                    
            # 게임 오버 동작
            if self.game_over:
                self.screen_scaled.set_alpha(50)  # 화면 흐림처리
                draw_text(self.screen_scaled, "GAME OVER", 10, (238, 238, 230), 125, 75)
                    
                self.handle_events()    # 매 프레임마다 이벤트가 처리되도록 보장

                if self.keyClear:   # 결합된 입력을 확인
                    self.player_rect.x, self.player_rect.y = PLAYER_RESPAWN_POS
                    self.camera_scroll = [PLAYER_RESPAWN_POS[0], PLAYER_RESPAWN_POS[1]]
                    self.player_vspeed = 0
                    self.player_flytime = 0
                    self.gameScore = 0
                    self.player_hp = 100
                    self.player_lives = 3
                    self.game_over = False
                    self.screen_scaled.set_alpha(None)  # 흐림처리 해제
                    
                    while self.enemies:
                        enemy = self.enemies.pop()
                        enemy.destroy = True  # 적 객체의 파괴 플래그 설정
                    for i in range(8):
                        #obj_snake = createObject(self.spr_enemy['snake'], (random.randrange(170, 990), 100), 'snake', self)
                        obj_slime = createObject(self.spr_enemy['slime'], (random.randrange(170, 990), 100), 'slime', self)
            
            # 게임 클리어 동작
            if self.game_clear:
                self.screen_scaled.set_alpha(50)  # 화면 흐림처리
                draw_text(self.screen_scaled, "GAME CLEAR", 10, (238, 238, 230), 125, 75)
                
                self.handle_events()  # 매 프레임마다 이벤트가 처리되도록 보장

                if self.keyClear:  # 결합된 입력을 확인
                    self.player_rect.x, self.player_rect.y = PLAYER_RESPAWN_POS
                    self.camera_scroll = [PLAYER_RESPAWN_POS[0], PLAYER_RESPAWN_POS[1]]
                    self.player_vspeed = 0
                    self.player_flytime = 0
                    self.gameScore = 0
                    self.player_hp = 100
                    self.player_lives = 3
                    self.game_clear = False
                    self.screen_scaled.set_alpha(None)  # 흐림처리 해제
                    
                    while self.enemies:
                        enemy = self.enemies.pop()
                        enemy.destroy = True  # 적 객체의 파괴 플래그 설정
                    for i in range(8):
                        #obj_snake = createObject(self.spr_enemy['snake'], (random.randrange(170, 990), 100), 'snake', self)
                        obj_slime = createObject(self.spr_enemy['slime'], (random.randrange(170, 990), 100), 'slime', self)

            self.screen_scaled.blit(pygame.transform.flip(self.spr_player[self.player_action][self.player_frame], self.player_flip, False)
                                    , (self.player_rect.x - self.camera_scroll[0] - 5, self.player_rect.y - self.camera_scroll[1] - 2))  # 플레이어 드로우

            self.screen_scaled.blit(self.mapImage_front, (-self.camera_scroll[0], -self.camera_scroll[1]))  # 프론트 맵 드로우

            # 점수 텍스트 표시
            draw_text(self.screen_scaled, "SCORE: " + str(self.gameScore), 8, (238, 238, 230), 205, 140)
            # 좌측하단에 라이프 텍스트 표시
            draw_text(self.screen_scaled, "LIVES: " + str(self.player_lives), 8, (238, 238, 230), 35, 140)
            # 플레이어 HP바 표시
            self.draw_player_hp()
            # 이벤트 컨트롤
            self.handle_events()

            surf = pygame.transform.scale(self.screen_scaled, WINDOW_SIZE)  # 창 배율 적용
            self.screen.blit(surf, (0, 0))

            pygame.display.update()
            self.clock.tick(60)
    
    def handle_events(self):
        if self.joystick_connected:
            # 조이스틱 입력 처리
            vrx_pos = readChannel(vrx_channel)
            vry_pos = readChannel(vry_channel)
            swt_val = GPIO.input(swt_pin)

            # 값 범위 0 ~ 1023
            joystick_left = vrx_pos < 300
            joystick_right = vrx_pos > 700
            joystick_jump = vry_pos < 300 and self.player_flytime < 6
            joystick_attack = swt_val == GPIO.LOW and self.player_attack_timer >= self.player_attack_speed
            joystick_clear = swt_val == GPIO.LOW  # 조이스틱 버튼으로 게임 클리어 처리 추가
        else:
            # 조이스틱이 연결되지 않은 경우, 기본 조이스틱 입력을 False로 설정
            joystick_left = joystick_right = joystick_jump = joystick_attack = joystick_clear = False

        # 키보드 입력 처리
        keys = pygame.key.get_pressed()
        key_left = keys[pygame.K_LEFT]
        key_right = keys[pygame.K_RIGHT]
        key_jump = keys[pygame.K_UP] and self.player_flytime < 6
        key_attack = keys[pygame.K_SPACE] and self.player_attack_timer >= self.player_attack_speed
        key_clear = keys[pygame.K_SPACE]  # 스페이스바로 게임 클리어 처리 추가

        # 조이스틱과 키보드 입력을 결합
        self.keyLeft = joystick_left or key_left
        self.keyRight = joystick_right or key_right
        self.keyClear = joystick_clear or key_clear  # 클리어 동작 결합

        # 점프 처리
        if joystick_jump or key_jump:
            self.player_vspeed = -3.5
            self.player_flytime += 1
            self.player_frame, self.player_action, self.player_frameSpeed, self.player_animationMode = change_playerAction(
                self.player_frame, self.player_action, 'jump', self.player_frameSpeed, 6, self.player_animationMode, False
            )

        # 공격 처리
        if joystick_attack or key_attack:
            self.player_attack_timer = 0
            self.player_shot = createObject(self.spr_effect['player_shot'], (self.player_rect.x, self.player_rect.y + 2), 'player_shot', self)
            self.player_shot.direction = self.player_flip
            self.sound_attack.play()

        # 이벤트 처리
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.keyLeft = True
                if event.key == pygame.K_RIGHT:
                    self.keyRight = True
                if event.key == pygame.K_UP and self.player_flytime < 6:  # 점프
                    self.player_vspeed = -3.5
                    self.player_flytime += 1
                    self.player_frame, self.player_action, self.player_frameSpeed, self.player_animationMode = change_playerAction(
                        self.player_frame, self.player_action, 'jump', self.player_frameSpeed, 6, self.player_animationMode, False
                    )
                if event.key == pygame.K_SPACE and self.player_attack_timer >= self.player_attack_speed:  # 공격
                    self.player_attack_timer = 0
                    self.player_shot = createObject(self.spr_effect['player_shot'], (self.player_rect.x, self.player_rect.y + 2), 'player_shot', self)
                    self.player_shot.direction = self.player_flip
                    self.sound_attack.play()
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    self.keyLeft = False
                if event.key == pygame.K_RIGHT:
                    self.keyRight = False


game = Game()   # 게임 실행
