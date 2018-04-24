#BACKEND = "xcb"
BACKEND = "tkinter"
#BACKEND = "opengl"
#BACKEND = "sdl"

MAINLOOP = "tkinter"
# Only for opengl backend. Ignores frequencies.
#MAINLOOP = "glut"

LOG_EVENTS = True
# Wait time in ms. Larger = slower.
POLL_FREQUENCY = 60
POLL_FREQUENCY = 30
#POLL_FREQUENCY = 10
#DRAW_FREQUENCY = 240
#DRAW_FREQUENCY = 120
DRAW_FREQUENCY = 20
# Always draw when an event is bpolled
DRAW_FREQUENCY = None
GRID = 20
