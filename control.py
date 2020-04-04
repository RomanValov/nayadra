import drawing
import compute

class Control:
    def __init__(self, (xtsz, ytsz), datapath):
        self.bounds = (xtsz, ytsz)
        self.length = xtsz * ytsz * 4
        self.glbufs = drawing.pixel_buffer(self.length)
        self.buffer = self.glbufs.bufs

        self.engine = compute.ComputeUnit(self.bounds, datapath, self.buffer, True)
        self.banner = self.engine.vengine()

        self.impulse((0.0, 0.0), 0.0, True)

    def impulse(self, point, radius, init=False):
        if init or int(self.tx) != int(point[0]) or int(self.ty) != int(point[1]):
            self.tx, self.ty = point
            self.engine.shifted()
        self.radius = radius

    def handled(self):
        return self.engine.handled()

    def reclaim(self, rotate, func):
        self.engine.preiter()

        if rotate:
            iteration = self.engine.iterate(self.tx, self.ty, self.radius)
            self.glbufs.bind(func=func)

        return self.engine.inspect()

def benchmark(fps=60):
    pass

