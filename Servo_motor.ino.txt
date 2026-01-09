#include<Servo.h> 
Servo servo1;      
Servo servo2;

float value1 = 0;    // 각도를 조절할 변수 value
float value2 =0;
float dth1=0;	//각도 시간당 증가시키기 위한 변수
float dth2=0;
float duration=0; 
float pre_value1=0,pre_value2=0;  
//이전의 명령값 저장 변수.   
float n_times=0;		
// 몇번 증가시킬 것인가를 저장하는 변수.

void setup() {
  servo1.attach(9);     //맴버함수인 attach : 핀 설정
  servo2.attach(10);     //맴버함수인 attach : 핀 설정
  Serial.begin(9600); //시리얼 모니터 사용 고고
  servo1.write(0);
  servo2.write(0);
  Serial.println("Input angle1, angle2, duration");
//(각도1, 각도2, 시간(duration))

}
void loop() {
  if(Serial.available())
  {
    value1=Serial.parseFloat();	//Input angle 1,
    value2=Serial.parseInt();		//Input angle 2
    duration=Serial.parseInt();		//Duration
    Serial.print(value1);Serial.print(',');		//
    Serial.print(value2);Serial.print(',');		//
    Serial.println(duration);		
    
      if(value1<0 && value1 >= 180)        //Range set
        value1 = 0;            		//
      if(value2<0 && value2 >= 180)
        value2 = 0;
    
    dth1=value1-pre_value1;		// desired relative angle
    dth2=value2-pre_value2;		// desired relative angle
    
    Serial.println(dth1);
    Serial.println(dth2);
    
    n_times=duration*10;		//n_times: section number 
    Serial.println(n_times);
    
    for(int i=0;i<n_times;i++)  // dth1, dht2 를 10번으로 나누어서 움직이자.
    {
    	servo1.write(pre_value1+float(dth1/n_times)*(i)); //value값의 각도로 회전. ex) value가 90이라면 90도 회전
    	servo2.write(pre_value2+float(dth2/n_times)*(i)); //value값의 각도로 회전. ex) value가 90이라면 90도 회전
    	Serial.print(pre_value1+float(dth1/n_times)*(i));Serial.print(',');
    	Serial.println(pre_value2+float(dth2/n_times)*(i));
	delay(100);
    }
    pre_value1= value1;
    pre_value2= value2;
    Serial.println(pre_value1);
    Serial.println(pre_value2);
    Serial.println("Input angle1, angle2, duration");
  }
}
