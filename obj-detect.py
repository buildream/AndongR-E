import cv2
import numpy as np

# 클래스 이름 (VOC 20종)
CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
           "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
           "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
           "sofa", "train", "tvmonitor"]

# 모델 파일 경로
prototxt_path = "deploy.prototxt"
model_path = "mobilenet_iter_73000.caffemodel"

# 모델 로딩
net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)

# 웹캠 열기
cap = cv2.VideoCapture(0)

print("Starting object detection. Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    h, w = frame.shape[:2]

    # DNN 입력 전처리
    blob = cv2.dnn.blobFromImage(frame, scalefactor=0.007843,
                                 size=(300, 300), mean=127.5)
    net.setInput(blob)
    detections = net.forward()

    # 탐지 결과 처리
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]

        if confidence > 0.5:
            idx = int(detections[0, 0, i, 1])
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            centerX = int((startX + endX) / 2)
            centerY = int((startY + endY) / 2)

            label = f"{CLASSES[idx]}: {confidence:.2f}"
            print(f"[{i}] {label}, Center: ({centerX}, {centerY})")

            # 시각화
            cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
            cv2.circle(frame, (centerX, centerY), 5, (0, 0, 255), -1)
            cv2.putText(frame, label, (startX, startY - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    cv2.imshow("Object Detection", frame)

    # 종료 키
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 정리
cap.release()
cv2.destroyAllWindows()
