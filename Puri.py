# =====================================================================
# 📐 REAL BITCOIN SECP256K1 CURVE PARAMETERS & ACCELERATED MATH
# =====================================================================
P_curve = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N_order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G = (Gx, Gy)

def ec_inv(n, p=P_curve):
    return pow(n, p - 2, p)

def ec_add(P, Q, p=P_curve):
    if P is None: return Q
    if Q is None: return P
    if P == Q: return ec_double(P, p)
    x1, y1 = P; x2, y2 = Q
    if x1 == x2: return None
    slope = ((y2 - y1) * ec_inv(x2 - x1, p)) % p
    x3 = (slope**2 - x1 - x2) % p
    y3 = (slope * (x1 - x3) - y1) % p
    return (x3, y3)

def ec_double(P, p=P_curve):
    if P is None: return None
    x, y = P
    if y == 0: return None
    slope = ((3 * x**2) * ec_inv(2 * y, p)) % p
    x3 = (slope**2 - 2 * x) % p
    y3 = (slope * (x - x3) - y) % p
    return (x3, y3)

def ec_mul(k, P, p=P_curve):
    R = None
    while k > 0:
        if k & 1: R = ec_add(R, P, p)
        P = ec_double(P, p)
        k >>= 1
    return R

def ec_neg(P, p=P_curve):
    if P is None: return None
    x, y = P
    # FIX 1: Correctly unpack the coordinate tuple and invert the Y-axis value
    return (x, (-y) % p)

# =====================================================================
# 🚀 BOTH-SIGN MATRIX BSGS ENGINE
# =====================================================================
def solve_puzzle_bsgs_5(Target_Point, range_start, range_end):
    H = range_end - range_start
    m = int(H**0.5) + 1  
    
    print(f"🐾 Pre-calculating {m} Baby Steps...")
    start_point = ec_mul(range_start, G)
    shifted_target = ec_add(Target_Point, ec_neg(start_point))
    
    baby_steps_x = {}
    current_baby = None  # Starts at identity point (None)
    
    for j in range(m):
        # FIX 2: Safely handle None state before indexing coordinate dictionary
        if current_baby is not None:
            baby_steps_x[current_baby[0]] = (j, current_baby)
        else:
            baby_steps_x['INF'] = (j, None)
        current_baby = ec_add(current_baby, G)

    mG = ec_mul(m, G)
    neg_mG = ec_neg(mG)
    
    print(f"🚀 Processing Giant Steps grid overlay...")
    giant_step_point = shifted_target
    
    for i in range(m):
        if giant_step_point is not None and giant_step_point[0] in baby_steps_x:
            j, baby_point = baby_steps_x[giant_step_point[0]]
            
            if baby_point is not None:
                if giant_step_point == baby_point:
                    return range_start + (i * m) + j
                else:
                    return range_start + (i * m) - j
                
        giant_step_point = ec_add(giant_step_point, neg_mG)
        
    return None

# =====================================================================
# 🎬 EXECUTION ON AN EXACT PUZZLE #5 POINT
# =====================================================================
search_min = 16  # 2^4
search_max = 32  # 2^5

# Simulated target private key strictly inside the Puzzle 5 space
REAL_PUZZLE_5_SECRET = 27 

# Compute target public coordinates
Target_Point = ec_mul(REAL_PUZZLE_5_SECRET, G)

print(f"--- SECP256K1 2^5 DETERMINISTIC ENGINE ---")
print(f"Target Public Key X: {hex(Target_Point[0])}")
print(f"Target Public Key Y: {hex(Target_Point[1])}\n")

private_key = solve_puzzle_bsgs_5(Target_Point, search_min, search_max)

if private_key:
    print(f"\n🎯 TARGET CRACKED SUCCESSFULLY!")
    print(f"🔑 Discovered Private Key (Decimal): {private_key}")
    print(f"🔑 Discovered Private Key (Hex):     {hex(private_key)}")
else:
    print("\n❌ Key not found inside the specified 2^5 range bounds.")
