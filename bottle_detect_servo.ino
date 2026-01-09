  #include <Servo.h>
  #include <Wire.h>
  #include <LiquidCrystal_I2C.h>
  #include <math.h> // 삼각 함수 (atan2, sqrt, acos 등) 사용을 위해 포함

  // =======================================================
  // 🛠️ 로봇 기구학 및 하드웨어 설정
  // =======================================================

  // 로봇팔의 링크 길이 (단위: cm)
  // Python 코드가 mm 좌표를 보내므로, 여기서는 cm 단위를 사용하려면 변환이 필수입니다.
  const float L1 = 5.0; // 첫 번째 링크 길이 (cm)
  const float L2 = 7.0; // 두 번째 링크 길이 (cm)

  // 서보 객체
  Servo servo1; // 관절 1 (베이스)
  Servo servo2; // 관절 2 (엘보)

  // LCD 설정 (주소와 크기는 실제 하드웨어에 맞게 수정)
  #define LCD_ADDR 0x27 
  #define LCD_COLS 16
  #define LCD_ROWS 2
  LiquidCrystal_I2C lcd(LCD_ADDR, LCD_COLS, LCD_ROWS); 

  const int BAUD_RATE = 9600; // Python과 동일하게 설정

  // =======================================================
  // 📐 역기구학 (Inverse Kinematics) 함수
  // =======================================================

  /**
  * 역기구학 계산 함수
  * X, Y 좌표 (mm 단위)를 입력받아 서보 각도 (0~180도)를 계산합니다.
  * @param X 목표 X 좌표 (cm)
  * @param Y 목표 Y 좌표 (cm)
  * @param angle1 계산된 Joint 1 서보 각도 (0~180)
  * @param angle2 계산된 Joint 2 서보 각도 (0~180)
  * @return 성공하면 true, 도달 불가능하면 false
  */
  bool inverseKinematics(float X, float Y, float &angle1, float &angle2) {
      float r = sqrt(X*X + Y*Y);
      
      // 1. 도달 불가능성 검사
      if (r > (L1 + L2) || r < abs(L1 - L2)) {
          return false; // 로봇팔의 최대/최소 길이 초과
      }
      
      // 2. Joint 2 (theta2) 계산 (코사인 법칙)
      float cosTheta2 = (r*r - L1*L1 - L2*L2) / (2 * L1 * L2);
      
      // 부동 소수점 오차로 인한 값 보정
      if (cosTheta2 > 1.0) cosTheta2 = 1.0;
      if (cosTheta2 < -1.0) cosTheta2 = -1.0;
      
      // Elbow Up 솔루션 선택 (각도 범위: 0 ~ 180도)
      float theta2_rad = acos(cosTheta2);
      
      // 3. Joint 1 (theta1) 계산
      float alpha = atan2(L2 * sin(theta2_rad), L1 + L2 * cos(theta2_rad));
      float theta1_rad = atan2(Y, X) - alpha;

      // --- 라디안을 Degree로 변환 ---
      float angle1_deg = theta1_rad * (180.0 / M_PI);
      float angle2_deg = theta2_rad * (180.0 / M_PI); 

      // ----------------------------------------------------------------------
      // 📌 서보 각도 변환 및 오프셋 적용
      // ----------------------------------------------------------------------

      // [베이스 관절 (Joint 1)]
      // 일반적인 IK 계산 결과 (-180~180)를 서보 범위 (0~180)로 변환
      // 90도를 영점으로 가정합니다. (예: -90도 -> 0도, 0도 -> 90도, 90도 -> 180도)
      angle1 = angle1_deg + 90.0; 
      
      // [엘보 관절 (Joint 2)]
      // IK 결과(angle2_deg)에 90도 반시계 방향 영점 오프셋 적용:
      angle2 = angle2_deg - 90.0;
      // 그리고 서보의 물리적 방향과 맞추기 위해 180도에서 빼서 방향을 반전합니다.
      // angle2 = 180.0 - (angle2_deg - 90.0); 

      // ----------------------------------------------------------------------
      
      // 4. 각도를 서보의 물리적 범위 (0~180)로 제한
      angle1 = constrain(angle1, 0, 180);
      angle2 = constrain(angle2, 0, 180);
      
      return true;
  }

  // =======================================================
  // 🚀 Setup 및 Loop 함수
  // =======================================================

  void setup() {
      Serial.begin(BAUD_RATE); 

      // 서보 핀 연결 (실제 핀 번호에 맞게 수정)
      servo1.attach(9); 
      servo2.attach(10); 

      // LCD 초기화
      lcd.begin();
      lcd.backlight();
      
      // 초기 자세 설정 (예: 90, 90)
      servo1.write(90);
      servo2.write(90);
      lcd.setCursor(0, 0);
      lcd.print("Tracker Ready");
  }

  void loop() {
      if (Serial.available() > 0) {
          // Python에서 보낸 "X,Y\n" 형식의 문자열을 읽습니다.
          String receivedData = Serial.readStringUntil('\n');

          int commaIndex = receivedData.indexOf(',');

          if (commaIndex != -1) {
              // 1. 수신 및 파싱
              float targetX_mm = receivedData.substring(0, commaIndex).toFloat();
              float targetY_mm = receivedData.substring(commaIndex + 1).toFloat();

              // 2. 🚨 단위 변환 (mm -> cm)
              // Python은 mm, IK는 L1/L2가 cm이므로 10으로 나눕니다.
              float targetX_cm = targetX_mm / 10.0;
              float targetY_cm = targetY_mm / 10.0;
              
              // 3. 역기구학 계산 및 서보 이동
              float angle1, angle2;
              if (inverseKinematics(targetX_cm, targetY_cm, angle1, angle2)) {
                  
                  // 3-1. 서보 이동 명령
                  servo1.write((int)angle1); 
                  servo2.write((int)angle2);
                  
                  // 3-2. LCD 출력 (목표 좌표)
                  lcd.clear();
                  lcd.setCursor(0, 0); 
                  lcd.print("TARGET X Y :"); 
                  lcd.setCursor(0, 1);
                  lcd.print((int)targetX_mm); // LCD에는 다시 mm로 출력
                  lcd.print(",");
                  lcd.print((int)targetY_mm);
                  
                  // 3-3. 시리얼 피드백 (디버깅)
                  Serial.print("IK Success: T1=");
                  Serial.print(angle1);
                  Serial.print(" T2=");
                  Serial.print(angle2);
                  Serial.print(" X=");
                  Serial.print(targetX_mm);
                  Serial.print(" Y=");
                  Serial.println(targetY_mm);
                  
              } else {
                  // 도달 불가능한 위치
                  lcd.clear();
                  lcd.print("Out of Reach!"); 
                  Serial.println("IK Failed: Out of Reach");
              }
          }
      }
  }