#Element table for building periodic table with valences & JMOL colors 
import wx        
#Need these in case go back to this periodic table coloring scheme
REcolor = wx.Colour(128, 128, 255)
Metcolor = wx.Colour(192, 192, 192)
Noblecolor = wx.Colour(255, 128, 255)
Alkcolor = wx.Colour(255, 255, 128)
AlkEcolor = wx.Colour(255, 128, 0)
SemMetcolor = wx.Colour(128, 255, 0)
NonMetcolor = wx.Colour(0, 255, 255)
White = wx.Colour(255, 255, 255)            
ElTable = [
    (["H","H-1"],                  0,0, "Hydrogen",    White,           0.0000,wx.Colour(255,255,255)),
    (["He",],                     17,0, "Helium",      Noblecolor,      0.0000,wx.Colour(217,255,255)),
    (["Li","Li+1"],                0,1, "Lithium",     Alkcolor,        0.0004,wx.Colour(204,128,255)),
    (["Be","Be+2"],                1,1, "Beryllium",   AlkEcolor,       0.0006,wx.Colour(194,255,0)),
    (["B",],                       2,1, "Boron",       NonMetcolor,     0.0012,wx.Colour(255,181,181)),
    (["C",],                      13,1, "Carbon",      NonMetcolor,     0.0018,wx.Colour(144,144,144)),
    (["N",],                      14,1, "Nitrogen",    NonMetcolor,     0.0030,wx.Colour(48,80,248)),
    (["O","O-1","O-2"],           15,1, "Oxygen",      NonMetcolor,     0.0042,wx.Colour(255,13,13)),
    (["F","F-1"],                 16,1, "Fluorine",    NonMetcolor,     0.0054,wx.Colour(144,224,80)),
    (["Ne",],                     17,1, "Neon",        Noblecolor,      0.0066,wx.Colour(179,227,245)),
    (["Na","Na+1"],                0,2, "Sodium",      Alkcolor,        0.0084,wx.Colour(171,92,242)),
    (["Mg","Mg+2"],                1,2, "Magnesium",   AlkEcolor,       0.0110,wx.Colour(138,255,0)),
    (["Al","Al+3"],                2,2, "Aluminum",    SemMetcolor,     0.0125,wx.Colour(191,166,166)),
    (["Si","Si+4"],               13,2, "Silicon",     NonMetcolor,     0.0158,wx.Colour(240,200,160)),
    (["P",],                      14,2, "Phosphorus",  NonMetcolor,     0.0180,wx.Colour(255,128,0)),
    (["S",],                      15,2, "Sulphur",     NonMetcolor,     0.0210,wx.Colour(255,255,48)),
    (["Cl","Cl-1"],               16,2, "Chlorine",    NonMetcolor,     0.0250,wx.Colour(31,240,31)),
    (["Ar",],                     17,2, "Argon",       Noblecolor,      0.0285,wx.Colour(128,209,227)),
    (["K","K+1"],                  0,3, "Potassium",   Alkcolor,        0.0320,wx.Colour(61,255,0)),
    (["Ca","Ca+2"],                1,3, "Calcium",     AlkEcolor,       0.0362,wx.Colour(61,255,0)),
    (["Sc","Sc+3"],                2,3, "Scandium",    Metcolor,        0.0410,wx.Colour(230,230,230)),
    (["Ti","Ti+2","Ti+3","Ti+4"],  3,3, "Titanium",    Metcolor,        0.0460,wx.Colour(191,194,199)),
    (["V","V+2","V+3","V+5"],      4,3, "Vanadium",    Metcolor,        0.0510,wx.Colour(166,166,171)),
    (["Cr","Cr+2","Cr+3"],         5,3, "Chromium",    Metcolor,        0.0560,wx.Colour(138,153,199)),
    (["Mn","Mn+2","Mn+3","Mn+4"],  6,3, "Manganese",   Metcolor,        0.0616,wx.Colour(156,122,199)),
    (["Fe","Fe+2","Fe+3"],         7,3, "Iron",        Metcolor,        0.0680,wx.Colour(224,102,51)),
    (["Co","Co+2","Co+3"],         8,3, "Cobalt",      Metcolor,        0.0740,wx.Colour(240,144,160)),
    (["Ni","Ni+2","Ni+3"],         9,3, "Nickel",      Metcolor,        0.0815,wx.Colour(80,208,80)),
    (["Cu","Cu+1","Cu+2"],        10,3, "Copper",      Metcolor,        0.0878,wx.Colour(200,128,51)),
    (["Zn","Zn+2"],               11,3, "Zinc",        Metcolor,        0.0960,wx.Colour(125,128,176)),
    (["Ga","Ga+3"],               12,3, "Gallium",     SemMetcolor,      0.104,wx.Colour(194,143,143)),
    (["Ge","Ge+4"],               13,3, "Germanium",   SemMetcolor,      0.114,wx.Colour(102,143,143)),
    (["As",],                     14,3, "Arsenic",     NonMetcolor,      0.120,wx.Colour(189,128,227)),
    (["Se",],                     15,3, "Selenium",    NonMetcolor,      0.132,wx.Colour(255,161,0)),
    (["Br","Br-1"],               16,3, "Bromine",     NonMetcolor,      0.141,wx.Colour(166,41,41)),
    (["Kr",],                     17,3, "Krypton",     Noblecolor,       0.150,wx.Colour(92,184,209)),
    (["Rb","Rb+1"],                0,4, "Rubidium",    Alkcolor,         0.159,wx.Colour(112,46,176)),
    (["Sr","Sr+2"],                1,4, "Strontium",   AlkEcolor,        0.171,wx.Colour(0,255,0)),
    (["Y","Y+3"],                  2,4, "Yittrium",    Metcolor,         0.180,wx.Colour(148,255,255)),
    (["Zr","Zr+4"],                3,4, "Zirconium",   Metcolor,         0.192,wx.Colour(148,224,224)),
    (["Nb","Nb+3","Nb+5"],         4,4, "Niobium",     Metcolor,         0.204,wx.Colour(115,194,201)),
    (["Mo","Mo+3","Mo+5","Mo+6"],  5,4, "Molybdenium", Metcolor,         0.216,wx.Colour(84,181,181)),
    (["Tc",],                      6,4, "Technetium",  Metcolor,         0.228,wx.Colour(59,158,158)),
    (["Ru","Ru+3","Ru+4"],         7,4, "Ruthenium",   Metcolor,         0.246,wx.Colour(36,143,143)),
    (["Rh","Rh+3","Rh+4"],         8,4, "Rhodium",     Metcolor,         0.258,wx.Colour(10,125,140)),
    (["Pd","Pd+2","Pd+4"],         9,4, "Palladium",   Metcolor,         0.270,wx.Colour(0,105,133)),
    (["Ag","Ag+1","Ag+2"],        10,4, "Silver",      Metcolor,         0.285,wx.Colour(192,192,192)),
    (["Cd","Cd+2"],               11,4, "Cadmium",     Metcolor,         0.300,wx.Colour(255,217,143)),
    (["In","In+3"],               12,4, "Indium",      SemMetcolor,      0.318,wx.Colour(166,117,115)),
    (["Sn","Sn+2","Sn+4"],        13,4, "Tin",         SemMetcolor,      0.330,wx.Colour(102,128,128)),
    (["Sb","Sb+3","Sb+5"],        14,4, "Antimony",    SemMetcolor,      0.348,wx.Colour(158,99,181)),
    (["Te",],                     15,4, "Tellurium",   NonMetcolor,      0.363,wx.Colour(212,122,0)),
    (["I","I-1"],                 16,4, "Iodine",      NonMetcolor,      0.384,wx.Colour(148,0,148)),
    (["Xe",],                     17,4, "Xenon",       Noblecolor,       0.396,wx.Colour(66,158,176)),
    (["Cs","Cs+1"],                0,5, "Caesium",     Alkcolor,         0.414,wx.Colour(87,23,143)),
    (["Ba","Ba+2"],                1,5, "Barium",      AlkEcolor,        0.438,wx.Colour(0,201,0)),
    (["La","La+3"],                2,5, "Lanthanium",  Metcolor,         0.456,wx.Colour(112,212,255)),
    (["Ce","Ce+3","Ce+4"],     3.5,6.5, "Cerium",      REcolor,          0.474,wx.Colour(255,255,199)),
    (["Pr","Pr+3","Pr+4"],     4.5,6.5, "Praseodymium",REcolor,          0.492,wx.Colour(217,255,199)),
    (["Nd","Nd+3"],            5.5,6.5, "Neodymium",   REcolor,          0.516,wx.Colour(199,255,199)),
    (["Pm","Pm+3"],            6.5,6.5, "Promethium",  REcolor,          0.534,wx.Colour(163,255,199)),
    (["Sm","Sm+3"],            7.5,6.5, "Samarium",    REcolor,          0.558,wx.Colour(143,255,199)),
    (["Eu","Eu+2","Eu+3"],     8.5,6.5, "Europium",    REcolor,          0.582,wx.Colour(97,255,199)),
    (["Gd","Gd+3"],            9.5,6.5, "Gadolinium",  REcolor,          0.610,wx.Colour(69,255,199)),
    (["Tb","Tb+3"],           10.5,6.5, "Terbium",     REcolor,          0.624,wx.Colour(48,255,199)),
    (["Dy","Dy+3"],           11.5,6.5, "Dysprosium",  REcolor,          0.648,wx.Colour(31,255,199)),
    (["Ho","Ho+3"],           12.5,6.5, "Holmium",     REcolor,          0.672,wx.Colour(0,255,156)),
    (["Er","Er+3"],           13.5,6.5, "Erbium",      REcolor,          0.696,wx.Colour(0,230,117)),
    (["Tm","Tm+3"],           14.5,6.5, "Thulium",     REcolor,          0.723,wx.Colour(0,212,82)),
    (["Yb","Yb+2","Yb+3"],    15.5,6.5, "Ytterbium",   REcolor,          0.750,wx.Colour(0,191,56)),
    (["Lu","Lu+3"],           16.5,6.5, "Lutetium",    REcolor,          0.780,wx.Colour(0,171,36)),
    (["Hf","Hf+4"],                3,5, "Hafnium",     Metcolor,         0.804,wx.Colour(77,194,255)),
    (["Ta","Ta+5"],                4,5, "Tantalum",    Metcolor,         0.834,wx.Colour(77,166,255)),
    (["W","W+6"],                  5,5, "Tungsten",    Metcolor,         0.864,wx.Colour(33,148,214)),
    (["Re",],                      6,5, "Rhenium",     Metcolor,         0.900,wx.Colour(38,125,171)),
    (["Os","Os+4"],                7,5, "Osmium",      Metcolor,         0.919,wx.Colour(38,102,150)),
    (["Ir","Ir+3","Ir+4"],         8,5, "Iridium",     Metcolor,         0.948,wx.Colour(23,84,135)),
    (["Pt","Pt+2","Pt+4"],         9,5, "Platinium",   Metcolor,         0.984,wx.Colour(208,208,224)),
    (["Au","Au+1","Au+3"],        10,5, "Gold",        Metcolor,         1.014,wx.Colour(255,209,35)),
    (["Hg","Hg+1","Hg+2"],        11,5, "Mercury",     Metcolor,         1.046,wx.Colour(184,184,208)),
    (["Tl","Tl+1","Tl+3"],        12,5, "Thallium",    SemMetcolor,      1.080,wx.Colour(166,84,77)),
    (["Pb","Pb+2","Pb+4"],        13,5, "Lead",        SemMetcolor,      1.116,wx.Colour(87,89,97)),
    (["Bi","Bi+3","Bi+5"],        14,5, "Bismuth",     SemMetcolor,      1.149,wx.Colour(158,79,181)),
    (["Po",],                     15,5, "Polonium",    SemMetcolor,      1.189,wx.Colour(171,92,0)),
    (["At",],                     16,5, "Astatine",    NonMetcolor,      1.224,wx.Colour(117,79,69)),
    (["Rn",],                     17,5, "Radon",       Noblecolor,       1.260,wx.Colour(66,130,150)),
    (["Fr",],                      0,6, "Francium",    Alkcolor,         1.296,wx.Colour(66,0,102)),
    (["Ra","Ra+2"],                1,6, "Radium",      AlkEcolor,        1.332,wx.Colour(0,125,0)),
    (["Ac","Ac+3"],                2,6, "Actinium",    Metcolor,         1.374,wx.Colour(112,171,250)),
    (["Th","Th+4"],            3.5,7.5, "Thorium",     REcolor,          1.416,wx.Colour(0,186,255)),
    (["Pa",],                  4.5,7.5, "Protactinium",REcolor,          1.458,wx.Colour(0,161,255)),
    (["U","U+3","U+4","U+6"],  5.5,7.5, "Uranium",     REcolor,          1.470,wx.Colour(0,143,255)),
    (["Np","Np+3","Np+4","Np+6"], 6.5,7.5, "Neptunium",   REcolor,       1.536,wx.Colour(0,128,255)),
    (["Pu","Pu+3","Pu+4","Pu+6"], 7.5,7.5, "Plutonium",   REcolor,       1.584,wx.Colour(0,107,255)),
    (["Am",],                  8.5,7.5, "Americium",   REcolor,          1.626,wx.Colour(84,92,242)),
    (["Cm",],                  9.5,7.5, "Curium",      REcolor,          1.669,wx.Colour(120,92,227)),
    (["Bk",],                 10.5,7.5, "Berkelium",   REcolor,          1.716,wx.Colour(138,79,227)),
    (["Cf",],                 11.5,7.5, "Californium", REcolor,          1.764,wx.Colour(161,54,212)),
    (["Q","QA","QB","QC","QD"],  14.5,7.5, "Special form factor", REcolor,  0.000,wx.Colour(161,54,212)),
    ]
