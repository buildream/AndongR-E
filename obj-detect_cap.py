import cv2
import numpy as np
import time

# VOC 클래스 목록
CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
           "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
           "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
           "sofa", "train", "tvmonitor"]

# DNN 모델 로딩
net = cv2.dnn.readNetFromCaffe("deploy.prototxt", "mobilenet_iter_73000.caffemodel")

# 웹캠 열기
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Cannot open camera.")
    exit()

print("▶ 실시간 객체 인식 중... (c: 캡처 및 감지, q: 종료)")

# 객체 인식 및 시각화 함수
def detect_and_display(image, window_name="Detection", print_info=False):
    h, w = image.shape[:2]
    blob = cv2.dnn.blobFromImage(image, 0.007843, (300, 300), 127.5)
    net.setInput(blob)
    detections = net.forward()
    output = image.copy()

    results = []
    obj_num = 1

    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > 0.5:
            idx = int(detections[0, 0, i, 1])
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
            centerX = int((startX + endX) / 2)
            centerY = int((startY + endY) / 2)
            label = CLASSES[idx]

            if print_info:
                print(f"- [{obj_num}] {label}, Center: ({centerX}, {centerY})")

            results.append([obj_num, label, centerX, centerY])
            obj_num += 1

            # 시각화
            cv2.rectangle(output, (startX, startY), (endX, endY), (0, 255, 0), 2)
            cv2.circle(output, (centerX, centerY), 5, (0, 0, 255), -1)
            cv2.putText(output, f"{label}", (startX, startY - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    if print_info:
        if not results:
            print("❗ No objects detected.")
        else:
            print("\n📦 객체 배열:")
            print(results)

    cv2.imshow(window_name, output)
    return results  # 결과 배열 반환

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
        # 캡처
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.png"
        cv2.imwrite(filename, frame)
        print(f"\n✅ 캡처된 프레임 저장됨: {filename}")

        cap.release()
        cv2.destroyAllWindows()

        # 감지 수행 및 결과 배열 저장
        print("\n=== 📷 캡처된 이미지에서 객체 감지 ===")
        detected_objects = detect_and_display(frame, window_name="Captured Detection", print_info=True)

        # 사용자 입력으로 특정 객체 선택
        if detected_objects:
            try:
                user_input = input("\n🔎 보고 싶은 객체 번호를 입력하세요: ")
                selected_id = int(user_input)
                selected = [obj for obj in detected_objects if obj[0] == selected_id]

                if selected:
                    print(f"\n➡ 선택된 객체: {selected[0]}")
                else:
                    print("❗ 해당 번호의 객체가 없습니다.")
            except ValueError:
                print("❗ 숫자를 입력해주세요.")

        cv2.waitKey(10)
        cv2.destroyAllWindows()
        break
