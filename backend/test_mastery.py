from app.services.mastery_service import (
    calculate_mastery,
    get_mastery_level,
    update_mastery
)


# Test 1: Calculate mastery
mastery = calculate_mastery(4, 5)

print("\n===== MASTERY CALCULATION =====")
print("Correct: 4")
print("Total: 5")
print("Mastery:", mastery)


# Test 2: Get mastery level
level = get_mastery_level(mastery)

print("\n===== MASTERY LEVEL =====")
print("Level:", level)


# Test 3: Correct answer
result = update_mastery(
    current_correct=4,
    current_total=5,
    is_correct=True
)

print("\n===== AFTER CORRECT ANSWER =====")
print(result)


# Test 4: Wrong answer
result = update_mastery(
    current_correct=4,
    current_total=5,
    is_correct=False
)

print("\n===== AFTER WRONG ANSWER =====")
print(result)