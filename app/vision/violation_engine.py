class ViolationEngine:
    """
    Analyzes tracked person detections and determines
    whether a restricted-zone violation has occurred.
    """

    def __init__(
        self,
        confidence_threshold=0.50,
        required_inside_frames=3
    ):
        """
        confidence_threshold:
            Minimum YOLO confidence required for processing
            a person detection.

        required_inside_frames:
            Number of consecutive frames a person must remain
            inside the restricted zone before the violation
            is confirmed.
        """

        self.confidence_threshold = confidence_threshold
        self.required_inside_frames = required_inside_frames

        # Stores state for every tracked person.
        #
        # Example:
        # {
        #     12: {
        #         "inside_frames": 3,
        #         "confirmed_inside": True
        #     }
        # }
        self.person_states = {}


    def check_restricted_zone(
        self,
        track_id,
        confidence,
        inside_zone
    ):
        """
        Analyze one person's current state.

        Returns:
            A violation event dictionary if a new violation
            is confirmed.

            Otherwise returns None.
        """

        # Create initial state for a new person
        if track_id not in self.person_states:
            self.person_states[track_id] = {
                "inside_frames": 0,
                "confirmed_inside": False
            }

        state = self.person_states[track_id]


        # --------------------------------------------------
        # Person is outside the restricted zone
        # --------------------------------------------------

        if not inside_zone:

            state["inside_frames"] = 0
            state["confirmed_inside"] = False

            return None


        # --------------------------------------------------
        # Person is inside but detection confidence is low
        # --------------------------------------------------

        if confidence < self.confidence_threshold:

            return None


        # --------------------------------------------------
        # Person is inside with acceptable confidence
        # --------------------------------------------------

        state["inside_frames"] += 1


        # --------------------------------------------------
        # Already confirmed as inside
        # --------------------------------------------------

        if state["confirmed_inside"]:

            # Do not generate repeated violations
            return None


        # --------------------------------------------------
        # Confirm violation after required frames
        # --------------------------------------------------

        if state["inside_frames"] >= self.required_inside_frames:

            state["confirmed_inside"] = True

            return {
                "violation_type": "restricted_zone_entry",
                "track_id": track_id,
                "confidence": confidence,
                "inside_frames": state["inside_frames"]
            }


        return None


    def remove_person(self, track_id):
        """
        Remove a person's state.

        Useful when a tracker permanently loses a person.
        """

        if track_id in self.person_states:
            del self.person_states[track_id]


    def reset(self):
        """
        Reset all tracked person states.
        """

        self.person_states.clear()