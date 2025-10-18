from math import radians, degrees, acos, sin, cos

from build123d import Vector, ThreePointArc, Line, Face, extrude, Wire

from sava.csg.build123d.common.geometry import shift_vector, create_vector


class Pencil:
    def __init__(self, start: Vector = Vector(0, 0)):
        self.curves = []
        self.start = start
        self.location = start

    def checkDestination(self, destination: Vector) -> Vector:
        tolerance = 1e-7
        return self.start if (destination - self.start).length < tolerance else destination


    def arcWithRadius(self, radius: float, centreAngle: float, arcDegrees: float):
        centre = shift_vector(self.location, radius, centreAngle)
        degreesDestinationFromCentre = ((arcDegrees + centreAngle + 180) % 360)
        degreesMiddleFromCentre = ((arcDegrees / 2 + centreAngle + 180) % 360)
        destination = self.checkDestination(shift_vector(centre, radius, degreesDestinationFromCentre))
        middle = shift_vector(centre, radius, degreesMiddleFromCentre)
        return self.arcAbs(middle, destination)

    def arcAbs(self, midpoint: Vector, destination: Vector):
        self.curves.append(ThreePointArc(self.location, midpoint, destination))
        self.location = destination
        return self

    def arcFromStart(self, midpointVector: Vector, destinationVector: Vector):
        return self.arcAbs(self.start + midpointVector, self.start + destinationVector)

    def arc(self, midpointVector: Vector, destinationVector: Vector):
        return self.arcAbs(self.location + midpointVector, self.location + destinationVector)

    def arcWithAngleToCentre(self, angleToCentre: float, destinationVector: Vector):
        return self.arcWithCentreDirection(create_vector(1, angleToCentre), destinationVector)

    def arcWithAngleToCentreAbs(self, angleToCentre: float, destination: Vector):
        return self.arcWithCentreDirectionAbs(create_vector(1, angleToCentre), destination)

    def arcWithCentreDirection(self, centreDirection: Vector, destinationVector: Vector):
        # Create copies and normalize to preserve original vectors
        # Calculate an angle between vectors using dot product
        dotProduct = Vector(centreDirection).normalized().dot(Vector(destinationVector).normalized())
        # Clamp dot product to [-1, 1] to handle floating point precision errors
        dotProduct = max(-1.0, min(1.0, dotProduct))
        a = degrees(acos(dotProduct))

        return self.arcWithDestination(destinationVector, 2 * a - 180)

    def arcWithCentreDirectionAbs(self, centreDirection: Vector, destination: Vector):
        return self.arcWithCentreDirection(centreDirection, destination - self.location)

    # create arc with specific destination and angle measure
    def arcWithDestinationAbs(self, destination: Vector, angle: float):
        # Calculate chord (straight line distance between start and end)
        destination = self.checkDestination(destination)
        chord = destination - self.location
        chordLength = chord.length
        
        chordMidpoint = (self.location + destination) / 2
        
        # Calculate radius using chord length and arc angle
        # For an arc with angle θ, radius = chord_length / (2 * sin(θ/2))
        halfAngleRad = radians(abs(angle) / 2)
        if halfAngleRad == 0:
            return self.jumpTo(destination)  # Straight line for 0° angle
            
        radius = chordLength / (2 * sin(halfAngleRad))
        
        # Distance from chord midpoint to arc center
        centerDistance = radius * cos(halfAngleRad)
        
        # Direction perpendicular to chord (for center calculation)
        # Positive angle goes counter-clockwise (left side of chord)
        perpDirection = Vector(-chord.Y, chord.X).normalized()
        if angle < 0:
            perpDirection = -perpDirection  # Clockwise for negative angles
            
        center = chordMidpoint + perpDirection * centerDistance
        
        # Calculate midpoint of arc for Part.Arc
        # The arc midpoint is on the arc, perpendicular to the chord at center
        arcMidpoint = center - perpDirection * radius
        
        return self.arcAbs(arcMidpoint, destination)

    # create arc with specific destination and angle measure
    def arcWithDestinationFromStart(self, destinationVector: Vector, angle: float):
        return self.arcWithDestinationAbs(destinationVector + self.start, angle)

    # create arc with specific destination and angle measure
    def arcWithDestination(self, destinationVector: Vector, angle: float):
        return self.arcWithDestinationAbs(destinationVector + self.location, angle)

    def jumpTo(self, absDestination: Vector):
        absDestination = self.checkDestination(absDestination)
        self.curves.append(Line(self.location, absDestination))
        self.location = absDestination
        return self

    def jump(self, destination: Vector):
        return self.jumpTo(destination + self.location)

    def jumpFromStart(self, destination: Vector):
        return self.jumpTo(destination + self.start)

    def draw(self, length: float, angle: float):
        absDestination = shift_vector(self.location, length, angle)
        return self.jumpTo(absDestination)

    def up(self, length: float):
        return self.draw(length, 0)

    def left(self, length: float):
        return self.draw(length, 90)

    def down(self, length: float):
        return self.draw(length, 180)

    def right(self, length: float):
        return self.draw(length, -90)

    def extrudeCustom(self, vector: Vector):
        wire = self.createWire()
        return extrude(Face(wire), vector.length, vector)

    def extrude(self, height: float):
        return self.extrudeCustom(Vector(0, 0, height))

    def extrudeX(self, height: float, transpose: Vector = Vector()):
        solid = self.extrude(height)
        solid.orientation = (90, 90, 0)
        solid.position = transpose
        return solid

    def extrudeY(self, height: float, transpose: Vector = Vector()):
        solid = self.extrude(height)
        solid.orientation = (90, 180, 0)
        solid.position = transpose
        return solid

    def createWire(self):
        curves = self.curves.copy()
        if self.location != self.start:
            curves.append(Line(self.location, self.start))

        return Wire(curves)
