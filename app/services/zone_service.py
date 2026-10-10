from pathlib import Path


class ZoneService:

    def __init__(self, zone_file="restricted_zone.txt"):
        self.zone_file = Path(zone_file)

    def get_zone(self):
        if not self.zone_file.exists():
            return []

        points = []

        with open(self.zone_file, "r") as file:
            content = file.read().strip()

        if not content:
            return []

        # Expected format:
        # [(118, 963), (129, 404), (505, 413), (490, 950)]

        content = content.replace("[", "")
        content = content.replace("]", "")
        content = content.replace("(", "")
        content = content.replace(")", "")

        values = [
            value.strip()
            for value in content.split(",")
            if value.strip()
        ]

        for i in range(0, len(values), 2):
            x = int(values[i])
            y = int(values[i + 1])

            points.append((x, y))

        return points

    def save_zone(self, points):

        if len(points) < 3:
            raise ValueError(
                "A restricted zone needs at least 3 points."
            )

        with open(self.zone_file, "w") as file:
            file.write(str(points))

        return points

    def clear_zone(self):

        if self.zone_file.exists():
            self.zone_file.write_text("")

        return True