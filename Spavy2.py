# =====================================================================
# 📐 REAL BITCOIN SECP256K1 CURVE PARAMETERS
# =====================================================================
P_curve = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N_order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# Base Point G
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G_affine = (Gx, Gy)

# Montgomery Constants (R = 2^256)
R_bits = 256
R = 1 << R_bits
R_mask = R - 1
P_prime = 0xee406143f331f35f8d9b80f1d39b82142da70ee7b35123d531efcb2a64700001

# =====================================================================
# ⚡ LAYER 1: MONTGOMERY BITWISE ARITHMETIC
# =====================================================================
def mont_red(T):
    m = ((T & R_mask) * P_prime) & R_mask
    t = (T + m * P_curve) >> R_bits
    return t - P_curve if t >= P_curve else t

def to_mont(x): return (x << R_bits) % P_curve
def from_mont(x_bar): return mont_red(x_bar)
def mont_mul(a_bar, b_bar): return mont_red(a_bar * b_bar)
def mont_add(a_bar, b_bar): return (a_bar + b_bar) % P_curve
def mont_sub(a_bar, b_bar): return (a_bar - b_bar + P_curve) % P_curve

MONT_2, MONT_3, MONT_4, MONT_8 = to_mont(2), to_mont(3), to_mont(4), to_mont(8)

# =====================================================================
# 📐 LAYER 2: JACOBIAN PROJECTIVE MATH
# =====================================================================
def to_jacobian(pt_affine):
    if pt_affine is None: return (0, 0, 0)
    return (to_mont(pt_affine[0]), to_mont(pt_affine[1]), to_mont(1))

def to_affine(pt_jac):
    X, Y, Z = pt_jac
    if Z == 0: return None
    z_inv = pow(from_mont(Z), P_curve - 2, P_curve)
    z_inv_bar = to_mont(z_inv)
    z_inv2 = mont_mul(z_inv_bar, z_inv_bar)
    z_inv3 = mont_mul(z_inv2, z_inv_bar)
    return (from_mont(mont_mul(X, z_inv2)), from_mont(mont_mul(Y, z_inv3)))

def jac_add(P, Q):
    if P == (0, 0, 0): return Q
    if Q == (0, 0, 0): return P
    X1, Y1, Z1 = P
    X2, Y2, Z2 = Q
    Z1_sq, Z2_sq = mont_mul(Z1, Z1), mont_mul(Z2, Z2)
    U1, U2 = mont_mul(X1, Z2_sq), mont_mul(X2, Z1_sq)
    S1 = mont_mul(mont_mul(Y1, Z2), Z2_sq)
    S2 = mont_mul(mont_mul(Y2, Z1), Z1_sq)
    if U1 == U2:
        if S1 != S2: return (0, 0, 0)
        return jac_double(P)
    H, R_slope = mont_sub(U2, U1), mont_sub(S2, S1)
    H_sq = mont_mul(H, H)
    H_cub = mont_mul(H_sq, H)
    X3 = mont_sub(mont_sub(mont_mul(R_slope, R_slope), H_cub), mont_mul(MONT_2, mont_mul(U1, H_sq)))
    Y3 = mont_sub(mont_mul(R_slope, mont_sub(mont_mul(U1, H_sq), X3)), mont_mul(S1, H_cub))
    Z3 = mont_mul(mont_mul(H, Z1), Z2)
    return (X3, Y3, Z3)

def jac_double(P):
    X, Y, Z = P
    if Y == 0 or P == (0, 0, 0): return (0, 0, 0)
    Y_sq = mont_mul(Y, Y)
    S = mont_mul(MONT_4, mont_mul(X, Y_sq))
    M = mont_mul(MONT_3, mont_mul(X, X))
    X3 = mont_sub(mont_mul(M, M), mont_mul(MONT_2, S))
    Y3 = mont_sub(mont_mul(M, mont_sub(S, X3)), mont_mul(MONT_8, mont_mul(Y_sq, Y_sq)))
    Z3 = mont_mul(MONT_2, mont_mul(Y, Z))
    return (X3, Y3, Z3)

def jac_mul(scalar, P):
    R_pt = (0, 0, 0)
    base = P
    while scalar > 0:
        if scalar & 1: R_pt = jac_add(R_pt, base)
        base = jac_double(base)
        scalar >>= 1
    return R_pt

# =====================================================================
# 🦘 LAYER 3: OPTIMIZED KANGAROO SEARCH ENGINE
# =====================================================================
def solve_target_public_key(Target_Jac, lower_bound, upper_bound):
    # Reduced jump parameters better suited for a 2^16 size range
    k = 4
    jump_distances = [1, 2, 4, 8]
    
    G_jac = to_jacobian(G_affine)
    jump_points_jac = [jac_mul(d, G_jac) for d in jump_distances]
    
    def get_jump_idx(pt_jac):
        # Deterministic slice using the Jacobian X coordinate array string
        return pt_jac[0] % k 

    def is_distinguished(pt_jac):
        # Slightly higher density matching our increased loop threshold
        return (pt_jac[0] & 0x3) == 0

    # 🐾 THE TAME KANGAROO
    tame_start = (lower_bound + upper_bound) // 2
    tame_pos = jac_mul(tame_start, G_jac)
    tame_distance = 0
    tame_db = {}

    print("🦘 Tame Kangaroo setting traps across the 2^16 space...")
    for _ in range(8000):  # Expanded step ceiling to avoid gaps
        if is_distinguished(tame_pos):
            aff = to_affine(tame_pos)
            if aff:
                tame_db[aff] = tame_distance
            
        idx = get_jump_idx(tame_pos)
        tame_pos = jac_add(tame_pos, jump_points_jac[idx])
        tame_distance += jump_distances[idx]

    # 🐾 THE WILD KANGAROO
    wild_pos = Target_Jac
    wild_distance = 0

    print("🦘 Wild Kangaroo released from the target public key...")
    for _ in range(8000):
        if is_distinguished(wild_pos):
            aff = to_affine(wild_pos)
            if aff and (aff in tame_db):
                print("\n🎯 COLLISION DETECTED AT A DISTINGUISHED POINT!")
                tame_dist_at_collision = tame_db[aff]
                
                # Extract Private Key: Secret = Tame_Start + Tame_Distance - Wild_Distance
                secret_key = (tame_start + tame_dist_at_collision - wild_distance) % N_order
                return secret_key
                
        idx = get_jump_idx(wild_pos)
        wild_pos = jac_add(wild_pos, jump_points_jac[idx])
        wild_distance += jump_distances[idx]

    return None

# =====================================================================
# 🎬 TARGET RUN (YOUR SPECIFIC EXPOSED PUBLIC KEY)
# =====================================================================
search_min = 32768
search_max = 65536

# Your target public key X coordinate from your puzzle framework
target_x = 0x5de1223b435c191c1b586a9f6545450a7c0a6973605e9ef02da503c5db22f365

# To run an EC point walk, we must compute the matching Y coordinate for secp256k1
# y^2 = x^3 + 7 (mod P_curve)
y_squared = (pow(target_x, 3, P_curve) + 7) % P_curve
target_y = pow(y_squared, (P_curve + 1) // 4, P_curve) # Modular square root

Target_Affine = (target_x, target_y)
Target_Jacobian = to_jacobian(Target_Affine)

print(f"--- SECP256K1 2^16 SOLVER ENGINE ---")
print(f"Exposed Public Key X-Coord (Hex): {hex(target_x)}")
print(f"Searching space from {search_min} to {search_max}...\n")

discovered_key = solve_target_public_key(Target_Jacobian, search_min, search_max)

if discovered_key:
    print(f"🔑 SUCCESS! Discovered Private Key (Decimal): {discovered_key}")
    print(f"🔑 Discovered Private Key (Hex):             {hex(discovered_key)}")
else:
    print("\n❌ Path missed again. Adjusting jump metrics required.")
