# =====================================================================
# 📐 REAL BITCOIN SECP256K1 CURVE PARAMETERS & ACCELERATED MATH
# =====================================================================
P_curve = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N_order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FB17B448A68554199C47D08FFB10D4B8
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
    return (P[0], (-P[1]) % p)

# =====================================================================
# 🚀 THE DETERMINISTIC BSGS SOLVER
# =====================================================================
def solve_puzzle_bsgs(Target_Point, range_start, range_end):
    # Total search size: 65536 - 32768 = 32768 keys
    H = range_end - range_start
    m = int(32768**0.5) + 1  # Matrix step size (~182 steps)
    
    print(f"🐾 Calculating {m} Baby Steps...")
    # Shift target to account for range offset: Target - (range_start * G)
    start_point = ec_mul(range_start, G)
    shifted_target = ec_add(Target_Point, ec_neg(start_point))
    
    # 1. Compute and store Baby Steps (j * G)
    baby_steps = {}
    current_baby = None  # 0 * G (Identity)
    
    for j in range(m):
        if current_baby is not None:
            # We map X-coordinate to the scalar j for ultra-fast lookup
            baby_steps[current_baby[0]] = (j, current_baby[1])
        current_baby = ec_add(current_baby, G)

    # 2. Compute Giant Step multiplier (m * G)
    mG = ec_mul(m, G)
    neg_mG = ec_neg(mG)
    
    print(f"🚀 Scanning {m} Giant Steps...")
    giant_step_point = shifted_target
    
    # 3. Search for collisions
    for i in range(m):
        if giant_step_point is not None and giant_step_point[0] in baby_steps:
            j, baby_y = baby_steps[giant_step_point[0]]
            
            # Check Y-parity to ensure it's not a negated point collision
            if giant_step_point[1] == baby_y:
                resolved_key = range_start + (i * m) + j
                return resolved_key
            else:
                # If Y is negated, the key is resolved symmetrically
                resolved_key = range_start + (i * m) - j
                return resolved_key
                
        giant_step_point = ec_add(giant_step_point, neg_mG)
        
    return None

# =====================================================================
# 🎬 TARGET EXECUTION
# =====================================================================
search_min = 32768
search_max = 65536
target_x = 0x5de1223b435c191c1b586a9f6545450a7c0a6973605e9ef02da503c5db22f365

# Recover valid Y coordinate for secp256k1 (y^2 = x^3 + 7)
y_squared = (pow(target_x, 3, P_curve) + 7) % P_curve
target_y = pow(y_squared, (P_curve + 1) // 4, P_curve)

Target_Point = (target_x, target_y)

print(f"--- SECP256K1 2^16 DETERMINISTIC ENGINE ---")
print(f"Target Public Key X: {hex(target_x)}")
print(f"Target Public Key Y: {hex(target_y)}\n")

private_key = solve_puzzle_bsgs(Target_Point, search_min, search_max)

if private_key:
    print(f"\n🎯 TARGET CRACKED SUCCESSFULLY!")
    print(f"🔑 Discovered Private Key (Decimal): {private_key}")
    print(f"🔑 Discovered Private Key (Hex):     {hex(private_key)}")
else:
    print("\n❌ Key not found in this segment. Double check if the key falls strictly between 32768 and 65536.")
