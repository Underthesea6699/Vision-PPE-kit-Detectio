from app.vision.violation_engine import ViolationEngine


engine = ViolationEngine(
    confidence_threshold=0.50,
    required_inside_frames=3
)


person_id = 10


print("Testing restricted-zone violation engine...\n")


# --------------------------------------------------
# Frame 1
# --------------------------------------------------

result = engine.check_restricted_zone(
    track_id=person_id,
    confidence=0.75,
    inside_zone=True
)

print("Frame 1:", result)


# --------------------------------------------------
# Frame 2
# --------------------------------------------------

result = engine.check_restricted_zone(
    track_id=person_id,
    confidence=0.78,
    inside_zone=True
)

print("Frame 2:", result)


# --------------------------------------------------
# Frame 3
# --------------------------------------------------

result = engine.check_restricted_zone(
    track_id=person_id,
    confidence=0.80,
    inside_zone=True
)

print("Frame 3:", result)


# --------------------------------------------------
# Frame 4
# --------------------------------------------------

result = engine.check_restricted_zone(
    track_id=person_id,
    confidence=0.82,
    inside_zone=True
)

print("Frame 4:", result)


# --------------------------------------------------
# Person exits
# --------------------------------------------------

result = engine.check_restricted_zone(
    track_id=person_id,
    confidence=0.80,
    inside_zone=False
)

print("Person exits:", result)


# --------------------------------------------------
# Person enters again
# --------------------------------------------------

print("\nPerson enters again...\n")


for frame in range(1, 4):

    result = engine.check_restricted_zone(
        track_id=person_id,
        confidence=0.85,
        inside_zone=True
    )

    print(f"Entry frame {frame}:", result)


print("\nViolation engine test completed.")