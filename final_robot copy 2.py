import numpy as np
import cv2
import serial
import time
import math

# =====================================================
# 사용자 설정 영역
# =====================================================

# 1. 시리얼 통신 설정
COM_PORT = 'COM3' 
BAUD_RATE = 9600

# 2. 픽셀-mm 변환 상수 설정
PIXEL_GRID_SIZE = 16.0 
MM_PER_PIXEL = 10.0 / PIXEL_GRID_SIZE 

# 3. X축을 어디에 그릴지 결정하는 Y 오프셋 (MM)
Y_AXIS_ZERO_MM = 120.0 

# 웹캠 초기화
cap = cv2.VideoCapture(1) # 노트북 사용시 1번으로 전환하기

if not cap.isOpened():
    print("Error: Could not open video stream or file")
    exit()

try:
    # 시리얼 포트 열기
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.1)
    time.sleep(2)
    print(f"시리얼 포트 {COM_PORT} 연결 성공")
except serial.SerialException as e:
    print(f"Error connecting to serial port: {e}")
    exit()

# 최종 계산된 좌표를 저장할 변수 초기화
col_loc = -1.0
row_loc = -1.0
center_x_mm = 0.0
center_y_mm = 0.0

last_calculation_time = 0.0 
last_valid_output_str_arduino = "0,0\n" # 객체가 없을 때 보낼 초기/마지막 유효 좌표

# VOC 클래스 목록
CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
           "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
           "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
           "sofa", "train", "tvmonitor"]

# DNN 모델 로딩
# 'deploy.prototxt'와 'mobilenet_iter_73000.caffemodel' 파일이 현재 디렉토리에 있어야 합니다.
net = cv2.dnn.readNetFromCaffe("deploy.prototxt", "mobilenet_iter_73000.caffemodel")

# ----------------------------------------------------
# 🌟 좌표계 Origin 픽셀 위치를 계산하는 공유 함수
# ----------------------------------------------------
def get_origin_pixels(height, width):
    PIXEL_PER_MM = 1.0 / MM_PER_PIXEL
    Y_OFFSET_PIX = Y_AXIS_ZERO_MM / MM_PER_PIXEL 
    
    rad = math.radians(180)
    c = np.cos(rad)
    s = np.sin(rad)
    
    # H 행렬을 위한 MM 좌표 계산 (Y축 중심 맞춤)
    tx_mm = (width / 2.0) * MM_PER_PIXEL
    ty_mm = height * MM_PER_PIXEL
    H = np.array([[c, -1*s, tx_mm], [s, c, ty_mm], [0, 0, 1]])

    # MM 좌표를 픽셀로 환산
    origin_x_pix = int(H[0, 2] * PIXEL_PER_MM) 
    origin_y_pix = int(H[1, 2] * PIXEL_PER_MM - 1 - Y_OFFSET_PIX) 
    
    if origin_y_pix < 0 or origin_y_pix >= height:
        display_y_pix = int(height / 2) 
    else:
        display_y_pix = origin_y_pix
    
    return origin_x_pix, display_y_pix

# ----------------------------------------------------
# 🌟 픽셀 좌표를 MM 좌표로 변환하는 공유 함수
# ----------------------------------------------------
def pixel_to_mm(center_x_pix, center_y_pix, origin_x_pix, display_y_pix):
    # MM 좌표 변환
    x_mm = (center_x_pix - origin_x_pix) * MM_PER_PIXEL
    y_mm = -(center_y_pix - display_y_pix) * MM_PER_PIXEL
    return x_mm, y_mm
    
    
# ----------------------------------------------------
# machine_vision 함수
# ----------------------------------------------------
def machine_vision():
    global last_calculation_time, last_valid_output_str_arduino
    global col_loc, row_loc, center_x_mm, center_y_mm 
    
    CALCULATION_PERIOD = 0.5 
    
    while(True):
        ret, frame = cap.read()
        
        if not ret:
            print("End of video stream or file")
            break

        height, width, channels = frame.shape 
        
        # 4. 좌표계 Origin 픽셀 위치 계산
        origin_x_pix, display_y_pix = get_origin_pixels(height, width)
        x_pix = origin_x_pix
        
        # ----------------------------------------------------
        # 🌟🌟🌟 딜레이 로직: 좌표 계산 주기가 되었는지 확인 🌟🌟🌟
        # ----------------------------------------------------
        current_time = time.time()
        
        if current_time - last_calculation_time >= CALCULATION_PERIOD:
            
            # --- (무게 중심 계산 로직 시작) ---
            
            col_loc_local = -1.0
            row_loc_local = -1.0
            output_to_send = last_valid_output_str_arduino # 기본값: 마지막 유효 좌표
            
            # 2. 색상 분리 및 이진화 (무게 중심용)
            red=frame[:,:,2]; green=frame[:,:,1]; blue=frame[:,:,0]
            blue_only=np.int16(blue)-np.int16(red)-np.int16(green)
            blue_only[blue_only<0]=0; blue_only[blue_only>255]=255
            blue_only0=np.uint8(blue_only)
            _, blue_only_thresh = cv2.threshold(blue_only0, 80, 255, cv2.THRESH_BINARY)

            # 3. 무게 중심 계산 (Center of Mass)
            x, y = blue_only_thresh.shape[:2] 
            total_total = np.sum(blue_only_thresh)
            
            if total_total > 0: # 🌟 객체 인식 성공
                col_nums = np.arange(y)
                row_nums = np.arange(x)
                col_loc_local = np.sum(np.sum(blue_only_thresh, axis=0) * col_nums) / total_total
                row_loc_local = np.sum(np.sum(blue_only_thresh, axis=1) * row_nums) / total_total
                
                # mm 좌표로 변환
                center_x_pix = int(col_loc_local)
                center_y_pix = int(row_loc_local)
                center_x_mm_new, center_y_mm_new = pixel_to_mm(center_x_pix, center_y_pix, origin_x_pix, display_y_pix)
                
                # 전역 변수 업데이트
                col_loc = col_loc_local; row_loc = row_loc_local
                center_x_mm = center_x_mm_new; center_y_mm = center_y_mm_new
                
                # 시리얼 출력 문자열 생성 및 저장
                X_out_arduino = int(round(center_x_mm)); Y_out_arduino = int(round(center_y_mm))
                output_to_send = f"{X_out_arduino},{Y_out_arduino}\n"
                last_valid_output_str_arduino = output_to_send 
                
                print(f"Object Detected - Pixel: ({center_x_pix}, {center_y_pix}), MM: ({center_x_mm:.2f}, {center_y_mm:.2f})")
            
            else: # 🌟 객체 인식 실패
                output_to_send = last_valid_output_str_arduino
                print(f"Object Lost - Sending last known coord: {output_to_send.strip()}")
                
            # 디버깅 시각화
            result=blue_only0
            if col_loc_local != -1.0:
                cv2.circle(result,(np.int32(col_loc_local),np.int32(row_loc_local)),10,(0,0,0),2,cv2.LINE_AA)
            cv2.imshow('result',result)
            
            # 📌 시리얼 데이터 전송
            try:
                ser.write(output_to_send.encode())
            except serial.SerialTimeoutException:
                print("Serial Write Timeout")

            last_calculation_time = current_time # 시간 기록
            
        # ----------------------------------------------------
        # 🌟🌟🌟 딜레이 로직 끝 🌟🌟🌟
        # ----------------------------------------------------
        
        # 5. 좌표계 시각화 및 mm 좌표 표시 (매 프레임 시각화)
        cv2.line(frame, (0, display_y_pix), (width, display_y_pix), (0, 0, 255), 2)
        cv2.putText(frame, '+X (mm)', (width - 60, display_y_pix - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.line(frame, (x_pix, 0), (x_pix, height), (255, 0, 0), 2)
        cv2.putText(frame, '+Y (mm)', (origin_x_pix + 10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        cv2.circle(frame, (x_pix, display_y_pix), 5, (255, 255, 255), -1)
        cv2.putText(frame, 'Origin (0,0)', (x_pix + 10, display_y_pix - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # 중심 좌표 시각화 (마지막 유효 전역 변수 사용)
        if col_loc != -1.0: 
            center_x_pix = int(col_loc)
            center_y_pix = int(row_loc)
            cv2.circle(frame, (center_x_pix, center_y_pix), 7, (0, 255, 0), 2)
            coord_text = f'Center (mm): ({center_x_mm:.1f}, {center_y_mm:.1f})'
            cv2.putText(frame, coord_text, (center_x_pix + 10, center_y_pix - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        cv2.imshow('frame1', frame) 
        
        k = cv2.waitKey(1) & 0xFF 
        if k == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    ser.close() 

# ----------------------------------------------------
#  AI_MODE 함수 (수정됨)
# ----------------------------------------------------
def AI_MODE():
    global center_x_mm, center_y_mm # mm 좌표를 업데이트할 필요는 없지만, 출력은 전역 변수로 할 수 있음

    # 객체 인식 및 시각화 함수
    def detect_and_display(image, window_name="Detection", print_info=False):
        h, w = image.shape[:2]
        blob = cv2.dnn.blobFromImage(image, 0.007843, (300, 300), 127.5)
        net.setInput(blob)
        detections = net.forward()
        output = image.copy()

        results = []
        obj_num = 1

        #  Origin 픽셀 위치를 가져옵니다.
        origin_x_pix, display_y_pix = get_origin_pixels(h, w)

        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.5:
                idx = int(detections[0, 0, i, 1])
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")
                centerX = int((startX + endX) / 2)
                centerY = int((startY + endY) / 2)
                label = CLASSES[idx]

                #  픽셀 좌표를 MM 좌표로 변환
                mm_x, mm_y = pixel_to_mm(centerX, centerY, origin_x_pix, display_y_pix)
                
                if print_info:
                    print(f"- [{obj_num}] {label}, Center: ({centerX}, {centerY}), MM: ({mm_x:.2f}, {mm_y:.2f})")

                results.append([obj_num, label, centerX, centerY, mm_x, mm_y])
                obj_num += 1

                # 시각화
                cv2.rectangle(output, (startX, startY), (endX, endY), (0, 255, 0), 2)
                cv2.circle(output, (centerX, centerY), 5, (0, 0, 255), -1)
                
                # MM 좌표 출력
                coord_text = f"{label} ({mm_x:.1f}, {mm_y:.1f})"
                cv2.putText(output, coord_text, (startX, startY - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        if print_info:
            if not results:
                print("❗ No objects detected.")
            else:
                print("\n📦 객체 배열 (ID, Label, Pixel X, Pixel Y, MM X, MM Y):")
                print(results)

        cv2.imshow(window_name, output)
        return results 

    # 실시간 루프
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to read frame.")
            break

        # 실시간 감지 (화면에만 표시)
        detect_and_display(frame, window_name="Live Detection", print_info=False)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            # 캡처 및 좌표 출력
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.png"
            cv2.imwrite(filename, frame)
            print(f"\n✅ 캡처된 프레임 저장됨: {filename}")

            # 감지 수행 및 결과 배열 저장 (MM 좌표 포함 출력)
            print("\n=== 📷 캡처된 이미지에서 객체 감지 ===")
            detected_objects = detect_and_display(frame, window_name="Captured Detection", print_info=True)

            # 사용자 입력으로 특정 객체 선택 (추가 로직 필요 시 여기에 구현)
            if detected_objects:
                try:
                    user_input = input("\n🔎 로봇이 이동할 객체 번호를 입력하세요: ")
                    selected_id = int(user_input)
                    selected = [obj for obj in detected_objects if obj[0] == selected_id]

                    if selected:
                        label, mm_x, mm_y = selected[0][1], selected[0][4], selected[0][5]
                        print(f"\n➡ 선택된 객체: {label}, 목표 MM 좌표: ({mm_x:.2f}, {mm_y:.2f})")
                        # 📌 로봇 이동 명령 전송 로직 (필요 시)
                        X_out_arduino = int(round(mm_x)); Y_out_arduino = int(round(mm_y))
                        output_str_arduino = f"{X_out_arduino},{Y_out_arduino}\n"
                        ser.write(output_str_arduino.encode())
                        
                    else:
                        print("❗ 해당 번호의 객체가 없습니다.")
                except ValueError:
                    print("❗ 숫자를 입력해주세요.")
                except Exception as e:
                    print(f"오류 발생: {e}")

            cv2.waitKey(10)
            cv2.destroyAllWindows()
            break

while True:
    com=input('Put number: 1. machine_vision_mode, 2. AI_mode, 3. Quit: ')
    if com.startswith('1'):
        machine_vision()
        
    elif com.startswith('2'):
        AI_MODE()
        print("▶ 실시간 객체 인식 중... (c: 캡처 및 감지, q: 종료)")

    elif com.startswith('3'):
        print("Program end")
        # 시리얼 포트를 닫고 프로그램 종료
        try:
            ser.close()
        except NameError:
            pass # ser이 정의되지 않았을 경우 무시
        break
print("--- 프로그램 종료 ---")