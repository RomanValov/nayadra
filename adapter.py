import threading
import buyokgl
import kosherd

class Adapter:
    def __init__(self, (xtsz, ytsz), datapath):
        self.bounds = (xtsz, ytsz)
        self.length = xtsz * ytsz * 4
        self.glbufs = buyokgl.pixel_buffer(self.length)
        self.buffer = self.glbufs.bufs

        self.kosher = kosherd.ComputeUnit(self.bounds, datapath, self.buffer, True)
        self.engine = self.kosher.vengine()

        self.impulse((0.0, 0.0), 0.0, True)

    def impulse(self, point, radius, init=False):
        if init or int(self.tx) != int(point[0]) or int(self.ty) != int(point[1]):
            self.tx, self.ty = point
            self.kosher.shifted()
        self.radius = radius

    def sendkey(self, key):
        self.kosher.command(key)

    def reclaim(self, kosher, func):
        self.kosher.preiter()

        if kosher:
            iteration = self.kosher.iterate(self.tx, self.ty, self.radius)
            self.glbufs.bind(func=func)

        return self.kosher.inspect()

def benchmark(fps=60):
    pass

