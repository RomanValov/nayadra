ORIGIN, TARGET = False, True

class Gradient:
    nuance =[
                [ 0x1F, 0x1F, 0x1F, 0x00 ], [ 0x00, 0x00, 0x00, 0x00 ], #0 
                [ 0x7F, 0x7F, 0x00, 0x00 ], [ 0x3F, 0x3F, 0x00, 0x00 ], #1
                [ 0x7F, 0x3F, 0x00, 0x00 ], [ 0x3F, 0x1F, 0x00, 0x00 ], #2
                [ 0x7F, 0x00, 0x00, 0x00 ], [ 0x3F, 0x00, 0x00, 0x00 ], #3
                [ 0x7F, 0x00, 0x3F, 0x00 ], [ 0x3F, 0x00, 0x1F, 0x00 ], #4
                [ 0x7F, 0x00, 0x7F, 0x00 ], [ 0x3F, 0x00, 0x3F, 0x00 ], #5
                [ 0x3F, 0x00, 0x7F, 0x00 ], [ 0x1F, 0x00, 0x3F, 0x00 ], #6
                [ 0x00, 0x00, 0x7F, 0x00 ], [ 0x00, 0x00, 0x3F, 0x00 ], #7
                [ 0x00, 0x3F, 0x7F, 0x00 ], [ 0x00, 0x1F, 0x3F, 0x00 ], #8
                [ 0x00, 0x7F, 0x7F, 0x00 ], [ 0x00, 0x3F, 0x3F, 0x00 ], #9
                [ 0x00, 0x7F, 0x3F, 0x00 ], [ 0x00, 0x3F, 0x1F, 0x00 ], #A
                [ 0x00, 0x7F, 0x00, 0x00 ], [ 0x00, 0x3F, 0x00, 0x00 ], #B
                [ 0x3F, 0x7F, 0x00, 0x00 ], [ 0x1F, 0x3F, 0x00, 0x00 ], #C

                [ 0x3F, 0x3F, 0x3F, 0x00 ], [ 0x1F, 0x1F, 0x1F, 0x00 ], #D
                [ 0x5F, 0x5F, 0x5F, 0x00 ], [ 0x3F, 0x3F, 0x3F, 0x00 ], #E
                [ 0x7F, 0x7F, 0x7F, 0x00 ], [ 0x5F, 0x5F, 0x5F, 0x00 ], #F
            ]

    def __init__(self, nitems, nindex):
        self.nitems = nitems
        self.nbytes = nitems * 4
        self.offset = nindex * self.nbytes
        self.params = {}

        self.colour = [ [ 0 ] * self.nbytes for p in [ ORIGIN, TARGET ] ]

    def useparam(self, usekey, usedef):
        result = self.params[usekey] = self.params.get(usekey, usedef)
        return result

    def gen_sequence(self, indice=None, **params):
        if not indice: indice = range(0x10)
        output = list(( 0, 0, 0, 0 ) * self.nitems)
        for n in xrange(self.nitems):
            output[4*n:4*n+4] = self.nuance[indice[n % len(indice)]]
        return output

    def gen_gradient(self, indice, **params):
        output = list(( 0, 0, 0, 0 ) * self.nitems)
        pieces = len(indice) - 1
        for r in xrange(pieces):
            prev, next = indice[pieces - r], indice[pieces - r - 1]
            since, until = r * self.nitems / pieces, (r + 1) * self.nitems / pieces
            delta = until - since
            for n in xrange(delta):
                pos = (since + n) * 4
                for i in xrange(4):
                    output[pos+i] = (self.nuance[prev][i] * (delta - n) + self.nuance[next][i] * n) / delta
        return output

    def gen_blending(self, master=(0x00, 0x00, 0x00, 0x00), alpha0=(0x00,0x00), alpha1=(0xFF,0xFF), **params):
        output = list(master * self.nitems)
        point0, point1 = 0xFF - alpha0[0], 0xFF - alpha1[0]
        alpha0, alpha1 = (point0, alpha0[1]), (point1, alpha1[1])
        amin, amax = (point0 < point1) and (alpha0, alpha1) or (alpha1, alpha0)

        for n in xrange(0, amin[0]):
            output[4*n+3] = amin[1]

        for n in xrange(amin[0], amax[0]):
            output[4*n+3] = amin[1] + (amax[1] - amin[1]) * (n - amin[0]) / (amax[0] - amin[0])

        for n in xrange(amax[0], self.nitems):
            output[4*n+3] = amax[1]

        return output

    def gen_constant(self, indice, **params):
        return self.nuance[indice] * self.nitems

    def generate(self, **params):
        self.params = params and params or self.params
        design = self.useparam('design', 'constant')
        return Gradient.__dict__['gen_' + design](self, **self.params)

class ChromaDB:
    def __init__(self, nlines, nitems, blends):
        self.nlines = nlines
        self.blends = blends

        self.data = [ Gradient(nitems, nindex) for nindex in xrange(nlines) ]
        self.size = sum([ self.data[nindex].nbytes for nindex in xrange(nlines) ])

        self.flip = [ -0x01 ] * self.nlines
        self.dirt = [ False ] * self.nlines

    def define(self, nindex, **params):
        if self.flip[nindex] > 0: return
        self.data[nindex].colour[TARGET][:] = self.data[nindex].generate(**params)
        self.flip[nindex] = not self.flip[nindex] and self.blends or -self.flip[nindex]
        self.dirt[nindex] = True

    def update(self, nindex, clears=True):
        coeffs = self.flip[nindex], self.blends - self.flip[nindex]

        output = [ 0 ] * self.data[nindex].nbytes
        for i in xrange(self.data[nindex].nbytes):
            aparts = self.data[nindex].colour[ORIGIN][i] * coeffs[ORIGIN], self.data[nindex].colour[TARGET][i] * coeffs[TARGET]
            output[i] = (aparts[ORIGIN] + aparts[TARGET]) / self.blends

        return output

    def smooth(self):
        chlist = []
        for nindex in xrange(self.nlines):
            if self.flip[nindex]:
                self.flip[nindex] -= 1
                chlist += [ (nindex, self.data[nindex].offset) ]
            elif self.dirt[nindex]:
                self.data[nindex].colour[ORIGIN][:] = self.data[nindex].colour[TARGET][:]
                self.dirt[nindex] = False
        return chlist

class ChromaTR:
    def __init__(self, nitems=0x100, blends=0x20):
        self.nitems = nitems
        self.blends = blends
        self.buffer = {}
        self.select = {}

    def create(self, bufkey, nlines):
        self.buffer[bufkey] = ChromaDB(nlines, self.nitems, self.blends)
        self.select[bufkey] = 0
        return self.buffer[bufkey].size

    def delete(self, bufkey):
        del self.buffer[bufkey]
        del self.select[bufkey]

    def switch(self, bufkey, nindex=None, dindex=0, nlimit=0):
        if nlimit <= 0 or nlimit > self.buffer[bufkey].nlines:
            nlimit = self.buffer[bufkey].nlines
        if nindex is None:
            nindex = self.select[bufkey] + dindex

        self.select[bufkey] = nindex % nlimit
        return self

    def change(self, bufkey, **params):
        self.buffer[bufkey].define(self.select[bufkey], **params)
        return self

    def update(self, bufkey, nindex):
        return self.buffer[bufkey].update(nindex)

    def smooth(self):
        chlist = []
        for bufkey in self.buffer.keys():
            chlist += [ (bufkey, nindex, offset) for nindex, offset in self.buffer[bufkey].smooth() ]
        return chlist
