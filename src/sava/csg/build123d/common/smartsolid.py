from build123d import Vector


class SmartSolid:
    def __init__(self, length: float, width: float, height: float, x: float = 0, y: float = 0, z: float = 0):
        self.length = length
        self.width = width
        self.height = height

        self.solid = None

        self.x = x
        self.y = y
        self.z = z

        self.x_to = x + length
        self.y_to = x + width
        self.z_to = z + height

    @property
    def base(self):
        return Vector(self.x, self.y, self.z)

    def translate_vector(self, vector: Vector):
        return self.translate(vector.X, vector.Y, vector.Z)

    def translate(self, x: float, y: float = 0, z: float = 0) -> 'SmartSolid':
        self.x += x
        self.y += y
        self.z += z

        self.x_to = self.x + self.length
        self.y_to = self.y + self.width
        self.z_to = self.z + self.height
        
        if self.solid:
            self.solid = self.solid.translate(Vector(x, y, z))
        return self
