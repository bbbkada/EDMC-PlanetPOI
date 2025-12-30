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
import overlay  # Använd samma overlay-instans som resten av pluginen


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
            self.overlay = overlay.this.overlay
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
        
        self.ttl = 5  # Time to live in seconds - longer TTL reduces flickering
    
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
        
        # If almost on course - show circle in center
        if abs(deviation) <= self.on_course_threshold:
            self._draw_center_circle()
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
        
        # Arrow shaft (rectangle)
        shaft_height = 4
        self.overlay.send_shape(
            "heading-arrow-shaft",
            "rect",
            self.arrow_fill,
            self.arrow_fill,
            arrow_end_x,
            arrow_y - shaft_height // 2,
            length,
            shaft_height,
            self.ttl
        )
        
        # Arrow head - filled triangle with denser lines for smoother appearance
        head_size = self.arrow_head_size
        
        # Draw arrow head as multiple horizontal lines for smooth filling
        for i in range(head_size // 2 + 1):
            # Calculate line width based on position
            line_y_top = arrow_y - i
            line_y_bottom = arrow_y + i
            line_x_start = arrow_end_x + (i * 2)
            
            if i == 0:
                # Draw tip as a small rectangle
                self.overlay.send_shape(
                    f"heading-arrow-head-{i}",
                    "rect",
                    self.arrow_fill,
                    self.arrow_fill,
                    arrow_end_x,
                    arrow_y,
                    2,
                    1,
                    self.ttl
                )
            else:
                # Draw horizontal line to fill triangle
                self.overlay.send_shape(
                    f"heading-arrow-head-{i}",
                    "rect",
                    self.arrow_fill,
                    self.arrow_fill,
                    line_x_start,
                    line_y_top,
                    1,
                    (line_y_bottom - line_y_top + 1),
                    self.ttl
                )
    
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
        
        # Arrow shaft (rectangle)
        shaft_height = 4
        self.overlay.send_shape(
            "heading-arrow-shaft",
            "rect",
            self.arrow_fill,
            self.arrow_fill,
            arrow_start_x,
            arrow_y - shaft_height // 2,
            length,
            shaft_height,
            self.ttl
        )
        
        # Arrow head - filled triangle with denser lines for smoother appearance
        head_size = self.arrow_head_size
        
        # Draw arrow head as multiple horizontal lines for smooth filling
        for i in range(head_size // 2 + 1):
            # Calculate line width based on position
            line_y_top = arrow_y - i
            line_y_bottom = arrow_y + i
            line_x_start = arrow_end_x - (i * 2)
            
            if i == 0:
                # Draw tip as a small rectangle
                self.overlay.send_shape(
                    f"heading-arrow-head-{i}",
                    "rect",
                    self.arrow_fill,
                    self.arrow_fill,
                    arrow_end_x - 2,
                    arrow_y,
                    2,
                    1,
                    self.ttl
                )
            else:
                # Draw horizontal line to fill triangle
                self.overlay.send_shape(
                    f"heading-arrow-head-{i}",
                    "rect",
                    self.arrow_fill,
                    self.arrow_fill,
                    line_x_start,
                    line_y_top,
                    1,
                    (line_y_bottom - line_y_top + 1),
                    self.ttl
                )
    
    def _draw_center_circle(self):
        """
        Draws a filled circle in center when on course
        """
        radius = 12  # Reduced from 20
        
        # Draw circle using many small rectangles for smooth filling
        # Draw from center outwards in concentric circles
        for r in range(radius + 1):
            # Calculate number of points based on radius for even coverage
            steps = max(8, int(2 * math.pi * r))
            
            for angle in range(0, 360, max(1, 360 // steps)):
                rad = math.radians(angle)
                x = self.center_x + int(r * math.cos(rad))
                y = self.center_y + int(r * math.sin(rad))
                
                # Draw a pixel
                self.overlay.send_shape(
                    f"heading-center-fill-{r}-{angle}",
                    "rect",
                    self.center_fill,
                    self.center_fill,
                    x,
                    y,
                    1,
                    1,
                    self.ttl
                )
    
    def _clear_arrows(self):
        """
        Clears all arrows, circles and checkmarks by setting TTL to 0
        """
        # Clear arrows
        self.overlay.send_message("heading-arrow-shaft", "", "", 0, 0, 0)
        
        # Clear arrow heads
        for i in range(self.arrow_head_size // 2 + 1):
            self.overlay.send_message(f"heading-arrow-head-{i}", "", "", 0, 0, 0)
        
        # Clear circle (concentric circles) - must match exactly how it's drawn
        radius = 12
        for r in range(radius + 1):
            steps = max(8, int(2 * math.pi * r))
            for angle in range(0, 360, max(1, 360 // steps)):
                self.overlay.send_message(f"heading-center-fill-{r}-{angle}", "", "", 0, 0, 0)
        
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
