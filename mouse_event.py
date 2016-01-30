MOVE = 'move'
WHEEL = 'wheel'
LEFT = 'left'
RIGHT = 'right'
MIDDLE = 'middle'
X = 'x'
X2 = 'x2'

UP = 'up'
DOWN = 'down'
DOUBLE = 'double'
HORIZONTAL = 'horizontal'

class MouseEvent(object):
	def __init__(self, event_type, arg='', x=0, y=0, delta_wheel=0):
		self.event_type = event_type
		self.arg = arg
		self.x = x
		self.y = y
		self.delta_wheel = delta_wheel

	def __repr__(self):
		name = self.event_type
		if self.arg:
			name += ' '+ self.arg
		return 'MouseEvent({} x:{} y:{} wheel:{})'.format(name, self.x, self.y, self.delta_wheel)