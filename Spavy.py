import random

# =====================================================================
# 📐 REAL BITCOIN SECP256K1 CURVE PARAMETERS
# =====================================================================
A_curve = 0
B_curve = 7
P_curve = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N_order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# Base Point G coordinates
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G_affine = (Gx, Gy)

# Montgomery Setup for 256-bit parameters: R = 2^256
R_bits = 256
R = 1 << R_bits
R_mask = R - 1

# Precomputed P_prime such that: (R * R_inv) - (P_curve * P_prime) = 1
# This replaces standard division with bit shifts during reduction
P_prime = 0xee406143f331f35f8d9b80f1d39b82142da70ee7b35123d531efcb2a64700001

# =====================================================================
# ⚡ LAYER 1: MONTGOMERY BITWISE ARITHMETIC
# =====================================================================
def mont_red(T):
    """Computes (T / R) mod P_curve using bit-shifts and masks (No Modulo Division)."""
    m = ((T & R_mask) * P_prime) & R_mask
    t = (T + m * P_curve) >> R_bits
    return t - P_curve if t >= P_curve else t

def to_mont(x): return (x << R_bits) % P_curve
def from_mont(x_bar): return mont_red(x_bar)

def mont_mul(a_bar, b_bar): return mont_red(a_bar * b_bar)
def mont_add(a_bar, b_bar): return (a_bar + b_bar) % P_curve
def mont_sub(a_bar, b_bar): return (a_bar - b_bar + P_curve) % P_curve

# Precomputing small numeric values into Montgomery form to speed up Jacobian formulas
MONT_2 = to_mont(2)
MONT_3 = to_mont(3)
MONT_4 = to_mont(4)
MONT_8 = to_mont(8)

# =====================================================================
# 📐 LAYER 2: JACOBIAN PROJECTIVE MATH ON SECP256K1
# =====================================================================
def to_jacobian(pt_affine):
    if pt_affine is None: return (0, 0, 0)
    return (to_mont(pt_affine[0]), to_mont(pt_affine[1]), to_mont(1))

def to_affine(pt_jac):
    """Converts a Jacobian point back to standard coordinates."""
    X, Y, Z = pt_jac
    if Z == 0: return None
    
    # Run a traditional modular inverse ONLY when extracting the final points
    z_inv = pow(from_mont(Z), P_curve - 2, P_curve)
    z_inv_bar = to_mont(z_inv)
    
    z_inv2 = mont_mul(z_inv_bar, z_inv_bar)
    z_inv3 = mont_mul(z_inv2, z_inv_bar)
    
    return (from_mont(mont_mul(X, z_inv2)), from_mont(mont_mul(Y, z_inv3)))

def jac_add(P, Q):
    """Adds two Jacobian points using ONLY Montgomery multiplication."""
    if P == (0, 0, 0): return Q
    if Q == (0, 0, 0): return P
    
    X1, Y1, Z1 = P
    X2, Y2, Z2 = Q
    
    Z1_sq = mont_mul(Z1, Z1)
    Z2_sq = mont_mul(Z2, Z2)
    
    U1 = mont_mul(X1, Z2_sq)
    U2 = mont_mul(X2, Z1_sq)
    
    S1 = mont_mul(mont_mul(Y1, Z2), Z2_sq)
    S2 = mont_mul(mont_mul(Y2, Z1), Z1_sq)
    
    if U1 == U2:
        if S1 != S2: return (0, 0, 0)
        return jac_double(P)
        
    H = mont_sub(U2, U1)
    R_slope = mont_sub(S2, S1)
    
    H_sq = mont_mul(H, H)
    H_cub = mont_mul(H_sq, H)
    
    X3 = mont_sub(mont_sub(mont_mul(R_slope, R_slope), H_cub), mont_mul(MONT_2, mont_mul(U1, H_sq)))
    Y3 = mont_sub(mont_mul(R_slope, mont_sub(mont_mul(U1, H_sq), X3)), mont_mul(S1, H_cub))
    Z3 = mont_mul(mont_mul(H, Z1), Z2)
    
    return (X3, Y3, Z3)

def jac_double(P):
    """Doubles a Jacobian point using ONLY Montgomery multiplication."""
    X, Y, Z = P
    if Y == 0 or P == (0, 0, 0): return (0, 0, 0)
    
    Y_sq = mont_mul(Y, Y)
    S = mont_mul(MONT_4, mont_mul(X, Y_sq))
    
    # secp256k1 has A=0, so the curve formula drops from (3X^2 + A*Z^4) down to just (3X^2)
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
# 🦘 LAYER 3: KANGAROO CRACK ENGINE FOR A 2^16 BOUNDARY
# =====================================================================
def solve_2_16_puzzle(Target_Jac, lower_bound, upper_bound):
    # Setting up 8 jump point sizes (Powers of 2 scale effectively)
    k = 8
    jump_distances = [2**i for i in range(k)]
    
    G_jac = to_jacobian(G_affine)
    jump_points_jac = [jac_mul(d, G_jac) for d in jump_distances]
    
    # Map points to jumps deterministically based on raw X coordinate
    def get_jump_idx(pt_jac):
        return pt_jac[0] % k 

    # A point is Distinguished if its Montgomery X representation ends with 000 in binary
    def is_distinguished(pt_jac):
        return (pt_jac[0] & 0x7) == 0

    # 🐾 THE TAME KANGAROO (Sets the traps)
    tame_start = (lower_bound + upper_bound) // 2
    tame_pos = jac_mul(tame_start, G_jac)
    tame_distance = 0
    tame_db = {}  # { Affine_X: Tame_Distance }

    print("🦘 Tame Kangaroo setting traps across the 2^16 space...")
    # Theoretical loop iteration limit for 2^16 space is roughly 4 * sqrt(2^16) = 1024
    for _ in range(4000):
        if is_distinguished(tame_pos):
            aff = to_affine(tame_pos)
            if aff:
                tame_db[aff[0]] = tame_distance
            
        idx = get_jump_idx(tame_pos)
        tame_pos = jac_add(tame_pos, jump_points_jac[idx])
        tame_distance += jump_distances[idx]

    # 🐾 THE WILD KANGAROO (Hunts the target)
    wild_pos = Target_Jac
    wild_distance = 0

    print("🦘 Wild Kangaroo released from the target public key...")
    for _ in range(4000):
        if is_distinguished(wild_pos):
            aff = to_affine(wild_pos)
            if aff and (aff[0] in tame_db):
                print("🎯 COLLISION DETECTED AT A TRACTION POINT!")
                tame_dist_at_collision = tame_db[aff[0]]
                
                # Math resolution
                secret_key = (tame_start + tame_dist_at_collision - wild_distance) % N_order
                return secret_key
                
        idx = get_jump_idx(wild_pos)
        wild_pos = jac_add(wild_pos, jump_points_jac[idx])
        wild_distance += jump_distances[idx]

    return None

# =====================================================================
# 🎬 SIMULATION TEST RUN
# =====================================================================
# Define a 2^16 target interval boundaries (Example: puzzle range 16)
search_min = 2**15          # 32,768
search_max = 2**16          # 65,536

# Generate a random test secret key safely within this 2^16 segment
HIDDEN_PRIVATE_KEY = random.randint(search_min + 10, search_max - 10)

# Derive the real secp256k1 public key
G_jacobian = to_jacobian(G_affine)
Exposed_Public_Key_Jac = jac_mul(HIDDEN_PRIVATE_KEY, G_jacobian)
Public_Key_Affine = to_affine(Exposed_Public_Key_Jac)

print(f"--- SECP256K1 2^16 SOLVER ENGINE ---")
print(f"Exposed Public Key X-Coord (Hex): {hex(Public_Key_Affine[0])}")
print(f"Searching space from {search_min} to {search_max}...\n")

discovered_key = solve_2_16_puzzle(Exposed_Public_Key_Jac, search_min, search_max)

if discovered_key:
    print(f"\n✅ SUCCESS!")
    print(f"Discovered Private Key (Decimal): {discovered_key}")
    print(f"Discovered Private Key (Hex):     {hex(discovered_key)}")
    print(f"Matches Hidden Key?               {discovered_key == HIDDEN_PRIVATE_KEY}")
else:
    print("\n❌ Path paths missed. Rerun to adjust the distinguished density parameters.")
