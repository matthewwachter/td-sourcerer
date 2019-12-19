
// License: MIT
// glsl transitions ported by Matthew Wachter from the two sources listed below (Jeffers / gl-transitions).
// please visit the web page or see the comments next to each transition function for more info.

// Jeffers - https://forum.derivative.ca/t/transition-component/1859
// gl-transitions - https://gl-transitions.com/


#define PI 3.14159265358979323846
uniform float progress;
uniform int mode;


// Common
uniform float seed;

// LINEAR BLUR
uniform float linblur_intensity;
uniform int linblur_passes;

// COLOR BURN
uniform vec3 colorburn_color;

// RIPPLE
uniform float ripple_amplitude;
uniform float ripple_speed;
uniform float ripple_frequency;
uniform vec2 ripple_center;

// RANDOM SQUARES
uniform float randsquares_smoothness;
uniform ivec2 randsquares_size;

// MORPH1
uniform float morph1_strength;

// COLOR DISTANCE
uniform float colordist_power;

// PERLIN

uniform float perlin_scale;
uniform float perlin_smoothness;

// PIXELIZE
uniform ivec2 pixelize_smin;
uniform int pixelize_steps;

// CIRCLE REVEAL
uniform float creveal_fuzzy;

// BLINDS
uniform int blinds;


// MAXIMUM
uniform float max_dist;
uniform float max_fadeindist;


// RADIAL BLUR
uniform vec2 rblur_center;

// SWAP
uniform float swap_perspective;
uniform float swap_depth;
const float swap_reflection = .3;

// CUBE
uniform float cube_persp;
uniform float cube_unzoom;
const float cube_reflection = .3;
const float cube_floating = .5;

// FadeColor

uniform vec4 fade_color;

// Slide
uniform vec2 slide_trans;

// HELPER FUNCTIONS

vec4 getFromColor(vec2 uv){ return texture(sTD2DInputs[0], uv); }
vec4 getToColor(vec2 uv){ return texture(sTD2DInputs[1], uv); }

vec4 getFromColorBias(vec2 uv, float bias){ return texture(sTD2DInputs[0], uv, bias); }
vec4 getToColorBias(vec2 uv, float bias){ return texture(sTD2DInputs[1], uv, bias); }

float rand (vec2 co) { return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453); }

vec2 offset(float progress, float x, float theta) {
  float phase = progress*progress + progress + theta;
  float shifty = 0.03*progress*cos(10.0*(progress+x));
  return vec2(0, shifty);
}

// http://byteblacksmith.com/improvements-to-the-canonical-one-liner-glsl-rand-for-opengl-es-2-0/
float random(vec2 co)
{
	highp float a = seed;
	highp float b = 78.233;
	highp float c = 43758.5453;
	highp float dt= dot(co.xy ,vec2(a,b));
	highp float sn= mod(dt,3.14);
	return fract(sin(sn) * c);
}

// 2D Noise based on Morgan McGuire @morgan3d
// https://www.shadertoy.com/view/4dS3Wd
float noise (in vec2 st) {
	vec2 i = floor(st);
	vec2 f = fract(st);

	// Four corners in 2D of a tile
	float a = random(i);
	float b = random(i + vec2(1.0, 0.0));
	float c = random(i + vec2(0.0, 1.0));
	float d = random(i + vec2(1.0, 1.0));

	// Smooth Interpolation

	// Cubic Hermine Curve.  Same as SmoothStep()
	vec2 u = f*f*(3.0-2.0*f);
	// u = smoothstep(0.,1.,f);

	// Mix 4 coorners porcentages
	return mix(a, b, u.x) +
			(c - a)* u.y * (1.0 - u.x) +
			(d - b) * u.x * u.y;
}


float noise2(vec2 p, float freq ){
	float unit = 1.0/freq;
	vec2 ij = floor(p/unit);
	vec2 xy = mod(p,unit)/unit;
	//xy = 3.*xy*xy-2.*xy*xy*xy;
	xy = .5*(1.-cos(PI*xy));
	float a = rand((ij+vec2(0.,0.)));
	float b = rand((ij+vec2(1.,0.)));
	float c = rand((ij+vec2(0.,1.)));
	float d = rand((ij+vec2(1.,1.)));
	float x1 = mix(a, b, xy.x);
	float x2 = mix(c, d, xy.x);
	return mix(x1, x2, xy.y);
}

float pNoise(vec2 p, int res){
	float persistance = .5;
	float n = 0.;
	float normK = 0.;
	float f = 10.;
	float amp = 1.;
	int iCount = 0;
	for (int i = 0; i<50; i++){
		n+=amp*noise2(p, f);
		f*=2.;
		normK+=amp;
		amp*=persistance;
		if (iCount == res) break;
		iCount++;
	}
	float nf = n/normK;
	return nf*nf*nf*nf;
}

float DistanceFromCenterToSquareEdge(vec2 dir)
{
	dir = abs(dir);
	float dist = dir.x > dir.y ? dir.x : dir.y;
	return dist;
}


const vec2 boundMin = vec2(0.0, 0.0);
const vec2 boundMax = vec2(1.0, 1.0);
bool swap_inBounds (vec2 p) {
  return all(lessThan(boundMin, p)) && all(lessThan(p, boundMax));
}
 
vec2 swap_project (vec2 p) {
  return p * vec2(1.0, -1.2) + vec2(0.0, -0.02);
}

const vec4 black = vec4(0.0, 0.0, 0.0, 1.0);
vec4 swap_bgColor (vec2 p, vec2 pfr, vec2 pto) {
  vec4 c = black;
  pfr = swap_project(pfr);
  if (swap_inBounds(pfr)) {
    c += mix(black, getFromColor(pfr), swap_reflection * mix(1.0, 0.0, pfr.y));
  }
  pto = swap_project(pto);
  if (swap_inBounds(pto)) {
    c += mix(black, getToColor(pto), swap_reflection * mix(1.0, 0.0, pto.y));
  }
  return c;
}


vec2 cube_project (vec2 p) {
  return p * vec2(1.0, -1.2) + vec2(0.0, -cube_floating/100.);
}



bool cube_inBounds (vec2 p) {
  return all(lessThan(vec2(0.0), p)) && all(lessThan(p, vec2(1.0)));
}



vec4 cube_bgColor (vec2 p, vec2 pfr, vec2 pto) {
  vec4 c = vec4(0.0, 0.0, 0.0, 1.0);
  pfr = cube_project(pfr);
  if (cube_inBounds(pfr)) {
    c += mix(vec4(0.0), getFromColor(pfr), cube_reflection * mix(1.0, 0.0, pfr.y));
  }
  pto = cube_project(pto);
  if (cube_inBounds(pto)) {
    c += mix(vec4(0.0), getToColor(pto), cube_reflection * mix(1.0, 0.0, pto.y));
  }
  return c;
}

vec2 cube_xskew (vec2 p, float cube_persp, float center) {

  float x = mix(p.x, 1.0-p.x, center);

  return((vec2( x, (p.y - 0.5*(1.0-cube_persp) * x) / (1.0+(cube_persp-1.0)*x) ) - vec2(0.5-distance(center, 0.5), 0.0)) * vec2(0.5 / distance(center, 0.5) * (center<0.5 ? 1.0 : -1.0), 1.0) + vec2(center<0.5 ? 0.0 : 1.0, 0.0));
}


// TRANSITIONS

// Author: Jeffers
// https://forum.derivative.ca/t/transition-component/1859
vec4 Additive(vec2 uv)
{
	return clamp((2.0-2.0*progress),0.0,1.0)*(1.0-progress)*getFromColor(uv) 
		 + clamp((2.0*progress),0.0,1.0)*(progress)*getToColor(uv);
}

// Author: Jeffers
// https://forum.derivative.ca/t/transition-component/1859
vec4 Average(vec2 uv)
{
	vec3 colL = (1-progress)*getFromColor(uv).rgb;
	vec3 colR = (progress)*getToColor(uv).rgb;
	vec3 colAdd = clamp((2.0-2.0*progress),0.0,1.0)*colL + clamp((2.0*progress),0.0,1.0)*colR;
	vec3 colBlend = mix(colL,colR,progress);
	float diff = clamp( min( dot(colL,colL),dot(colR,colR) ), 0.0, 1.0);
	return vec4( mix(colAdd,colBlend,diff), 1.0);
}

// Author: Jeffers
// https://forum.derivative.ca/t/transition-component/1859
vec4 Blinds(vec2 uv)
{		
	if(fract(uv.y * blinds) < 1.0-progress)
	{
		return getFromColor(uv.xy);
	}
	else
	{
		return getToColor(uv.xy);
	}
}

// Author: Jeffers
// https://forum.derivative.ca/t/transition-component/1859
vec4 Blood(vec2 uv)
{
	float offset = min(progress + progress * noise(vec2(uv.x*30, seed)).r, 1.0);
	uv.y += offset;
	
	if(uv.y < 1.0) 
	{
		return getFromColor(uv);
	}
	else
	{
		return getToColor(fract(uv));
	}
}

// Author: Jeffers
// https://forum.derivative.ca/t/transition-component/1859
vec4 CircleStretch(vec2 uv)
{
	vec2 center = vec2(0.5,0.5);
	float radius = progress * 0.70710678;
	vec2 toUV = uv - center;
	float len = length(toUV);
	vec2 normToUV = toUV / len;
	
	if(len < radius)
	{
		float distFromCenterToEdge = DistanceFromCenterToSquareEdge(normToUV) / 2.0;
		vec2 edgePoint = center + distFromCenterToEdge * normToUV;
	
		float minRadius = min(radius, distFromCenterToEdge);
		float percentFromCenterToRadius = len / minRadius;
		
		vec2 newUV = mix(center, edgePoint, percentFromCenterToRadius);
		return getToColor(newUV);
	}
	else
	{
		float distFromCenterToEdge = DistanceFromCenterToSquareEdge(normToUV);
		vec2 edgePoint = center + distFromCenterToEdge * normToUV;
		float distFromRadiusToEdge = distFromCenterToEdge - radius;
		
		vec2 radiusPoint = center + radius * normToUV;
		vec2 radiusToUV = uv - radiusPoint;
		
		float percentFromRadiusToEdge = length(radiusToUV) / distFromRadiusToEdge;
		
		vec2 newUV = mix(center, edgePoint, percentFromRadiusToEdge);
		return getFromColor(newUV);
	}
}

// Author: Jeffers
// https://forum.derivative.ca/t/transition-component/1859
vec4 CircleReveal(vec2 uv)
{
	float radius = -creveal_fuzzy + progress * (0.70710678 + 2.0 * creveal_fuzzy);
	float fromCenter = length(uv - vec2(0.5,0.5));
	float distFromCircle = fromCenter - radius;
	
	vec4 c1 = getFromColor(uv); 
		vec4 c2 = getToColor(uv);
	
	float p = clamp((distFromCircle + creveal_fuzzy) / (2.0 * creveal_fuzzy), 0.0, 1.0);
	return mix(c2, c1, p);
}

// Author: Jeffers
// https://forum.derivative.ca/t/transition-component/1859
vec4 CloudReveal(vec2 uv)
{
	float cloud = pNoise(uv*2,3).r;
	
	vec4 c1 = getFromColor(uv);
	vec4 c2 = getToColor(uv);
	
	float a;

	float p = ((1.0-progress) / 2.0)+.25;
	
	if (p < 0.5)
	{
		a = mix(0.0, cloud, p / 0.5);
	}
	else
	{
		a = mix(cloud, 1.0, (p - 0.5) / 0.5);
	}
	
	return (a < 0.5) ? c2 : c1;
}

// author: gre
// License: MIT
// gl-transitions - https://gl-transitions.com/
vec4 ColorBurn(vec2 uv)
{
	return mix(
	getFromColor(vUV.st) + vec4(progress*colorburn_color, 1.0),
	getToColor(vUV.st) + vec4((1.0-progress)*colorburn_color, 1.0),
	progress);
}


// Author: P-Seebauer
// License: MIT
// ported by gre from https://gist.github.com/P-Seebauer/2a5fa2f77c883dd661f9
// gl-transitions - https://gl-transitions.com/
vec4 ColorDistance(vec2 uv)
{
	vec4 fTex = getFromColor(vUV.st);
	vec4 tTex = getToColor(vUV.st);
	float m = step(distance(fTex, tTex), progress);

	return mix(
	mix(fTex, tTex, m),
	tTex,
	pow(progress, colordist_power)
	);
}

// Author: Eke Péter <peterekepeter@gmail.com>
// License: MIT
// gl-transitions - https://gl-transitions.com/
vec4 CrossWarp(vec2 uv)
{
	float x = progress;
	x=smoothstep(.0,1.0,(x*2.0+vUV.x-1.0));
	return mix(getFromColor((vUV.st-.5)*(1.-x)+.5), getToColor((vUV.st-.5)*x+.5), x);
}

// Author: gre
// License: MIT
// gl-transitions - https://gl-transitions.com/
vec4 Cube(vec2 uv, bool invert)
{
  
  float prog = progress;
  if (invert){
	prog = 1.0-progress;
  }

  float uz = cube_unzoom * 2.0*(0.5-distance(0.5, prog));

  	

  vec2 p = -uz*0.5+(1.0+uz) * uv;

  vec2 fromP = cube_xskew(
    (p - vec2(prog, 0.0)) / vec2(1.0-prog, 1.0),
    1.0-mix(prog, 0.0, cube_persp),
    0.0
  );

  vec2 toP = cube_xskew(
    p / vec2(prog, 1.0),
    mix(pow(prog, 2.0), 1.0, cube_persp),
    1.0
  );

  if (invert){
	  if (cube_inBounds(fromP)) {
	    return getToColor(fromP);
	  }

	  else if (cube_inBounds(toP)) {
	    return getFromColor(toP);
	  }

	  else {
	    return cube_bgColor(uv, fromP, toP);
	  }
  }
  else {
	  if (cube_inBounds(fromP)) {
	    return getFromColor(fromP);
	  }

	  else if (cube_inBounds(toP)) {
	    return getToColor(toP);
	  }

	  else {
	    return cube_bgColor(uv, fromP, toP);
	  }	
  }


}

// Author: Jeffers
// https://forum.derivative.ca/t/transition-component/1859
vec4 Difference(vec2 uv)
{
	vec4 colL = (1.0-progress)*getFromColor(uv);
	vec4 colR = (progress)*getToColor(uv);
	vec4 diff = abs(colL - colR);
	return vec4(mix( mix(colL,diff,progress*2.0), mix(diff,colR,(2.0*progress-1.0)), step(0.5,progress)).rgb,1.0);
}

// Author: Jeffers
// https://forum.derivative.ca/t/transition-component/1859
vec4 Dissolve(vec2 uv)
{
	float noise = noise( fract(uv + seed) * 1000 ).x;
	if(noise > progress)
	{
		return getFromColor(uv);
	}
	else
	{
		return getToColor(uv);
	}
}

// Author: mikolalysenko
// License: MIT
// gl-transitions - https://gl-transitions.com/
vec4 Dreamy(vec2 uv)
{
	return mix(
		getFromColor(vUV.st + offset(progress, vUV.s, 0.0)),
		getToColor(vUV.st + offset(1.0-progress, vUV.x, 3.14)),
		progress);
}

// author: gre
// license: MIT
// gl-transitions - https://gl-transitions.com/
vec4 Fade(vec2 uv)
{
	return mix(
	getFromColor(uv),
	getToColor(uv),
	progress);
}

// author: gre
// License: MIT
// gl-transitions - https://gl-transitions.com/
vec4 FadeColor(vec2 uv)
{
		
	float p1 = clamp(progress * 2.0, 0.0, 1.0);
	float p2 = clamp((progress * 2.0)-1.0, 0.0, 1.0);

	vec4 o = vec4(0.0);

	if (progress < .5){
		o += mix(
		getFromColor(vUV.st),
		fade_color,
		p1);		
	}
	else {
		o += mix(
		fade_color,
		getToColor(vUV.st),
		p2);		
	}
	return o;
}

// author: gre
// license: MIT
// gl-transitions - https://gl-transitions.com/
vec4 LinearBlur(vec2 uv)
{
	vec4 c1 = vec4(0.0);
	vec4 c2 = vec4(0.0);

	float disp = linblur_intensity*(0.5-distance(0.5, progress));
	for (int xi=0; xi<linblur_passes; xi++)
	{
		float x = float(xi) / float(linblur_passes) - 0.5;
		for (int yi=0; yi<linblur_passes; yi++)
		{
			float y = float(yi) / float(linblur_passes) - 0.5;
			vec2 v = vec2(x,y);
			float d = disp;
			c1 += getFromColor( uv + d*v );
			c2 += getToColor( vUV.st + d*v);
		}
	}
	c1 /= float(linblur_passes*linblur_passes);
	c2 /= float(linblur_passes*linblur_passes);

	return mix( c1, c2, progress);
}

// Author: Jeffers
// https://forum.derivative.ca/t/transition-component/1859
vec4 Maximum(vec2 uv)
{
	vec4 col = getFromColor(uv)*1.0-progress;
	float As = (1.0-progress)*(col.r+col.g+col.b);
	
	vec4 col2 = getToColor(uv)*progress;
	float Bs = progress*(col2.r+col2.g+col2.b);
	
	float Ar = smoothstep(-max_dist,max_dist,Bs-As);
	
	Ar = Ar * smoothstep(0.0,max_fadeindist,progress);
	Ar = mix(Ar,1.0,smoothstep(1.0-max_fadeindist,1.0,progress));
	
	return mix(col,col2, Ar);
}

// Author: paniq
// License: MIT
// gl-transitions - https://gl-transitions.com/
vec4 Morph1(vec2 uv)
{
	vec4 ca = getFromColor(vUV.st);
	vec4 cb = getToColor(vUV.st);

	vec2 oa = (((ca.rg+ca.b)*0.5)*2.0-1.0);
	vec2 ob = (((cb.rg+cb.b)*0.5)*2.0-1.0);
	vec2 oc = mix(oa,ob,0.5)*morph1_strength;

	float w0 = progress;
	float w1 = 1.0-w0;

	return mix(getFromColor(vUV.st+oc*w0), getToColor(vUV.st-oc*w1), progress);
}

// Author: Jeffers
// https://forum.derivative.ca/t/transition-component/1859
vec4 Morph2(vec2 uv)
{
	float rad = mix((1.0 - (1.0-progress)), progress, progress);
	rad = mix( rad, progress, abs(2.1*progress - 1.0) - 0.1 );
	float bias = 5.0;
	float scale_x = 0.02;
	float scale_y = 0.02;
	float stretch = 0.02;

	vec2 perturb;
	vec2 slope;
	vec4 color;

	vec4 pd_bl_a = getFromColorBias( vec2( -scale_x, -scale_y ) + uv, bias ) * (1.0-progress);
	vec4 pd_bl_b = getToColorBias( vec2( -scale_x, -scale_y ) + uv, bias ) * progress;
	vec4 pd_tr_a = getFromColorBias( vec2( scale_x, scale_y ) + uv, bias ) * (1.0-progress);
	vec4 pd_tr_b = getToColorBias( vec2( scale_x, scale_y ) + uv, bias ) * progress;
	vec4 pd_tl_a = getFromColorBias( vec2( -scale_x, scale_y ) + uv, bias ) * (1.0-progress);
	vec4 pd_tl_b = getToColorBias( vec2( -scale_x, scale_y ) + uv, bias ) * progress;
	vec4 pd_br_a = getFromColorBias( vec2( scale_x, -scale_y ) + uv, bias ) * (1.0-progress);
	vec4 pd_br_b = getToColorBias( vec2( scale_x, -scale_y ) + uv, bias ) * progress;

	vec4 from = getFromColorBias( uv, bias ) * (1.0-progress);
	vec4 to = getToColorBias( uv, bias ) * progress;

	vec4 d = (pd_tl_a + pd_tr_a + pd_bl_a + pd_br_a + from * 2.0
	-(pd_tl_b + pd_tr_b + pd_bl_b + pd_br_b + to * 2.0 ));
	float diff = d.r + d.g + d.b;
	vec4 sx = ((pd_tl_a + pd_tl_b + pd_bl_a + pd_bl_b)
	- (pd_tr_a + pd_tr_b + pd_br_a + pd_br_b));
	vec4 sy = ((pd_bl_a + pd_bl_b + pd_br_a + pd_br_b)
	- (pd_tl_a + pd_tl_b + pd_tr_a + pd_tr_b));
	slope.x = sx.r + sx.g + sx.b;
	slope.y = sy.r + sy.g + sy.b;

	float p_len = dot( slope, slope ) + 1.0;
	perturb = vec2( slope.x / p_len, slope.y / p_len ) * diff;

	vec2 pert_to = perturb * (1.0-rad) * stretch;
	perturb *= rad * stretch;

	vec4 col1 = getFromColor( uv + perturb ) * (1.0-progress);
	vec4 col2 = getToColor( uv - pert_to ) * progress;
	return col1 + col2; //mix(col1, col2, progress);
}

// Author: Rich Harris
// License: MIT
// gl-transitions - https://gl-transitions.com/
vec4 Perlin(vec2 uv)
{
	vec4 from = getFromColor(vUV.st);
	vec4 to = getToColor(vUV.st);
	float n = noise(vUV.st * perlin_scale);

	float p = mix(-perlin_smoothness, 1.0 + perlin_smoothness, progress);
	float lower = p - perlin_smoothness;
	float higher = p + perlin_smoothness;

	float q = smoothstep(lower, higher, n);

	return mix(
	from,
	to,
	1.0 - q
	);
}

// Author: gre
// License: MIT
// forked from https://gist.github.com/benraziel/c528607361d90a072e98
// gl-transitions - https://gl-transitions.com/
vec4 Pixelize(vec2 uv)
{
	float d = min(progress, 1.0 - progress);
	float dist = pixelize_steps>0 ? ceil(d * float(pixelize_steps)) / float(pixelize_steps) : d;
	vec2 squareSize = 2.0 * dist / vec2(pixelize_smin);
	vec2 p = dist>0.0 ? (floor(vUV.st / squareSize) + 0.5) * squareSize : vUV.st;
	return mix(getFromColor(p), getToColor(p), progress);
}

// Author: Jeffers
// https://forum.derivative.ca/t/transition-component/1859
vec4 RadialBlur(vec2 uv)
{
	vec2 toUV = uv - rblur_center;
	vec2 normToUV = toUV;
	
	
	vec4 c1 = vec4(0,0,0,0);
	int count = 24;
	float s = progress * 0.02;
	
	for(int i=0; i<count; i++)
	{
		c1 += getFromColor( uv - normToUV * s * i); 
	}
	
	c1 /= count;
		vec4 c2 = getToColor( uv );

	return mix(c1, c2, progress);
}

// Author: gre
// License: MIT
// gl-transitions - https://gl-transitions.com/
vec4 RandomSquares(vec2 uv)
{
	float r = rand(floor(vec2(randsquares_size) * vUV.st));
	float m = smoothstep(0.0, -randsquares_smoothness, r - (progress * (1.0 + randsquares_smoothness)));

	return mix(getFromColor(vUV.st), getToColor(vUV.st), m);
}

// Author: gre
// License: MIT
// gl-transitions - https://gl-transitions.com/
vec4 Ripple(vec2 uv)
{


	vec2 toUV = uv - ripple_center;
	float distanceFromCenter = length(toUV);
	vec2 normToUV = toUV / distanceFromCenter;

	float wave = cos(ripple_frequency * distanceFromCenter - ripple_speed * progress);
	float offset1 = progress * wave * ripple_amplitude;
	float offset2 = (1.0 - progress) * wave * ripple_amplitude;
	
	vec2 newUV1 = ripple_center + normToUV * (distanceFromCenter + offset1);
	vec2 newUV2 = ripple_center + normToUV * (distanceFromCenter + offset2);
	
	vec4 c1 = getFromColor(newUV1); 
	vec4 c2 = getToColor(newUV2);

	return mix(c1, c2, progress);
}

// Author: gre
// License: MIT
// gl-transitions - https://gl-transitions.com/
vec4 Slide(vec2 uv)
{

    float x = progress * slide_trans.x;
    float y = progress * slide_trans.y;

    if (x >= 0.0 && y >= 0.0) {
        if (uv.x >= x && uv.y >= y) {
            return getFromColor(uv - vec2(x, y));
        }
        else {
            vec2 iuv;
            if (x > 0.0)
                iuv = vec2(x - 1.0, y);
            else if (y > 0.0)
                iuv = vec2(x, y - 1.0);
            return getToColor(uv - iuv);
        }
    }
    else if (x <= 0.0 && y <= 0.0) {
        if (uv.x <= (1.0 + x) && uv.y <= (1.0 + y))
           return getFromColor(uv - vec2(x, y));
        else {
            vec2 iuv;
            if (x < 0.0)
                iuv = vec2(x + 1.0, y);
            else if (y < 0.0)
                iuv = vec2(x, y + 1.0);
            return getToColor(uv - iuv);
        }
    }
    else
        return vec4(0.0);
}

// Author: Jeffers
// https://forum.derivative.ca/t/transition-component/1859
vec4 Stretch(vec2 uv)
{
	vec2 texCoord1 = uv;
	texCoord1.t = clamp(texCoord1.t,0.5-(0.499-progress),0.5+(0.499-progress)) * step(0.0,texCoord1.t) * step(0.0,1.0 - texCoord1.t);
	vec2 texCoord2 = uv;
	texCoord2.t = clamp(texCoord2.t,0.5-(progress-0.5),0.5+(progress-0.5)) * step(0.0,texCoord2.t) * step(0.0,1.0 - texCoord2.t);
	
	vec4 col1 = (1-progress)*getFromColor(texCoord1);
	vec4 col2 = (progress)*getToColor(texCoord2);
	
	return mix(col1,col2,smoothstep(-0.1,0.1,progress-0.5));
	//return col1 + col2;
}

// Author: gre
// License: MIT
// gl-transitions - https://gl-transitions.com/
vec4 Swap(vec2 uv, bool invert)
{

  float prog = progress;
  if (invert){
	prog = 1.0-progress;
  }

  vec2 pfr, pto = vec2(-1.);
 
  float size = mix(1.0, swap_depth, prog);
  float persp = swap_perspective * prog;
  pfr = (uv + vec2(-0.0, -0.5)) * vec2(size/(1.0-swap_perspective*prog), size/(1.0-size*persp*uv.x)) + vec2(0.0, 0.5);
 
  size = mix(1.0, swap_depth, 1.-prog);
  persp = swap_perspective * (1.-prog);
  pto = (uv + vec2(-1.0, -0.5)) * vec2(size/(1.0-swap_perspective*(1.0-prog)), size/(1.0-size*persp*(0.5-uv.x))) + vec2(1.0, 0.5);
 
  bool fromOver = prog < 0.5;
 
  if (invert){
	  if (fromOver) {
	    if (swap_inBounds(pfr)) {
	      return getToColor(pfr);
	    }
	    else if (swap_inBounds(pto)) {
	      return getFromColor(pto);
	    }
	    else {
	      return swap_bgColor(uv, pto, pfr);
	    }
	  }
	  else {
	    if (swap_inBounds(pto)) {
	      return getFromColor(pto);
	    }
	    else if (swap_inBounds(pfr)) {
	      return getToColor(pfr);
	    }
	    else {
	      return swap_bgColor(uv, pto, pfr);
	    }
	  }
  }
  else{
	  if (fromOver) {
	    if (swap_inBounds(pfr)) {
	      return getFromColor(pfr);
	    }
	    else if (swap_inBounds(pto)) {
	      return getToColor(pto);
	    }
	    else {
	      return swap_bgColor(uv, pfr, pto);
	    }
	  }
	  else {
	    if (swap_inBounds(pto)) {
	      return getToColor(pto);
	    }
	    else if (swap_inBounds(pfr)) {
	      return getFromColor(pfr);
	    }
	    else {
	      return swap_bgColor(uv, pfr, pto);
	    }
	  }
  }

}


layout(location = 0) out vec4 fragColor;
void main() {
	vec4 o = vec4(0.0,0.0,0.0,0.0);
	
	switch(mode) {
		case 0: o = Additive(vUV.st); break;
		case 1: o = Average(vUV.st); break;
		case 2: o = Blinds(vUV.st); break;
		case 3: o = Blood(vUV.st); break;
		case 4: o = CircleReveal(vUV.st); break;
		case 5: o = CircleStretch(vUV.st); break;
		case 6: o = CloudReveal(vUV.st); break;
		case 7: o = ColorBurn(vUV.st); break;
		case 8: o = ColorDistance(vUV.st); break;
		case 9: o = CrossWarp(vUV.st); break;
		case 10: o = Cube(vUV.st, true); break;
		case 11: o = Cube(vUV.st, false); break;
		case 12: o = Difference(vUV.st); break;
		case 13: o = Dissolve(vUV.st); break;
		case 14: o = Dreamy(vUV.st); break;
		case 15: o = Fade(vUV.st); break;
		case 16: o = FadeColor(vUV.st); break;
		case 17: o = LinearBlur(vUV.st); break;
		case 18: o = Maximum(vUV.st); break;
		case 19: o = Morph1(vUV.st); break;
		case 20: o = Morph2(vUV.st); break;
		case 21: o = Perlin(vUV.st); break;
		case 22: o = Pixelize(vUV.st); break;
		case 23: o = RadialBlur(vUV.st); break;
		case 24: o = RandomSquares(vUV.st); break;
		case 25: o = Ripple(vUV.st); break;
		case 26: o = Slide(vUV.st); break;
		case 27: o = Stretch(vUV.st); break;
		case 28: o = Swap(vUV.st, false); break;
		case 29: o = Swap(vUV.st, true); break;
	}

	fragColor = TDOutputSwizzle(o);
}