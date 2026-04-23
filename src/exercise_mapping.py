from typing import Optional

# fmt: off
_EXERCISE_TO_MUSCLE = {
    # Chest
    "Bench Press (Barbell)": "Chest",
    "Bench Press (Dumbbell)": "Chest",
    "Incline Bench Press (Barbell)": "Chest",
    "Incline Bench Press (Dumbbell)": "Chest",
    "Decline Bench Press (Barbell)": "Chest",
    "Chest Fly (Dumbbell)": "Chest",
    "Chest Fly (Cable)": "Chest",
    "Chest Fly (Machine)": "Chest",
    "Chest Press (Machine)": "Chest",
    "Push Up": "Chest",
    "Dip": "Chest",

    # Back
    "Deadlift (Barbell)": "Back",
    "Deadlift (Dumbbell)": "Back",
    "Romanian Deadlift (Barbell)": "Back",
    "Romanian Deadlift (Dumbbell)": "Back",
    "Pull Up": "Back",
    "Chin Up": "Back",
    "Lat Pulldown (Cable)": "Back",
    "Lat Pulldown (Machine)": "Back",
    "Seated Cable Row - V Grip (Cable)": "Back",
    "Seated Cable Row (Cable)": "Back",
    "Bent Over Row (Barbell)": "Back",
    "Bent Over Row (Dumbbell)": "Back",
    "T-Bar Row": "Back",
    "Rowing Machine": "Back",
    "Back Extension": "Back",
    "Shrug (Barbell)": "Back",
    "Shrug (Dumbbell)": "Back",

    # Shoulders
    "Shoulder Press (Barbell)": "Shoulders",
    "Shoulder Press (Dumbbell)": "Shoulders",
    "Overhead Press (Barbell)": "Shoulders",
    "Overhead Press (Dumbbell)": "Shoulders",
    "Lateral Raise (Dumbbell)": "Shoulders",
    "Lateral Raise (Cable)": "Shoulders",
    "Lateral Raise (Machine)": "Shoulders",
    "Front Raise (Dumbbell)": "Shoulders",
    "Front Raise (Cable)": "Shoulders",
    "Rear Delt Fly (Dumbbell)": "Shoulders",
    "Rear Delt Fly (Cable)": "Shoulders",
    "Rear Delt Fly (Machine)": "Shoulders",
    "Face Pull": "Shoulders",
    "Shoulder Rehab Pulling Band Apart": "Shoulders",
    "Arnold Press (Dumbbell)": "Shoulders",

    # Legs
    "Squat (Barbell)": "Legs",
    "Squat (Dumbbell)": "Legs",
    "Squat (Machine)": "Legs",
    "Front Squat (Barbell)": "Legs",
    "Goblet Squat": "Legs",
    "Leg Press (Machine)": "Legs",
    "Hack Squat (Machine)": "Legs",
    "Pendulum Squat (Machine)": "Legs",
    "Leg Extension (Machine)": "Legs",
    "Seated Leg Curl (Machine)": "Legs",
    "Lying Leg Curl (Machine)": "Legs",
    "Romanian Deadlift (Barbell)": "Legs",
    "Romanian Deadlift (Dumbbell)": "Legs",
    "Bulgarian Split Squat": "Legs",
    "Lunge (Dumbbell)": "Legs",
    "Lunge (Barbell)": "Legs",
    "Step Up": "Legs",
    "Hip Thrust (Barbell)": "Legs",
    "Hip Thrust (Machine)": "Legs",
    "Glute Kickback (Machine)": "Legs",
    "Adduction (Machine)": "Legs",
    "Abduction (Machine)": "Legs",
    "Standing Calf Raise": "Legs",
    "Seated Calf Raise (Machine)": "Legs",
    "Calf Press (Machine)": "Legs",
    "Treadmill": "Legs",

    # Arms – Triceps
    "Triceps Pushdown": "Triceps",
    "Triceps Extension (Dumbbell)": "Triceps",
    "Triceps Extension (Cable)": "Triceps",
    "Triceps Extension (Barbell)": "Triceps",
    "Skullcrusher (Barbell)": "Triceps",
    "Close Grip Bench Press (Barbell)": "Triceps",
    "Diamond Push Up": "Triceps",

    # Arms – Biceps
    "Bicep Curl (Barbell)": "Biceps",
    "Bicep Curl (Dumbbell)": "Biceps",
    "Bicep Curl (Cable)": "Biceps",
    "Bicep Curl (Machine)": "Biceps",
    "Hammer Curl (Dumbbell)": "Biceps",
    "Hammer Curl (Cable)": "Biceps",
    "Preacher Curl (Barbell)": "Biceps",
    "Preacher Curl (Dumbbell)": "Biceps",
    "Concentration Curl (Dumbbell)": "Biceps",
    "Incline Curl (Dumbbell)": "Biceps",
    "Reverse Curl (Barbell)": "Biceps",
    "Reverse Curl (Dumbbell)": "Biceps",

    # Core
    "Plank": "Core",
    "Hanging Leg Raise": "Core",
    "Leg Raise": "Core",
    "Crunch": "Core",
    "Sit Up": "Core",
    "Russian Twist": "Core",
    "Ab Wheel Rollout": "Core",
    "Cable Crunch": "Core",
}
# fmt: on

_KEYWORD_FALLBACKS = [
    ("chest", "Chest"),
    ("bench", "Chest"),
    ("fly", "Chest"),
    ("deadlift", "Back"),
    ("row", "Back"),
    ("pulldown", "Back"),
    ("pull up", "Back"),
    ("chin up", "Back"),
    ("shrug", "Back"),
    ("rowing", "Back"),
    ("press", "Shoulders"),
    ("lateral raise", "Shoulders"),
    ("front raise", "Shoulders"),
    ("rear delt", "Shoulders"),
    ("face pull", "Shoulders"),
    ("shoulder", "Shoulders"),
    ("arnold", "Shoulders"),
    ("squat", "Legs"),
    ("leg press", "Legs"),
    ("leg extension", "Legs"),
    ("leg curl", "Legs"),
    ("lunge", "Legs"),
    ("hip thrust", "Legs"),
    ("calf", "Legs"),
    ("treadmill", "Legs"),
    ("triceps", "Triceps"),
    ("pushdown", "Triceps"),
    ("skullcrusher", "Triceps"),
    ("bicep", "Biceps"),
    ("curl", "Biceps"),
    ("hammer curl", "Biceps"),
    ("plank", "Core"),
    ("crunch", "Core"),
    ("leg raise", "Core"),
    ("ab wheel", "Core"),
    ("sit up", "Core"),
]


def get_muscle_group(exercise_name: str) -> Optional[str]:
    """Return the primary muscle group for an exercise.

    Uses an explicit lookup table first, then falls back to keyword matching.
    Returns ``None`` when no mapping can be inferred.
    """
    if exercise_name in _EXERCISE_TO_MUSCLE:
        return _EXERCISE_TO_MUSCLE[exercise_name]

    lowered = exercise_name.lower()
    for keyword, muscle in _KEYWORD_FALLBACKS:
        if keyword in lowered:
            return muscle

    return None
