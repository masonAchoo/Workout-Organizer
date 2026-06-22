import json
import time
import webbrowser
from pathlib import Path

import questionary


def display_exercise_image(image: str | None) -> None:
    if not image:
        return
    path = Path(image).expanduser()
    try:
        if path.exists():
            webbrowser.open(path.as_uri())
        elif image.startswith(("http://", "https://")):
            webbrowser.open(image)
    except Exception:
        pass

DATA_DIR = Path(__file__).resolve().parent / "data"
WORKOUTS_FILE = DATA_DIR / "workouts.json"
EXERCISES_FILE = DATA_DIR / "exercises.json"


def ensure_data_files() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    for path in (WORKOUTS_FILE, EXERCISES_FILE):
        if not path.exists():
            path.write_text("[]", encoding="utf-8")


def load_json(path: Path) -> list[dict]:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]", encoding="utf-8")
        return []

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_json(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def build_choice_list(items: list[dict], label_key: str) -> list[questionary.Choice]:
    return [
        questionary.Choice(title=f"{item[label_key]} ({i + 1})", value=i)
        for i, item in enumerate(items)
    ]


def prompt_unique_name(
    message: str,
    existing_names: set[str],
    current_name: str | None = None,
) -> str | None:
    def validate(text: str) -> bool | str:
        value = text.strip()
        if not value:
            return "Enter a name."
        lowered = value.lower()
        if current_name is None or lowered != current_name.lower():
            if lowered in existing_names:
                return "Name already exists; choose a different one."
        return True

    return questionary.text(message, validate=validate).ask()


def choose_action() -> str | None:
    return questionary.select(
        "Choose an action:",
        choices=["Select Workout", "Select Exercise", "Quit"],
    ).ask()


def choose_workout(workouts: list[dict]) -> dict | None:
    if not workouts:
        print("No workouts available. Add a workout first.")
        return None

    choice = questionary.select(
        "Choose a workout:",
        choices=build_choice_list(workouts, "name"),
    ).ask()

    if choice is None:
        return None
    return workouts[choice]


def choose_exercise(exercises: list[dict]) -> dict | None:
    if not exercises:
        print("No exercises available. Add an exercise first.")
        return None

    choice = questionary.select(
        "Choose an exercise:",
        choices=build_choice_list(exercises, "name"),
    ).ask()

    if choice is None:
        return None
    return exercises[choice]


def select_workout_flow(workouts: list[dict], exercises: list[dict]) -> None:
    if not workouts:
        create = questionary.select(
            "No workouts exist. Would you like to create one now?",
            choices=[questionary.Choice("Yes", value=True), questionary.Choice("No", value=False)],
        ).ask()
        if create:
            add_workout(workouts, exercises)
        return

    choices = [
        *build_choice_list(workouts, "name"),
        questionary.Separator(),
        questionary.Choice("Create new workout", value="create"),
    ]
    choice = questionary.select("Choose a workout or action:", choices=choices).ask()
    if choice is None:
        return
    if choice == "create":
        add_workout(workouts, exercises)
        return

    workout = workouts[choice]
    action = questionary.select(
        f"What would you like to do with '{workout['name']}'?",
        choices=["Run workout", "Edit workout", "Delete workout", "Back"],
    ).ask()
    if action == "Run workout":
        execute_workout(workout, exercises)
    elif action == "Edit workout":
        edit_workout(workouts, exercises, selected_index=choice)
    elif action == "Delete workout":
        delete_workout(workouts, selected_index=choice)


def select_exercise_flow(exercises: list[dict]) -> None:
    if not exercises:
        create = questionary.select(
            "No exercises exist. Would you like to create one now?",
            choices=[questionary.Choice("Yes", value=True), questionary.Choice("No", value=False)],
        ).ask()
        if create:
            add_exercise(exercises)
        return

    choices = [
        *build_choice_list(exercises, "name"),
        questionary.Separator(),
        questionary.Choice("Create new exercise", value="create"),
    ]
    choice = questionary.select("Choose an exercise or action:", choices=choices).ask()
    if choice is None:
        return
    if choice == "create":
        add_exercise(exercises)
        return

    exercise = exercises[choice]
    print(f"\nExercise: {exercise['name']}")
    print(f"Image: {exercise.get('image') or 'None'}\n")

    action = questionary.select(
        f"What would you like to do with '{exercise['name']}'?",
        choices=["Edit exercise", "Delete exercise", "Back"],
    ).ask()
    if action == "Edit exercise":
        edit_exercise(exercises, selected_index=choice)
    elif action == "Delete exercise":
        delete_exercise(exercises, selected_index=choice)


def prompt_positive_int(message: str, default: int = 1) -> int | None:
    response = questionary.text(
        message,
        default=str(default),
        validate=lambda text: text.isdigit() and int(text) > 0 or "Enter a positive number",
    ).ask()
    if response is None:
        return None
    return int(response)


def run_timer(seconds: int) -> None:
    """Display a countdown timer for the given number of seconds."""
    print(f"\nTimer started: {seconds} seconds")
    for remaining in range(seconds, 0, -1):
        mins, secs = divmod(remaining, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        print(f"\rTime remaining: {time_str}", end="", flush=True)
        time.sleep(1)
    print(f"\rTime remaining: 00:00")
    input("Time's up! Press Enter to continue to the next exercise...\n")


def execute_workout(workout: dict, exercises: list[dict]) -> None:
    sets = prompt_positive_int("How many sets?", default=workout.get("sets", 1))
    if sets is None:
        return

    print(f"\nStarting workout: {workout['name']} ({sets} set{'s' if sets != 1 else ''})")
    for set_number in range(1, sets + 1):
        print(f"\nSet {set_number}/{sets}")
        for exercise in workout["exercises"]:
            exercise_name = exercise["exercise_name"]
            count = exercise["count"]
            kind = exercise["kind"]
            when_text = "reps" if kind == "reps" else "seconds"
            print(f"\nExercise: {exercise_name}")
            print(f"{count} {when_text}")

            if exercise.get("note"):
                print(f"Note: {exercise['note']}")

            matched = next((item for item in exercises if item["name"] == exercise_name), None)
            if matched:
                display_exercise_image(matched.get("image"))

            if kind == "seconds":
                run_timer(count)
            else:
                input("Press Enter to continue to the next exercise...")

    print("\nWorkout complete! Returning to the main menu.\n")


def add_workout(workouts: list[dict], exercises: list[dict]) -> None:
    if not exercises:
        print("No stored exercises exist yet. Add an exercise first.")
        return

    workout_name = prompt_unique_name(
        "Workout name:",
        {workout["name"].lower() for workout in workouts},
    )
    if not workout_name:
        print("Workout creation canceled.")
        return

    selected_exercises: list[dict] = []
    while True:
        exercise = choose_exercise(exercises)
        if exercise is None:
            return

        kind = questionary.select(
            "Choose the measurement type:",
            choices=["Reps", "Seconds"],
        ).ask()
        if kind is None:
            return

        count = prompt_positive_int(f"How many {kind.lower()}?", default=10)
        if count is None:
            return

        selected_exercises.append(
            {
                "exercise_name": exercise["name"],
                "kind": kind.lower(),
                "count": count,
            }
        )

        keep_adding = questionary.select(
            "Add another exercise to this workout?",
            choices=[questionary.Choice("Yes", value=True), questionary.Choice("No", value=False)],
        ).ask()
        if not keep_adding:
            break

    if not selected_exercises:
        print("No exercises were added to the workout.")
        return

    workout_sets = prompt_positive_int("How many sets should this workout have?", default=1)
    if workout_sets is None:
        return

    workouts.append(
        {
            "name": workout_name,
            "sets": workout_sets,
            "exercises": selected_exercises,
        }
    )
    save_json(WORKOUTS_FILE, workouts)
    print(f"Workout '{workout_name}' saved.\n")


def add_exercise(exercises: list[dict]) -> None:
    exercise_name = prompt_unique_name(
        "Exercise name:",
        {exercise["name"].lower() for exercise in exercises},
    )
    if not exercise_name:
        print("Exercise creation canceled.")
        return

    image = questionary.text(
        "Optional image path or URL (leave blank if none):",
        default="",
    ).ask()
    if image is None:
        return

    exercises.append(
        {
            "name": exercise_name,
            "image": image.strip() or None,
        }
    )
    save_json(EXERCISES_FILE, exercises)
    print(f"Exercise '{exercise_name}' saved.\n")


def edit_workout(workouts: list[dict], exercises: list[dict], selected_index: int | None = None) -> None:
    if not workouts:
        print("No workouts available. Add a workout first.")
        return

    if selected_index is None:
        choice = questionary.select(
            "Choose a workout to edit:",
            choices=build_choice_list(workouts, "name"),
        ).ask()
        if choice is None:
            return
        selected_index = choice

    workout = workouts[selected_index]
    workout_name = prompt_unique_name(
        "Workout name:",
        {w["name"].lower() for w in workouts},
        current_name=workout["name"],
    )
    if not workout_name:
        print("Workout edit canceled.")
        return

    workout["name"] = workout_name
    workout["sets"] = prompt_positive_int(
        "How many sets should this workout have?",
        default=workout.get("sets", 1),
    ) or workout["sets"]

    if questionary.confirm("Modify exercises in this workout?", default=False).ask():
        selected_exercises: list[dict] = []
        while True:
            exercise = choose_exercise(exercises)
            if exercise is None:
                return

            kind = questionary.select(
                "Choose the measurement type:",
                choices=["Reps", "Seconds"],
            ).ask()

            count = prompt_positive_int(f"How many {kind.lower()}?", default=10)
            if count is None:
                return

            selected_exercises.append(
                {
                    "exercise_name": exercise["name"],
                    "kind": kind.lower(),
                    "count": count,
                }
            )

            keep_adding = questionary.confirm("Add another exercise to this workout?", default=True).ask()
            if not keep_adding:
                break

        if selected_exercises:
            workout["exercises"] = selected_exercises

    save_json(WORKOUTS_FILE, workouts)
    print(f"Workout '{workout_name}' updated.\n")


def delete_workout(workouts: list[dict], selected_index: int | None = None) -> None:
    if not workouts:
        print("No workouts to delete.")
        return

    if selected_index is None:
        choice = questionary.select(
            "Choose a workout to delete:",
            choices=build_choice_list(workouts, "name"),
        ).ask()
        selected_index = choice

    workout = workouts[selected_index]
    del workouts[selected_index]
    save_json(WORKOUTS_FILE, workouts)
    print(f"Workout '{workout['name']}' deleted.\n")


def delete_exercise(exercises: list[dict], selected_index: int | None = None) -> None:
    if not exercises:
        print("No exercises to delete.")
        return

    if selected_index is None:
        choice = questionary.select(
            "Choose an exercise to delete:",
            choices=build_choice_list(exercises, "name"),
        ).ask()
        selected_index = choice

    exercise = exercises[selected_index]
    del exercises[selected_index]
    save_json(EXERCISES_FILE, exercises)
    print(f"Exercise '{exercise['name']}' deleted.\n")


def edit_exercise(exercises: list[dict], selected_index: int | None = None) -> None:
    if not exercises:
        print("No exercises available. Add an exercise first.")
        return

    if selected_index is None:
        choice = questionary.select(
            "Choose an exercise to edit:",
            choices=build_choice_list(exercises, "name"),
        ).ask()
        if choice is None:
            return
        selected_index = choice

    exercise = exercises[selected_index]
    exercise_name = prompt_unique_name(
        "Exercise name:",
        {e["name"].lower() for e in exercises},
        current_name=exercise["name"],
    )
    if not exercise_name:
        print("Exercise edit canceled.")
        return

    exercise["name"] = exercise_name

    image = questionary.text(
        "Optional image path or URL (leave blank if none):",
        default=exercise.get("image") or "",
    ).ask()
    if image is None:
        return

    exercise["image"] = image.strip() or None
    save_json(EXERCISES_FILE, exercises)
    print(f"Exercise '{exercise_name}' updated.\n")


def main() -> None:
    ensure_data_files()
    workouts = load_json(WORKOUTS_FILE)
    exercises = load_json(EXERCISES_FILE)

    print("Hello from workout-organizer!")

    try:
        while True:
            action = choose_action()
            if action is None or action == "Quit":
                print("Goodbye!")
                break

            match action:
                case "Select Workout":
                    select_workout_flow(workouts, exercises)
                    workouts = load_json(WORKOUTS_FILE)
                case "Select Exercise":
                    select_exercise_flow(exercises)
                    exercises = load_json(EXERCISES_FILE)
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
