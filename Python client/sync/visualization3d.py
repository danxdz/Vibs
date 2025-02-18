import numpy as np
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math

# Constants
ROTATION_SCALE = 0.000001  # Adjust rotation scale
SMOOTHING_FACTOR = 0.95  # Low-pass filter for smoothing
ACCEL_SCALE = 0.01  # Acceleration scale

# Global variables
cube_rotation = [0, 0, 0]
prev_rotation = [0, 0, 0]
cube_position = [0, 0, 0]

def update_gyro_data(gyro_data):
    """Update cube rotation with smoothing & drift correction."""
    global cube_rotation, prev_rotation

    # Apply smoothing filter
    smoothed_data = [
        prev_rotation[i] * SMOOTHING_FACTOR + gyro_data[i] * (1 - SMOOTHING_FACTOR)
        for i in range(3)
    ]

    # Apply scaled rotation
    cube_rotation[0] += smoothed_data[0] * ROTATION_SCALE
    cube_rotation[1] += smoothed_data[1] * ROTATION_SCALE
    cube_rotation[2] += smoothed_data[2] * ROTATION_SCALE

    # Store the previous values
    prev_rotation = smoothed_data

def update_accel_data(acceleration_data):
    """Update second cube's position based on acceleration."""
    global cube_position

    # Convert acceleration to displacement
    cube_position[0] += acceleration_data[0] * ACCEL_SCALE
    cube_position[1] += acceleration_data[1] * ACCEL_SCALE
    cube_position[2] += acceleration_data[2] * ACCEL_SCALE

    # Smooth out the movement for visual effect (sway)
    cube_position[0] = math.sin(cube_position[0])
    cube_position[1] = math.cos(cube_position[1])

def init_gl():
    """OpenGL initialization."""
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    glLightfv(GL_LIGHT0, GL_POSITION, (5, 5, 5, 1))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (1, 1, 1, 1))

def draw_axes():
    """Draw the X, Y, Z coordinate axes."""
    glBegin(GL_LINES)
    glColor3f(1, 0, 0); glVertex3f(0, 0, 0); glVertex3f(2, 0, 0)  # X - Red
    glColor3f(0, 1, 0); glVertex3f(0, 0, 0); glVertex3f(0, 2, 0)  # Y - Green
    glColor3f(0, 0, 1); glVertex3f(0, 0, 0); glVertex3f(0, 0, 2)  # Z - Blue
    glEnd()

def draw_cube(color):
    """Draw a 3D cube with dynamic colors."""
    glColor3f(*color)  # Color based on input
    glBegin(GL_QUADS)

    # Define the six faces of the cube
    faces = [
        ([1, 0, 0], [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]),  # Front - Red
        ([0, 1, 0], [-1, -1, -1], [-1, 1, -1], [1, 1, -1], [1, -1, -1]),  # Back - Green
        ([0, 0, 1], [-1, 1, -1], [-1, 1, 1], [1, 1, 1], [1, 1, -1]),  # Top - Blue
        ([1, 1, 0], [-1, -1, -1], [1, -1, -1], [1, -1, 1], [-1, -1, 1]),  # Bottom - Yellow
        ([1, 0, 1], [1, -1, -1], [1, 1, -1], [1, 1, 1], [1, -1, 1]),  # Right - Magenta
        ([0, 1, 1], [-1, -1, -1], [-1, -1, 1], [-1, 1, 1], [-1, 1, -1])  # Left - Cyan
    ]

    for color, v1, v2, v3, v4 in faces:
        glVertex3f(*v1)
        glVertex3f(*v2)
        glVertex3f(*v3)
        glVertex3f(*v4)

    glEnd()

def display():
    """Render the OpenGL scene."""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    gluLookAt(4, 4, 4, 0, 0, 0, 0, 1, 0)

    draw_axes()

    # Rotate first cube based on gyro
    glPushMatrix()
    glRotatef(cube_rotation[0], 1, 0, 0)
    glRotatef(cube_rotation[1], 0, 1, 0)
    glRotatef(cube_rotation[2], 0, 0, 1)
    draw_cube([1, 0, 0])  # Red cube for rotation
    glPopMatrix()

    # Move second cube based on acceleration, and add sine wave for movement
    glPushMatrix()
    glTranslatef(cube_position[0], cube_position[1], cube_position[2])
    draw_cube([0, 1, 0])  # Green cube for translation
    glPopMatrix()
    
    glutSwapBuffers()

def reshape(width, height):
    """Handle window resizing."""
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, width / height, 0.1, 50.0)
    glMatrixMode(GL_MODELVIEW)

def keyboard(key, x, y):
    """Handle keyboard inputs."""
    global cube_rotation, cube_position
    if key == b'q':
        print("🚪 Exiting visualization.")
        glutLeaveMainLoop()
    elif key == b'r':
        cube_rotation = [0, 0, 0]
        cube_position = [0, 0, 0]  # Reset second cube position

def start_visualization3d():
    """Start the OpenGL visualization."""
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(800, 600)
    glutCreateWindow(b"ESP32 3D Cube")

    init_gl()

    glutDisplayFunc(display)
    glutIdleFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)

    print("\n🎮 Controls:")
    print("  R - Reset orientation and position")
    print("  Q - Quit")

    glutMainLoop()

