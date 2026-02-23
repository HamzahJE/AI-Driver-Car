// ============================================================================
// AI Driver Car — Smart Motor Controller with Front Ultrasonic Sensor
// ============================================================================
// The Pi/LLM sends a GOAL direction (F/B/L/R/S). This Arduino uses a front
// ultrasonic sensor to drive smoothly toward that goal while avoiding
// head-on collisions. Movement is continuous and reactive.
// ============================================================================

// --- Motor Pins ---
const int M1_A = 9;  // Left Motor Pin A
const int M1_B = 10; // Left Motor Pin B
const int M2_A = 5;  // Right Motor Pin A
const int M2_B = 6;  // Right Motor Pin B

// --- Ultrasonic Sensor Pins (Front only) ---
const int TRIG_F = 7; // Front sensor trigger
const int ECHO_F = 8; // Front sensor echo

// --- Tuning Constants ---
const int STOP_DIST = 10;       // cm — emergency stop if closer
const int SLOW_DIST = 30;       // cm — start slowing down
const int BASE_SPEED = 200;     // PWM 0-255 — normal driving speed
const int MIN_SPEED = 80;       // PWM — slowest we'll go (below this motors stall)
const int TURN_SPEED = 180;     // PWM — speed during turns
const int SENSOR_INTERVAL = 50; // ms — how often to read sensor

// --- State ---
char currentGoal = 'S'; // Goal direction from LLM (F/B/L/R/S)
unsigned long lastSensorRead = 0;
int distFront = 999;

// ============================================================================
// SETUP
// ============================================================================
void setup()
{
  Serial.begin(115200);

  // Motor pins
  pinMode(M1_A, OUTPUT);
  pinMode(M1_B, OUTPUT);
  pinMode(M2_A, OUTPUT);
  pinMode(M2_B, OUTPUT);

  // Sensor pins
  pinMode(TRIG_F, OUTPUT);
  pinMode(ECHO_F, INPUT);

  stopMotors();
  Serial.println("Robot Ready. Front sensor active. Send F, B, L, R, S or T.");
}

// ============================================================================
// MAIN LOOP — runs every ~50ms
// ============================================================================
void loop()
{
  // --- Check for new commands from Pi ---
  if (Serial.available() > 0)
  {
    char cmd = Serial.read();
    if (cmd == 'T')
    {
      runTestSequence();
      return;
    }
    if (cmd == 'F' || cmd == 'B' || cmd == 'L' || cmd == 'R' || cmd == 'S')
    {
      currentGoal = cmd;
      Serial.write('A'); // ACK
    }
    else
    {
      Serial.write('E'); // Unknown command
    }
  }

  // --- Read sensor at regular intervals ---
  unsigned long now = millis();
  if (now - lastSensorRead >= SENSOR_INTERVAL)
  {
    lastSensorRead = now;
    distFront = readDistance(TRIG_F, ECHO_F);

    // Send sensor data to Pi for logging
    Serial.print("D:");
    Serial.println(distFront);
  }

  // --- Drive based on goal + sensor feedback ---
  drive();
}

// ============================================================================
// SMART DRIVING — goal direction + front sensor safety
// ============================================================================
void drive()
{
  if (currentGoal == 'S')
  {
    stopMotors();
    return;
  }

  // --- FORWARD ---
  if (currentGoal == 'F')
  {
    if (distFront <= STOP_DIST)
    {
      // Wall right ahead — stop, let LLM re-evaluate
      stopMotors();
      return;
    }

    // Calculate speed based on front distance (slow down as we approach)
    int speed = BASE_SPEED;
    if (distFront < SLOW_DIST)
    {
      speed = map(distFront, STOP_DIST, SLOW_DIST, MIN_SPEED, BASE_SPEED);
      speed = constrain(speed, MIN_SPEED, BASE_SPEED);
    }

    driveMotors(speed, speed, true); // true = forward
    return;
  }

  // --- BACKWARD ---
  if (currentGoal == 'B')
  {
    driveMotors(BASE_SPEED, BASE_SPEED, false); // false = reverse
    return;
  }

  // --- TURN LEFT ---
  if (currentGoal == 'L')
  {
    // Spin left: left motor backward, right motor forward
    setMotor(M1_A, M1_B, TURN_SPEED, false); // left backward
    setMotor(M2_A, M2_B, TURN_SPEED, true);  // right forward
    return;
  }

  // --- TURN RIGHT ---
  if (currentGoal == 'R')
  {
    // Spin right: left motor forward, right motor backward
    setMotor(M1_A, M1_B, TURN_SPEED, true);  // left forward
    setMotor(M2_A, M2_B, TURN_SPEED, false); // right backward
    return;
  }
}

// ============================================================================
// MOTOR HELPERS
// ============================================================================

void setMotor(int pinA, int pinB, int speed, bool forward)
{
  if (forward)
  {
    analogWrite(pinA, 0);
    analogWrite(pinB, speed);
  }
  else
  {
    analogWrite(pinA, speed);
    analogWrite(pinB, 0);
  }
}

void driveMotors(int leftSpeed, int rightSpeed, bool forward)
{
  setMotor(M1_A, M1_B, leftSpeed, forward);
  setMotor(M2_A, M2_B, rightSpeed, forward);
}

void stopMotors()
{
  analogWrite(M1_A, 0);
  analogWrite(M1_B, 0);
  analogWrite(M2_A, 0);
  analogWrite(M2_B, 0);
}

// ============================================================================
// ULTRASONIC SENSOR
// ============================================================================

int readDistance(int trigPin, int echoPin)
{
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 25000); // 25ms timeout (~4m max)
  if (duration == 0)
    return 999;                // No echo = nothing in range
  return duration * 0.034 / 2; // Convert to cm
}

// ============================================================================
// TEST SEQUENCE — standalone motor test (no LLM needed)
// ============================================================================
void runTestSequence()
{
  Serial.println("Starting Test Sequence...");

  Serial.print("Front distance: ");
  Serial.print(readDistance(TRIG_F, ECHO_F));
  Serial.println(" cm");

  char tests[] = {'F', 'B', 'L', 'R', 'S'};
  for (int i = 0; i < 5; i++)
  {
    currentGoal = tests[i];
    Serial.print("Testing: ");
    Serial.println(tests[i]);
    for (int j = 0; j < 20; j++)
    { // Run for ~1 second (20 x 50ms)
      distFront = readDistance(TRIG_F, ECHO_F);
      drive();
      delay(SENSOR_INTERVAL);
    }
  }
  stopMotors();
  currentGoal = 'S';
  Serial.println("Test Complete.");
}