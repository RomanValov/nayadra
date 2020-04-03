#define	GX	get_global_id(0)
#define GY	get_global_id(1)
#define SX	get_global_size(0)
#define SY	get_global_size(1)
#define LX	get_local_id(0)
#define LY	get_local_id(1)
#define CX	get_local_size(0)
#define CY	get_local_size(1)

#define NN	0x08
#define NS	0x10

struct impact {
	unsigned char	step;
	unsigned char	type;
	unsigned char	rank;
	unsigned char	keep;
	unsigned int	impx;
	unsigned int	impy;
};

struct points {
	uchar4 object;
	uchar4 neighs[NN];
};

__constant char2 deltas[NN] = {	(char2)(-1,-1),	(char2)( 0,-1),	(char2)(+1,-1),
				(char2)(-1, 0),			(char2)(+1, 0),
				(char2)(-1,+1),	(char2)( 0,+1), (char2)(+1, +1)	};

struct points dump_points(__global uchar4 *buffer, unsigned int indice)
{
	struct points points;

	points.object = buffer[indice];
	for (int i = 0; i < NN; i++) {
		unsigned int nindex = ((GX + deltas[i].x) & (SX - 1)) + (SX * ((GY + deltas[i].y) & (SY - 1)));
		points.neighs[i] = buffer[nindex];
	}

	return points;
}

struct recipe {
	unsigned short	around;		// bit-mask of neighbours to count
	unsigned char	rarity;		// minimum tries to make a reaction
	unsigned char	forced;		// mandatory neighbour to count
	unsigned char	effect[12];	// for 0-8 effect if number neighbours
};

unsigned int take_recipe(const struct impact impact, unsigned int random)
{
	unsigned int  basedx = abs_diff(impact.impx, (unsigned int)GX);
	unsigned int  basedy = abs_diff(impact.impy, (unsigned int)GY);
	unsigned int  realdx = min(basedx, (unsigned int)SX - basedx);
	unsigned int  realdy = min(basedy, (unsigned int)SY - basedy);

	unsigned int  radius = realdx*realdx + realdy*realdy;

	unsigned int  sparse = (radius < impact.rank*impact.rank) ? impact.type : 0;

	unsigned int  offset = (random <= impact.keep) ? (sparse << 4) : 0;

	return offset;
}

uchar4 make_behave(__constant struct recipe *script, unsigned int offset, const struct points points)
{
	unsigned int  origin = points.object.x;
	struct recipe recipe = script[offset + origin];

	unsigned int  actual = 0;
	unsigned int  mandat = !recipe.forced;
	for (int i = 0; i < NN; i++) {
		unsigned int neighs = points.neighs[i].x;
		unsigned int nbmask = (1 << neighs);
		actual += (bool)(nbmask  & recipe.around);
		mandat += (bool)(neighs == recipe.forced);
	}

	unsigned int  result = recipe.effect[actual];

	unsigned int  change = (origin != result) && mandat;
	unsigned int  strike = (recipe.rarity <= (0xFF - points.object.w));

	unsigned int  future = (points.object.w != 0x00) && (change || !recipe.rarity);

	unsigned int  assign = (change && strike) ? result : origin;
	unsigned int  regenr = (change && strike) ?  0xFF  : points.object.w - future;

	points.object.x = assign;

	points.object.z = actual;
	points.object.w = regenr;

	return points.object;
}

unsigned int calc_random(__global unsigned int *states, unsigned int indice, unsigned int cycles)
{
	unsigned int buffer = 0x00000000;
	unsigned int regist = states[indice];
	unsigned int usebit = regist & 1;

	for (int i = 0; i < cycles; i++) {
		regist = (regist >> 1) ^ (usebit ? 0xD0000001 : 0);
		usebit = regist & 1;
		buffer = (buffer << 1) | usebit;
	}

	states[indice] = regist;

	return buffer;
}

unsigned int calc_hashed(uchar4 source)
{
	unsigned int hash = 0;
	unsigned char bts[] = { source.x, source.y, source.z, source.w };

	for (int i = 0; i < 4; ++i) { hash += bts[i]; hash += (hash << 10); hash ^= (hash >> 6); }

	hash += (hash << 3); hash ^= (hash >> 11); hash += (hash << 15);

	return hash;
}

__kernel void seedinit(__global uchar4 *buffer, __global unsigned int *states, unsigned int seed)
{
	unsigned int indice = GX + (SX * GY);
	unsigned int undice = (SX * SY) - indice;

	states[indice] = calc_hashed(as_uchar4(seed ^ undice));

	unsigned int random = calc_random(states, indice, 8);

	buffer[indice] = (uchar4)(random & (NS - 1), 0x00, 0x00, 0xFF);
}

__kernel void niterate(
				__global uchar4			*srcbuf,
				__global uchar4			*dstbuf,
				__global unsigned int		*states,
				__constant struct recipe	*script,
				const struct impact		impact)
{
	unsigned int  indice = GX + (SX * GY);
	unsigned int  random = calc_random(states, indice, 8);
	struct points points = dump_points(srcbuf, indice);
	unsigned int  offset = take_recipe(impact, random);
	const uchar4  object = make_behave(script, offset, points);

	dstbuf[indice] = object;
}

const uchar4 find_colour(__global uchar4 *buffer, __constant uchar4 *scheme, unsigned int indice)
{
	const uchar4 object = buffer[indice];
	unsigned int offset = (object.x << 8) + object.w;
	const uchar4 colour = scheme[offset];

	colour.w = object.z;

	return colour;
}

struct factor {
	unsigned char smooth;
	unsigned char sorder;
	unsigned char pad0;
	unsigned char pad1;
};

const uchar4 xlat_colour(const uchar4 wasobj, const uchar4 nowobj, const struct factor factor)
{
	unsigned char dither = (1 << factor.sorder) - factor.smooth;
	unsigned char x = ((unsigned int)wasobj.x * dither + (unsigned int)nowobj.x * factor.smooth) >> factor.sorder;
	unsigned char y = ((unsigned int)wasobj.y * dither + (unsigned int)nowobj.y * factor.smooth) >> factor.sorder;
	unsigned char z = ((unsigned int)wasobj.z * dither + (unsigned int)nowobj.z * factor.smooth) >> factor.sorder;
	unsigned char w = nowobj.w;

	return (uchar4)(x, y, z, w);
}

__kernel void colorize(
				__global uchar4			*wasbuf,
				__global uchar4			*nowbuf,
				__global uchar4			*output,
				__constant uchar4		*scheme,
				const struct factor		factor)
{
	unsigned int  indice = GX + (SX * GY);
	const uchar4  wasobj = find_colour(wasbuf, scheme, indice);
	const uchar4  nowobj = find_colour(nowbuf, scheme, indice);
	const uchar4  object = xlat_colour(wasobj, nowobj, factor);

	output[indice] = object;
}
