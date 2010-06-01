'''Perform lattice-related computations'''

import numpy as np
import numpy.linalg as nl

# trig functions in degrees
sind = lambda x: np.sin(x*np.pi/180.)
asind = lambda x: 180.*np.arcsin(x)/np.pi
tand = lambda x: np.tan(x*np.pi/180.)
atand = lambda x: 180.*np.arctan(x)/np.pi
atan2d = lambda y,x: 180.*np.atan2(y,x)/np.pi
cosd = lambda x: np.cos(x*np.pi/180.)
acosd = lambda x: 180.*np.arccos(x)/np.pi
rdsq2d = lambda x,p: round(1.0/np.sqrt(x),p)

def fillgmat(cell):
    '''Compute lattice metric tensor from unit cell constants
    cell is tuple with a,b,c,alpha, beta, gamma (degrees)
    returns 3x3 numpy array
    '''
    a,b,c,alp,bet,gam = cell
    g = np.array([[a*a,a*b*cosd(gam),a*c*cosd(bet)],[a*b*cosd(gam),b*b,b*c*cosd(alp)],
        [a*c*cosd(bet),b*c*cosd(alp),c*c]])
    return g
           
def cell2Gmat(cell):
    '''Compute real and reciprocal lattice metric tensor from unit cell constants
    cell is tuple with a,b,c,alpha, beta, gamma (degrees)
    returns reciprocal (G) & real (g) metric tensors (list of two 3x3 arrays)
    '''
    g = fillgmat(cell)
    G = nl.inv(g)        
    return G,g

def A2Gmat(A):
    '''Compute reciprocal metric tensor (G) from A tensor
    returns reciprocal (G) & real (g) metric tensors (list of two 3x3 arrays)
    '''
    G = np.zeros(shape=(3,3))
    G = [[A[0],A[3]/2.,A[4]/2.], [A[3]/2.,A[1],A[5]/2.], [A[4]/2.,A[5]/2.,A[2]]]
    g = nl.inv(G)
    return G,g

def Gmat2A(G):
    'Compute A tensor from reciprocal metric tensor (G)'
    return [G[0][0],G[1][1],G[2][2],2.*G[0][1],2.*G[0][2],2.*G[1][2]]
    
def cell2A(cell):
    G,g = cell2Gmat(cell)
    return Gmat2A(G)

def A2cell(A):
    '''Compute unit cell constants from A tensor
    returns tuple with a,b,c,alpha, beta, gamma (degrees)
    '''
    G,g = A2Gmat(A)
    return Gmat2cell(g)

def Gmat2cell(g):
    '''Compute lattice parameters from real metric tensor (g)
    returns tuple with a,b,c,alpha, beta, gamma (degrees)
    '''
    a = np.sqrt(max(0,g[0][0]))
    b = np.sqrt(max(0,g[1][1]))
    c = np.sqrt(max(0,g[2][2]))
    alp = acosd(g[2][1]/(b*c))
    bet = acosd(g[2][0]/(a*c))
    gam = acosd(g[0][1]/(a*b))
    return a,b,c,alp,bet,gam

def invcell2Gmat(invcell):
    '''Compute real and reciprocal lattice metric tensor from reciprocal 
       unit cell constants
    invcell is tuple with a*,b*,c*,alpha*, beta*, gamma* (degrees)
    returns reciprocal (G) & real (g) metric tensors (list of two 3x3 arrays)
    '''
    G = fillgmat(invcell)
    g = nl.inv(G)
    return G,g
        
def calc_rVsq(A):
    'Compute the square of the reciprocal lattice volume (V* **2) from A tensor'
    rVsq = A[0]*A[1]*A[2]+0.25*(A[3]*A[4]*A[5]-A[0]*A[5]**2-A[1]*A[4]**2-A[2]*A[3]**2)
    if rVsq < 0:
        return 1
    return rVsq
    
def calc_rV(A):
    'Compute the reciprocal lattice volume (V*) from A tensor'
    return np.sqrt(calc_rVsq(A))
    
def calc_V(A):
    'Compute the real lattice volume (V) from A tensor'
    return 1./calc_rV(A)

def A2invcell(A):
    '''Compute reciprocal unit cell constants from A tensor
    returns tuple with a*,b*,c*,alpha*, beta*, gamma* (degrees)
    '''
    G,g = A2Gmat(A)
    return Gmat2cell(G)
    # Code below is broken
    ainv = np.sqrt(max(0.,A[0]))
    binv = np.sqrt(max(0.,A[1]))
    cinv = np.sqrt(max(0.,A[2]))
    gaminv = acosd(max(-0.5,min(0.5,0.5*A[3]/(ainv*binv))))
    betinv = acosd(max(-0.5,min(0.5,0.5*A[4]/(ainv*cinv))))
    alpinv = acosd(max(-0.5,min(0.5,0.5*A[5]/(binv*cinv))))
    return ainv,binv,cinv,alpinv,betinv,gaminv

def cell2AB(cell):
    '''Computes orthogonalization matrix from unit cell constants
    cell is tuple with a,b,c,alpha, beta, gamma (degrees)
    returns list of two 3x3 numpy arrays
       A for Cartesian to crystal transformations A*X = x 
       B (inverse) for crystal to Cartesian transformation B*x = X
    '''
    G,g = cell2Gmat(cell) 
    cellstar = Gmat2cell(G)
    A = np.zeros(shape=(3,3))
    # from Giacovazzo (Fundamentals 2nd Ed.) p.75
    A[0][0] = cell[0]                # a
    A[0][1] = cell[1]*cosd(cell[5])  # b cos(gamma)
    A[0][2] = cell[2]*cosd(cell[4])  # c cos(beta)
    A[1][1] = cell[1]*sind(cell[5])  # b sin(gamma)
    A[1][2] = -cell[2]*cosd(cellstar[3])*sind(cell[4]) # - c cos(alpha*) sin(beta)
    A[2][2] = 1/cellstar[2]         # 1/c*
    B = nl.inv(A)
    return A,B
    # bob's code:
    G,g = cell2Gmat(cell)       #reciprocal & real metric tensors
    cosAlpStar = G[2][1]/np.sqrt(G[1][1]*G[2][2])
    sinAlpStar = np.sqrt(1.0-cosAlpStar**2)
    B = np.eye(3)
    B *= cell[:3]
    A = np.zeros(shape=(3,3))
    A[0][0] = 1.0
    A[0][1] = cosd(cell[5])
    A[1][1] = sinAlpStar*sind(cell[5])
    A[1][2] = -cosAlpStar*sind(cell[5])
    A[0][2] = cosd(cell[4])
    A[2][2] = sind(cell[4])
    B = np.dot(A,B)
    A = nl.inv(B)
    return A,B


# output from uctbx computed on platform darwin on 2010-05-28
array = np.array
CellTestData = [
# cell, g, G, cell*, V, V*
  [(4, 4, 4, 90, 90, 90), 
   array([[  1.60000000e+01,   9.79717439e-16,   9.79717439e-16],
       [  9.79717439e-16,   1.60000000e+01,   9.79717439e-16],
       [  9.79717439e-16,   9.79717439e-16,   1.60000000e+01]]), array([[  6.25000000e-02,   3.82702125e-18,   3.82702125e-18],
       [  3.82702125e-18,   6.25000000e-02,   3.82702125e-18],
       [  3.82702125e-18,   3.82702125e-18,   6.25000000e-02]]), (0.25, 0.25, 0.25, 90.0, 90.0, 90.0), 64.0, 0.015625],
# cell, g, G, cell*, V, V*
  [(4.0999999999999996, 5.2000000000000002, 6.2999999999999998, 100, 80, 130), 
   array([[ 16.81      , -13.70423184,   4.48533243],
       [-13.70423184,  27.04      ,  -5.6887143 ],
       [  4.48533243,  -5.6887143 ,  39.69      ]]), array([[ 0.10206349,  0.05083339, -0.00424823],
       [ 0.05083339,  0.06344997,  0.00334956],
       [-0.00424823,  0.00334956,  0.02615544]]), (0.31947376387537696, 0.25189277536327803, 0.16172643497798223, 85.283666420376008, 94.716333579624006, 50.825714168082683), 100.98576357983838, 0.0099023858863968445],
# cell, g, G, cell*, V, V*
  [(3.5, 3.5, 6, 90, 90, 120), 
   array([[  1.22500000e+01,  -6.12500000e+00,   1.28587914e-15],
       [ -6.12500000e+00,   1.22500000e+01,   1.28587914e-15],
       [  1.28587914e-15,   1.28587914e-15,   3.60000000e+01]]), array([[  1.08843537e-01,   5.44217687e-02,   3.36690552e-18],
       [  5.44217687e-02,   1.08843537e-01,   3.36690552e-18],
       [  3.36690552e-18,   3.36690552e-18,   2.77777778e-02]]), (0.32991443953692895, 0.32991443953692895, 0.16666666666666669, 90.0, 90.0, 60.000000000000021), 63.652867178156257, 0.015710211406520427],
]
CoordTestData = [
# cell, ((frac, ortho),...)
  ((4,4,4,90,90,90,), [
 ((0.10000000000000001, 0.0, 0.0),(0.40000000000000002, 0.0, 0.0)),
 ((0.0, 0.10000000000000001, 0.0),(2.4492935982947065e-17, 0.40000000000000002, 0.0)),
 ((0.0, 0.0, 0.10000000000000001),(2.4492935982947065e-17, -2.4492935982947065e-17, 0.40000000000000002)),
 ((0.10000000000000001, 0.20000000000000001, 0.29999999999999999),(0.40000000000000013, 0.79999999999999993, 1.2)),
 ((0.20000000000000001, 0.29999999999999999, 0.10000000000000001),(0.80000000000000016, 1.2, 0.40000000000000002)),
 ((0.29999999999999999, 0.20000000000000001, 0.10000000000000001),(1.2, 0.80000000000000004, 0.40000000000000002)),
 ((0.5, 0.5, 0.5),(2.0, 1.9999999999999998, 2.0)),
]),
# cell, ((frac, ortho),...)
  ((4.1,5.2,6.3,100,80,130,), [
 ((0.10000000000000001, 0.0, 0.0),(0.40999999999999998, 0.0, 0.0)),
 ((0.0, 0.10000000000000001, 0.0),(-0.33424955703700043, 0.39834311042186865, 0.0)),
 ((0.0, 0.0, 0.10000000000000001),(0.10939835193016617, -0.051013289294572106, 0.6183281045774256)),
 ((0.10000000000000001, 0.20000000000000001, 0.29999999999999999),(0.069695941716497567, 0.64364635296002093, 1.8549843137322766)),
 ((0.20000000000000001, 0.29999999999999999, 0.10000000000000001),(-0.073350319180835066, 1.1440160419710339, 0.6183281045774256)),
 ((0.29999999999999999, 0.20000000000000001, 0.10000000000000001),(0.67089923785616512, 0.74567293154916525, 0.6183281045774256)),
 ((0.5, 0.5, 0.5),(0.92574397446582857, 1.7366491056364828, 3.0916405228871278)),
]),
# cell, ((frac, ortho),...)
  ((3.5,3.5,6,90,90,120,), [
 ((0.10000000000000001, 0.0, 0.0),(0.35000000000000003, 0.0, 0.0)),
 ((0.0, 0.10000000000000001, 0.0),(-0.17499999999999993, 0.3031088913245536, 0.0)),
 ((0.0, 0.0, 0.10000000000000001),(3.6739403974420595e-17, -3.6739403974420595e-17, 0.60000000000000009)),
 ((0.10000000000000001, 0.20000000000000001, 0.29999999999999999),(2.7675166561703527e-16, 0.60621778264910708, 1.7999999999999998)),
 ((0.20000000000000001, 0.29999999999999999, 0.10000000000000001),(0.17500000000000041, 0.90932667397366063, 0.60000000000000009)),
 ((0.29999999999999999, 0.20000000000000001, 0.10000000000000001),(0.70000000000000018, 0.6062177826491072, 0.60000000000000009)),
 ((0.5, 0.5, 0.5),(0.87500000000000067, 1.5155444566227676, 3.0)),
]),
]

def test0():
    msg = 'test cell2Gmat, fillgmat, Gmat2cell'
    for (cell, tg, tG, trcell, tV, trV) in CellTestData:
        G, g = cell2Gmat(cell)
        assert np.allclose(G,tG),msg
        assert np.allclose(g,tg),msg
        tcell = Gmat2cell(g)
        assert np.allclose(cell,tcell),msg
        tcell = Gmat2cell(G)
        assert np.allclose(tcell,trcell),msg

def test1():
    msg = 'test cell2A and A2Gmat'
    for (cell, tg, tG, trcell, tV, trV) in CellTestData:
        G, g = A2Gmat(cell2A(cell))
        assert np.allclose(G,tG),msg
        assert np.allclose(g,tg),msg

def test2():
    msg = 'test Gmat2A, A2cell, A2Gmat, Gmat2cell'
    for (cell, tg, tG, trcell, tV, trV) in CellTestData:
        G, g = cell2Gmat(cell)
        tcell = A2cell(Gmat2A(G))
        assert np.allclose(cell,tcell),msg

def test3():
    msg = 'test invcell2Gmat'
    for (cell, tg, tG, trcell, tV, trV) in CellTestData:
        G, g = invcell2Gmat(trcell)
        assert np.allclose(G,tG),msg
        assert np.allclose(g,tg),msg

def test4():
    msg = 'test calc_rVsq, calc_rV, calc_V'
    for (cell, tg, tG, trcell, tV, trV) in CellTestData:
        assert np.allclose(calc_rV(cell2A(cell)),trV), msg
        assert np.allclose(calc_V(cell2A(cell)),tV), msg

def test5():
    msg = 'test A2invcell'
    for (cell, tg, tG, trcell, tV, trV) in CellTestData:
        rcell = A2invcell(cell2A(cell))
        assert np.allclose(rcell,trcell),msg

def test6():
    msg = 'test cell2AB'
    for (cell,coordlist) in CoordTestData:
        A,B = cell2AB(cell)
        for (frac,ortho) in coordlist:
            to = np.inner(A,frac)
            tf = np.inner(B,to)
            assert np.allclose(ortho,to), msg
            assert np.allclose(frac,tf), msg

if __name__ == '__main__':
    test0()
    test1()
    test2()
    test3()
    test4()
    test5()
    test6()
    print "OK"