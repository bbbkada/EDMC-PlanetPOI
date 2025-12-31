"""
Heading Guidance Example - Visar pilar för kursguidning med EDMCOverlay

Användning:
    guidance = HeadingGuidance()
    guidance.update(current_heading=45, target_heading=90)  # Behöver svänga höger
    guidance.clear()  # Rensa grafiken
"""

import sys
import os
import math
from PlanetPOI import overlay  # Använd samma overlay-instans som resten av pluginen


class HeadingGuidance:
    """
    Visar grafisk kursguidning med pilar som växer baserat på hur mycket man är ur kurs
    """
    
    def __init__(self, center_x=960, center_y=540, on_course_threshold=4):
        """
        Initialize course guidance
        
        Args:
            center_x: X-position for center (default: middle of 1920px screen)
            center_y: Y-position for center (default: middle of 1080px screen)
            on_course_threshold: Degrees tolerance for being "on course" (default: 4)
        """
        # Use the shared overlay instance from overlay.py
        if not overlay.ensure_overlay():
            self.overlay = None
        else:
            self.overlay = overlay.overlay
        self.center_x = center_x
        self.center_y = center_y
        
        # Arrow settings
        self.arrow_base_length = 30      # Base arrow length (reduced from 50)
        self.arrow_max_length = 150      # Maximum arrow length (reduced from 300)
        self.arrow_width = 12            # Arrow thickness (reduced from 20)
        self.arrow_head_size = 25        # Arrow head size (reduced from 40)
        
        # Colors
        self.arrow_color = "#ff8800"     # Orange
        self.arrow_fill = "#ff8800"      # Orange
        self.center_color = "#00ff00"    # Green
        self.center_fill = "#00ff00"     # Green
        
        # Thresholds
        self.on_course_threshold = on_course_threshold  # Degrees tolerance for being "on course"
        self.max_deviation = 90          # Maximum measured deviation (degrees)
        
        self.ttl = 15  # Time to live in seconds - longer TTL reduces flickering
    
    def update(self, current_heading, target_heading):
        """
        Updates the guidance based on current and target course
        
        Args:
            current_heading: Current heading in degrees (0-359)
            target_heading: Target heading in degrees (0-359)
        """
        if not self.overlay:
            return
            
        # Calculate shortest angular deviation (-180 to +180)
        deviation = self._calculate_deviation(current_heading, target_heading)
        
        # Clear old arrows first
        self._clear_arrows()
        
        # If almost on course - show fine-tuning bar
        if abs(deviation) <= self.on_course_threshold:
            self._draw_center_circle(deviation)
        # Otherwise show arrow in correct direction
        elif deviation > 0:
            # Need to turn right (positive deviation)
            self._draw_right_arrow(deviation)
        else:
            # Need to turn left (negative deviation)
            self._draw_left_arrow(abs(deviation))
    
    def show_checkmark(self):
        """
        Shows a green checkmark when within guidance stop distance from target
        """
        if not self.overlay:
            return
        
        # Clear old arrows
        self._clear_arrows()
        
        # Draw a green checkmark
        # The checkmark consists of two lines forming a V-shape
        check_size = 20
        
        # Left part of checkmark (lower left to middle)
        left_start_x = self.center_x - check_size
        left_start_y = self.center_y
        left_end_x = self.center_x - 5
        left_end_y = self.center_y + check_size
        
        # Right part of checkmark (middle to upper right)
        right_start_x = left_end_x
        right_start_y = left_end_y
        right_end_x = self.center_x + check_size
        right_end_y = self.center_y - check_size
        
        # Draw left line (thicker through multiple parallel lines)
        for offset in range(-2, 3):
            for step in range(20):
                t = step / 20.0
                x = int(left_start_x + (left_end_x - left_start_x) * t)
                y = int(left_start_y + (left_end_y - left_start_y) * t) + offset
                self.overlay.send_shape(
                    f"checkmark-left-{step}-{offset}",
                    "rect",
                    "#00ff00",
                    "#00ff00",
                    x,
                    y,
                    2,
                    2,
                    self.ttl
                )
        
        # Draw right line (thicker through multiple parallel lines)
        for offset in range(-2, 3):
            for step in range(30):
                t = step / 30.0
                x = int(right_start_x + (right_end_x - right_start_x) * t)
                y = int(right_start_y + (right_end_y - right_start_y) * t) + offset
                self.overlay.send_shape(
                    f"checkmark-right-{step}-{offset}",
                    "rect",
                    "#00ff00",
                    "#00ff00",
                    x,
                    y,
                    2,
                    2,
                    self.ttl
                )
        
        # Don't clear after drawing - checkmark stays visible
    
    def _calculate_deviation(self, current, target):
        """
        Calculates the shortest angular deviation between current and target heading
        
        Returns:
            Deviation in degrees (-180 to +180)
            Positive value = turn right
            Negative value = turn left
        """
        diff = target - current
        
        # Normalize to -180 to +180
        while diff > 180:
            diff -= 360
        while diff < -180:
            diff += 360
            
        return diff
    
    def _calculate_arrow_length(self, deviation):
        """
        Calculates arrow length based on deviation
        
        Args:
            deviation: Absolute value of deviation in degrees
            
        Returns:
            Length in pixels
        """
        # Normalize deviation (0.0 to 1.0)
        normalized = min(abs(deviation) / self.max_deviation, 1.0)
        
        # Interpolate between base and max length
        length = self.arrow_base_length + (self.arrow_max_length - self.arrow_base_length) * normalized
        
        return int(length)
    
    def _draw_left_arrow(self, deviation):
        """
        Draws a left arrow pointing left
        
        Args:
            deviation: Absolute value of deviation in degrees
        """
        length = self._calculate_arrow_length(deviation)
        
        # Calculate arrow position (points from center to the left)
        arrow_start_x = self.center_x
        arrow_end_x = self.center_x - length
        arrow_y = self.center_y
        
        # Arrow shaft (rectangle) - shortened to end at arrow head base
        shaft_height = 4
        head_size = self.arrow_head_size
        shaft_length = length - head_size
        self.overlay.send_shape(
            "heading-arrow-shaft",
            "rect",
            self.arrow_fill,
            self.arrow_fill,
            arrow_end_x + head_size,
            arrow_y - shaft_height // 2,
            shaft_length,
            shaft_height,
            self.ttl
        )
        
        # Arrow head - vector triangle pointing left
        
        # Create vector triangle - capitalize keys to match C# Graphic class
        msg = {
            "id": "heading-arrow-head",
            "shape": "vect",
            "color": self.arrow_color,
            "ttl": self.ttl,
            "vector": [
                {"x": arrow_end_x, "y": arrow_y},
                {"x": arrow_end_x + head_size, "y": arrow_y - head_size // 2},
                {"x": arrow_end_x + head_size, "y": arrow_y + head_size // 2},
                {"x": arrow_end_x, "y": arrow_y}
            ]
        }
        self.overlay.send_raw(msg)
    
    def _draw_right_arrow(self, deviation):
        """
        Draws a right arrow pointing right
        
        Args:
            deviation: Absolute value of deviation in degrees
        """
        length = self._calculate_arrow_length(deviation)
        
        # Calculate arrow position (points from center to the right)
        arrow_start_x = self.center_x
        arrow_end_x = self.center_x + length
        arrow_y = self.center_y
        
        # Arrow shaft (rectangle) - shortened to end at arrow head base
        shaft_height = 4
        head_size = self.arrow_head_size
        shaft_length = length - head_size
        self.overlay.send_shape(
            "heading-arrow-shaft",
            "rect",
            self.arrow_fill,
            self.arrow_fill,
            arrow_start_x,
            arrow_y - shaft_height // 2,
            shaft_length,
            shaft_height,
            self.ttl
        )
        
        # Arrow head - vector triangle pointing right
        
        # Create vector triangle - capitalize keys to match C# Graphic class
        msg = {
            "id": "heading-arrow-head",
            "shape": "vect",
            "color": self.arrow_color,
            "ttl": self.ttl,
            "vector": [
                {"x": arrow_end_x, "y": arrow_y},
                {"x": arrow_end_x - head_size, "y": arrow_y - head_size // 2},
                {"x": arrow_end_x - head_size, "y": arrow_y + head_size // 2},
                {"x": arrow_end_x, "y": arrow_y}
            ]
        }
        self.overlay.send_raw(msg)
    
    def _draw_center_circle(self, deviation=0):
        """
        Draws a fixed-width bar that moves left/right based on deviation
        
        Args:
            deviation: Current deviation in degrees (positive = too far right, negative = too far left)
        """
        # Fine-tuning bar dimensions - fixed width
        width = 50  # Fixed width
        height = 32
        max_offset = 50  # Maximum pixels to move left/right
        rect_offset_y = 16  # Move rectangle down 16px
        
        # Calculate horizontal offset based on deviation
        # Negative deviation (too far left) = move bar left
        # Positive deviation (too far right) = move bar right
        if abs(deviation) > 0:
            offset = int((deviation / self.on_course_threshold) * max_offset)
            offset = max(-max_offset, min(max_offset, offset))  # Clamp to ±50px
        else:
            offset = 0
        
        # Calculate X position (offset moves bar in same direction as deviation)
        x_pos = self.center_x - width // 2 + offset
        
        # Draw green box first
        self.overlay.send_shape(
            "heading-center-rect",
            "rect",
            self.center_color,
            self.center_fill,
            x_pos,
            self.center_y + rect_offset_y - height // 2,
            width,
            height,
            self.ttl
        )
        
        # Draw T-shaped reference line below green box
        t_line_width = 3
        t_horizontal_width = 50
        t_vertical_height = 20
        
        # Bottom of green box
        green_box_bottom = self.center_y + rect_offset_y + height // 2
        
        # Horizontal part of T (50px wide, directly below green box)
        self.overlay.send_shape(
            "heading-t-horizontal",
            "rect",
            "#ffffff",
            "#ffffff",
            self.center_x - t_horizontal_width // 2,
            green_box_bottom,
            t_horizontal_width,
            t_line_width,
            self.ttl
        )
        
        # Vertical part of T (20px tall, from center of horizontal going down)
        self.overlay.send_shape(
            "heading-t-vertical",
            "rect",
            "#ffffff",
            "#ffffff",
            self.center_x - t_line_width // 2,
            green_box_bottom,
            t_line_width,
            t_vertical_height,
            self.ttl
        )

    
    def _clear_arrows(self):
        """
        Clears all arrows, circles and checkmarks by setting TTL to 0
        """
        # Clear arrows
        self.overlay.send_message("heading-arrow-shaft", "", "", 0, 0, 0)
        
        # Clear arrow head (single vector shape)
        self.overlay.send_message("heading-arrow-head", "", "", 0, 0, 0)
        
        # Clear center rectangle
        self.overlay.send_message("heading-center-rect", "", "", 0, 0, 0)
        
        # Clear T-shaped reference line
        self.overlay.send_message("heading-t-horizontal", "", "", 0, 0, 0)
        self.overlay.send_message("heading-t-vertical", "", "", 0, 0, 0)
        
        # Clear checkmark
        for offset in range(-2, 3):
            for step in range(30):
                self.overlay.send_message(f"checkmark-left-{step}-{offset}", "", "", 0, 0, 0)
                self.overlay.send_message(f"checkmark-right-{step}-{offset}", "", "", 0, 0, 0)
    
    def clear(self):
        """
        Clears all graphics
        """
        if not self.overlay:
            return
        self._clear_arrows()


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_left_turn():
    """
    Test: Turn left (from 90° to 45°)
    """
    print("Test: Turn left")
    guidance = HeadingGuidance()
    guidance.update(current_heading=90, target_heading=45)
    print("Showing left arrow for 3 seconds...")
    import time
    time.sleep(3)
    guidance.clear()


def test_right_turn():
    """
    Test: Turn right (from 45° to 90°)
    """
    print("Test: Turn right")
    guidance = HeadingGuidance()
    guidance.update(current_heading=45, target_heading=90)
    print("Showing right arrow for 3 seconds...")
    import time
    time.sleep(3)
    guidance.clear()


def test_on_course():
    """
    Test: On course (90° to 91°)
    """
    print("Test: On course")
    guidance = HeadingGuidance()
    guidance.update(current_heading=90, target_heading=91)
    print("Showing green circle for 3 seconds...")
    import time
    time.sleep(3)
    guidance.clear()


def test_animation():
    """
    Test: Animated demonstration from 0° to 90°
    """
    print("Test: Animated demonstration")
    print("Turning from 0° to 90° (right)")
    guidance = HeadingGuidance()
    import time
    
    for current in range(0, 91, 2):
        guidance.update(current_heading=current, target_heading=90)
        time.sleep(0.1)
    
    print("Done! Clearing...")
    time.sleep(1)
    guidance.clear()


if __name__ == "__main__":
    print("=" * 60)
    print("HEADING GUIDANCE TEST")
    print("=" * 60)
    print("\nAvailable tests:")
    print("1. Left arrow")
    print("2. Right arrow")
    print("3. On course (green circle)")
    print("4. Animated demonstration")
    print()
    
    choice = input("Choose test (1-4) or press Enter for all: ")
    
    if choice == "1":
        test_left_turn()
    elif choice == "2":
        test_right_turn()
    elif choice == "3":
        test_on_course()
    elif choice == "4":
        test_animation()
    else:
        print("\nRunning all tests...")
        test_right_turn()
        print()
        test_left_turn()
        print()
        test_on_course()
        print()
        test_animation()
    
    print("\nDone!")
