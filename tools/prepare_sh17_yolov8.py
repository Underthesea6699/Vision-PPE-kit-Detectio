from pathlib import Path
import shutil


RAW_DIR = Path("SH17_raw")
OUTPUT_DIR = Path("dataset/SH17_YOLOv8")

# SH17 original classes
# 0  = person
# 10 = helmet
# 16 = safety-vest

CLASS_MAP = {
    0: 0,    # person
    10: 1,   # helmet
    16: 2    # safety-vest
}


def prepare_split(split_name, file_list_name):

    image_output = OUTPUT_DIR / "images" / split_name
    label_output = OUTPUT_DIR / "labels" / split_name

    image_output.mkdir(parents=True, exist_ok=True)
    label_output.mkdir(parents=True, exist_ok=True)

    file_list = RAW_DIR / file_list_name

    with open(file_list, "r") as f:
        image_names = [
            line.strip()
            for line in f
            if line.strip()
        ]

    processed = 0
    objects = 0
    missing_images = 0
    missing_labels = 0

    for image_name in image_names:

        image_path = RAW_DIR / "images" / image_name

        if not image_path.exists():
            # Some file lists may contain paths instead of bare names
            image_path = RAW_DIR / "images" / Path(image_name).name

        if not image_path.exists():
            missing_images += 1
            continue

        label_name = image_path.stem + ".txt"
        label_path = RAW_DIR / "labels" / label_name

        if not label_path.exists():
            missing_labels += 1
            continue

        output_image = image_output / image_path.name
        output_label = label_output / label_name

        shutil.copy2(
            image_path,
            output_image
        )

        selected_labels = []

        with open(label_path, "r") as f:
            for line in f:

                parts = line.strip().split()

                if len(parts) != 5:
                    continue

                original_class = int(parts[0])

                if original_class not in CLASS_MAP:
                    continue

                new_class = CLASS_MAP[original_class]

                selected_labels.append(
                    f"{new_class} "
                    f"{parts[1]} "
                    f"{parts[2]} "
                    f"{parts[3]} "
                    f"{parts[4]}\n"
                )

                objects += 1

        # Keep image even if it contains none of our 3 classes.
        # YOLOv8 can handle an empty label file.
        with open(output_label, "w") as f:
            f.writelines(selected_labels)

        processed += 1

    print(f"\n{split_name.upper()} COMPLETE")
    print(f"Images: {processed}")
    print(f"Selected objects: {objects}")
    print(f"Missing images: {missing_images}")
    print(f"Missing labels: {missing_labels}")


def create_yaml():

    yaml_content = f"""train: {str((OUTPUT_DIR / 'images' / 'train').resolve()).replace(chr(92), '/')}
val: {str((OUTPUT_DIR / 'images' / 'val').resolve()).replace(chr(92), '/')}

nc: 3

names:
  0: person
  1: helmet
  2: safety-vest
"""

    yaml_path = OUTPUT_DIR / "data.yaml"

    with open(yaml_path, "w") as f:
        f.write(yaml_content)

    print("\nCreated:", yaml_path)


def main():

    if not RAW_DIR.exists():
        raise FileNotFoundError(
            f"SH17 dataset not found: {RAW_DIR.resolve()}"
        )

    if OUTPUT_DIR.exists():
        print("Removing existing YOLOv8 dataset...")
        shutil.rmtree(OUTPUT_DIR)

    prepare_split(
        "train",
        "train_files.txt"
    )

    prepare_split(
        "val",
        "val_files.txt"
    )

    create_yaml()

    print("\n===================================")
    print("SH17 YOLOv8 preparation complete!")
    print("===================================")
    print(f"Output: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()